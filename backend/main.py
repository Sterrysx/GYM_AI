import sqlite3
import json
import os
import glob
from datetime import date, datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from weekly_coach import run_weekly_update

app = FastAPI()
DB_NAME = "gym.db"

# ── Data Lake paths ──────────────────────────────────────────────────────────
# Resolve relative to this file's parent → project root → /data
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WORKOUTS_DIR = DATA_DIR / "workouts"
METRICS_DIR = DATA_DIR / "metrics"
BODY_COMP_CSV = METRICS_DIR / "body_composition.csv"

# Ensure dirs exist on startup
WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

# Allow the Vite dev server to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models (Validation)
class LogSet(BaseModel):
    week_id: int
    day: int
    exercise: str
    actual_weight: List[float] # Expected as [22, 22, 20]
    actual_reps: List[int]     # Expected as [10, 8, 8]
    rpe: Optional[int] = None

@app.get("/stats")
def get_stats():
    """
    Returns dashboard data: bench cycle progress and per-day completion for the current week.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0] or 1

    cursor.execute("SELECT value FROM user_stats WHERE key='current_bench_cycle_week'")
    row = cursor.fetchone()
    bench_cycle_week = int(row[0]) if row else 1

    cursor.execute("SELECT value FROM user_stats WHERE key='bench_1rm'")
    row = cursor.fetchone()
    bench_1rm = float(row[0]) if row else 90.0

    cycle_map = {
        1: (5, "5", 0.75, "Strength"),
        2: (4, "4", 0.82, "Strength+"),
        3: (3, "3", 0.88, "Heavy"),
        4: (2, "2", 0.92, "Peak"),
        5: (3, "5", 0.60, "Deload"),
        6: (1, "1", 1.02, "PR Test"),
    }
    c_sets, c_reps, c_int, c_label = cycle_map.get(bench_cycle_week, (5, "5", 0.75, "Strength"))
    bench_weight = round(bench_1rm * c_int / 2.5) * 2.5

    # Per-day completion (non-static only)
    day_names = {1: "Push", 2: "Pull", 3: "Lower", 4: "Chest & Back", 5: "Arms"}
    day_completion = []
    for d in range(1, 6):
        cursor.execute(
            "SELECT COUNT(DISTINCT exercise) FROM workout_plan WHERE week_id=? AND day=? AND strategy != 'static'",
            (current_week, d)
        )
        planned = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT wl.exercise)
            FROM workout_logs wl
            INNER JOIN workout_plan wp
                ON wl.exercise = wp.exercise AND wl.week_id = wp.week_id
            WHERE wl.week_id = ? AND wp.day = ? AND wp.strategy != 'static'
        """, (current_week, d))
        logged = cursor.fetchone()[0]

        day_completion.append({
            "day": d,
            "name": day_names[d],
            "planned": planned,
            "logged": logged,
        })

    conn.close()

    return {
        "current_week": current_week,
        "bench_cycle_week": bench_cycle_week,
        "bench_1rm": bench_1rm,
        "bench_session": {
            "sets": c_sets,
            "reps": c_reps,
            "weight": bench_weight,
            "intensity_pct": round(c_int * 100),
            "label": c_label,
        },
        "day_completion": day_completion,
    }


@app.get("/workout/{day_id}")
def get_workout(day_id: int):
    """
    Fetches the plan for a specific day (e.g., Day 1).
    Parses the JSON strings back into Arrays for the phone.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    cursor = conn.cursor()
    
    # Get the latest active week
    # (In a real scenario, you might track current_week in user_stats)
    # For now, we grab the highest week_id found in the plan
    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    
    if not current_week:
        return {"error": "No workout plan found. Run init_db.py!"}

    # Fetch exercises for that Day & Week
    cursor.execute('''
        SELECT exercise, sets, target_reps, target_weight_json, superset_group, strategy, rounding 
        FROM workout_plan 
        WHERE week_id = ? AND day = ? 
        ORDER BY exercise_order
    ''', (current_week, day_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    workout_data = []
    for row in rows:
        # Convert DB Row to Dictionary
        item = dict(row)
        # Parse the JSON string back to a list: "[22, 19.5]" -> [22, 19.5]
        item["target_weights"] = json.loads(item["target_weight_json"])
        del item["target_weight_json"] # Clean up
        workout_data.append(item)
        
    return {"week": current_week, "day": day_id, "exercises": workout_data}

@app.post("/log")
def log_workout(log: LogSet):
    """
    Receives the results from the phone and saves them to SQLite.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Convert lists back to JSON strings for storage
    weights_json = json.dumps(log.actual_weight)
    reps_json = json.dumps(log.actual_reps)
    
    cursor.execute('''
        INSERT INTO workout_logs (date, week_id, day, exercise, actual_weight_json, actual_reps_json, rpe)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
    ''', (log.week_id, log.day, log.exercise, weights_json, reps_json, log.rpe))
    
    conn.commit()
    conn.close()
    return {"status": "Saved", "exercise": log.exercise}


# ── Data-Lake: complete-day dump ─────────────────────────────────────────────

@app.post("/complete-day")
def complete_day(week_id: int, day: int):
    """
    Dumps the full performance for a completed day into the data lake as
    /data/workouts/YYYY-MM-DD_DayX.json.
    Call this after the last exercise for the day is logged.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Gather all logs for this week+day
    cursor.execute("""
        SELECT wl.exercise, wl.actual_weight_json, wl.actual_reps_json, wl.rpe,
               wp.sets, wp.target_reps, wp.strategy
        FROM workout_logs wl
        INNER JOIN workout_plan wp
            ON wl.exercise = wp.exercise AND wl.week_id = wp.week_id AND wp.day = ?
        WHERE wl.week_id = ?
        ORDER BY wp.exercise_order
    """, (day, week_id))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No logs found for Week {week_id} Day {day}.")

    today = date.today().isoformat()
    exercises = []
    seen = set()
    for r in rows:
        name = r["exercise"]
        if name in seen:
            continue
        seen.add(name)
        exercises.append({
            "exercise": name,
            "strategy": r["strategy"],
            "planned_sets": r["sets"],
            "planned_reps": r["target_reps"],
            "actual_weight": json.loads(r["actual_weight_json"]),
            "actual_reps": json.loads(r["actual_reps_json"]),
            "rpe": r["rpe"],
        })

    payload = {
        "date": today,
        "week_id": week_id,
        "day": day,
        "exercises": exercises,
    }

    filename = f"{today}_Day{day}.json"
    filepath = WORKOUTS_DIR / filename
    filepath.write_text(json.dumps(payload, indent=2))

    return {"status": "dumped", "file": str(filepath.relative_to(PROJECT_ROOT))}


@app.post("/generate-next-week")
def generate_next_week():
    """
    Exports the current week's data and generates the next week's plan.
    Safety: refuses to run if the user hasn't logged all non-static exercises.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Determine current week
    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]

    if not current_week:
        conn.close()
        raise HTTPException(status_code=400, detail="No workout plan found. Run init_db.py!")

    # 2. Count planned non-static exercises for the current week
    cursor.execute("""
        SELECT COUNT(DISTINCT exercise) FROM workout_plan
        WHERE week_id = ? AND strategy != 'static'
    """, (current_week,))
    planned_count = cursor.fetchone()[0]

    # 3. Count unique exercises that have at least one log entry this week
    cursor.execute("""
        SELECT COUNT(DISTINCT wl.exercise)
        FROM workout_logs wl
        INNER JOIN workout_plan wp
            ON wl.exercise = wp.exercise AND wl.week_id = wp.week_id
        WHERE wl.week_id = ? AND wp.strategy != 'static'
    """, (current_week,))
    logged_count = cursor.fetchone()[0]

    conn.close()

    # 4. Block if incomplete
    if logged_count < planned_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate next week. Week {current_week} is not fully logged. "
                   f"({logged_count}/{planned_count} exercises logged)"
        )

    # 5. All clear — run the update
    try:
        run_weekly_update()
        return {"status": "success", "message": "Next week generated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard: Volume chart (reads from data lake) ──────────────────────────

@app.get("/dashboard/volume")
def dashboard_volume():
    """
    Reads every JSON file in /data/workouts/ and returns a per-day volume
    summary (total sets, total reps, total tonnage) for Recharts consumption.
    """
    files = sorted(WORKOUTS_DIR.glob("*.json"))
    series = []
    for f in files:
        try:
            doc = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        total_sets = 0
        total_reps = 0
        total_tonnage = 0.0
        for ex in doc.get("exercises", []):
            weights = ex.get("actual_weight", [])
            reps = ex.get("actual_reps", [])
            total_sets += len(reps)
            total_reps += sum(reps)
            total_tonnage += sum(w * r for w, r in zip(weights, reps))
        series.append({
            "date": doc.get("date"),
            "week": doc.get("week_id"),
            "day": doc.get("day"),
            "sets": total_sets,
            "reps": total_reps,
            "tonnage_kg": round(total_tonnage, 1),
        })
    return {"volume": series}


@app.get("/dashboard/metrics")
def dashboard_metrics():
    """
    Reads /data/metrics/body_composition.csv via pandas and returns ALL columns
    as a JSON array of records for the frontend Dashboard.
    """
    import pandas as pd

    if not BODY_COMP_CSV.exists():
        return {"data": []}

    try:
        df = pd.read_csv(BODY_COMP_CSV)
        return {"data": df.to_dict(orient="records")}
    except Exception:
        return {"data": []}


def _safe_float(val):
    """Convert a string to float or return None."""
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    import uvicorn
    # This is for testing locally. In production, Systemd handles this.
    uvicorn.run(app, host="0.0.0.0", port=8000)
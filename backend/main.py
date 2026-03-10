import sqlite3
import json
import csv
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Any
from uuid import uuid4

import pandas as pd
import requests as http_requests
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Internal logic
from weekly_coach import run_weekly_update

app = FastAPI()
DB_NAME = "gym.db"

# ── LLM config ──────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
CHAT_MODEL = "qwen2.5:32b"

# ── Data Lake paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WORKOUTS_DIR = DATA_DIR / "workouts"
METRICS_DIR = DATA_DIR / "metrics"
CONVERSATIONS_DIR = DATA_DIR / "conversations"

BODY_COMP_CSV = METRICS_DIR / "body_composition.csv"
APPLE_HEALTH_CSV = METRICS_DIR / "apple_health.csv"
TARGETS_JSON = METRICS_DIR / "targets.json"

# Ensure dirs exist on startup
WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Default targets ──────────────────────────────────────────────────────────
DEFAULT_TARGETS = {"weight_kg": 67.5, "bodyfat_pct": 13.0, "muscle_kg": 57.0}

def _load_targets() -> dict:
    if TARGETS_JSON.exists():
        try:
            return json.loads(TARGETS_JSON.read_text())
        except Exception:
            pass
    return dict(DEFAULT_TARGETS)

def _save_targets(t: dict):
    TARGETS_JSON.write_text(json.dumps(t, indent=2))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB helper ────────────────────────────────────────────────────────────────

def _get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ── Data Models ──────────────────────────────────────────────────────────────

class LogSetPayload(BaseModel):
    """Log a single set of a single exercise."""
    week_id: int
    day: int
    exercise_id: str
    set_number: int
    actual_weight: float
    actual_reps: int
    rpe: Optional[int] = None


class LogExercisePayload(BaseModel):
    """Log all sets of an exercise at once (backwards compat + convenience)."""
    week_id: int
    day: int
    exercise_id: str
    actual_weight: List[float]
    actual_reps: List[int]
    rpe: Optional[int] = None


class EditSetPayload(BaseModel):
    """Edit an already-logged set."""
    week_id: int
    day: int
    exercise_id: str
    set_number: int
    actual_weight: Optional[float] = None
    actual_reps: Optional[int] = None
    rpe: Optional[int] = None


class WatchPayload(BaseModel):
    """Matches the JSON structure from the Apple Watch Shortcut."""
    date: str
    km_distance: Optional[Any] = 0.0
    active_energy: Optional[float] = 0.0
    resting_energy: Optional[float] = 0.0
    steps: Optional[float] = 0.0
    sleep_awake: Optional[float] = 0.0
    sleep_rem: Optional[float] = 0.0
    sleep_core: Optional[float] = 0.0
    sleep_deep: Optional[float] = 0.0


class EquipmentConfigPayload(BaseModel):
    """Update custom increments for a machine exercise."""
    custom_increments: List[float]


# ── Configuration Endpoints ──────────────────────────────────────────────────

@app.get("/config/equipment")
def get_equipment_config():
    """Returns all machine exercises and their custom increments."""
    catalog_path = Path(__file__).resolve().parent / "exercises.json"
    if not catalog_path.exists():
        return {"exercises": []}
        
    try:
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    results = []
    for ex_id, data in catalog.items():
        if data.get("equipment") == "machine":
            results.append({
                "exercise_id": ex_id,
                "name": data.get("name", ex_id),
                "equipment": data.get("equipment"),
                "custom_increments": data.get("custom_increments", [])
            })
            
    # Sort alphabetically by name
    results.sort(key=lambda x: x["name"])
    return {"exercises": results}


@app.put("/config/equipment/{exercise_id}")
def update_equipment_config(exercise_id: str, payload: EquipmentConfigPayload):
    catalog_path = Path(__file__).resolve().parent / "exercises.json"
    if not catalog_path.exists():
        raise HTTPException(status_code=404, detail="Exercises catalog not found")
        
    try:
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if exercise_id not in catalog:
        raise HTTPException(status_code=404, detail="Exercise not found")
        
    catalog[exercise_id]["custom_increments"] = payload.custom_increments
    
    try:
        with open(catalog_path, "w") as f:
            json.dump(catalog, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "success", "exercise_id": exercise_id, "custom_increments": payload.custom_increments}


# ── Apple Health Webhook → now writes to DB ──────────────────────────────────

@app.post("/webhook/apple-health")
async def receive_apple_health(payload: WatchPayload):
    """
    Receives Apple Watch data, cleans European commas,
    converts seconds to minutes, upserts into DB (one row per calendar day).
    Also writes to CSV for backwards compatibility.
    """
    try:
        if isinstance(payload.km_distance, str):
            clean_dist = float(payload.km_distance.replace(',', '.'))
        else:
            clean_dist = float(payload.km_distance or 0.0)
    except (ValueError, TypeError):
        clean_dist = 0.0

    m_awake = round(payload.sleep_awake / 60, 1)
    m_rem = round(payload.sleep_rem / 60, 1)
    m_core = round(payload.sleep_core / 60, 1)
    m_deep = round(payload.sleep_deep / 60, 1)
    total_sleep_h = round((m_rem + m_core + m_deep) / 60, 2)

    raw_date = payload.date.strip()
    day_key = _normalise_date(raw_date)

    # Write to DB (upsert)
    conn = _get_db()
    conn.execute('''
        INSERT OR REPLACE INTO apple_health
        (date, active_kcal, resting_kcal, steps, distance_km,
         sleep_total_hrs, sleep_deep_min, sleep_rem_min, sleep_core_min, sleep_awake_min,
         updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (
        day_key,
        round(payload.active_energy, 1),
        round(payload.resting_energy, 1),
        int(payload.steps),
        round(clean_dist, 3),
        total_sleep_h,
        m_deep, m_rem, m_core, m_awake,
    ))
    conn.commit()
    conn.close()

    # Also write to CSV for backwards compat
    new_row = {
        "Date": day_key,
        "Active_Kcal": round(payload.active_energy, 1),
        "Resting_Kcal": round(payload.resting_energy, 1),
        "Steps": int(payload.steps),
        "Distance_Km": round(clean_dist, 3),
        "Sleep_Total_Hrs": total_sleep_h,
        "Sleep_Deep_Min": m_deep,
        "Sleep_REM_Min": m_rem,
        "Sleep_Core_Min": m_core,
        "Sleep_Awake_Min": m_awake,
    }
    _upsert_csv(APPLE_HEALTH_CSV, new_row, key_col="Date")

    print(f"✅ Logged Watch Data for {day_key}")
    return {"status": "success", "logged": day_key}


# ── CSV helpers (kept for backwards compat) ──────────────────────────────────

APPLE_HEADERS = [
    "Date", "Active_Kcal", "Resting_Kcal", "Steps", "Distance_Km",
    "Sleep_Total_Hrs", "Sleep_Deep_Min", "Sleep_REM_Min", "Sleep_Core_Min", "Sleep_Awake_Min",
]

BODY_HEADERS = [
    "Date", "Weight_kg", "BMI", "BodyFat_pct", "Water_pct", "MuscleMass_kg",
    "BoneMass_kg", "BMR_kcal", "VisceralFat", "SubcutaneousFat_pct",
    "Protein_pct", "MetabolicAge",
]


def _normalise_date(raw: str) -> str:
    raw = raw.strip()
    if len(raw) == 10 and raw[4] == '-':
        return raw
    if ' at ' in raw:
        raw = raw.split(' at ')[0].strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _upsert_csv(csv_path: Path, new_row: dict, key_col: str = "Date"):
    headers = list(new_row.keys())
    rows: list[dict] = []

    if csv_path.exists():
        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    r[key_col] = _normalise_date(r.get(key_col, ""))
                    rows.append(r)
        except Exception:
            pass

    found = False
    for i, r in enumerate(rows):
        if r.get(key_col) == new_row[key_col]:
            rows[i] = new_row
            found = True
            break
    if not found:
        rows.append(new_row)

    rows.sort(key=lambda r: r.get(key_col, ""))

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})


# ══════════════════════════════════════════════════════════════════════════════
# WORKOUT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/stats")
def get_stats():
    conn = _get_db()
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
        2: (4, "4", 0.80, "Strength+"),
        3: (3, "3", 0.85, "Heavy"),
        4: (2, "2", 0.90, "Peak"),
        5: (3, "5", 0.60, "Deload"),
        6: (1, "1", 1.00, "PR Test"),
    }
    c_sets, c_reps, c_int, c_label = cycle_map.get(bench_cycle_week, (5, "5", 0.75, "Strength"))
    bench_weight = round(bench_1rm * c_int / 2.5) * 2.5

    day_names = {1: "Push", 2: "Pull", 3: "Lower", 4: "Chest & Back", 5: "Arms"}
    day_completion = []
    for d in range(1, 6):
        # Count planned exercises (non-static)
        cursor.execute(
            "SELECT COUNT(DISTINCT exercise_id) FROM workout_plan WHERE week_id=? AND day=? AND strategy != 'static'",
            (current_week, d)
        )
        planned = cursor.fetchone()[0]

        # Count fully-logged exercises (all sets logged)
        cursor.execute("""
            SELECT exercise_id, COUNT(*) as total_sets,
                   SUM(CASE WHEN actual_reps IS NOT NULL THEN 1 ELSE 0 END) as logged_sets
            FROM workout_logs
            WHERE week_id = ? AND day = ? AND strategy != 'static'
            GROUP BY exercise_id
        """, (current_week, d))
        logged = sum(1 for r in cursor.fetchall() if r["logged_sets"] == r["total_sets"])

        day_completion.append({
            "day": d, "name": day_names[d], "planned": planned, "logged": logged,
        })

    conn.close()
    return {
        "current_week": current_week,
        "bench_cycle_week": bench_cycle_week,
        "bench_1rm": bench_1rm,
        "bench_session": {
            "sets": c_sets, "reps": c_reps, "weight": bench_weight,
            "intensity_pct": round(c_int * 100), "label": c_label,
        },
        "day_completion": day_completion,
    }


@app.get("/workout/{day_id}")
def get_workout(day_id: int, week_id: Optional[int] = Query(None)):
    """
    Returns the workout for a day INCLUDING already-logged data.
    Each exercise includes a `sets_data` array where each set shows
    target weight/reps AND actual weight/reps if already logged.
    Accepts optional week_id query param; defaults to latest week.
    """
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT week_id FROM workout_plan ORDER BY week_id")
    all_weeks = [r["week_id"] for r in cursor.fetchall()]

    if not all_weeks:
        conn.close()
        return {"error": "No workout plan found."}

    current_week = week_id if week_id and week_id in all_weeks else all_weeks[-1]

    # Get all sets for this day (plan + logs are in workout_logs)
    cursor.execute('''
        SELECT exercise_id, exercise_name, exercise_order, set_number,
               target_weight, target_reps, actual_weight, actual_reps, rpe, logged_at,
               superset_group, strategy, rounding, equipment
        FROM workout_logs
        WHERE week_id = ? AND day = ?
        ORDER BY exercise_order, set_number
    ''', (current_week, day_id))

    rows = cursor.fetchall()
    conn.close()

    # Group by exercise
    exercises = {}
    for row in rows:
        ex_id = row["exercise_id"]
        if ex_id not in exercises:
            exercises[ex_id] = {
                "exercise_id": ex_id,
                "exercise": row["exercise_name"],
                "exercise_order": row["exercise_order"],
                "target_reps": row["target_reps"],
                "superset_group": row["superset_group"],
                "strategy": row["strategy"],
                "rounding": row["rounding"],
                "equipment": row["equipment"],
                "sets": 0,
                "target_weights": [],
                "sets_data": [],
                "all_logged": True,
            }
        ex = exercises[ex_id]
        ex["sets"] += 1
        ex["target_weights"].append(row["target_weight"])

        set_info = {
            "set_number": row["set_number"],
            "target_weight": row["target_weight"],
            "target_reps": row["target_reps"],
            "actual_weight": row["actual_weight"],
            "actual_reps": row["actual_reps"],
            "rpe": row["rpe"],
            "logged": row["logged_at"] is not None,
        }
        ex["sets_data"].append(set_info)

        if row["logged_at"] is None:
            ex["all_logged"] = False

    workout_data = sorted(exercises.values(), key=lambda x: x["exercise_order"])

    return {"week": current_week, "day": day_id, "exercises": workout_data, "weeks": all_weeks}


# ── Per-set logging ──────────────────────────────────────────────────────────

@app.post("/log/set")
def log_single_set(payload: LogSetPayload):
    """Log a single set. Can be called as soon as you finish that set."""
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE workout_logs
        SET actual_weight = ?, actual_reps = ?, rpe = ?, logged_at = datetime('now')
        WHERE week_id = ? AND day = ? AND exercise_id = ? AND set_number = ?
    ''', (
        payload.actual_weight, payload.actual_reps, payload.rpe,
        payload.week_id, payload.day, payload.exercise_id, payload.set_number
    ))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Set not found in workout plan.")

    conn.commit()
    conn.close()
    return {"status": "saved", "exercise_id": payload.exercise_id, "set": payload.set_number}


@app.post("/log")
def log_exercise(payload: LogExercisePayload):
    """Log all sets of an exercise at once (convenience endpoint)."""
    conn = _get_db()
    cursor = conn.cursor()

    for i, (w, r) in enumerate(zip(payload.actual_weight, payload.actual_reps), start=1):
        cursor.execute('''
            UPDATE workout_logs
            SET actual_weight = ?, actual_reps = ?, rpe = ?, logged_at = datetime('now')
            WHERE week_id = ? AND day = ? AND exercise_id = ? AND set_number = ?
        ''', (w, r, payload.rpe, payload.week_id, payload.day, payload.exercise_id, i))

    conn.commit()
    conn.close()
    return {"status": "saved", "exercise": payload.exercise_id}


@app.put("/log/edit")
def edit_set(payload: EditSetPayload):
    """Edit an already-logged set (fix typos)."""
    conn = _get_db()
    cursor = conn.cursor()

    updates = []
    params = []
    if payload.actual_weight is not None:
        updates.append("actual_weight = ?")
        params.append(payload.actual_weight)
    if payload.actual_reps is not None:
        updates.append("actual_reps = ?")
        params.append(payload.actual_reps)
    if payload.rpe is not None:
        updates.append("rpe = ?")
        params.append(payload.rpe)

    if not updates:
        conn.close()
        return {"status": "nothing to update"}

    updates.append("logged_at = datetime('now')")
    sql = f"UPDATE workout_logs SET {', '.join(updates)} WHERE week_id = ? AND day = ? AND exercise_id = ? AND set_number = ?"
    params.extend([payload.week_id, payload.day, payload.exercise_id, payload.set_number])

    cursor.execute(sql, params)
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Set not found.")

    conn.commit()
    conn.close()
    return {"status": "updated", "exercise_id": payload.exercise_id, "set": payload.set_number}


# ── Complete Day ─────────────────────────────────────────────────────────────

@app.post("/complete-day")
def complete_day(week_id: int, day: int):
    """Mark an entire day as complete.
    - Zero-fills any unlogged sets (actual_weight=0, actual_reps=0).
    - Dumps the final state to the data-lake JSON file.
    """
    conn = _get_db()
    cursor = conn.cursor()

    # 1) Zero-fill unlogged sets
    cursor.execute("""
        UPDATE workout_logs
        SET actual_weight = 0, actual_reps = 0, logged_at = datetime('now')
        WHERE week_id = ? AND day = ? AND actual_reps IS NULL AND strategy != 'static'
    """, (week_id, day))
    zeroed = cursor.rowcount
    conn.commit()

    # 2) Dump the completed day to JSON archive
    cursor.execute("""
        SELECT exercise_id, exercise_name, set_number, target_weight, target_reps,
               actual_weight, actual_reps, rpe, strategy
        FROM workout_logs
        WHERE week_id = ? AND day = ? AND strategy != 'static'
        ORDER BY exercise_order, set_number
    """, (week_id, day))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No logs found.")

    today = date.today().isoformat()
    exercises = {}
    for r in rows:
        ex_id = r["exercise_id"]
        if ex_id not in exercises:
            exercises[ex_id] = {
                "exercise": r["exercise_name"],
                "exercise_id": ex_id,
                "strategy": r["strategy"],
                "planned_reps": r["target_reps"],
                "sets": [],
            }
        exercises[ex_id]["sets"].append({
            "set": r["set_number"],
            "target_weight": r["target_weight"],
            "actual_weight": r["actual_weight"],
            "actual_reps": r["actual_reps"],
            "rpe": r["rpe"],
        })

    payload = {
        "date": today,
        "week_id": week_id,
        "day": day,
        "exercises": list(exercises.values()),
    }
    filename = f"{today}_Day{day}.json"
    filepath = WORKOUTS_DIR / filename
    filepath.write_text(json.dumps(payload, indent=2))

    return {"status": "completed", "zeroed_sets": zeroed, "file": str(filepath.relative_to(PROJECT_ROOT))}


# ── Complete Exercise(s) ─────────────────────────────────────────────────────

@app.post("/complete-exercise")
def complete_exercise(week_id: int, day: int, exercise_ids: list[str] = Body(...)):
    """Zero-fill unlogged sets for specific exercise(s).
    Accepts a list of exercise_ids so a whole superset can be completed at once.
    """
    conn = _get_db()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in exercise_ids)
    cursor.execute(f"""
        UPDATE workout_logs
        SET actual_weight = 0, actual_reps = 0, logged_at = datetime('now')
        WHERE week_id = ? AND day = ? AND exercise_id IN ({placeholders})
              AND actual_reps IS NULL AND strategy != 'static'
    """, [week_id, day] + exercise_ids)
    zeroed = cursor.rowcount
    conn.commit()
    conn.close()
    return {"status": "completed", "zeroed_sets": zeroed}


# ── Has completed days (for gating) ─────────────────────────────────────────

@app.get("/has-completed-days")
def has_completed_days():
    """Returns whether the user has logged at least one exercise set."""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM workout_logs
        WHERE strategy != 'static' AND actual_reps IS NOT NULL
        LIMIT 1
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return {"has_completed": count > 0}


@app.post("/generate-next-week")
def generate_next_week():
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]

    if not current_week:
        conn.close()
        raise HTTPException(status_code=400, detail="No plan found.")

    # Check completion: all non-static exercises must have all sets logged
    cursor.execute("""
        SELECT exercise_id, COUNT(*) as total,
               SUM(CASE WHEN actual_reps IS NOT NULL THEN 1 ELSE 0 END) as logged
        FROM workout_logs
        WHERE week_id = ? AND strategy != 'static'
        GROUP BY exercise_id
    """, (current_week,))
    incomplete = [r for r in cursor.fetchall() if r["logged"] < r["total"]]

    conn.close()

    if incomplete:
        raise HTTPException(status_code=400, detail="Incomplete logs.")

    try:
        new_week = run_weekly_update(use_ai_review=False)
        return {"status": "success", "new_week": new_week}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai-review/{week_id}")
def trigger_ai_review(week_id: int):
    """Trigger an AI review of a deterministically-generated week."""
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM workout_plan WHERE week_id = ?", (week_id,))
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        raise HTTPException(status_code=404, detail=f"Week {week_id} not found.")
    try:
        from weekly_coach import ai_review, apply_ai_suggestions
        prev_week = week_id - 1
        review = ai_review(prev_week, week_id)
        suggestions = review.get("suggestions", []) if review else []
        if suggestions:
            apply_ai_suggestions(week_id, suggestions)
        return {"status": "success", "suggestions_applied": len(suggestions), "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Strength Progression ─────────────────────────────────────────────────────

@app.get("/progression/{exercise_id}")
def get_progression(exercise_id: str):
    """
    Returns the strength progression history for an exercise across all weeks.
    Each entry = one week/day occurrence with per-set data.
    Also computes summary stats: total reps, total weight, avg weight per rep.
    """
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT week_id, day, set_number, target_weight, target_reps,
               actual_weight, actual_reps, rpe, logged_at
        FROM workout_logs
        WHERE exercise_id = ? AND actual_reps IS NOT NULL
        ORDER BY week_id, day, set_number
    """, (exercise_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"exercise_id": exercise_id, "history": [], "summary": None}

    # Group by (week, day)
    sessions = {}
    for r in rows:
        key = (r["week_id"], r["day"])
        if key not in sessions:
            sessions[key] = {
                "week_id": r["week_id"],
                "day": r["day"],
                "logged_at": r["logged_at"],
                "sets": [],
                "total_reps": 0,
                "total_volume": 0.0,
            }
        s = sessions[key]
        w = r["actual_weight"] or 0
        reps = r["actual_reps"] or 0
        s["sets"].append({
            "set_number": r["set_number"],
            "target_weight": r["target_weight"],
            "target_reps": r["target_reps"],
            "actual_weight": w,
            "actual_reps": reps,
            "rpe": r["rpe"],
        })
        s["total_reps"] += reps
        s["total_volume"] += w * reps

    history = []
    for key in sorted(sessions.keys()):
        s = sessions[key]
        s["avg_weight_per_rep"] = round(s["total_volume"] / s["total_reps"], 2) if s["total_reps"] > 0 else 0
        s["total_volume"] = round(s["total_volume"], 1)
        history.append(s)

    # Global summary across all logged sessions
    all_reps = sum(s["total_reps"] for s in history)
    all_volume = sum(s["total_volume"] for s in history)
    max_weight = max(
        (set_d["actual_weight"] for s in history for set_d in s["sets"]),
        default=0
    )

    summary = {
        "total_sessions": len(history),
        "total_reps": all_reps,
        "total_volume_kg": round(all_volume, 1),
        "avg_weight_per_rep": round(all_volume / all_reps, 2) if all_reps > 0 else 0,
        "max_weight": max_weight,
    }

    return {"exercise_id": exercise_id, "history": history, "summary": summary}


@app.get("/progression")
def get_all_progressions():
    """
    Returns a compact summary of progression for ALL exercises
    (latest session vs first session).
    """
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT exercise_id, exercise_name
        FROM workout_logs
        WHERE actual_reps IS NOT NULL AND strategy != 'static'
    """)
    exercises = cursor.fetchall()

    results = []
    for ex in exercises:
        ex_id = ex["exercise_id"]
        ex_name = ex["exercise_name"]

        # First logged session
        cursor.execute("""
            SELECT week_id, day, actual_weight, actual_reps
            FROM workout_logs
            WHERE exercise_id = ? AND actual_reps IS NOT NULL
            ORDER BY week_id, day, set_number
            LIMIT 1
        """, (ex_id,))
        first = cursor.fetchone()

        # Latest logged session
        cursor.execute("""
            SELECT week_id, day, actual_weight, actual_reps
            FROM workout_logs
            WHERE exercise_id = ? AND actual_reps IS NOT NULL
            ORDER BY week_id DESC, day DESC, set_number DESC
            LIMIT 1
        """, (ex_id,))
        latest = cursor.fetchone()

        # Averages across all logged sets
        cursor.execute("""
            SELECT COUNT(*) as total_sets,
                   SUM(actual_reps) as total_reps,
                   SUM(actual_weight * actual_reps) as total_volume,
                   AVG(actual_weight) as avg_weight
            FROM workout_logs
            WHERE exercise_id = ? AND actual_reps IS NOT NULL
        """, (ex_id,))
        agg = cursor.fetchone()

        results.append({
            "exercise_id": ex_id,
            "exercise_name": ex_name,
            "first_weight": first["actual_weight"] if first else None,
            "latest_weight": latest["actual_weight"] if latest else None,
            "total_sets": agg["total_sets"],
            "total_reps": agg["total_reps"],
            "total_volume_kg": round(agg["total_volume"], 1) if agg["total_volume"] else 0,
            "avg_weight": round(agg["avg_weight"], 1) if agg["avg_weight"] else 0,
        })

    conn.close()
    return {"progressions": results}


# ── Abs Routine — Incomplete-Time History ─────────────────────────────────────

@app.get("/abs/history")
def get_abs_history():
    """
    Returns per-week incomplete-seconds for the abs routine.
    The 'rpe' field on the first abs exercise of each (week, day) stores
    the number of seconds the user couldn't complete in the 6-min routine.
    """
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT week_id, day, rpe, logged_at
        FROM workout_logs
        WHERE strategy = 'static'
          AND actual_reps IS NOT NULL
          AND set_number = 1
          AND rpe IS NOT NULL
        ORDER BY week_id, day
    """)
    rows = cursor.fetchall()
    conn.close()

    # Deduplicate: keep only first abs exercise per (week, day) — rpe = incomplete secs
    seen = set()
    history = []
    for r in rows:
        key = (r["week_id"], r["day"])
        if key not in seen:
            seen.add(key)
            history.append({
                "week_id": r["week_id"],
                "day": r["day"],
                "incomplete_secs": r["rpe"],
                "logged_at": r["logged_at"],
            })

    return {"history": history}


# ── Muscle Levels — True-Level RPG System ─────────────────────────────────────
#
# XP Formula (Quality-Adjusted Tonnage):
#   Base_XP = (Weight × Reps) × e^(k × Weight / est_1RM)
#   Muscle_XP += Base_XP × Activation_Ratio  (from ACTIVATION_MULTIPLIERS)
#
# Level Cap (exponential):
#   Total_XP_Required(Lv) = Base × Lv^2.5
#   Base = 50  ⇒  Lv1 = 50, Lv5 = 2,795, Lv10 = 15,811, Lv20 = 89,442
#
# Strength Gates (1RM / Bodyweight ratio on the Anchor exercise):
#   Lv 20 gate: chest needs 1.0× BW bench, back needs 1.0× BW lat pulldown, ...
#   Lv 40 gate: 1.5× BW
#   Lv 60 gate: 2.0× BW
#
# 1RM Estimation: Epley formula  1RM = w × (1 + r/30)  using heaviest set

EXERCISES_JSON = Path(__file__).resolve().parent / "exercises.json"
_EXERCISE_MUSCLES: dict = {}

def _load_exercise_muscles():
    global _EXERCISE_MUSCLES
    if EXERCISES_JSON.exists():
        try:
            _EXERCISE_MUSCLES = json.loads(EXERCISES_JSON.read_text())
        except Exception:
            pass

_load_exercise_muscles()

# ── Activation Multipliers ────────────────────────────────────────────────────
# Maps exercise_name → { library_muscle_key: ratio }
# The library uses: chest, triceps, front-deltoids, side-deltoids, back-deltoids,
# biceps, forearm, trapezius, upper-back, lower-back, abs, obliques,
# quadriceps, hamstring, calves, gluteal, abductors, adductor, lats
ACTIVATION_MULTIPLIERS = {
    # --- PUSH ---
    "Barbell Bench Press":            {"chest": 1.0, "triceps": 0.4, "front-deltoids": 0.3},
    "Flat Dumbbell Bench Press":      {"chest": 1.0, "triceps": 0.3, "front-deltoids": 0.3},
    "Incline Dumbbell Bench Press":   {"chest": 1.0, "front-deltoids": 0.5, "triceps": 0.3},
    "Low Cable Flyes":                {"chest": 1.0},
    "Push Ups":                       {"chest": 1.0, "triceps": 0.4, "front-deltoids": 0.2},
    "Frontal Plate Raises":           {"front-deltoids": 1.0},
    "Lateral Dumbbell Raises":        {"side-deltoids": 1.0},
    "Cable Lateral Raises":           {"side-deltoids": 1.0},
    "DB Lateral Raises":              {"side-deltoids": 1.0},
    "Overhead Tricep Extension (DB)": {"triceps": 1.0},
    "Overhead DB Tricep Ext":         {"triceps": 1.0},
    "Tricep Pushdowns":               {"triceps": 1.0},
    "Tricep Rope Pulldowns":          {"triceps": 1.0},
    # --- PULL ---
    "Lat Pulldowns":                  {"lats": 1.0, "biceps": 0.4, "upper-back": 0.3},
    "Closed Grip Lat Pulldown":       {"lats": 1.0, "biceps": 0.5, "upper-back": 0.3},
    "Pull Ups":                       {"lats": 1.0, "biceps": 0.4, "upper-back": 0.3},
    "Machine Closed Row":             {"upper-back": 1.0, "lats": 0.5, "biceps": 0.3},
    "Machine Open Row":               {"upper-back": 1.0, "back-deltoids": 0.4, "biceps": 0.2},
    "Reverse Cable Flyes":            {"back-deltoids": 1.0, "trapezius": 0.5},
    "Cable Face Pulls":               {"back-deltoids": 1.0, "trapezius": 0.6},
    "Trapezoid Raises":               {"trapezius": 1.0},
    "Standing Finger Plate Curls":    {"biceps": 1.0, "forearm": 0.3},
    "Cable Bicep Open Curls":         {"biceps": 1.0},
    "Open DB Curls":                  {"biceps": 1.0},
    "Dumbbell Hammer Curls":          {"biceps": 1.0, "forearm": 0.8},
    "DB Hammer Curls":                {"biceps": 1.0, "forearm": 0.8},
    # --- LEGS & CORE ---
    "Hip Abduction Machine":          {"gluteal": 1.0},
    "Glute Machine":                  {"gluteal": 1.0, "hamstring": 0.3},
    "Lying Leg Curls":                {"hamstring": 1.0},
    "Leg Extensions":                 {"quadriceps": 1.0},
    "Machine Calf Extensions":        {"calves": 1.0},
    "Weighted Back Extensions":       {"lower-back": 1.0, "gluteal": 0.4},
    "Abdominal Crunch Machine":       {"abs": 1.0},
    # --- ABS / CORE (static & bodyweight) ---
    "Abs: 21 Crunch":                 {"abs": 1.0, "obliques": 0.3},
    "Abs: Figure 8's":                {"abs": 1.0, "obliques": 0.6},
    "Abs: Hands Back Raises":         {"abs": 1.0, "lower-back": 0.2},
    "Abs: Lower abs up/down":         {"abs": 1.0},
    "Abs: Scissor V Ups":             {"abs": 1.0, "obliques": 0.4},
    "Abs: Seated 8's Left":           {"abs": 0.8, "obliques": 1.0},
    "Abs: Seated 8's Right":          {"abs": 0.8, "obliques": 1.0},
}

# Build a quick lookup by exercise_id too (snake_case)
_ACTIVATION_BY_ID: dict[str, dict[str, float]] = {}
for _name, _ratios in ACTIVATION_MULTIPLIERS.items():
    _key = _name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    _ACTIVATION_BY_ID[_key] = _ratios

# Friendly display names — now using the library's muscle keys
_MUSCLE_DISPLAY = {
    "chest": "Chest",
    "front-deltoids": "Front Delts",
    "side-deltoids": "Side Delts",
    "back-deltoids": "Rear Delts",
    "triceps": "Triceps",
    "biceps": "Biceps",
    "forearm": "Forearms",
    "trapezius": "Traps",
    "upper-back": "Upper Back",
    "lower-back": "Lower Back",
    "lats": "Lats",
    "abs": "Abs",
    "obliques": "Obliques",
    "quadriceps": "Quads",
    "hamstring": "Hamstrings",
    "calves": "Calves",
    "gluteal": "Glutes",
    "abductors": "Hip Abductors",
}

# Target levels (aspirational ceiling)
_MUSCLE_TARGETS = {
    "chest": 30, "front-deltoids": 25, "side-deltoids": 20,
    "back-deltoids": 20, "triceps": 20, "biceps": 20,
    "forearm": 15, "trapezius": 18, "upper-back": 25,
    "lower-back": 18, "lats": 28, "abs": 20, "obliques": 15,
    "quadriceps": 28, "hamstring": 22, "calves": 18,
    "gluteal": 22, "abductors": 10,
}

# Anchor exercises per muscle (for Benchmark PR display)
_MUSCLE_ANCHOR = {
    "chest":          "Barbell Bench Press",
    "triceps":        "Tricep Pushdowns",
    "front-deltoids": "Frontal Plate Raises",
    "side-deltoids":  "Cable Lateral Raises",
    "back-deltoids":  "Cable Face Pulls",
    "biceps":         "Cable Bicep Open Curls",
    "forearm":        "Dumbbell Hammer Curls",
    "trapezius":      "Trapezoid Raises",
    "upper-back":     "Machine Closed Row",
    "lower-back":     "Weighted Back Extensions",
    "lats":           "Lat Pulldowns",
    "abs":            "Abdominal Crunch Machine",
    "quadriceps":     "Leg Extensions",
    "hamstring":      "Lying Leg Curls",
    "calves":         "Machine Calf Extensions",
    "gluteal":        "Glute Machine",
    "abductors":      "Hip Abduction Machine",
}

# 1RM gate benchmarks per muscle: { gate_level: required_ratio_to_bodyweight }
# Based on average-man strength standards (ExRx / Symmetric Strength / Strength Level)
# for a ~70 kg male.  Lv 20 = novice, Lv 40 = intermediate, Lv 60 = advanced.
_STRENGTH_GATES = {
    # ── Compounds ────────────────────────────────────────────────────
    "chest":          {20: 0.75, 40: 1.0,  60: 1.5},   # Bench Press
    "lats":           {20: 0.7,  40: 1.0,  60: 1.3},   # Lat Pulldown
    "quadriceps":     {20: 0.6,  40: 0.9,  60: 1.3},   # Leg Extension
    "hamstring":      {20: 0.4,  40: 0.6,  60: 0.9},   # Lying Leg Curl
    "gluteal":        {20: 0.5,  40: 0.8,  60: 1.2},   # Glute Machine
    "upper-back":     {20: 0.6,  40: 0.9,  60: 1.2},   # Machine Closed Row
    "lower-back":     {20: 0.15, 40: 0.3,  60: 0.45},  # Weighted Back Ext.
    "abs":            {20: 0.5,  40: 0.8,  60: 1.1},   # Ab Crunch Machine
    # ── Isolation ────────────────────────────────────────────────────
    "triceps":        {20: 0.35, 40: 0.55, 60: 0.75},  # Tricep Pushdowns
    "biceps":         {20: 0.25, 40: 0.4,  60: 0.55},  # Cable Bicep Curls
    "front-deltoids": {20: 0.15, 40: 0.25, 60: 0.35},  # Frontal Plate Raise
    "side-deltoids":  {20: 0.06, 40: 0.1,  60: 0.15},  # Cable Lateral Raise
    "back-deltoids":  {20: 0.3,  40: 0.5,  60: 0.7},   # Cable Face Pull
    "trapezius":      {20: 0.25, 40: 0.4,  60: 0.55},  # Trapezoid Raises
    "forearm":        {20: 0.2,  40: 0.35, 60: 0.5},   # Hammer Curls
    "calves":         {20: 0.7,  40: 1.1,  60: 1.5},   # Machine Calf Ext.
    "abductors":      {20: 0.8,  40: 1.2,  60: 1.6},   # Hip Abduction
}

# --- XP constants ---
_XP_BASE = 50       # base constant for level curve
_XP_EXPONENT = 2.5  # polynomial exponent
_INTENSITY_K = 1.5  # intensity multiplier constant

def _xp_required_for_level(level: int) -> float:
    """Total cumulative XP to reach a given level."""
    if level <= 0:
        return 0
    return _XP_BASE * (level ** _XP_EXPONENT)

def _level_from_xp(xp: float) -> tuple[int, float, float]:
    """Return (level, xp_into_current_level, xp_needed_to_advance)."""
    level = 0
    while _xp_required_for_level(level + 1) <= xp:
        level += 1
        if level > 99:
            break
    floor_xp = _xp_required_for_level(level)
    ceil_xp = _xp_required_for_level(level + 1)
    return level, xp - floor_xp, ceil_xp - floor_xp

def _estimate_1rm(weight: float, reps: int) -> float:
    """Epley formula: 1RM = w × (1 + r/30). Returns 0 if invalid."""
    if weight <= 0 or reps <= 0:
        return 0.0
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30), 1)

def _get_bodyweight() -> float:
    """Fetch latest bodyweight from body composition CSV."""
    try:
        if BODY_COMP_CSV.exists():
            df = pd.read_csv(BODY_COMP_CSV)
            if len(df) > 0 and "Weight_kg" in df.columns:
                return float(df["Weight_kg"].iloc[-1])
    except Exception:
        pass
    return 70.0  # default


def _resolve_activation(ex_id: str, ex_name: str) -> dict[str, float]:
    """Get activation multipliers for an exercise.
    Priority: ACTIVATION_MULTIPLIERS by name → by id → fallback to exercises.json.
    """
    # Try by display name first
    if ex_name in ACTIVATION_MULTIPLIERS:
        return ACTIVATION_MULTIPLIERS[ex_name]
    # Try by exercise_id (snake_case)
    if ex_id in _ACTIVATION_BY_ID:
        return _ACTIVATION_BY_ID[ex_id]
    # Fallback to exercises.json primary/secondary
    info = _EXERCISE_MUSCLES.get(ex_id, {})
    primary = info.get("muscle_group")
    secondaries = info.get("secondary_muscles", [])
    fallback: dict[str, float] = {}
    if primary:
        # Map old muscle names to library keys
        fallback[_OLD_TO_LIB.get(primary, primary)] = 1.0
    for s in secondaries:
        fallback[_OLD_TO_LIB.get(s, s)] = 0.4
    return fallback


# Old muscle name → library muscle key mapping (for exercises.json fallback)
_OLD_TO_LIB = {
    "chest": "chest", "shoulders": "front-deltoids", "triceps": "triceps",
    "back": "lats", "biceps": "biceps", "forearms": "forearm",
    "rear_delts": "back-deltoids", "traps": "trapezius", "glutes": "gluteal",
    "hamstrings": "hamstring", "quads": "quadriceps", "calves": "calves",
    "lower_back": "lower-back", "abs": "abs", "upper_back": "upper-back",
    "hip_abductors": "abductors",
}


@app.get("/muscle-levels")
def get_muscle_levels():
    """
    True-Level RPG with activation-weighted XP:
    - Per-exercise activation ratios  (ACTIVATION_MULTIPLIERS)
    - Quality-adjusted intensity      (e^(k × weight/1RM))
    - Exponential level curve         (Base × Lv^2.5)
    - 1RM strength gates on anchors   (bodyweight-ratio gated)
    - Benchmark PR per muscle          (anchor exercise 1RM)
    """
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT exercise_id, exercise_name, actual_weight, actual_reps
        FROM workout_logs
        WHERE actual_reps IS NOT NULL AND actual_weight IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()

    bodyweight = _get_bodyweight()

    # --- Pass 1: per-exercise best 1RM + last-used weight/reps ---
    exercise_max: dict[str, float] = {}           # ex_id → best 1RM
    exercise_last: dict[str, tuple] = {}          # ex_id → (weight, reps) of heaviest set

    for r in rows:
        ex_id = r["exercise_id"]
        w = r["actual_weight"] or 0
        reps = r["actual_reps"] or 0
        est = _estimate_1rm(w, reps)
        if est > exercise_max.get(ex_id, 0):
            exercise_max[ex_id] = est
            exercise_last[ex_id] = (w, reps)

    # --- Pass 2: per-muscle anchor 1RM (Benchmark PR) ---
    muscle_benchmark: dict[str, dict] = {}  # muscle → {1rm, exercise_name, weight, reps}
    for muscle, anchor_name in _MUSCLE_ANCHOR.items():
        anchor_id = anchor_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        est_1rm = exercise_max.get(anchor_id, 0)
        if est_1rm > 0:
            w, reps = exercise_last.get(anchor_id, (0, 0))
            muscle_benchmark[muscle] = {
                "exercise_name": anchor_name,
                "estimated_1rm": round(est_1rm, 1),
                "best_weight": w,
                "best_reps": reps,
            }

    # --- Pass 3: quality-adjusted XP per muscle (activation-weighted) ---
    muscle_xp: dict[str, float] = {}
    muscle_exercises: dict[str, dict] = {}

    for r in rows:
        ex_id = r["exercise_id"]
        ex_name = r["exercise_name"]
        weight = r["actual_weight"] or 0
        reps = r["actual_reps"] or 0
        if weight == 0 and reps == 0:
            continue

        # For bodyweight / static exercises (weight 0 or 1), use a
        # bodyweight-proxy so they still earn meaningful XP.
        # Reps for timed exercises = seconds held.
        effective_weight = weight if weight > 1 else (bodyweight * 0.3)
        raw_volume = effective_weight * reps

        # Intensity multiplier:  e^(k × weight / 1RM)
        best_1rm = exercise_max.get(ex_id, 0)
        if best_1rm > 0 and weight > 1:
            intensity_ratio = min(weight / best_1rm, 1.0)
            multiplier = math.exp(_INTENSITY_K * intensity_ratio)
        else:
            multiplier = 1.0

        base_xp = raw_volume * multiplier

        # Use activation multipliers
        activations = _resolve_activation(ex_id, ex_name)
        if not activations:
            continue

        for muscle, ratio in activations.items():
            xp_gain = base_xp * ratio
            muscle_xp[muscle] = muscle_xp.get(muscle, 0) + xp_gain

            if muscle not in muscle_exercises:
                muscle_exercises[muscle] = {}
            if ex_id not in muscle_exercises[muscle]:
                muscle_exercises[muscle][ex_id] = {
                    "exercise_id": ex_id,
                    "name": ex_name,
                    "ratio": ratio,
                    "volume": 0, "sets": 0, "reps": 0,
                    "last_weight": weight,
                }
            entry = muscle_exercises[muscle][ex_id]
            entry["volume"] += xp_gain
            entry["sets"] += 1
            entry["reps"] += reps
            entry["last_weight"] = weight  # track most recent weight

    # --- Pass 4: apply strength gates + compute levels + recommendations ---
    all_muscles = set(list(muscle_xp.keys()) + list(_MUSCLE_DISPLAY.keys()))
    levels = []

    for muscle in sorted(all_muscles):
        xp = muscle_xp.get(muscle, 0)
        raw_level, xp_in, xp_need = _level_from_xp(xp)

        # Check strength gates
        gates = _STRENGTH_GATES.get(muscle, {})
        benchmark = muscle_benchmark.get(muscle)
        est_1rm = benchmark["estimated_1rm"] if benchmark else 0
        bw_ratio = est_1rm / bodyweight if bodyweight > 0 and est_1rm > 0 else 0

        gate_blocked = False
        gate_message = ""
        effective_level = raw_level

        for gate_lvl in sorted(gates.keys()):
            required_ratio = gates[gate_lvl]
            required_kg = round(required_ratio * bodyweight, 1)
            if raw_level >= gate_lvl and bw_ratio < required_ratio:
                effective_level = gate_lvl - 1
                gate_blocked = True
                gate_message = (
                    f"1RM must reach {required_kg}kg ({required_ratio}× BW) "
                    f"to unlock Lv.{gate_lvl}. Current: {est_1rm}kg ({bw_ratio:.2f}× BW)."
                )
                floor_xp = _xp_required_for_level(effective_level)
                ceil_xp = _xp_required_for_level(effective_level + 1)
                xp_in = xp - floor_xp
                xp_need = ceil_xp - floor_xp
                break

        target_lvl = _MUSCLE_TARGETS.get(muscle, 15)

        # Build exercises list with level-up recommendations
        exercises_list = sorted(
            muscle_exercises.get(muscle, {}).values(),
            key=lambda e: e["volume"], reverse=True,
        )
        xp_remaining = max(0, xp_need - max(xp_in, 0))
        for e in exercises_list:
            e["volume"] = round(e["volume"], 1)
            # Calculate "reps needed at last weight to bridge the gap"
            if xp_remaining > 0 and e["last_weight"] > 0 and e["ratio"] > 0:
                # XP per rep ≈ weight × intensity_mult × ratio
                ex_1rm = exercise_max.get(e["exercise_id"], e["last_weight"])
                if ex_1rm > 0:
                    intensity_ratio = min(e["last_weight"] / ex_1rm, 1.0)
                    xp_per_rep = e["last_weight"] * math.exp(_INTENSITY_K * intensity_ratio) * e["ratio"]
                else:
                    xp_per_rep = e["last_weight"] * e["ratio"]
                reps_needed = math.ceil(xp_remaining / xp_per_rep) if xp_per_rep > 0 else 0
                e["reps_to_next"] = reps_needed
                e["weight_for_calc"] = e["last_weight"]
            else:
                e["reps_to_next"] = None
                e["weight_for_calc"] = None

        levels.append({
            "muscle": muscle,
            "display_name": _MUSCLE_DISPLAY.get(muscle, muscle.replace("-", " ").replace("_", " ").title()),
            "level": effective_level,
            "raw_level": raw_level,
            "target_level": target_lvl,
            "xp": round(xp, 1),
            "xp_in_level": round(max(xp_in, 0), 1),
            "xp_for_next": round(xp_need, 1),
            "xp_pct": round(max(xp_in, 0) / xp_need * 100, 1) if xp_need > 0 else 100,
            "benchmark": benchmark,  # {exercise_name, estimated_1rm, best_weight, best_reps} or null
            "bodyweight": round(bodyweight, 1),
            "gate_blocked": gate_blocked,
            "gate_message": gate_message,
            "exercises": exercises_list,
        })

    return {"muscle_levels": levels}


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard/volume")
def dashboard_volume():
    files = sorted(WORKOUTS_DIR.glob("*.json"))
    series = []
    for f in files:
        try:
            doc = json.loads(f.read_text())
        except:
            continue
        t_sets = 0
        t_reps = 0
        t_tonnage = 0.0
        for ex in doc.get("exercises", []):
            for s in ex.get("sets", []):
                w = s.get("actual_weight") or 0
                r = s.get("actual_reps") or 0
                t_sets += 1
                t_reps += r
                t_tonnage += w * r
        series.append({
            "date": doc.get("date"),
            "week": doc.get("week_id"),
            "day": doc.get("day"),
            "sets": t_sets,
            "reps": t_reps,
            "tonnage_kg": round(t_tonnage, 1),
        })
    return {"volume": series}


@app.get("/dashboard/metrics")
def dashboard_metrics(range: Optional[str] = Query(None)):
    """Returns Body Composition + Apple Health + Targets from DB."""
    targets = _load_targets()
    response = {"body_comp": [], "apple_health": [], "targets": targets}

    cutoff = None
    today = date.today()
    if range == "day":
        cutoff = today.isoformat()
    elif range == "week":
        cutoff = (today - timedelta(days=7)).isoformat()
    elif range == "month":
        cutoff = (today - timedelta(days=30)).isoformat()

    conn = _get_db()

    # Body Composition from DB
    try:
        if cutoff:
            rows = conn.execute(
                "SELECT * FROM renpho_body_comp WHERE date >= ? ORDER BY date", (cutoff,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM renpho_body_comp ORDER BY date"
            ).fetchall()
        response["body_comp"] = [
            {
                "Date": r["date"],
                "Weight_kg": r["weight_kg"],
                "BMI": r["bmi"],
                "BodyFat_pct": r["bodyfat_pct"],
                "Water_pct": r["water_pct"],
                "MuscleMass_kg": r["muscle_mass_kg"],
                "BoneMass_kg": r["bone_mass_kg"],
                "BMR_kcal": r["bmr_kcal"],
                "VisceralFat": r["visceral_fat"],
                "SubcutaneousFat_pct": r["subcutaneous_fat_pct"],
                "Protein_pct": r["protein_pct"],
                "MetabolicAge": r["metabolic_age"],
            }
            for r in rows
        ]
    except Exception:
        pass

    # Apple Health from DB
    try:
        if cutoff:
            rows = conn.execute(
                "SELECT * FROM apple_health WHERE date >= ? ORDER BY date", (cutoff,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM apple_health ORDER BY date"
            ).fetchall()
        response["apple_health"] = [
            {
                "Date": r["date"],
                "Active_Kcal": r["active_kcal"],
                "Resting_Kcal": r["resting_kcal"],
                "Steps": r["steps"],
                "Distance_Km": r["distance_km"],
                "Sleep_Total_Hrs": r["sleep_total_hrs"],
                "Sleep_Deep_Min": r["sleep_deep_min"],
                "Sleep_REM_Min": r["sleep_rem_min"],
                "Sleep_Core_Min": r["sleep_core_min"],
                "Sleep_Awake_Min": r["sleep_awake_min"],
            }
            for r in rows
        ]
    except Exception:
        pass

    conn.close()
    return response


# ── Targets CRUD ─────────────────────────────────────────────────────────────

class TargetsPayload(BaseModel):
    weight_kg: float
    bodyfat_pct: float
    muscle_kg: float

@app.get("/targets")
def get_targets():
    return _load_targets()

@app.put("/targets")
def update_targets(payload: TargetsPayload):
    t = payload.model_dump()
    _save_targets(t)
    return {"status": "saved", "targets": t}

def _safe_float(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


# ── Plan Weight Update ────────────────────────────────────────────────────────

class PlanWeightUpdate(BaseModel):
    week_id: int
    day: int
    exercise_id: str
    weights: List[float]

@app.put("/plan/weight")
def update_plan_weight(body: PlanWeightUpdate):
    """Update target weights for an exercise in the plan AND workout_logs."""
    conn = _get_db()
    cursor = conn.cursor()
    weight_json = json.dumps(body.weights)

    # Update workout_plan template
    cursor.execute("""
        UPDATE workout_plan
        SET target_weight_json = ?
        WHERE week_id = ? AND day = ? AND exercise_id = ?
    """, (weight_json, body.week_id, body.day, body.exercise_id))

    # Update individual sets in workout_logs (only unlogged sets)
    for i, w in enumerate(body.weights):
        cursor.execute("""
            UPDATE workout_logs
            SET target_weight = ?
            WHERE week_id = ? AND day = ? AND exercise_id = ? AND set_number = ?
              AND logged_at IS NULL
        """, (w, body.week_id, body.day, body.exercise_id, i + 1))

    conn.commit()
    conn.close()
    return {"ok": True, "updated_sets": len(body.weights)}


# ── Plan Viewer ──────────────────────────────────────────────────────────────

@app.get("/plan")
def get_plan(week_id: Optional[int] = Query(None)):
    conn = _get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT week_id FROM workout_plan ORDER BY week_id")
    all_weeks = [r["week_id"] for r in cursor.fetchall()]

    if not all_weeks:
        conn.close()
        return {"weeks": [], "current_week": None, "days": {}}

    target_week = week_id if week_id and week_id in all_weeks else all_weeks[-1]

    cursor.execute("""
        SELECT day, day_name, exercise_order, exercise_id, exercise_name, sets, target_reps,
               target_weight_json, superset_group, strategy, equipment
        FROM workout_plan
        WHERE week_id = ?
        ORDER BY day, exercise_order
    """, (target_week,))
    rows = cursor.fetchall()
    conn.close()

    days = {}
    for r in rows:
        d = r["day"]
        if d not in days:
            days[d] = {"day": d, "day_name": r["day_name"] or "", "exercises": []}
        weights = json.loads(r["target_weight_json"]) if r["target_weight_json"] else []
        days[d]["exercises"].append({
            "exercise_id": r["exercise_id"],
            "exercise": r["exercise_name"],
            "sets": r["sets"],
            "target_reps": r["target_reps"],
            "weights": weights,
            "superset_group": r["superset_group"],
            "strategy": r["strategy"],
            "equipment": r["equipment"],
        })

    return {"weeks": all_weeks, "current_week": target_week, "days": days}


# ── AI Chat ──────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


def _conversation_path(cid: str) -> Path:
    return CONVERSATIONS_DIR / f"{cid}.json"


def _load_conversation(cid: str) -> dict:
    p = _conversation_path(cid)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {
        "id": cid,
        "created": datetime.now().isoformat(),
        "messages": [],
        "summary": "",
    }


def _save_conversation(conv: dict):
    p = _conversation_path(conv["id"])
    p.write_text(json.dumps(conv, indent=2, default=str))


def _gather_user_context() -> str:
    """Build a compact summary of the user's current state for the AI."""
    parts = []
    targets = _load_targets()
    parts.append(f"Goals — Target weight: {targets['weight_kg']}kg, Target BF: {targets['bodyfat_pct']}%, Target muscle: {targets['muscle_kg']}kg")

    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM renpho_body_comp ORDER BY date DESC LIMIT 1").fetchone()
        if row:
            parts.append(
                f"Current body comp ({row['date']}): "
                f"Weight {row['weight_kg']}kg, BF {row['bodyfat_pct']}%, "
                f"Muscle {row['muscle_mass_kg']}kg"
            )
            # Compute gap to target
            w_gap = round(row['weight_kg'] - targets['weight_kg'], 1)
            bf_gap = round(row['bodyfat_pct'] - targets['bodyfat_pct'], 1)
            m_gap = round(targets['muscle_kg'] - row['muscle_mass_kg'], 1)
            parts.append(
                f"Gap to targets: weight {'+'if w_gap>0 else ''}{w_gap}kg, "
                f"BF {'+'if bf_gap>0 else ''}{bf_gap}%, "
                f"muscle need +{m_gap}kg"
            )
    except Exception:
        pass

    try:
        row = conn.execute("SELECT * FROM apple_health ORDER BY date DESC LIMIT 1").fetchone()
        if row:
            parts.append(
                f"Latest activity ({row['date']}): "
                f"Steps {row['steps']}, Dist {row['distance_km']:.2f}km, "
                f"Sleep {row['sleep_total_hrs']:.1f}h"
            )
    except Exception:
        pass

    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(week_id) FROM workout_plan")
        wk = cur.fetchone()[0]
        if wk:
            parts.append(f"Current training week: {wk}")
            # Count completed days this week
            done = cur.execute(
                "SELECT COUNT(DISTINCT day) FROM workout_log WHERE week_id = ?", (wk,)
            ).fetchone()[0]
            parts.append(f"Workouts completed this week: {done}")
    except Exception:
        pass

    conn.close()

    # ── Muscle RPG levels + strength gates ──
    try:
        ml_data = get_muscle_levels()
        all_muscles = ml_data["muscle_levels"]
        gated = []
        top5 = sorted(all_muscles, key=lambda m: m["level"], reverse=True)[:5]
        bottom3 = sorted(all_muscles, key=lambda m: m["level"])[:3]
        parts.append("Top 5 muscles:")
        for m in top5:
            line = f"  {m['display_name']}: Lv.{m['level']} ({m['xp']:.0f} XP)"
            bm = m.get("benchmark")
            if bm:
                line += f" | Benchmark PR: {bm['estimated_1rm']}kg ({bm['exercise_name']})"
            parts.append(line)
        parts.append("Weakest muscles (focus areas):")
        for m in bottom3:
            parts.append(f"  {m['display_name']}: Lv.{m['level']} ({m['xp']:.0f} XP)")
        for m in all_muscles:
            if m.get("gate_blocked"):
                gated.append(f"  ⚠ {m['display_name']} GATE-BLOCKED at Lv.{m['level']}: {m['gate_message']}")
        if gated:
            parts.append("Strength gates (must be cleared to level up):")
            parts.extend(gated)
        if gated:
            parts.append("Strength gates (must be cleared to level up):")
            parts.extend(gated)
    except Exception:
        pass

    return "\n".join(parts)


def _summarise(messages: list) -> str:
    if len(messages) < 4:
        return ""
    transcript = "\n".join(
        f"{'User' if m['role']=='user' else 'Coach'}: {m['content']}" for m in messages
    )
    try:
        resp = http_requests.post(
            OLLAMA_URL,
            json={
                "model": CHAT_MODEL,
                "prompt": f"Summarise the following gym-coaching conversation in one short paragraph:\n\n{transcript}",
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        return ""


def _next_conversation_id() -> str:
    """Generate a date-based conversation ID: YYYY-MM-DD_N (e.g. 2026-02-24_1)."""
    today = date.today().isoformat()  # '2026-02-24'
    n = 1
    while (_conversation_path(f"{today}_{n}")).exists():
        n += 1
    return f"{today}_{n}"


@app.post("/chat")
async def chat(body: ChatMessage):
    cid = body.conversation_id or _next_conversation_id()
    conv = _load_conversation(cid)
    conv["messages"].append({"role": "user", "content": body.message, "ts": datetime.now().isoformat()})

    user_ctx = _gather_user_context()
    system = (
        "You are a highly knowledgeable strength & body-recomposition coach embedded in a "
        "fitness app. You combine evidence-based exercise science with practical gym wisdom.\n\n"
        "COACHING PRINCIPLES:\n"
        "• Prioritize progressive overload — small, consistent weight/rep increases matter most.\n"
        "• Body recomposition (gaining muscle while losing fat) is the user's core goal. "
        "Advise slight caloric surplus on training days, maintenance/slight deficit on rest days.\n"
        "• Recommend 1.6-2.2g protein per kg bodyweight daily. Emphasize meal timing around workouts.\n"
        "• Recovery is training — stress sleep quality (7-9h), hydration, and deload weeks.\n"
        "• When muscles are gate-blocked, suggest specific strength progressions to break through.\n"
        "• Reference the user's actual numbers (weight, body fat, muscle levels, PRs) to make advice concrete.\n"
        "• Be concise and actionable. Use bullet points for multi-part answers.\n"
        "• Use metric units (kg, km, cm). Be motivating but honest — celebrate PRs, flag plateaus.\n"
        "• If the user asks about something outside fitness/nutrition, keep it brief and redirect.\n\n"
        "TRAINING CONTEXT:\n"
        "The user follows a periodized push/pull/legs split with progressive overload. "
        "The app tracks an RPG-style muscle leveling system where quality-adjusted volume (XP) "
        "determines muscle levels 0-60+, with strength gates at levels 20, 40, and 60 "
        "requiring specific 1RM benchmarks relative to bodyweight.\n\n"
        f"USER DATA:\n{user_ctx}"
    )

    recent = conv["messages"][-20:]
    prompt_parts = []
    for m in recent:
        prefix = "User" if m["role"] == "user" else "Coach"
        prompt_parts.append(f"{prefix}: {m['content']}")
    prompt_text = "\n".join(prompt_parts) + "\nCoach:"

    try:
        resp = http_requests.post(
            OLLAMA_URL,
            json={
                "model": CHAT_MODEL,
                "system": system,
                "prompt": prompt_text,
                "stream": False,
                "options": {"temperature": 0.7},
            },
            timeout=120,
        )
        resp.raise_for_status()
        ai_reply = resp.json().get("response", "").strip()
    except Exception as e:
        ai_reply = f"Sorry, I couldn't reach the AI model. ({e})"

    conv["messages"].append({"role": "assistant", "content": ai_reply, "ts": datetime.now().isoformat()})

    if len(conv["messages"]) % 10 == 0:
        conv["summary"] = _summarise(conv["messages"])

    _save_conversation(conv)
    return {"conversation_id": cid, "reply": ai_reply}


@app.post("/chat/stream")
async def chat_stream(body: ChatMessage):
    """Streaming version of /chat — returns Server-Sent Events with incremental tokens."""
    cid = body.conversation_id or _next_conversation_id()
    conv = _load_conversation(cid)
    conv["messages"].append({"role": "user", "content": body.message, "ts": datetime.now().isoformat()})

    user_ctx = _gather_user_context()
    system = (
        "You are a highly knowledgeable strength & body-recomposition coach embedded in a "
        "fitness app. You combine evidence-based exercise science with practical gym wisdom.\n\n"
        "COACHING PRINCIPLES:\n"
        "• Prioritize progressive overload — small, consistent weight/rep increases matter most.\n"
        "• Body recomposition (gaining muscle while losing fat) is the user's core goal. "
        "Advise slight caloric surplus on training days, maintenance/slight deficit on rest days.\n"
        "• Recommend 1.6-2.2g protein per kg bodyweight daily. Emphasize meal timing around workouts.\n"
        "• Recovery is training — stress sleep quality (7-9h), hydration, and deload weeks.\n"
        "• When muscles are gate-blocked, suggest specific strength progressions to break through.\n"
        "• Reference the user's actual numbers (weight, body fat, muscle levels, PRs) to make advice concrete.\n"
        "• Be concise and actionable. Use bullet points for multi-part answers.\n"
        "• Use metric units (kg, km, cm). Be motivating but honest — celebrate PRs, flag plateaus.\n"
        "• If the user asks about something outside fitness/nutrition, keep it brief and redirect.\n\n"
        "TRAINING CONTEXT:\n"
        "The user follows a periodized push/pull/legs split with progressive overload. "
        "The app tracks an RPG-style muscle leveling system where quality-adjusted volume (XP) "
        "determines muscle levels 0-60+, with strength gates at levels 20, 40, and 60 "
        "requiring specific 1RM benchmarks relative to bodyweight.\n\n"
        f"USER DATA:\n{user_ctx}"
    )

    recent = conv["messages"][-20:]
    prompt_parts = []
    for m in recent:
        prefix = "User" if m["role"] == "user" else "Coach"
        prompt_parts.append(f"{prefix}: {m['content']}")
    prompt_text = "\n".join(prompt_parts) + "\nCoach:"

    def generate():
        full_reply = ""
        try:
            with http_requests.post(
                OLLAMA_URL,
                json={
                    "model": CHAT_MODEL,
                    "system": system,
                    "prompt": prompt_text,
                    "stream": True,
                    "options": {"temperature": 0.7},
                },
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        full_reply += token
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    if chunk.get("done"):
                        break
        except Exception as e:
            error_msg = f"Sorry, I couldn't reach the AI model. ({e})"
            full_reply = error_msg
            yield f"data: {json.dumps({'token': error_msg})}\n\n"

        # Save conversation after streaming completes
        conv["messages"].append({"role": "assistant", "content": full_reply.strip(), "ts": datetime.now().isoformat()})
        if len(conv["messages"]) % 10 == 0:
            conv["summary"] = _summarise(conv["messages"])
        _save_conversation(conv)

        yield f"data: {json.dumps({'done': True, 'conversation_id': cid})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/chat/history")
def chat_history():
    convs = []
    for f in sorted(CONVERSATIONS_DIR.glob("*.json"), reverse=True):
        try:
            c = json.loads(f.read_text())
            convs.append({
                "id": c["id"],
                "summary": c.get("summary", ""),
                "message_count": len(c.get("messages", [])),
                "created": c.get("created", ""),
                "last_ts": c["messages"][-1]["ts"] if c.get("messages") else c.get("created", ""),
            })
        except Exception:
            continue
    return {"conversations": convs}


@app.get("/chat/{conversation_id}")
def chat_get(conversation_id: str):
    conv = _load_conversation(conversation_id)
    if not conv["messages"]:
        raise HTTPException(404, "Conversation not found.")
    return conv


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

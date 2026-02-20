import sqlite3
import json
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Any
from uuid import uuid4

import pandas as pd
import requests as http_requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
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
DEFAULT_TARGETS = {"weight_kg": 67.5, "bodyfat_pct": 13.0, "muscle_kg": 58.0}

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

# ── Data Models ──────────────────────────────────────────────────────────────

class LogSet(BaseModel):
    week_id: int
    day: int
    exercise: str
    actual_weight: List[float]
    actual_reps: List[int]
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

# ── Apple Health Webhook ─────────────────────────────────────────────────────

@app.post("/webhook/apple-health")
async def receive_apple_health(payload: WatchPayload):
    """
    Receives Apple Watch data, cleans European commas, 
    converts seconds to minutes, upserts into CSV (one row per calendar day).
    """
    # 1. Handle European Comma (e.g., "1,09" -> 1.09)
    try:
        if isinstance(payload.km_distance, str):
            clean_dist = float(payload.km_distance.replace(',', '.'))
        else:
            clean_dist = float(payload.km_distance or 0.0)
    except (ValueError, TypeError):
        clean_dist = 0.0

    # 2. Convert raw seconds into Minutes
    m_awake = round(payload.sleep_awake / 60, 1)
    m_rem = round(payload.sleep_rem / 60, 1)
    m_core = round(payload.sleep_core / 60, 1)
    m_deep = round(payload.sleep_deep / 60, 1)
    
    # Calculate Total Sleep (excluding awake time)
    total_sleep_h = round((m_rem + m_core + m_deep) / 60, 2)

    # 3. Normalise the date to YYYY-MM-DD for dedup
    raw_date = payload.date.strip()
    day_key = _normalise_date(raw_date)

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

    # 4. Upsert into CSV (one row per day_key)
    _upsert_csv(APPLE_HEALTH_CSV, new_row, key_col="Date")

    print(f"✅ Logged Watch Data for {day_key}")
    return {"status": "success", "logged": day_key}


# ── CSV helpers ──────────────────────────────────────────────────────────────

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
    """
    Convert various date formats to YYYY-MM-DD.
    Handles: '20 Feb 2026 at 16:20', '2026-02-20', etc.
    """
    raw = raw.strip()
    # Already ISO
    if len(raw) == 10 and raw[4] == '-':
        return raw
    # Strip ' at HH:MM' suffix if present
    if ' at ' in raw:
        raw = raw.split(' at ')[0].strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # fallback: keep original


def _upsert_csv(csv_path: Path, new_row: dict, key_col: str = "Date"):
    """
    Read existing CSV into a list of dicts, replace the row whose `key_col`
    matches new_row[key_col], or append. Then rewrite the file sorted by key.
    """
    headers = list(new_row.keys())
    rows: list[dict] = []

    if csv_path.exists():
        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    # Normalise existing key too
                    r[key_col] = _normalise_date(r.get(key_col, ""))
                    rows.append(r)
        except Exception:
            pass

    # Upsert
    found = False
    for i, r in enumerate(rows):
        if r.get(key_col) == new_row[key_col]:
            rows[i] = new_row
            found = True
            break
    if not found:
        rows.append(new_row)

    # Sort by key
    rows.sort(key=lambda r: r.get(key_col, ""))

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})

# ── Workout Plan & Logs (SQLite) ─────────────────────────────────────────────

@app.get("/stats")
def get_stats():
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
def get_workout(day_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    
    if not current_week:
        return {"error": "No workout plan found."}

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
        item = dict(row)
        item["target_weights"] = json.loads(item["target_weight_json"])
        del item["target_weight_json"]
        workout_data.append(item)
        
    return {"week": current_week, "day": day_id, "exercises": workout_data}

@app.post("/log")
def log_workout(log: LogSet):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    weights_json = json.dumps(log.actual_weight)
    reps_json = json.dumps(log.actual_reps)
    
    cursor.execute('''
        INSERT INTO workout_logs (date, week_id, day, exercise, actual_weight_json, actual_reps_json, rpe)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
    ''', (log.week_id, log.day, log.exercise, weights_json, reps_json, log.rpe))
    
    conn.commit()
    conn.close()
    return {"status": "Saved", "exercise": log.exercise}

@app.post("/complete-day")
def complete_day(week_id: int, day: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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
        raise HTTPException(status_code=404, detail="No logs found.")

    today = date.today().isoformat()
    exercises = []
    seen = set()
    for r in rows:
        name = r["exercise"]
        if name in seen: continue
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

    payload = {"date": today, "week_id": week_id, "day": day, "exercises": exercises}
    filename = f"{today}_Day{day}.json"
    filepath = WORKOUTS_DIR / filename
    filepath.write_text(json.dumps(payload, indent=2))

    return {"status": "dumped", "file": str(filepath.relative_to(PROJECT_ROOT))}

@app.post("/generate-next-week")
def generate_next_week():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]

    if not current_week:
        conn.close()
        raise HTTPException(status_code=400, detail="No plan found.")

    cursor.execute("SELECT COUNT(DISTINCT exercise) FROM workout_plan WHERE week_id = ? AND strategy != 'static'", (current_week,))
    planned_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT wl.exercise)
        FROM workout_logs wl
        INNER JOIN workout_plan wp ON wl.exercise = wp.exercise AND wl.week_id = wp.week_id
        WHERE wl.week_id = ? AND wp.strategy != 'static'
    """, (current_week,))
    logged_count = cursor.fetchone()[0]
    conn.close()

    if logged_count < planned_count:
        raise HTTPException(status_code=400, detail="Incomplete logs.")

    try:
        run_weekly_update()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Dashboard (Aggregated Data) ──────────────────────────────────────────────

@app.get("/dashboard/volume")
def dashboard_volume():
    files = sorted(WORKOUTS_DIR.glob("*.json"))
    series = []
    for f in files:
        try:
            doc = json.loads(f.read_text())
        except: continue
        t_sets = 0
        t_reps = 0
        t_tonnage = 0.0
        for ex in doc.get("exercises", []):
            weights = ex.get("actual_weight", [])
            reps = ex.get("actual_reps", [])
            t_sets += len(reps)
            t_reps += sum(reps)
            t_tonnage += sum(w * r for w, r in zip(weights, reps))
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
    """
    Returns Body Composition + Apple Health + Targets.
    Optional ?range= lifetime | day | week | month  (filters by date).
    """
    targets = _load_targets()
    response = {"body_comp": [], "apple_health": [], "targets": targets}

    # Determine date cutoff
    cutoff = None
    today = date.today()
    if range == "day":
        cutoff = today.isoformat()
    elif range == "week":
        cutoff = (today - timedelta(days=7)).isoformat()
    elif range == "month":
        cutoff = (today - timedelta(days=30)).isoformat()
    # 'lifetime' or None → no cutoff

    # Load Body Composition
    if BODY_COMP_CSV.exists():
        try:
            df = pd.read_csv(BODY_COMP_CSV)
            # Normalise dates
            df["Date"] = df["Date"].apply(_normalise_date)
            df = df.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
            if cutoff:
                df = df[df["Date"] >= cutoff]
            response["body_comp"] = df.to_dict(orient="records")
        except Exception:
            pass

    # Load Apple Health
    if APPLE_HEALTH_CSV.exists():
        try:
            df = pd.read_csv(APPLE_HEALTH_CSV)
            df["Date"] = df["Date"].apply(_normalise_date)
            df = df.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
            if cutoff:
                df = df[df["Date"] >= cutoff]
            response["apple_health"] = df.to_dict(orient="records")
        except Exception:
            pass

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
    parts.append(f"Targets — Weight: {targets['weight_kg']}kg, BF: {targets['bodyfat_pct']}%, Muscle: {targets['muscle_kg']}kg")

    if BODY_COMP_CSV.exists():
        try:
            df = pd.read_csv(BODY_COMP_CSV)
            last = df.iloc[-1]
            parts.append(
                f"Latest body comp ({last.get('Date','?')}): "
                f"Weight {last.get('Weight_kg','?')}kg, BF {last.get('BodyFat_pct','?')}%, "
                f"Muscle {last.get('MuscleMass_kg','?')}kg"
            )
        except Exception:
            pass

    if APPLE_HEALTH_CSV.exists():
        try:
            df = pd.read_csv(APPLE_HEALTH_CSV)
            last = df.iloc[-1]
            parts.append(
                f"Latest activity ({last.get('Date','?')}): "
                f"Steps {int(last.get('Steps',0))}, Dist {last.get('Distance_Km',0):.2f}km, "
                f"Sleep {last.get('Sleep_Total_Hrs',0):.1f}h"
            )
        except Exception:
            pass

    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT MAX(week_id) FROM workout_plan")
        wk = cur.fetchone()[0]
        if wk:
            parts.append(f"Current training week: {wk}")
        conn.close()
    except Exception:
        pass

    return "\n".join(parts)


def _summarise(messages: list) -> str:
    """Ask the LLM for a one-paragraph summary of the conversation."""
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


@app.post("/chat")
async def chat(body: ChatMessage):
    cid = body.conversation_id or str(uuid4())
    conv = _load_conversation(cid)
    conv["messages"].append({"role": "user", "content": body.message, "ts": datetime.now().isoformat()})

    # Build system prompt with user context
    user_ctx = _gather_user_context()
    system = (
        "You are a friendly, expert gym and nutrition coach embedded in a fitness app. "
        "You have access to the user's current stats below. "
        "Give concise, actionable advice. Use metric units (kg, km). "
        "Be motivating but honest.\n\n"
        f"USER CONTEXT:\n{user_ctx}"
    )

    # Build conversation history for context (last 20 messages)
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

    # Auto-summarise every 10 messages
    if len(conv["messages"]) % 10 == 0:
        conv["summary"] = _summarise(conv["messages"])

    _save_conversation(conv)
    return {"conversation_id": cid, "reply": ai_reply}


@app.get("/chat/history")
def chat_history():
    """Return a list of all conversations (id + summary + message count + last ts)."""
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
    """Return full conversation by ID."""
    conv = _load_conversation(conversation_id)
    if not conv["messages"]:
        raise HTTPException(404, "Conversation not found.")
    return conv


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
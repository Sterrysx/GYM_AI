import sqlite3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any

app = FastAPI()
DB_NAME = "gym.db"

# Data Models (Validation)
class LogSet(BaseModel):
    week_id: int
    day: int
    exercise: str
    actual_weight: List[float] # Expected as [22, 22, 20]
    actual_reps: List[int]     # Expected as [10, 8, 8]
    rpe: Optional[int] = None

@app.get("/")
def health_check():
    return {"status": "Gym Clerk is Awake", "mode": "Zero-Idle-RAM"}

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
    Receives the results from the phone and saves them.
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

if __name__ == "__main__":
    import uvicorn
    # This is for testing locally. In production, Systemd handles this.
    uvicorn.run(app, host="0.0.0.0", port=8000)
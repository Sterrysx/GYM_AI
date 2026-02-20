import sqlite3
import json
import os
import requests
import pandas as pd

DB_NAME = "gym.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:32b" # Change to llama3.1:70b if you prefer

def export_week_data(cursor, week_id):
    """Export full week data (plan + logs) to data/week_{week_id}.json."""
    os.makedirs("data", exist_ok=True)
    cursor.execute("SELECT * FROM workout_plan WHERE week_id = ?", (week_id,))
    plan_rows = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM workout_logs WHERE week_id = ?", (week_id,))
    log_rows = [dict(row) for row in cursor.fetchall()]

    archive = {"week_id": week_id, "plan": plan_rows, "logs": log_rows}
    filepath = f"data/week_{week_id}.json"
    with open(filepath, "w") as f:
        json.dump(archive, f, indent=2)
    print(f"Exported Week {week_id} data to {filepath}")

def get_current_body_weight():
    """Fetch the latest weight from the data lake to give the AI context."""
    try:
        df = pd.read_csv("data/metrics/body_composition.csv")
        return df.iloc[-1]['Weight']
    except Exception:
        return 70.0

def run_weekly_update():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Gather Current State
    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    
    if not current_week:
        print("No data found in DB.")
        return

    export_week_data(cursor, current_week)
    next_week = current_week + 1
    current_weight = get_current_body_weight()

    cursor.execute("SELECT value FROM user_stats WHERE key='current_bench_cycle_week'")
    row = cursor.fetchone()
    bench_cycle_week = int(row[0]) if row else 1

    cursor.execute("SELECT value FROM user_stats WHERE key='bench_1rm'")
    row = cursor.fetchone()
    bench_1rm = float(row[0]) if row else 90.0

    print(f"--- Analyzing Week {current_week} Logs via Local LLM -> Generating Week {next_week} ---")

    # Load the archived logs we just saved to send to the AI
    with open(f"data/week_{current_week}.json", "r") as f:
        week_context = f.read()

    # 2. Build the System Prompt
    system_prompt = f"""
    You are an elite hypertrophy AI coach. Your client is a highly experienced lifter.
    Current Body Weight: {current_weight}kg. Previous baseline: 75kg. Goal: Recomposition.
    He purposely started with low weights to rebuild work capacity.

    CONTEXT:
    - Current Week: {current_week}. Next Week: {next_week}.
    - He is currently moving fast through the "muscle memory" phase. 

    YOUR TASK:
    Analyze the provided JSON logs of Week {current_week}'s performance (actual weights, actual reps, and RPE).
    Generate the strictly formatted JSON workout plan for Week {next_week}.

    PROGRESSION RULES:
    1. The "Slingshot" (Weeks 1 & 2): If he hit all Target Reps easily (RPE < 8), aggressively increase the weight by 2x the listed 'rounding' value. 
    2. The "Wall" (Weeks 3+): Progression will slow. If he hits all Target Reps, increase by exactly 1x the 'rounding' value. 
    3. Double Progression: If he fails to hit the Target Reps on ANY set within an exercise, DO NOT increase the weight for next week. Keep the weight identical.
    4. Post-Hiatus Rule: If RPE is 9 or 10 on an isolation movement, DO NOT increase weight, even if he hit the reps.
    5. Drop Sets / Arrays: Evaluate per-set. If his logged reps for [Set 1, Set 2, Set 3] were [15, 15, 12] against a target of 15, only increase the weight for Sets 1 and 2 next week.
    6. Periodized Bench: He is on week {bench_cycle_week} of his cycle. His 1RM is {bench_1rm}kg. Advance to week {(bench_cycle_week % 6) + 1} and calculate the exact array of weights based on the standard percentage.

    OUTPUT FORMAT:
    Return ONLY a valid JSON object. The keys must be the day numbers ("1", "2", "3", "4", "5").
    The values must be an array of exercise objects containing exactly these keys:
    "Day Name", "Exercise", "Sets", "Target Reps", "Weight Input" (MUST be an array of floats), "Strategy", "Rounding", "Superset Group".
    """

    # 3. Call Ollama API
    payload = {
        "model": MODEL_NAME,
        "system": system_prompt,
        "prompt": f"Here is the data for Week {current_week}:\n{week_context}\nGenerate Week {next_week}.",
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1} # Keep it deterministic and mathematical
    }

    try:
        print(f"🧠 Pinging {MODEL_NAME} on Dual 3090s... (This may take a few seconds)")
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        # Parse the JSON response directly from the LLM
        ai_response_text = response.json()["response"]
        new_plan = json.loads(ai_response_text)
        
    except Exception as e:
        print(f"❌ AI Generation Failed: {e}")
        return

    # 4. Insert New Week into SQLite
    new_plan_data = []
    for day_str, exercises in new_plan.items():
        day_id = int(day_str)
        for order, ex in enumerate(exercises, start=1):
            
            # Ensure Weight Input is a JSON string array for SQLite
            target_weights = ex.get("Weight Input")
            if not isinstance(target_weights, list):
                target_weights = [target_weights] * ex.get("Sets", 3)
                
            new_plan_data.append((
                next_week,
                day_id,
                ex.get("Day Name"),
                order,
                ex.get("Exercise"),
                ex.get("Sets"),
                str(ex.get("Target Reps")),
                json.dumps(target_weights),
                ex.get("Strategy"),
                ex.get("Rounding"),
                ex.get("Superset Group")
            ))

    cursor.executemany("""
        INSERT INTO workout_plan (
            week_id, day, day_name, exercise_order, exercise, 
            sets, target_reps, target_weight_json, strategy, rounding, superset_group
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, new_plan_data)

    # 5. Advance Bench Cycle
    if bench_cycle_week < 6:
        cursor.execute("UPDATE user_stats SET value = ? WHERE key='current_bench_cycle_week'", (str(bench_cycle_week + 1),))
    else:
        cursor.execute("UPDATE user_stats SET value = '1' WHERE key='current_bench_cycle_week'")

    conn.commit()
    conn.close()
    print(f"✅ Success! Week {next_week} generated by {MODEL_NAME} and loaded into database.")

if __name__ == "__main__":
    run_weekly_update()
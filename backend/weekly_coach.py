#!/usr/bin/env python3
"""
weekly_coach.py — Analyses the current week's logs via a local LLM and
generates the next week's workout plan using the exercises.json structure.

Uses the new DB schema: workout_logs (per-set), workout_plan, user_stats.
"""

import sqlite3
import json
import os
from pathlib import Path

import requests
import pandas as pd

from generate_baseline import (
    load_exercises_catalog,
    SCHEDULE,
    EQUIPMENT_INCREMENTS,
    snap_weight,
    get_equipment_rounding,
)

DB_NAME = "gym.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:32b"


def export_week_data(cursor, week_id):
    """Export the plan + per-set logs for archival."""
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
    """Get latest weight from renpho_body_comp table."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT weight_kg FROM renpho_body_comp ORDER BY date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return row["weight_kg"]
    except Exception:
        pass
    return 70.0


def run_weekly_update():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    if not current_week:
        print("No data found in DB.")
        conn.close()
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

    print(f"--- Analysing Week {current_week} Logs via Local LLM → Generating Week {next_week} ---")

    with open(f"data/week_{current_week}.json", "r") as f:
        week_context = f.read()

    # Load exercise catalog and schedule from generate_baseline
    exercises_catalog = load_exercises_catalog()

    # Build linked exercises context from SCHEDULE
    linked_info = []
    for day_id, day_info in SCHEDULE.items():
        for entry in day_info["exercises"]:
            if entry.get("linked_to"):
                ex_name = exercises_catalog.get(entry["exercise_id"], {}).get("name", entry["exercise_id"])
                linked_ex_name = exercises_catalog.get(entry["linked_to"]["exercise_id"], {}).get("name", entry["linked_to"]["exercise_id"])
                linked_info.append(
                    f"  Day {day_id}: {ex_name} ↔ Day {entry['linked_to']['day']}: {linked_ex_name}"
                )

    linked_context = "\n".join(linked_info) if linked_info else "None"

    system_prompt = f"""
    You are an elite hypertrophy AI coach. Your client is a highly experienced lifter.
    Current Body Weight: {current_weight}kg. Previous baseline: 75kg. Goal: Recomposition.
    He purposely started with low weights to rebuild work capacity.

    CONTEXT:
    - Current Week: {current_week}. Next Week: {next_week}.
    - He is currently moving fast through the "muscle memory" phase.
    - LINKED EXERCISES (same exercise across different days — keep weights synced):
{linked_context}

    YOUR TASK:
    Analyse the provided JSON logs of Week {current_week}'s performance (actual weights, actual reps per set, and RPE).
    Generate the strictly formatted JSON workout plan for Week {next_week}.

    IMPORTANT: The logs are now PER-SET. Each log entry has:
    - exercise_id, set_number, target_weight, actual_weight, actual_reps, rpe

    PROGRESSION RULES:
    1. The "Slingshot" (Weeks 1 & 2): If he hit all Target Reps easily (RPE < 8), aggressively increase the weight by 2x the listed 'rounding' value.
    2. The "Wall" (Weeks 3+): Progression will slow. If he hits all Target Reps, increase by exactly 1x the 'rounding' value.
    3. Double Progression: If he fails to hit the Target Reps on ANY set within an exercise, DO NOT increase the weight for next week. Keep the weight identical.
    4. Post-Hiatus Rule: If RPE is 9 or 10 on an isolation movement, DO NOT increase weight, even if he hit the reps.
    5. Drop Sets / Arrays: Evaluate per-set. If his logged reps for [Set 1, Set 2, Set 3] were [15, 15, 12] against a target of 15, only increase the weight for Sets 1 and 2 next week.
    6. Periodized Bench: He is on week {bench_cycle_week} of his cycle. His 1RM is {bench_1rm}kg. Advance to week {(bench_cycle_week % 6) + 1} and calculate the exact array of weights based on the standard percentage.
    7. Linked exercises: When an exercise appears on multiple days, ensure the weights are consistent.

    OUTPUT FORMAT:
    Return ONLY a valid JSON object. The keys must be the day numbers ("1", "2", "3", "4", "5").
    The values must be an array of exercise objects containing exactly these keys:
    "exercise_id", "Exercise" (display name), "Sets", "Target Reps", "Weight Input" (MUST be an array of floats), "Strategy", "Rounding", "Superset Group".
    """

    payload = {
        "model": MODEL_NAME,
        "system": system_prompt,
        "prompt": f"Here is the data for Week {current_week}:\n{week_context}\nGenerate Week {next_week}.",
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1}
    }

    try:
        print(f"🧠 Pinging {MODEL_NAME}... (This may take a few seconds)")
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        ai_response_text = response.json()["response"]
        new_plan = json.loads(ai_response_text)
    except Exception as e:
        print(f"❌ AI Generation Failed: {e}")
        conn.close()
        return

    # Insert into workout_plan and pre-populate workout_logs
    for day_str, exercises_list in new_plan.items():
        day_id = int(day_str)
        schedule_day = SCHEDULE.get(day_id, {})
        day_name = schedule_day.get("day_name", "")

        for order, ex in enumerate(exercises_list, start=1):
            ex_id = ex.get("exercise_id", "")
            ex_name = ex.get("Exercise", exercises_catalog.get(ex_id, {}).get("name", ex_id))
            equipment = exercises_catalog.get(ex_id, {}).get("equipment", "unknown")
            rounding = get_equipment_rounding(equipment)
            target_weights = ex.get("Weight Input")
            if not isinstance(target_weights, list):
                target_weights = [target_weights] * ex.get("Sets", 3)
            # Snap weights to valid equipment increments
            target_weights = [snap_weight(w, equipment) for w in target_weights]
            sets = ex.get("Sets", len(target_weights))
            target_reps = str(ex.get("Target Reps", 12))
            strategy = ex.get("Strategy", "linear")
            superset_group = ex.get("Superset Group")

            # Find linked info from SCHEDULE
            linked_day = None
            linked_ex_id = None
            for sday_id, sinfo in SCHEDULE.items():
                for sentry in sinfo["exercises"]:
                    if sentry["exercise_id"] == ex_id and sday_id == day_id:
                        linked = sentry.get("linked_to")
                        if linked:
                            linked_day = linked["day"]
                            linked_ex_id = linked["exercise_id"]
                        break

            cursor.execute("""
                INSERT INTO workout_plan (
                    week_id, day, day_name, exercise_order, exercise_id, exercise_name,
                    sets, target_reps, target_weight_json, strategy, rounding,
                    superset_group, equipment, linked_day, linked_exercise_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_week, day_id, day_name,
                order, ex_id, ex_name,
                sets, target_reps, json.dumps(target_weights),
                strategy, rounding, superset_group, equipment,
                linked_day, linked_ex_id
            ))

            # Pre-populate workout_logs per set
            for set_num in range(1, sets + 1):
                w = target_weights[set_num - 1] if set_num - 1 < len(target_weights) else target_weights[-1]
                cursor.execute("""
                    INSERT OR IGNORE INTO workout_logs (
                        week_id, day, exercise_id, exercise_name, exercise_order,
                        set_number, target_weight, target_reps,
                        superset_group, strategy, rounding, equipment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    next_week, day_id, ex_id, ex_name, order,
                    set_num, w, target_reps,
                    superset_group, strategy, rounding, equipment
                ))

    # Advance bench cycle
    if bench_cycle_week < 6:
        cursor.execute(
            "UPDATE user_stats SET value = ? WHERE key='current_bench_cycle_week'",
            (str(bench_cycle_week + 1),)
        )
    else:
        cursor.execute(
            "UPDATE user_stats SET value = '1' WHERE key='current_bench_cycle_week'"
        )

    conn.commit()
    conn.close()
    print(f"✅ Success! Week {next_week} generated by {MODEL_NAME} and loaded into database.")


if __name__ == "__main__":
    run_weekly_update()

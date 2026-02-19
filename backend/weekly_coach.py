import sqlite3
import json
import os
import pandas as pd

DB_NAME = "gym.db"


# ---------------------------------------------------------
# HELPER: UNIFORM SET (For Periodized Bench)
# ---------------------------------------------------------
def generate_uniform_set(weight, sets):
    """Generate uniform weight list: [weight, weight, weight, ...]"""
    return json.dumps([float(weight)] * sets)


# ---------------------------------------------------------
# HELPER: STRICT LIST (Reused for Drop Set Calculation)
# ---------------------------------------------------------
def generate_drop_set(anchor_weight, sets, rounding):
    """
    Re-calculates the drop set array based on a new Anchor Weight.
    Example: Anchor 24, Rounding 2 -> [24.0, 22.0, 20.0]
    """
    weight_list = []
    current_weight = float(anchor_weight)
    
    for i in range(sets):
        safe_weight = max(0, current_weight)
        weight_list.append(safe_weight)
        current_weight -= rounding
        
    return json.dumps(weight_list)

# ---------------------------------------------------------
# EXPORT: Archive completed week to JSON
# ---------------------------------------------------------
def export_week_data(cursor, week_id):
    """Export full week data (plan + logs) to data/week_{week_id}.json."""
    os.makedirs("data", exist_ok=True)

    cursor.execute("SELECT * FROM workout_plan WHERE week_id = ?", (week_id,))
    plan_rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM workout_logs WHERE week_id = ?", (week_id,))
    log_rows = [dict(row) for row in cursor.fetchall()]

    archive = {
        "week_id": week_id,
        "plan": plan_rows,
        "logs": log_rows
    }

    filepath = f"data/week_{week_id}.json"
    with open(filepath, "w") as f:
        json.dump(archive, f, indent=2)

    print(f"Exported Week {week_id} data to {filepath}")


# ---------------------------------------------------------
# LOGIC CORE
# ---------------------------------------------------------
def run_weekly_update():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Determine Current Week
    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    
    if not current_week:
        print("No data found in DB.")
        return

    # 1b. Export completed week's data before generating next
    export_week_data(cursor, current_week)

    next_week = current_week + 1
    print(f"--- Analyzing Week {current_week} -> Generating Week {next_week} ---")

    # 2. Fetch the Plan for Current Week
    cursor.execute("""
        SELECT * FROM workout_plan WHERE week_id = ? ORDER BY day, exercise_order
    """, (current_week,))
    plan_rows = cursor.fetchall()

    # 3. Fetch User Stats (For Bench Cycle)
    cursor.execute("SELECT value FROM user_stats WHERE key='current_bench_cycle_week'")
    row = cursor.fetchone()
    bench_cycle_week = int(row[0]) if row else 1

    cursor.execute("SELECT value FROM user_stats WHERE key='bench_1rm'")
    row = cursor.fetchone()
    bench_1rm = float(row[0]) if row else 120.0

    new_plan_data = []

    for row in plan_rows:
        exercise = dict(row)
        strategy = exercise['strategy']
        
        # Default: Copy old values
        new_target_weight_json = exercise['target_weight_json']
        new_sets = exercise['sets']
        new_reps_str = exercise['target_reps']
        
        # Fetch Logs for this specific exercise in the current week
        cursor.execute("""
            SELECT actual_reps_json, actual_weight_json, rpe 
            FROM workout_logs 
            WHERE week_id = ? AND exercise = ?
            ORDER BY date DESC LIMIT 1
        """, (current_week, exercise['exercise']))
        
        log = cursor.fetchone()

        # --- STRATEGY A: PERIODIZED BENCH (Strict Cycle) ---
        if strategy == 'periodized_bench':
            next_cycle_week = (bench_cycle_week % 6) + 1

            cycle_map = {
                1: (5, "5", 0.75),
                2: (4, "4", 0.82),
                3: (3, "3", 0.88),
                4: (2, "2", 0.92),
                5: (3, "5", 0.60), # Deload
                6: (1, "1", 1.02)  # PR
            }

            c_sets, c_reps, c_int = cycle_map[next_cycle_week]

            # Compute new weight from stored 1RM, rounded to nearest rounding increment
            rounding = exercise['rounding']
            raw_weight = bench_1rm * c_int
            if rounding > 0:
                new_weight = round(raw_weight / rounding) * rounding
            else:
                new_weight = raw_weight

            new_sets = c_sets
            new_reps_str = c_reps
            new_target_weight_json = generate_uniform_set(new_weight, c_sets)

            print(f"  [BENCH] Cycle {bench_cycle_week}->{next_cycle_week}: "
                  f"{c_sets}x{c_reps} @ {new_weight}kg ({c_int*100:.0f}% of {bench_1rm:.1f}kg 1RM)")

        # --- STRATEGY B: LINEAR & VARIABLE DROP ---
        elif strategy in ['linear', 'variable_drop']:
            if log:
                # Parse JSON logs
                actual_reps = json.loads(log['actual_reps_json'])
                target_reps_val = int(new_reps_str) if new_reps_str.isdigit() else 8 # Default safety
                
                # Check performance of Set 1 (The Anchor)
                set_1_reps = actual_reps[0] if len(actual_reps) > 0 else 0
                
                # Rule: If Set 1 Reps >= Target, Increase Weight
                if set_1_reps >= target_reps_val:
                    # Get old anchor
                    old_weights = json.loads(exercise['target_weight_json'])
                    old_anchor = old_weights[0]
                    
                    # Increase Anchor
                    new_anchor = old_anchor + exercise['rounding']
                    
                    # Generate new Array
                    new_target_weight_json = generate_drop_set(new_anchor, new_sets, exercise['rounding'])
                    print(f"  [UPGRADE] {exercise['exercise']}: {old_anchor} -> {new_anchor}kg")
                else:
                    # Keep same
                    print(f"  [KEEP] {exercise['exercise']}")
            else:
                # No log found? Keep same.
                pass

        # --- STRATEGY C: STATIC (Abs) ---
        elif strategy == 'static':
            pass # Changes nothing

        # Prepare Row for Insertion
        new_plan_data.append((
            next_week,
            exercise['day'],
            exercise['day_name'],
            exercise['exercise_order'],
            exercise['exercise'],
            new_sets,
            new_reps_str,
            new_target_weight_json,
            exercise['strategy'],
            exercise['rounding'],
            exercise['superset_group']
        ))

    # 4. Insert New Week
    cursor.executemany("""
        INSERT INTO workout_plan (
            week_id, day, day_name, exercise_order, exercise, 
            sets, target_reps, target_weight_json, strategy, rounding, superset_group
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, new_plan_data)

    # 5. Update Bench Cycle State
    if bench_cycle_week < 6:
        cursor.execute("UPDATE user_stats SET value = ? WHERE key='current_bench_cycle_week'", (str(bench_cycle_week + 1),))
    else:
        # Reset after Week 6
        cursor.execute("UPDATE user_stats SET value = '1' WHERE key='current_bench_cycle_week'")

    conn.commit()
    conn.close()
    print(f"Success! Week {next_week} is ready.")

if __name__ == "__main__":
    run_weekly_update()
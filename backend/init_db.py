#!/usr/bin/env python3
"""
init_db.py — Initialises the gym.db database with 3 core tables + supporting tables.

Tables:
  1. renpho_body_comp   — One row per calendar day (Renpho scale data)
  2. apple_health       — One row per calendar day (Apple Watch data)
  3. workout_logs       — One row per SET per exercise per day per week

Supporting tables:
  - workout_plan        — Weekly programme template (generated from exercises.json)
  - user_stats          — Key/value pairs (bench 1RM, cycle week, etc.)
"""

import sqlite3
import json
from pathlib import Path

DB_NAME = "gym.db"
EXERCISES_JSON = Path(__file__).resolve().parent / "exercises.json"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ──────────────────────────────────────────────────────────
    # TABLE 1: Renpho Body Composition (one row per day, keep newest)
    # ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS renpho_body_comp (
        date TEXT PRIMARY KEY,
        weight_kg REAL,
        bmi REAL,
        bodyfat_pct REAL,
        water_pct REAL,
        muscle_mass_kg REAL,
        bone_mass_kg REAL,
        bmr_kcal REAL,
        visceral_fat REAL,
        subcutaneous_fat_pct REAL,
        protein_pct REAL,
        metabolic_age REAL,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    ''')

    # ──────────────────────────────────────────────────────────
    # TABLE 2: Apple Health (one row per day, keep newest)
    # ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS apple_health (
        date TEXT PRIMARY KEY,
        active_kcal REAL,
        resting_kcal REAL,
        steps INTEGER,
        distance_km REAL,
        sleep_total_hrs REAL,
        sleep_deep_min REAL,
        sleep_rem_min REAL,
        sleep_core_min REAL,
        sleep_awake_min REAL,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    ''')

    # ──────────────────────────────────────────────────────────
    # TABLE 3: Workout Logs (one row per SET)
    # ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workout_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id INTEGER NOT NULL,
        day INTEGER NOT NULL,
        exercise_id TEXT NOT NULL,
        exercise_name TEXT NOT NULL,
        exercise_order INTEGER NOT NULL,
        set_number INTEGER NOT NULL,
        target_weight REAL NOT NULL,
        target_reps TEXT NOT NULL,
        actual_weight REAL,
        actual_reps INTEGER,
        rpe INTEGER,
        logged_at TEXT,
        superset_group TEXT,
        strategy TEXT,
        rounding REAL,
        equipment TEXT,
        UNIQUE(week_id, day, exercise_id, set_number)
    )
    ''')

    # ──────────────────────────────────────────────────────────
    # Workout Plan (template — keeps exercise metadata per week)
    # ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workout_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id INTEGER,
        day INTEGER,
        day_name TEXT,
        exercise_order INTEGER,
        exercise_id TEXT,
        exercise_name TEXT,
        sets INTEGER,
        target_reps TEXT,
        target_weight_json TEXT,
        strategy TEXT,
        rounding REAL,
        superset_group TEXT,
        equipment TEXT,
        linked_day INTEGER,
        linked_exercise_id TEXT,
        completed BOOLEAN DEFAULT 0
    )
    ''')

    # ──────────────────────────────────────────────────────────
    # User Stats (key/value)
    # ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    print("✓ Tables initialised.")

    # ──────────────────────────────────────────────────────────
    # SEED: Load Week 1 from exercises.json
    # ──────────────────────────────────────────────────────────
    cursor.execute("SELECT count(*) FROM workout_plan")
    plan_count = cursor.fetchone()[0]

    if plan_count == 0:
        print("Seeding Week 1 from exercises.json …")

        if not EXERCISES_JSON.exists():
            print(f"ERROR: {EXERCISES_JSON} not found!")
            conn.close()
            return

        with open(EXERCISES_JSON) as f:
            data = json.load(f)

        seed_week(cursor, 1, data)

        # Initialize bench cycle & 1RM
        cursor.execute(
            "INSERT OR REPLACE INTO user_stats (key, value) VALUES (?, ?)",
            ("current_bench_cycle_week", "1")
        )
        cursor.execute(
            "INSERT OR REPLACE INTO user_stats (key, value) VALUES (?, ?)",
            ("bench_1rm", "90")
        )

        print("✓ Week 1 seeded successfully!")
    else:
        print("Database already contains data. Skipping seed.")

    # Migrate existing CSVs into DB tables (one-time)
    _migrate_csv_to_db(cursor)

    conn.commit()
    conn.close()
    print(f"✓ Database {DB_NAME} is ready.")


def seed_week(cursor, week_id, exercises_data, weight_overrides=None):
    """
    Populate workout_plan + workout_logs for a given week.
    
    exercises_data: the full parsed exercises.json dict
    weight_overrides: optional dict keyed by (day, exercise_id) → [weight_list]
                      Used by the AI coach when generating next-week plans.
    """
    exercises_catalog = exercises_data["exercises"]
    schedule = exercises_data["schedule"]

    for day_str, day_info in schedule.items():
        day_id = int(day_str)
        day_name = day_info["day_name"]

        for order, entry in enumerate(day_info["exercises"], start=1):
            ex_id = entry["exercise_id"]
            ex_def = exercises_catalog.get(ex_id, {})
            ex_name = ex_def.get("name", ex_id)
            equipment = ex_def.get("equipment", "unknown")

            # Use override weights if provided, else baseline
            if weight_overrides and (day_id, ex_id) in weight_overrides:
                weights = weight_overrides[(day_id, ex_id)]
            else:
                weights = entry["baseline_weights"]

            target_weight_json = json.dumps(weights)
            linked = entry.get("linked_to")
            linked_day = linked["day"] if linked else None
            linked_ex_id = linked["exercise_id"] if linked else None

            # Insert into workout_plan
            cursor.execute('''
                INSERT INTO workout_plan (
                    week_id, day, day_name, exercise_order, exercise_id, exercise_name,
                    sets, target_reps, target_weight_json, strategy, rounding,
                    superset_group, equipment, linked_day, linked_exercise_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                week_id, day_id, day_name, order, ex_id, ex_name,
                entry["sets"], str(entry["target_reps"]), target_weight_json,
                entry["strategy"], entry["rounding"],
                entry.get("superset_group"), equipment,
                linked_day, linked_ex_id
            ))

            # Pre-populate workout_logs with one row per set (actual_* = NULL)
            for set_num in range(1, entry["sets"] + 1):
                w = weights[set_num - 1] if set_num - 1 < len(weights) else weights[-1]
                cursor.execute('''
                    INSERT OR IGNORE INTO workout_logs (
                        week_id, day, exercise_id, exercise_name, exercise_order,
                        set_number, target_weight, target_reps,
                        superset_group, strategy, rounding, equipment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    week_id, day_id, ex_id, ex_name, order,
                    set_num, w, str(entry["target_reps"]),
                    entry.get("superset_group"), entry["strategy"],
                    entry["rounding"], equipment
                ))


def _migrate_csv_to_db(cursor):
    """Import existing CSV data into the new DB tables (idempotent)."""
    import csv

    project_root = Path(__file__).resolve().parent.parent
    body_csv = project_root / "data" / "metrics" / "body_composition.csv"
    health_csv = project_root / "data" / "metrics" / "apple_health.csv"

    if body_csv.exists():
        try:
            with open(body_csv, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute('''
                        INSERT OR REPLACE INTO renpho_body_comp
                        (date, weight_kg, bmi, bodyfat_pct, water_pct, muscle_mass_kg,
                         bone_mass_kg, bmr_kcal, visceral_fat, subcutaneous_fat_pct,
                         protein_pct, metabolic_age)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get("Date", ""),
                        _float(row.get("Weight_kg")),
                        _float(row.get("BMI")),
                        _float(row.get("BodyFat_pct")),
                        _float(row.get("Water_pct")),
                        _float(row.get("MuscleMass_kg")),
                        _float(row.get("BoneMass_kg")),
                        _float(row.get("BMR_kcal")),
                        _float(row.get("VisceralFat")),
                        _float(row.get("SubcutaneousFat_pct")),
                        _float(row.get("Protein_pct")),
                        _float(row.get("MetabolicAge")),
                    ))
            print("✓ Migrated body composition CSV → renpho_body_comp")
        except Exception as e:
            print(f"⚠ Could not migrate body CSV: {e}")

    if health_csv.exists():
        try:
            with open(health_csv, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cursor.execute('''
                        INSERT OR REPLACE INTO apple_health
                        (date, active_kcal, resting_kcal, steps, distance_km,
                         sleep_total_hrs, sleep_deep_min, sleep_rem_min,
                         sleep_core_min, sleep_awake_min)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get("Date", ""),
                        _float(row.get("Active_Kcal")),
                        _float(row.get("Resting_Kcal")),
                        _int(row.get("Steps")),
                        _float(row.get("Distance_Km")),
                        _float(row.get("Sleep_Total_Hrs")),
                        _float(row.get("Sleep_Deep_Min")),
                        _float(row.get("Sleep_REM_Min")),
                        _float(row.get("Sleep_Core_Min")),
                        _float(row.get("Sleep_Awake_Min")),
                    ))
            print("✓ Migrated apple health CSV → apple_health")
        except Exception as e:
            print(f"⚠ Could not migrate health CSV: {e}")


def _float(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _int(val):
    try:
        return int(float(val)) if val else None
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    init_db()

import sqlite3
import pandas as pd
import os
import json

DB_NAME = "gym.db"
EXCEL_FILE = "gym_routine_master.xlsx"

def init_db():
    # 1. Connect (creates file if not exists)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # 2. CREATE TABLES (With JSON Support)
    # ---------------------------------------------------------
    
    # Table: Active Plan
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workout_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_id INTEGER,
        day INTEGER,
        day_name TEXT,
        exercise_order INTEGER,
        exercise TEXT,
        sets INTEGER,
        target_reps TEXT,
        target_weight_json TEXT, -- Stores "[22, 19.5, 17]"
        strategy TEXT,
        rounding REAL,
        superset_group TEXT,
        completed BOOLEAN DEFAULT 0
    )
    ''')

    # Table: Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workout_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        week_id INTEGER,
        day INTEGER,
        exercise TEXT,
        actual_weight_json TEXT,
        actual_reps_json TEXT,
        rpe INTEGER
    )
    ''')
    
    # Table: User Stats
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    print("Tables initialized.")

    # ---------------------------------------------------------
    # 3. SEED DATA (Import Week 1 from Excel)
    # ---------------------------------------------------------
    
    # Check if table is empty
    cursor.execute("SELECT count(*) FROM workout_plan")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"Database empty. Seeding Week 1 from {EXCEL_FILE}...")
        
        if not os.path.exists(EXCEL_FILE):
            print(f"ERROR: {EXCEL_FILE} not found! Run the generator script first.")
            return

        # Load Excel
        df = pd.read_excel(EXCEL_FILE)

        # Insert rows
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO workout_plan (
                    week_id, day, day_name, exercise_order, exercise, 
                    sets, target_reps, target_weight_json, strategy, rounding, superset_group
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                1, # Start at Week 1
                row['Day'], 
                row['Day Name'], 
                row['Order'], 
                row['Exercise'], 
                row['Sets'], 
                str(row['Target Reps']), 
                row['target_weight_json'], # This is already a string like "[22, 19.5]"
                row['Strategy'], 
                row['Rounding'],
                row['Superset Group'] if pd.notna(row['Superset Group']) else None
            ))
        
        # Initialize Bench Cycle
        cursor.execute("INSERT OR REPLACE INTO user_stats (key, value) VALUES (?, ?)", 
                       ("current_bench_cycle_week", "1"))
        # Baseline 1RM for bench press (user-defined: 90kg)
        cursor.execute("INSERT OR REPLACE INTO user_stats (key, value) VALUES (?, ?)",
                       ("bench_1rm", "90"))
        
        print("Week 1 seeded successfully!")
    else:
        print("Database already contains data. Skipping seed.")

    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} is ready.")

if __name__ == "__main__":
    init_db()
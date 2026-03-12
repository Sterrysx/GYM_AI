import os
import json
import csv
import glob
from datetime import datetime
from sqlalchemy.orm import Session
from backend.db.init import SessionLocal, init_db
from backend.db.schema import (
    Session as DbSession, SessionExercise, Set,
    DailyMetric, BodyComposition, Exercise
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
WORKOUTS_DIR = os.path.join(DATA_DIR, 'workouts')
METRICS_DIR = os.path.join(DATA_DIR, 'metrics')

def migrate_workouts(db: Session):
    files = glob.glob(os.path.join(WORKOUTS_DIR, '*.json'))
    sessions_added = 0
    sets_added = 0
    
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            
        date_str = data.get('date')
        if not date_str:
            continue
            
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
            
        # Check if session exists
        existing = db.query(DbSession).filter(DbSession.date == date_obj).first()
        if existing:
            continue
            
        session = DbSession(
            date=date_obj,
            day_label=f"Day{data.get('day', 0)}_{data.get('day_name', 'Workout')}",
            week_number=data.get('week_id', 1)
        )
        db.add(session)
        db.flush() # get session.id
        sessions_added += 1
        
        exercises = data.get('exercises', [])
        for order_idx, ex_data in enumerate(exercises, start=1):
            ex_id_str = ex_data.get('exercise_id')
            
            ex_obj = db.query(Exercise).filter(Exercise.name == ex_data.get('exercise', ex_id_str)).first()
            if not ex_obj:
               # Fallback to exercise_id match if name is not matched
               ex_obj = db.query(Exercise).filter(Exercise.name == ex_id_str).first()
               if not ex_obj:
                   # Try to create dummy if missing
                   ex_obj = Exercise(
                       name=ex_data.get('exercise', ex_id_str),
                       muscle_group="unknown",
                       tier="small",
                       rep_floor=8, rep_ceiling=15,
                       weights_available="[0.0]"
                   )
                   db.add(ex_obj)
                   db.flush()
                   
            sess_ex = SessionExercise(
                session_id=session.id,
                exercise_id=ex_obj.id,
                exercise_order=order_idx,
                is_superset=False
            )
            db.add(sess_ex)
            db.flush()
            
            for set_data in ex_data.get('sets', []):
                weight = float(set_data.get('actual_weight', 0))
                reps = int(set_data.get('actual_reps', 0))
                
                # omit zeroed out unlogged sets
                if weight == 0 and reps == 0:
                    continue
                    
                e1rm = weight * (1 + reps / 30.0)
                
                s = Set(
                    session_exercise_id=sess_ex.id,
                    set_number=int(set_data.get('set', 1)),
                    weight_kg=weight,
                    reps=reps,
                    e1rm=e1rm
                )
                db.add(s)
                sets_added += 1
                
    db.commit()
    print(f"Migrated {sessions_added} sessions and {sets_added} sets.")

def migrate_apple_health(db: Session):
    csv_file = os.path.join(METRICS_DIR, 'apple_health.csv')
    if not os.path.exists(csv_file):
        print("No apple_health.csv found.")
        return
        
    metrics_added = 0
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get('Date')
            if not date_str:
                continue
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
                
            existing = db.query(DailyMetric).filter(DailyMetric.date == date_obj).first()
            if existing:
                continue
                
            metric = DailyMetric(
                date=date_obj,
                steps=int(float(row.get('Steps', 0))),
                active_calories=int(float(row.get('Active_Kcal', 0))),
                sleep_hours=float(row.get('Sleep_Total_Hrs', 0))
            )
            db.add(metric)
            metrics_added += 1
            
    db.commit()
    print(f"Migrated {metrics_added} daily metrics.")

def migrate_body_comp(db: Session):
    csv_file = os.path.join(METRICS_DIR, 'body_composition.csv')
    if not os.path.exists(csv_file):
        print("No body_composition.csv found.")
        return
        
    bc_added = 0
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get('Date', row.get('Timestamp', '')[:10])
            if not date_str:
                continue
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
                
            existing = db.query(BodyComposition).filter(BodyComposition.date == date_obj).first()
            if existing:
                continue
                
            bc = BodyComposition(
                date=date_obj,
                bodyweight_kg=float(row.get('Weight_kg', 0)),
                body_fat_pct=float(row.get('BodyFat_pct', 0)),
                muscle_mass_kg=float(row.get('MuscleMass_kg', 0)),
                water_pct=float(row.get('Water_pct', 0)),
                source="renpho"
            )
            db.add(bc)
            bc_added += 1
            
            # mirror bodyweight to DailyMetric if missing
            metric = db.query(DailyMetric).filter(DailyMetric.date == date_obj).first()
            if not metric:
                metric = DailyMetric(date=date_obj, bodyweight_kg=bc.bodyweight_kg)
                db.add(metric)
            elif not metric.bodyweight_kg:
                metric.bodyweight_kg = bc.bodyweight_kg
                
    db.commit()
    print(f"Migrated {bc_added} body composition records.")

if __name__ == '__main__':
    # Ensure DB is initialized
    init_db()
    
    db = SessionLocal()
    try:
        migrate_workouts(db)
        migrate_apple_health(db)
        migrate_body_comp(db)
        print("Migration complete!")
    finally:
        db.close()

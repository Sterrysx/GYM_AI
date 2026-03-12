from datetime import date
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import json
from contextlib import asynccontextmanager

from db.init import init_db, SessionLocal
from db.schema import Exercise, BenchCycle, Session as DbSessionModel, DailyMetric
from services.progression import compute_next_week, get_bench_cycle_targets, advance_bench_cycle, validate_session_data
from services.session import create_session, get_all_sessions, get_session, log_set, edit_set
from services.metrics import log_apple_health, log_renpho, get_recent_metrics, get_recent_body_composition

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic Models
class SessionCreate(BaseModel):
    date: date
    day_label: str
    week_number: int

class SetCreate(BaseModel):
    set_number: int
    weight_kg: float
    reps: int

class SetEdit(BaseModel):
    weight_kg: Optional[float] = None
    reps: Optional[int] = None

class BenchComplete(BaseModel):
    completed_weight_kg: float

class AppleHealthPayload(BaseModel):
    date: date
    active_energy: float
    resting_energy: float
    steps: int
    km_distance: float
    sleep_total_hrs: float

class BodyCompPayload(BaseModel):
    date: date
    weight_kg: float
    body_fat_pct: float
    muscle_mass_kg: float
    water_pct: float

class ExerciseConfigUpdate(BaseModel):
    weights_available: Optional[Any] = None
    substitution_id: Optional[int] = None


@app.get("/health")
def health_check():
    return {"status": "ok"}


# SESSIONS
@app.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = get_all_sessions(db)
    return [{"id": s.id, "date": s.date, "day_label": s.day_label, "week_number": s.week_number} for s in sessions]

@app.get("/sessions/{session_id}")
def get_session_detail(session_id: int, db: Session = Depends(get_db)):
    s = get_session(db, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    res = {
        "id": s.id,
        "date": s.date,
        "day_label": s.day_label,
         "exercises": []
    }
    for se in s.session_exercises:
        ex_data = {
            "session_exercise_id": se.id,
            "exercise_id": se.exercise_id,
            "exercise_name": se.exercise.name,
            "order": se.exercise_order,
            "sets": [{"id": st.id, "set": st.set_number, "weight": st.weight_kg, "reps": st.reps, "e1rm": st.e1rm} for st in se.sets]
        }
        res["exercises"].append(ex_data)
    return res

@app.post("/sessions")
def create_new_session(payload: SessionCreate, db: Session = Depends(get_db)):
    s = create_session(db, payload.date, payload.day_label, payload.week_number)
    return {"status": "created", "session_id": s.id}

@app.post("/sessions/{session_id}/complete")
def complete_session(session_id: int, db: Session = Depends(get_db)):
    s = get_session(db, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    # Progression targets can be fetched from /progression endpoints
    return {"status": "completed", "message": "Progression ready for next week"}


# SETS
@app.post("/sessions/{session_id}/exercises/{exercise_id}/sets")
def add_set(session_id: int, exercise_id: int, payload: SetCreate, db: Session = Depends(get_db)):
    s = get_session(db, session_id)
    if not s:
         raise HTTPException(404, "Session not found")
         
    se = next((e for e in s.session_exercises if e.exercise_id == exercise_id), None)
    if not se:
        from services.session import add_exercise_to_session
        order = len(s.session_exercises) + 1
        se = add_exercise_to_session(db, session_id, exercise_id, order)
        
    st = log_set(db, se.id, payload.set_number, payload.weight_kg, payload.reps)
    return {"status": "logged", "set_id": st.id}

@app.put("/sets/{set_id}")
def edit_set_endpoint(set_id: int, payload: SetEdit, db: Session = Depends(get_db)):
    st = edit_set(db, set_id, payload.weight_kg, payload.reps)
    if not st:
        raise HTTPException(404, "Set not found")
    return {"status": "edited"}

@app.post("/log/set")
def log_single_set_legacy(payload: dict, db: Session = Depends(get_db)):
    # This matches the old frontend's api.post('/log/set', payload)
    # The frontend payload usually has:
    # { week_id, day, exercise_id, set_idx, weight, reps }
    # Or something similar. Since it wasn't strictly typed matching our new schema:
    session = db.query(DbSessionModel).filter(DbSessionModel.week_number == payload.get("week_id"), DbSessionModel.day_label.like(f"%Day{payload.get('day')}%")).first()
    if not session:
        session = create_session(db, date.today(), f"Day{payload.get('day')}_Workout", payload.get("week_id"))
        
    se = next((e for e in session.session_exercises if e.exercise_id == payload.get("exercise_id")), None)
    if not se:
        from services.session import add_exercise_to_session
        order = len(session.session_exercises) + 1
        se = add_exercise_to_session(db, session.id, payload.get("exercise_id"), order)
        
    st = log_set(db, se.id, payload.get("set_idx", 1), payload.get("weight", 0), payload.get("reps", 0))
    return {"success": True, "set_id": st.id}
    
@app.put("/log/edit")
def edit_set_legacy(payload: dict, db: Session = Depends(get_db)):
    # Legacy wrapper for editSet(payload)
    return edit_set_endpoint(payload.get("set_id"), SetEdit(weight_kg=payload.get("weight"), reps=payload.get("reps")), db)

# PLAN AND WORKOUT VIEWS
@app.get("/plan")
def get_plan(week_id: Optional[int] = None, db: Session = Depends(get_db)):
    # Group sessions by week
    target_week = week_id or db.query(DbSessionModel.week_number).order_by(DbSessionModel.week_number.desc()).first()[0] if db.query(DbSessionModel).count() > 0 else 1
    
    sessions = db.query(DbSessionModel).filter(DbSessionModel.week_number == target_week).all()
    all_weeks = sorted(list(set([s.week_number for s in db.query(DbSessionModel).all()])))
    if target_week not in all_weeks:
        all_weeks.append(target_week)
        
    days_dict = {}
    for s in sessions:
        # Day label format typically f"Day{day}_{day_name}" or similar backfill
        try:
            day_num = int(s.day_label.split('_')[0].replace('Day', ''))
            day_name = s.day_label.split('_')[1] if '_' in s.day_label else "Workout"
        except:
            day_num = len(days_dict) + 1
            day_name = "Workout"
            
        exercises = []
        for se in s.session_exercises:
            ex_data = {
                "exercise_id": se.exercise_id,
                "exercise": se.exercise.name,
                "sets": len(se.sets) if se.sets else 3,
                "target_reps": se.exercise.rep_ceiling,
                "weights": [st.weight_kg for st in se.sets]
            }
            if se.is_superset:
                 ex_data["superset_group"] = se.superset_group
            exercises.append(ex_data)
               
        days_dict[str(day_num)] = {
            "day": day_num,
            "day_name": day_name,
            "exercises": exercises
        }
        
    # Merge with a static template of all 5 days so unlogged days still appear in UI
    template_days = {
        "1": {"day": 1, "day_name": "Push", "exercises": []},
        "2": {"day": 2, "day_name": "Pull", "exercises": []},
        "3": {"day": 3, "day_name": "Legs", "exercises": []},
        "4": {"day": 4, "day_name": "Push", "exercises": []},
        "5": {"day": 5, "day_name": "Pull", "exercises": []}
    }
    
    # Overwrite template with any actually logged days
    for day_str, logged_data in days_dict.items():
        if day_str in template_days:
            template_days[day_str] = logged_data
        else:
            template_days[day_str] = logged_data

    return {
        "weeks": all_weeks,
        "current_week": target_week,
        "days": template_days
    }

@app.get("/workout/{day_id}")
def get_workout(day_id: int, week_id: Optional[int] = None, db: Session = Depends(get_db)):
    target_week = week_id or db.query(DbSessionModel.week_number).order_by(DbSessionModel.week_number.desc()).first()[0] if db.query(DbSessionModel).count() > 0 else 1
    day_str_match = f"Day{day_id}%"
    session = db.query(DbSessionModel).filter(DbSessionModel.week_number == target_week, DbSessionModel.day_label.like(day_str_match)).first()
    
    if not session:
         # Return an empty template rather than nothing so ExerciseCards can render
         return { 
            "day": day_id, 
            "week_id": target_week, 
            "exercises": [
                 # Just a dummy placeholder so it doesn't crash if they click a future unlogged day
                 {"exercise_id": 1, "exercise": "Scheduled Exercises", "sets": 3, "target_reps": 10, "target_weights": ["", "", ""], "sets_data": []}
            ] 
         }
         
    exercises = []
    for se in session.session_exercises:
        sets_data = []
        for i in range(max(3, len(se.sets))):
            st = se.sets[i] if i < len(se.sets) else None
            sets_data.append({
                "set": i + 1,
                "actual_weight": st.weight_kg if st else "",
                "actual_reps": st.reps if st else ""
            })
            
        ex_data = {
            "exercise_id": se.exercise_id,
            "exercise": se.exercise.name,
            "sets": len(sets_data),
            "target_reps": se.exercise.rep_ceiling,
            "target_weights": [st.weight_kg for st in se.sets] if se.sets else [""] * max(3, len(se.sets)),
            "sets_data": sets_data
        }
        if se.is_superset:
             ex_data["superset_group"] = se.superset_group
        exercises.append(ex_data)

    return {
        "day": day_id,
        "week_id": target_week,
        "exercises": exercises
    }



# PROGRESSION
@app.get("/progression/{exercise_id}")
def get_exercise_progression(exercise_id: int, db: Session = Depends(get_db)):
    # Gather historical sessions
    sessions_hist = []
    # simplistic extraction for demonstration; in prod, query join carefully
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
         raise HTTPException(404, "Exercise not found")
         
    from db.schema import SessionExercise
    history = db.query(SessionExercise).filter(SessionExercise.exercise_id == exercise_id).all()
    
    for h in history:
        sets = [{"weight_kg": st.weight_kg, "reps": st.reps} for st in h.sets]
        sessions_hist.append({"exercise_order": h.exercise_order, "sets": sets})
        
    metrics = db.query(DailyMetric).order_by(DailyMetric.date.asc()).all()
    metric_list = [{"bodyweight_kg": m.bodyweight_kg} for m in metrics]
    
    plan = compute_next_week(exercise_id, sessions_hist, metric_list, db)
    return {"exercise": ex.name, "plan": plan}

@app.get("/progression/week")
def get_weekly_progression(db: Session = Depends(get_db)):
    return {"status": "not_implemented"}


# BENCH CYCLE
@app.get("/bench/current")
def get_current_bench(db: Session = Depends(get_db)):
    bc = db.query(BenchCycle).first()
    if not bc:
        return get_bench_cycle_targets(67.5, 1) # fallback
    return get_bench_cycle_targets(bc.bench_pr_kg, bc.cycle_week)

@app.post("/bench/complete")
def complete_bench(payload: BenchComplete, db: Session = Depends(get_db)):
    bc = db.query(BenchCycle).first()
    if not bc:
         raise HTTPException(404, "Bench cycle absent")
    res = advance_bench_cycle(bc.cycle_week, payload.completed_weight_kg, bc.bench_pr_kg, db)
    return {"status": "advanced", "new_cycle": res}


# METRICS
@app.post("/metrics/apple_health")
def apple_health_hook(payload: AppleHealthPayload, db: Session = Depends(get_db)):
    log_apple_health(db, payload.date, payload.active_energy, payload.resting_energy, payload.steps, payload.km_distance, payload.sleep_total_hrs)
    return {"status": "logged"}

@app.post("/metrics/body_composition")
def body_comp_hook(payload: BodyCompPayload, db: Session = Depends(get_db)):
    log_renpho(db, payload.date, payload.weight_kg, payload.body_fat_pct, payload.muscle_mass_kg, payload.water_pct)
    return {"status": "logged"}

@app.get("/metrics/daily")
def read_daily_metrics(db: Session = Depends(get_db)):
    return get_recent_metrics(db)

@app.get("/metrics/body_composition")
def read_body_comp(db: Session = Depends(get_db)):
    return get_recent_body_composition(db)

@app.get("/muscle-levels")
def get_muscle_levels():
    # Legacy RPG styling mock
    return {
        "chest": 15, "back": 12, "legs": 18, 
        "shoulders": 10, "arms": 11, "core": 8, "calves": 5
    }

# LEGACY FRONTEND ALIGNMENT ENDPOINTS
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    target_week = db.query(DbSessionModel.week_number).order_by(DbSessionModel.week_number.desc()).first()[0] if db.query(DbSessionModel).count() > 0 else 1
    bc = db.query(BenchCycle).first()
    
    sessions = db.query(DbSessionModel).filter(DbSessionModel.week_number == target_week).all()
    day_completion = []
    
    for s in sessions:
        try:
            day_num = int(s.day_label.split('_')[0].replace('Day', ''))
            day_name = s.day_label.split('_')[1] if '_' in s.day_label else "Workout"
        except:
            day_num = len(day_completion) + 1
            day_name = "Workout"
            
        planned = len(s.session_exercises)
        logged = sum(1 for se in s.session_exercises if len(se.sets) > 0)
        
        day_completion.append({
            "day": day_num,
            "name": day_name,
            "planned": planned,
            "logged": logged
        })
        
    bench_data = {"sets": 4, "reps": 4, "weight": 70, "intensity_pct": 77, "label": "Volume"}
    if bc:
        b_target = get_bench_cycle_targets(bc.bench_pr_kg, bc.cycle_week)
        bench_data = {
            "sets": b_target.get("target_sets", 4),
            "reps": b_target.get("target_reps", 4),
            "weight": b_target.get("target_weight_kg", 70),
            "intensity_pct": b_target.get("intensity_pct", 77),
            "label": b_target.get("phase", "Volume")
        }

    return {
        "current_week": target_week,
        "bench_cycle_week": bc.cycle_week if bc else 1,
        "bench_1rm": bc.bench_pr_kg if bc else 90,
        "bench_session": bench_data,
        "day_completion": day_completion
    }

@app.get("/has-completed-days")
def check_has_completed_days(db: Session = Depends(get_db)):
    # Check if any sessions exist
    count = db.query(DbSessionModel).count()
    return {"has_completed": count > 0}

@app.post("/complete-day")
def complete_day_legacy(week_id: int, day: int, db: Session = Depends(get_db)):
    # Mark day as completed
    return {"status": "ok"}
    
@app.post("/complete-exercise")
def complete_exercise_legacy(week_id: int, day: int, payload: list, db: Session = Depends(get_db)):
    return {"status": "ok"}
    
@app.get("/dashboard/volume")
def get_volume(db: Session = Depends(get_db)):
    # Legacy chart volume mock
    return {
        "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
        "datasets": [
            {
                "label": "Total Volume (kg)",
                "data": [10000, 11000, 12500, 13000]
            }
        ]
    }

@app.get("/dashboard/metrics")
def get_dashboard_metrics(range: str = "7d", db: Session = Depends(get_db)):
    # Legacy chart metrics mock
    return {
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "datasets": [
            {
                "label": "Bodyweight",
                "yAxisID": "y",
                "data": [65, 65.5, 65.2, 65, 64.8, 65, 65.1]
            }
        ]
    }




# CONFIG
@app.get("/config/exercises")
def list_exercises(db: Session = Depends(get_db)):
    exs = db.query(Exercise).all()
    return [{"id": e.id, "name": e.name, "muscle": e.muscle_group, "weights_available": e.weights_available} for e in exs]

@app.put("/config/exercises/{exercise_id}")
def update_exercise_config(exercise_id: int, payload: ExerciseConfigUpdate, db: Session = Depends(get_db)):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
         raise HTTPException(404, "Exercise not found")
    if payload.weights_available is not None:
         ex.weights_available = json.dumps(payload.weights_available) if isinstance(payload.weights_available, list) else payload.weights_available
    if payload.substitution_id is not None:
         ex.substitution_id = payload.substitution_id
    db.commit()
    return {"status": "updated"}

@app.get("/config/targets")
def get_targets():
    targets_path = os.path.join(os.path.dirname(__file__), 'config', 'targets.json')
    try:
        with open(targets_path, 'r') as f:
            return json.load(f)
    except:
        return {}
        
@app.put("/config/targets")
def update_targets(payload: dict):
    targets_path = os.path.join(os.path.dirname(__file__), 'config', 'targets.json')
    with open(targets_path, 'w') as f:
        json.dump(payload, f, indent=2)
    return {"status": "updated"}

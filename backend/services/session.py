from datetime import date
from sqlalchemy.orm import Session as DbSession
from backend.db.schema import Session, SessionExercise, Set

def create_session(db: DbSession, date_val: date, day_label: str, week_number: int):
    s = Session(date=date_val, day_label=day_label, week_number=week_number)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def get_session(db: DbSession, session_id: int):
    return db.query(Session).filter(Session.id == session_id).first()

def get_all_sessions(db: DbSession):
    return db.query(Session).order_by(Session.date.desc()).all()

def add_exercise_to_session(db: DbSession, session_id: int, exercise_id: int, order: int, is_superset: bool = False, superset_group: int = None):
    se = SessionExercise(
        session_id=session_id,
        exercise_id=exercise_id,
        exercise_order=order,
        is_superset=is_superset,
        superset_group=superset_group
    )
    db.add(se)
    db.commit()
    db.refresh(se)
    return se

def log_set(db: DbSession, session_exercise_id: int, set_number: int, weight_kg: float, reps: int):
    e1rm = weight_kg * (1 + reps / 30.0)
    s = Set(
        session_exercise_id=session_exercise_id,
        set_number=set_number,
        weight_kg=weight_kg,
        reps=reps,
        e1rm=e1rm
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def edit_set(db: DbSession, set_id: int, weight_kg: float = None, reps: int = None):
    s = db.query(Set).filter(Set.id == set_id).first()
    if not s:
        return None
    
    if weight_kg is not None:
        s.weight_kg = weight_kg
    if reps is not None:
        s.reps = reps
        
    s.e1rm = s.weight_kg * (1 + s.reps / 30.0)
    db.commit()
    db.refresh(s)
    return s

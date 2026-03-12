from datetime import date
from sqlalchemy.orm import Session as DbSession
from backend.db.schema import DailyMetric, BodyComposition

def log_apple_health(db: DbSession, date_val: date, active_cal: int, resting_cal: int, steps: int, distance_km: float, sleep_hours: float):
    m = db.query(DailyMetric).filter(DailyMetric.date == date_val).first()
    if not m:
        m = DailyMetric(date=date_val)
        db.add(m)
        
    m.active_calories = active_cal
    m.steps = steps
    m.sleep_hours = sleep_hours
    # Note: distance_km and resting_cal are omitted in daily_metrics per schema but can be added into notes
    m.notes = f"Dist: {distance_km}km, RestingKcal: {resting_cal}"
    
    db.commit()
    db.refresh(m)
    return m

def log_renpho(db: DbSession, date_val: date, weight: float, bf: float, muscle: float, water: float):
    bc = db.query(BodyComposition).filter(BodyComposition.date == date_val, BodyComposition.source == "renpho").first()
    if not bc:
        bc = BodyComposition(date=date_val, source="renpho")
        db.add(bc)
        
    bc.bodyweight_kg = weight
    bc.body_fat_pct = bf
    bc.muscle_mass_kg = muscle
    bc.water_pct = water
    db.commit()
    db.refresh(bc)
    
    # Mirror weight to DailyMetric
    m = db.query(DailyMetric).filter(DailyMetric.date == date_val).first()
    if not m:
        m = DailyMetric(date=date_val, bodyweight_kg=weight)
        db.add(m)
    elif not m.bodyweight_kg:
        m.bodyweight_kg = weight
        
    db.commit()
    return bc

def get_recent_metrics(db: DbSession, limit: int = 14):
    return db.query(DailyMetric).order_by(DailyMetric.date.desc()).limit(limit).all()

def get_recent_body_composition(db: DbSession, limit: int = 14):
    return db.query(BodyComposition).order_by(BodyComposition.date.desc()).limit(limit).all()

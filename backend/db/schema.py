from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import json

Base = declarative_base()

class Exercise(Base):
    __tablename__ = 'exercises'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    muscle_group = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    rep_floor = Column(Integer, nullable=False)
    rep_ceiling = Column(Integer, nullable=False)
    weights_available = Column(String, nullable=False)
    machine_max = Column(Float, nullable=True)
    substitution_id = Column(Integer, ForeignKey('exercises.id'), nullable=True)
    is_bench_cycle = Column(Boolean, nullable=False, default=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    substitution = relationship("Exercise", remote_side=[id])


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    day_label = Column(String, nullable=False)
    week_number = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    session_exercises = relationship("SessionExercise", back_populates="session", cascade="all, delete-orphan")


class SessionExercise(Base):
    __tablename__ = 'session_exercises'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    exercise_order = Column(Integer, nullable=False)
    is_superset = Column(Boolean, default=False)
    superset_group = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)

    session = relationship("Session", back_populates="session_exercises")
    exercise = relationship("Exercise")
    sets = relationship("Set", back_populates="session_exercise", cascade="all, delete-orphan")


class Set(Base):
    __tablename__ = 'sets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_exercise_id = Column(Integer, ForeignKey('session_exercises.id'), nullable=False)
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    e1rm = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

    session_exercise = relationship("SessionExercise", back_populates="sets")


class DailyMetric(Base):
    __tablename__ = 'daily_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    bodyweight_kg = Column(Float, nullable=True)
    sleep_hours = Column(Float, nullable=True)
    sleep_score = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    active_calories = Column(Integer, nullable=True)
    resting_hr = Column(Integer, nullable=True)
    hrv = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())


class BodyComposition(Base):
    __tablename__ = 'body_composition'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    bodyweight_kg = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    water_pct = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())


class BenchCycle(Base):
    __tablename__ = 'bench_cycle'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cycle_week = Column(Integer, nullable=False)
    sets = Column(Integer, nullable=False)
    rep_label = Column(String, nullable=False)
    intensity_factor = Column(Float, nullable=False)
    bench_pr_kg = Column(Float, nullable=False)
    target_weight_kg = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())

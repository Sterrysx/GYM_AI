import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schema import Base, Exercise, BenchCycle

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gym.db')
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_bench_pr():
    targets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'targets.json')
    try:
        with open(targets_path, 'r') as f:
            targets = json.load(f)
            return targets.get("bench_pr_kg", 0.0)
    except Exception:
        return 0.0

def init_db():
    # 1. Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Seed exercises if empty
        if db.query(Exercise).count() == 0:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'exercises.json')
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    for ex_data in data.get("exercises", []):
                        db.add(Exercise(
                            name=ex_data["name"],
                            muscle_group=ex_data["muscle_group"],
                            tier=ex_data["tier"],
                            rep_floor=ex_data["rep_floor"],
                            rep_ceiling=ex_data["rep_ceiling"],
                            weights_available=json.dumps(ex_data["weights_available"]) if isinstance(ex_data["weights_available"], list) else ex_data["weights_available"],
                            machine_max=ex_data.get("machine_max"),
                            is_bench_cycle=ex_data.get("is_bench_cycle", False),
                            notes=ex_data.get("notes")
                        ))
                    db.commit()
                    
                    # Second pass for substitutions if needed
                    for ex_data in data.get("exercises", []):
                        if ex_data.get("substitution"):
                            ex = db.query(Exercise).filter(Exercise.name == ex_data["name"]).first()
                            sub = db.query(Exercise).filter(Exercise.name == ex_data["substitution"]).first()
                            if ex and sub:
                                ex.substitution_id = sub.id
                    db.commit()
            except Exception as e:
                print(f"Warning: Could not seed exercises.json: {e}")

        # 3. Seed bench_cycle if empty
        if db.query(BenchCycle).count() == 0:
            bench_pr_kg = get_bench_pr()
            intensity_factor = 0.75
            target = round((bench_pr_kg * intensity_factor) / 2.5) * 2.5
            
            db.add(BenchCycle(
                cycle_week=1,
                sets=5,
                rep_label="5",
                intensity_factor=intensity_factor,
                bench_pr_kg=bench_pr_kg,
                target_weight_kg=target
            ))
            db.commit()
    finally:
        db.close()

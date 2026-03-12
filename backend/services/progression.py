import json

def validate_session_data(sets: list[dict]) -> list[str]:
    """
    Returns a list of warning strings for suspicious data.
    Empty list = data is clean.
    """
    warnings = []
    
    for i in range(len(sets) - 1):
        if sets[i+1]["weight_kg"] > sets[i]["weight_kg"]:
            warnings.append(f"Set {i+2} weight exceeds set {i+1} — constraint violation")
            
    for i, s in enumerate(sets):
        if s["reps"] < 1:
            warnings.append(f"Set {i+1} has suspiciously low reps (< 1)")
        if s["weight_kg"] <= 0:
            warnings.append(f"Set {i+1} has zero weight")
            
    return warnings

def get_bench_cycle_targets(bench_pr_kg: float, current_week: int) -> dict:
    BENCH_CYCLE = {
        1: {"sets": 5, "rep_label": "5", "intensity": 0.75},
        2: {"sets": 4, "rep_label": "4", "intensity": 0.82},
        3: {"sets": 3, "rep_label": "3", "intensity": 0.88},
        4: {"sets": 2, "rep_label": "2", "intensity": 0.92},
        5: {"sets": 3, "rep_label": "5", "intensity": 0.60},
        6: {"sets": 1, "rep_label": "1", "intensity": 1.02},
    }
    week = BENCH_CYCLE.get(current_week, BENCH_CYCLE[1])
    raw_weight = bench_pr_kg * week["intensity"]
    target_weight = round(raw_weight / 2.5) * 2.5

    sets_list = [
        {"set_number": i + 1, "weight_kg": target_weight, "reps": int(week["rep_label"])}
        for i in range(week["sets"])
    ]
    return {
        "week": current_week,
        "rep_label": week["rep_label"],
        "intensity_factor": week["intensity"],
        "target_weight_kg": target_weight,
        "sets": sets_list
    }

def advance_bench_cycle(current_week: int, completed_weight_kg: float, bench_pr_kg: float, db_session) -> dict:
    from backend.db.schema import BenchCycle

    if current_week == 6:
        new_pr = max(completed_weight_kg, bench_pr_kg)
        next_week = 1
    else:
        new_pr = bench_pr_kg
        next_week = current_week + 1

    cycle = db_session.query(BenchCycle).first()
    if not cycle:
        cycle = BenchCycle()
        db_session.add(cycle)
        
    cycle.cycle_week = next_week
    cycle.bench_pr_kg = new_pr
    
    targets = get_bench_cycle_targets(new_pr, next_week)
    cycle.sets = len(targets["sets"])
    cycle.rep_label = targets["rep_label"]
    cycle.intensity_factor = targets["intensity_factor"]
    cycle.target_weight_kg = targets["target_weight_kg"]
    
    db_session.commit()

    return {"next_week": next_week, "bench_pr_kg": new_pr}

def get_next_weight(current_weight, weights_available, direction):
    if not weights_available:
        return current_weight
        
    if current_weight not in weights_available:
        current_weight = min(weights_available, key=lambda x: abs(x - current_weight))
        
    idx = weights_available.index(current_weight)
    if direction == "up":
        return weights_available[min(idx + 1, len(weights_available) - 1)]
    else:
        return weights_available[max(idx - 1, 0)]

def compute_next_week(exercise_id: int, sessions_history: list[dict], daily_metrics: list[dict], db_session) -> list[dict]:
    from backend.db.schema import Exercise
    exercise = db_session.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        return []

    if exercise.is_bench_cycle:
        return []
        
    if not sessions_history:
        return [{"set_number": 1, "weight_kg": 0.0, "reps": exercise.rep_ceiling}]

    avail_str = exercise.weights_available
    if avail_str == "free_barbell":
        weights_available = [20.0 + i*2.5 for i in range(100)]
    elif avail_str == "free_dumbbell":
        weights_available = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0, 36.0, 38.0, 40.0]
    else:
        try:
            weights_available = json.loads(avail_str)
            if not isinstance(weights_available, list):
                weights_available = [0.0]
        except:
            weights_available = [0.0]
            
    weights_available.sort()

    last_session = sessions_history[-1]
    sets = last_session.get("sets", [])
    if not sets:
         return [{"set_number": 1, "weight_kg": 0.0, "reps": exercise.rep_ceiling}]
         
    s1 = sets[0]
    weight_s1 = s1["weight_kg"]
    reps_s1 = s1["reps"]
    
    drop_rates = []
    for i in range(len(sets) - 1):
        wi = sets[i]["weight_kg"]
        wnext = sets[i+1]["weight_kg"]
        if wi > 0:
            drop_rates.append((wi - wnext) / wi)
    
    drop_rate_mean = sum(drop_rates) / len(drop_rates) if drop_rates else 0.05
    
    if reps_s1 > exercise.rep_ceiling:
        status = "ADD_WEIGHT"
    elif reps_s1 < exercise.rep_floor:
        status = "CHECK_FATIGUE"
    else:
        status = "WITHIN_RANGE"
        
    bw_delta = 0.0
    if len(daily_metrics) >= 8:
        bw_last = daily_metrics[-1].get("bodyweight_kg", 0)
        bw_prev = daily_metrics[-8].get("bodyweight_kg", 0)
        if bw_last and bw_prev:
            bw_delta = bw_last - bw_prev

    decision = "DROP"
    if status == "CHECK_FATIGUE":
        exercise_order_last = last_session.get("exercise_order", 1)
        all_orders = [s.get("exercise_order", 1) for s in sessions_history if s.get("exercise_order") is not None]
        mean_order = sum(all_orders) / len(all_orders) if all_orders else 1
        
        if (exercise_order_last - mean_order) >= 2:
            decision = "HOLD"
            
    next_top_weight = weight_s1
    next_top_reps = reps_s1
    
    substitution_flag = False
    
    if status == "ADD_WEIGHT":
        next_top_weight = get_next_weight(weight_s1, weights_available, "up")
        if exercise.machine_max is not None and next_top_weight >= exercise.machine_max and reps_s1 > exercise.rep_ceiling:
            substitution_flag = True
        next_top_reps = exercise.rep_floor
        
    elif status == "WITHIN_RANGE":
        next_top_reps = min(reps_s1 + 1, exercise.rep_ceiling)
        next_top_weight = weight_s1
        if bw_delta <= 0 and reps_s1 >= exercise.rep_ceiling - 1:
            next_top_weight = get_next_weight(weight_s1, weights_available, "up")
            next_top_reps = exercise.rep_floor
            
    elif status == "CHECK_FATIGUE":
        if decision == "HOLD":
            next_top_weight = weight_s1
            next_top_reps = reps_s1
        else:
            next_top_weight = get_next_weight(weight_s1, weights_available, "down")
            next_top_reps = exercise.rep_ceiling
            
    results = []
    results.append({"set_number": 1, "weight_kg": next_top_weight, "reps": next_top_reps})
    
    num_sets = len(sets)
    if num_sets == 0:
        num_sets = 3
        
    for p in range(2, num_sets + 1):
        target_w = next_top_weight * ((1 - drop_rate_mean) ** (p - 1))
        
        target_w = min(weights_available, key=lambda x: abs(x - target_w))
        
        prev_w = results[-1]["weight_kg"]
        if target_w >= prev_w:
            target_w = get_next_weight(prev_w, weights_available, "down")
            
        results.append({"set_number": p, "weight_kg": target_w, "reps": next_top_reps})
        
    if substitution_flag:
        for r in results:
            r["substitution_flag"] = True
            
    return results

#!/usr/bin/env python3
"""
weekly_coach.py — Deterministic progression engine + optional AI review.

Phase 1 (instant, deterministic):
    Reads last week's per-set logs and applies heuristic progression rules
    to generate next week's weights.  Zero LLM dependency.

Phase 2 (optional, async-friendly):
    Feeds the deterministic plan + logs to a local LLM and asks it to
    propose *minimal* tweaks (edge-cases the heuristic may miss).

Uses the DB schema: workout_logs (per-set), workout_plan, user_stats.
"""

import sqlite3
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import requests

from generate_baseline import (
    load_exercises_catalog,
    SCHEDULE,
    snap_weight,
    get_equipment_rounding,
)

DB_NAME = "gym.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:32b"

# ── Bench periodization percentages (6-week wave) ───────────────────────────
# Each cycle week defines: (sets, reps_per_set, %1RM per set)
BENCH_CYCLE = {
    1: {"sets": 5, "reps": 5, "pcts": [0.75, 0.75, 0.75, 0.75, 0.75]},       # 5×5  Strength
    2: {"sets": 4, "reps": 4, "pcts": [0.80, 0.80, 0.80, 0.80]},              # 4×4  Strength+
    3: {"sets": 3, "reps": 3, "pcts": [0.85, 0.85, 0.85]},                    # 3×3  Heavy
    4: {"sets": 2, "reps": 2, "pcts": [0.90, 0.90]},                          # 2×2  Peak
    5: {"sets": 3, "reps": 5, "pcts": [0.60, 0.60, 0.60]},                    # 3×5  Deload
    6: {"sets": 1, "reps": 1, "pcts": [1.00]},                                # 1×1  PR Test
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def export_week_data(cursor, week_id):
    """Export the plan + per-set logs for archival."""
    os.makedirs("data", exist_ok=True)
    cursor.execute("SELECT * FROM workout_plan WHERE week_id = ?", (week_id,))
    plan_rows = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM workout_logs WHERE week_id = ?", (week_id,))
    log_rows = [dict(row) for row in cursor.fetchall()]
    archive = {"week_id": week_id, "plan": plan_rows, "logs": log_rows}
    filepath = f"data/week_{week_id}.json"
    with open(filepath, "w") as f:
        json.dump(archive, f, indent=2)
    print(f"Exported Week {week_id} data -> {filepath}")


def get_current_body_weight() -> float:
    """Get latest weight from renpho_body_comp table."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT weight_kg FROM renpho_body_comp ORDER BY date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return row["weight_kg"]
    except Exception:
        pass
    return 70.0


def _is_compound(exercise_id: str, catalog: dict) -> bool:
    """Heuristic: compound if it has secondary muscles."""
    ex = catalog.get(exercise_id, {})
    return bool(ex.get("secondary_muscles"))


# ── e1RM estimation constants ────────────────────────────────────────────────
MIN_TARGET_REPS = 6          # lowest rep target the engine will set
MAX_TARGET_REPS = 10         # highest rep target (user prefers 6–10)
INTRASET_FATIGUE_FACTOR = 0.90  # ~10% rep loss per repeated same-weight set
                                 # e.g. 10 → 9 → 8 across three sets
MAX_WEIGHT_JUMP_FACTOR = 3      # cap single-week weight increase at 3× rounding


def _estimate_e1rm(weight: float, reps: int) -> float:
    """Epley formula for estimated one-rep max."""
    if reps <= 0 or weight <= 0:
        return weight
    if reps == 1:
        return weight
    return weight * (1.0 + reps / 30.0)


def _predict_reps_at(e1rm: float, weight: float) -> int:
    """Inverse Epley: predicted reps at *weight* given a known e1RM."""
    if weight <= 0 or e1rm <= 0 or weight >= e1rm:
        return 1
    return max(1, round(30.0 * (e1rm / weight - 1.0)))


def _apply_intraset_fatigue(plan: list) -> list:
    """
    Post-processing pass: for consecutive sets at the SAME weight, enforce
    strictly decreasing rep targets to model intra-session fatigue.

    Rules:
      - Same weight as previous set → target = min(computed, prev_target × FACTOR)
      - The result is ALWAYS < prev_target (strictly decreasing), floor = 1.
        Fatigued sets are allowed to go below MIN_TARGET_REPS (e.g. S3 can land
        on 5 reps when S2 was 7) because that is physiologically realistic.
      - Weight change (drop set or increase) resets the fatigue chain.
      - Non-numeric targets (Failure, 30s…) are passed through unchanged.
    """
    result = list(plan)
    prev_w = None
    prev_r = None

    for i, (w, r_str) in enumerate(result):
        try:
            r = int(r_str)
        except (ValueError, TypeError):
            prev_w = None
            prev_r = None
            continue

        if w == prev_w and prev_r is not None:
            # Same weight — user constraint: reps MUST be the same
            r = prev_r
            result[i] = (w, str(r))
        # else: different weight — reset chain

        prev_w = w
        prev_r = r

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC PROGRESSION (Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

# Performance classifications
_CRUSHED   = "CRUSHED"    # actual ≥ target + 2, or RPE ≤ 6
_EXCEEDED  = "EXCEEDED"   # actual ≥ target + 1, or RPE = 7
_MET       = "MET"        # actual = target, RPE ≤ 8
_STRUGGLED = "STRUGGLED"  # actual = target, RPE ≥ 9
_MISSED    = "MISSED"     # actual = target − 1
_FAILED    = "FAILED"     # actual ≤ target − 2


def _classify_set(target_reps: int, actual_reps: int, rpe: int | None) -> str:
    """
    Classify a set's performance relative to its target.
    RPE modulates the classification when available.
    """
    diff = actual_reps - target_reps

    # RPE overrides when available
    if rpe is not None:
        if diff >= 0 and rpe <= 6:
            return _CRUSHED
        if diff >= 0 and rpe >= 9:
            return _STRUGGLED

    # Rep-based classification
    if diff >= 2:
        return _CRUSHED
    if diff == 1:
        return _EXCEEDED
    if diff == 0:
        # Distinguish met vs struggled via RPE if available
        if rpe is not None and rpe >= 9:
            return _STRUGGLED
        return _MET
    if diff == -1:
        return _MISSED
    return _FAILED  # diff <= -2


def _compute_next_progression(
    current_week: int,
    exercise_id: str,
    equipment: str,
    strategy: str,
    sets_data: list,
    catalog: dict,
) -> tuple:
    """
    Performance-based, RPE-aware per-set progression.

    Returns:
        plan  – [(weight, target_reps_str), …]  one tuple per set
        e1rms – [float, …]  per-set e1RM (used for linked-exercise reconciliation)

    Algorithm (per set):
        1. Classify the set: CRUSHED / EXCEEDED / MET / STRUGGLED / MISSED / FAILED
        2. Based on classification, decide weight action (bump / hold / drop)
        3. Predict reps at the new weight via inverse Epley using per-set e1RM
        4. Apply safeguards (min/max reps, max weight jump)
        5. Important: Ensure strictly descending weights across sets (Y <= X).
    """
    rounding = get_equipment_rounding(equipment)
    compound = _is_compound(exercise_id, catalog)
    ex_def = catalog.get(exercise_id, {})
    custom_increments = ex_def.get("custom_increments")

    plan = []
    e1rms = []
    for s in sorted(sets_data, key=lambda x: x["set_number"]):
        tw = s["target_weight"]
        tr_str = s.get("target_reps", "8")
        aw = s.get("actual_weight")
        ar = s.get("actual_reps")
        rpe = s.get("rpe")

        # ── Non-numeric targets (Failure, 30s, etc.) → carry forward ──
        try:
            tr = int(tr_str)
        except (ValueError, TypeError):
            plan.append((tw, tr_str))
            e1rms.append(0.0)
            continue

        # ── No actual data → carry forward ──
        if aw is None or ar is None or ar <= 0:
            plan.append((tw, tr_str))
            e1rms.append(0.0)
            continue

        # Use actual weight if available, else target
        aw = aw if aw > 0 else tw

        # ── Bodyweight (weight == 0) → target +1 rep ──
        if aw <= 0:
            plan.append((0, str(min(ar + 1, MAX_TARGET_REPS))))
            e1rms.append(0.0)
            continue

        # ── Estimate per-set e1RM ──
        e1rm = _estimate_e1rm(aw, ar)
        e1rms.append(e1rm)

        # ── Classify this set's performance ──
        classification = _classify_set(tr, ar, rpe)

        # ── Compute max allowed weight jump ──
        max_jump = rounding * MAX_WEIGHT_JUMP_FACTOR

        # ── Apply classification-based progression ──
        if classification == _CRUSHED:
            # Aggressive bump: 2× rounding
            bump = min(rounding * 2, max_jump)
            candidate = snap_weight(aw + bump, equipment, custom_increments)
            pred = _predict_reps_at(e1rm, candidate)
            if pred >= MIN_TARGET_REPS:
                plan.append((candidate, str(min(pred, MAX_TARGET_REPS))))
            else:
                # Fallback: 1× rounding
                candidate = snap_weight(aw + rounding, equipment, custom_increments)
                pred = _predict_reps_at(e1rm, candidate)
                plan.append((candidate, str(min(max(pred, MIN_TARGET_REPS), MAX_TARGET_REPS))))

        elif classification == _EXCEEDED:
            # Standard bump: 1× rounding
            candidate = snap_weight(aw + rounding, equipment, custom_increments)
            pred = _predict_reps_at(e1rm, candidate)
            if pred >= MIN_TARGET_REPS:
                plan.append((candidate, str(min(pred, MAX_TARGET_REPS))))
            else:
                # Can't go up — double progression (add 1 rep at same weight)
                plan.append((aw, str(min(ar + 1, MAX_TARGET_REPS))))

        elif classification == _MET:
            # Moderate bump: 1× rounding, but only if predicted reps ≥ MIN
            candidate = snap_weight(aw + rounding, equipment, custom_increments)
            pred = _predict_reps_at(e1rm, candidate)
            if pred >= MIN_TARGET_REPS:
                plan.append((candidate, str(min(pred, MAX_TARGET_REPS))))
            else:
                # Double progression: same weight, +1 rep
                plan.append((aw, str(min(tr + 1, MAX_TARGET_REPS))))

        elif classification == _STRUGGLED:
            # Hold weight, target = actual + 1 (double progression)
            # Don't increase weight if it was a grind
            plan.append((aw, str(min(ar + 1, MAX_TARGET_REPS))))

        elif classification == _MISSED:
            # Keep weight, retry same target
            plan.append((aw, str(tr)))

        elif classification == _FAILED:
            # Drop weight by 1× rounding, predict reps at lower weight
            candidate = snap_weight(max(aw - rounding, rounding), equipment, custom_increments)
            pred = _predict_reps_at(e1rm, candidate)
            plan.append((candidate, str(min(max(pred, MIN_TARGET_REPS), MAX_TARGET_REPS))))

        else:
            # Fallback: carry forward
            plan.append((tw, tr_str))

    # ── Enforce strictly non-increasing weights across consecutive sets ──
    for i in range(1, len(plan)):
        prev_w = plan[i-1][0]
        curr_w, curr_r_str = plan[i]
        try:
            curr_r = int(curr_r_str)
        except (ValueError, TypeError):
            continue
            
        if curr_w > prev_w:
            # Cap the weight at the previous set's weight to prevent increasing weight
            capped_w = prev_w
            # Recalculate reps at the capped weight
            if e1rms[i] > 0:
                pred = _predict_reps_at(e1rms[i], capped_w)
                capped_r_str = str(min(max(pred, MIN_TARGET_REPS), MAX_TARGET_REPS))
            else:
                capped_r_str = curr_r_str
            plan[i] = (capped_w, capped_r_str)

    # ── Apply intra-set fatigue deduction for same-weight consecutive sets ──
    plan = _apply_intraset_fatigue(plan)

    return plan, e1rms


def _compute_bench_plan(bench_1rm: float, next_cycle_week: int) -> list:
    """Compute periodized bench [(weight, reps_str), …] for the cycle week."""
    cycle = BENCH_CYCLE.get(next_cycle_week, BENCH_CYCLE[1])
    reps_str = str(cycle["reps"])
    return [(snap_weight(bench_1rm * pct, "barbell"), reps_str)
            for pct in cycle["pcts"]]


def generate_next_week_deterministic(conn) -> int:
    """
    Deterministic engine: reads current week logs, applies progression
    rules, writes new week into DB.  Returns the new week_id.
    """
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    if not current_week:
        raise RuntimeError("No workout plan found in DB.")

    next_week = current_week + 1
    catalog = load_exercises_catalog()

    # -- Read bench stats --
    cursor.execute("SELECT value FROM user_stats WHERE key='current_bench_cycle_week'")
    row = cursor.fetchone()
    bench_cycle_week = int(row[0]) if row else 1
    next_bench_cycle = (bench_cycle_week % 6) + 1

    cursor.execute("SELECT value FROM user_stats WHERE key='bench_1rm'")
    row = cursor.fetchone()
    bench_1rm = float(row[0]) if row else 90.0

    # -- Gather all logged sets for current week, keyed by (day, exercise_id) --
    cursor.execute("""
        SELECT day, exercise_id, set_number, target_weight, target_reps,
               actual_weight, actual_reps, rpe, strategy, equipment,
               exercise_name, exercise_order, superset_group, rounding
        FROM workout_logs
        WHERE week_id = ?
        ORDER BY day, exercise_order, set_number
    """, (current_week,))

    all_rows = [dict(r) for r in cursor.fetchall()]

    # Group by (day, exercise_id)
    logs_by_ex = defaultdict(list)
    meta_by_ex = {}
    for r in all_rows:
        key = (r["day"], r["exercise_id"])
        logs_by_ex[key].append(r)
        if key not in meta_by_ex:
            meta_by_ex[key] = r  # first row carries the metadata

    # -- Compute next (weight, target_reps) for every exercise --
    # next_plan[(day, ex_id)] = [(weight, reps_str), ...]
    # e1rm_cache[(day, ex_id)] = [e1rm_per_set, ...]
    next_plan = {}
    e1rm_cache = {}

    for key, sets_data in logs_by_ex.items():
        day_id, ex_id = key
        meta = meta_by_ex[key]
        equipment = meta["equipment"]
        strategy = meta["strategy"]

        if strategy == "static":
            next_plan[key] = [
                (s["target_weight"], s.get("target_reps", "30s"))
                for s in sorted(sets_data, key=lambda x: x["set_number"])
            ]
            e1rm_cache[key] = [0.0] * len(sets_data)
            continue

        if strategy == "periodized_bench":
            bench_plan = _compute_bench_plan(bench_1rm, next_bench_cycle)
            next_plan[key] = bench_plan
            e1rm_cache[key] = [0.0] * len(bench_plan)
            continue

        # Normal linear progression (e1RM-based per-set evaluation)
        plan, e1rms = _compute_next_progression(
            current_week, ex_id, equipment, strategy,
            sets_data, catalog,
        )
        next_plan[key] = plan
        e1rm_cache[key] = e1rms

    # -- Reconcile linked exercises --
    # Take the MAX weight per set-position; recalculate reps for the side
    # that got bumped using its own e1RM at the new weight.
    for day_id, day_info in SCHEDULE.items():
        for entry in day_info["exercises"]:
            linked = entry.get("linked_to")
            if not linked:
                continue
            key_a = (day_id, entry["exercise_id"])
            key_b = (linked["day"], linked["exercise_id"])

            if key_a not in next_plan or key_b not in next_plan:
                continue

            pa = next_plan[key_a]
            pb = next_plan[key_b]
            ea = e1rm_cache.get(key_a, [])
            eb = e1rm_cache.get(key_b, [])
            min_len = min(len(pa), len(pb))

            for i in range(min_len):
                wa, ra = pa[i]
                wb, rb = pb[i]
                if wa == wb:
                    continue
                chosen_w = max(wa, wb)
                if chosen_w != wa and i < len(ea) and ea[i] > 0:
                    pred = _predict_reps_at(ea[i], chosen_w)
                    pa[i] = (chosen_w, str(min(max(pred, MIN_TARGET_REPS), MAX_TARGET_REPS)))
                elif chosen_w != wa:
                    pa[i] = (chosen_w, rb)
                if chosen_w != wb and i < len(eb) and eb[i] > 0:
                    pred = _predict_reps_at(eb[i], chosen_w)
                    pb[i] = (chosen_w, str(min(max(pred, MIN_TARGET_REPS), MAX_TARGET_REPS)))
                elif chosen_w != wb:
                    pb[i] = (chosen_w, ra)

    # Second fatigue pass — reconciliation may have created new same-weight
    # consecutive sets that weren't visible before linking was resolved.
    for key in next_plan:
        next_plan[key] = _apply_intraset_fatigue(next_plan[key])

    # -- Write new week into DB --
    for day_id, day_info in SCHEDULE.items():
        day_name = day_info["day_name"]

        for order, entry in enumerate(day_info["exercises"], start=1):
            ex_id = entry["exercise_id"]
            ex_def = catalog.get(ex_id, {})
            ex_name = ex_def.get("name", ex_id)
            equipment = ex_def.get("equipment", "unknown")
            rounding = get_equipment_rounding(equipment)
            strategy = entry["strategy"]
            superset_group = entry.get("superset_group")

            linked = entry.get("linked_to")
            linked_day = linked["day"] if linked else None
            linked_ex_id = linked["exercise_id"] if linked else None

            key = (day_id, ex_id)
            num_sets = entry["sets"]

            # Get plan data: [(weight, reps_str), ...]
            if key in next_plan:
                plan_data = next_plan[key]
            else:
                # Fallback: carry forward weights+reps from previous plan/schedule
                cursor.execute(
                    "SELECT target_weight_json, target_reps FROM workout_plan WHERE week_id=? AND day=? AND exercise_id=?",
                    (current_week, day_id, ex_id),
                )
                row = cursor.fetchone()
                if row:
                    old_weights = json.loads(row[0])
                    old_reps = str(row[1]) if row[1] else str(entry["target_reps"])
                    plan_data = [(w, old_reps) for w in old_weights]
                else:
                    plan_data = [(0, str(entry["target_reps"]))] * num_sets

            # Ensure correct length
            while len(plan_data) < num_sets:
                plan_data.append(plan_data[-1] if plan_data else (0, "8"))
            plan_data = plan_data[:num_sets]

            custom_inc = ex_def.get("custom_increments")
            # Snap weights to equipment increments
            plan_data = [(snap_weight(w, equipment, custom_inc), r) for w, r in plan_data]

            weights = [w for w, _ in plan_data]
            # Representative target_reps for workout_plan (first set's value)
            plan_target_reps = plan_data[0][1]

            cursor.execute("""
                INSERT INTO workout_plan (
                    week_id, day, day_name, exercise_order, exercise_id, exercise_name,
                    sets, target_reps, target_weight_json, strategy, rounding,
                    superset_group, equipment, linked_day, linked_exercise_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_week, day_id, day_name,
                order, ex_id, ex_name,
                num_sets, plan_target_reps, json.dumps(weights),
                strategy, rounding, superset_group, equipment,
                linked_day, linked_ex_id,
            ))

            # Pre-populate workout_logs per set (with per-set target_reps)
            for set_num in range(1, num_sets + 1):
                w, r = plan_data[set_num - 1]
                cursor.execute("""
                    INSERT OR IGNORE INTO workout_logs (
                        week_id, day, exercise_id, exercise_name, exercise_order,
                        set_number, target_weight, target_reps,
                        superset_group, strategy, rounding, equipment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    next_week, day_id, ex_id, ex_name, order,
                    set_num, w, r,
                    superset_group, strategy, rounding, equipment,
                ))

    # -- Advance bench cycle --
    cursor.execute(
        "INSERT OR REPLACE INTO user_stats (key, value) VALUES (?, ?)",
        ("current_bench_cycle_week", str(next_bench_cycle)),
    )

    conn.commit()
    return next_week


# ═══════════════════════════════════════════════════════════════════════════════
# AI REVIEW (Phase 2 — optional, non-blocking)
# ═══════════════════════════════════════════════════════════════════════════════

def ai_review(current_week: int, next_week: int) -> Optional[dict]:
    """
    Feed logs + deterministic plan to LLM; ask for a SHORT list of suggested
    weight tweaks.  Returns a dict like:
        {"suggestions": [{"day": 1, "exercise_id": "...", "set_number": 2,
                          "current_weight": 60.0, "suggested_weight": 62.5,
                          "reason": "..."}]}
    or None if the LLM is unreachable / returns nothing useful.
    """
    try:
        with open(f"data/week_{current_week}.json") as f:
            logs = f.read()

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workout_plan WHERE week_id = ?", (next_week,))
        plan_rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        plan_json = json.dumps(plan_rows, indent=2)

        system_prompt = (
            "You are an elite hypertrophy coach reviewing a programmatically "
            "generated week plan.\n"
            "You are given:\n"
            "1. Last week's per-set logs (actual weight, reps, RPE).\n"
            "2. The DETERMINISTIC next-week plan already generated by a heuristic engine.\n\n"
            "Your job: identify ONLY the edge-cases the heuristic missed. Examples:\n"
            "- An exercise where the lifter clearly sandbagged (very low RPE) and could jump more.\n"
            "- An exercise where fatigue is accumulating and a deload would be wise.\n"
            "- Linked exercises where weights drifted apart.\n\n"
            "Return a JSON object: {\"suggestions\": [...]} where each suggestion has:\n"
            "  \"day\", \"exercise_id\", \"set_number\", \"current_weight\", "
            "\"suggested_weight\", \"reason\"\n\n"
            "If the plan looks good, return: {\"suggestions\": []}\n"
            "Do NOT rewrite the whole plan. Only suggest MINIMAL changes."
        )

        prompt = (
            f"LAST WEEK LOGS:\n{logs[:8000]}\n\n"
            f"DETERMINISTIC PLAN FOR WEEK {next_week}:\n{plan_json[:8000]}"
        )

        payload = {
            "model": MODEL_NAME,
            "system": system_prompt,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }

        print(f"  AI Review: pinging {MODEL_NAME} for suggestions...")
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        result = json.loads(resp.json()["response"])
        suggestions = result.get("suggestions", [])
        if suggestions:
            print(f"  AI proposed {len(suggestions)} tweak(s).")
        else:
            print("  AI review: heuristic plan looks good, no changes.")
        return result

    except Exception as e:
        print(f"  AI review skipped: {e}")
        return None


def apply_ai_suggestions(next_week: int, suggestions: list):
    """Apply AI-suggested weight tweaks to the already-written plan."""
    if not suggestions:
        return

    conn = sqlite3.connect(DB_NAME)
    catalog = load_exercises_catalog()

    for s in suggestions:
        day = s.get("day")
        ex_id = s.get("exercise_id")
        set_num = s.get("set_number")
        new_w = s.get("suggested_weight")
        reason = s.get("reason", "")

        if not all([day, ex_id, set_num, new_w]):
            continue

        equipment = catalog.get(ex_id, {}).get("equipment", "unknown")
        custom_inc = catalog.get(ex_id, {}).get("custom_increments")
        new_w = snap_weight(new_w, equipment, custom_inc)

        conn.execute("""
            UPDATE workout_logs SET target_weight = ?
            WHERE week_id = ? AND day = ? AND exercise_id = ? AND set_number = ?
        """, (new_w, next_week, day, ex_id, set_num))

        row = conn.execute(
            "SELECT id, target_weight_json FROM workout_plan "
            "WHERE week_id=? AND day=? AND exercise_id=?",
            (next_week, day, ex_id),
        ).fetchone()
        if row:
            weights = json.loads(row[1] if row[1] else "[]")
            if 0 < set_num <= len(weights):
                weights[set_num - 1] = new_w
                conn.execute(
                    "UPDATE workout_plan SET target_weight_json = ? WHERE id = ?",
                    (json.dumps(weights), row[0]),
                )

        print(f"    Day {day} / {ex_id} set {set_num}: -> {new_w}kg  ({reason})")

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def run_weekly_update(use_ai_review: bool = True) -> int:
    """
    Main entry point.
    1. Export current week's data.
    2. Run deterministic progression -> writes new week to DB instantly.
    3. (Optional) Ask AI to review and apply minimal tweaks.

    Returns the new week_id.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(week_id) FROM workout_plan")
    current_week = cursor.fetchone()[0]
    if not current_week:
        conn.close()
        raise RuntimeError("No workout plan found in DB.")

    print(f"--- Generating Week {current_week + 1} (deterministic) ---")

    # 1. Archive
    export_week_data(cursor, current_week)

    # 2. Deterministic progression
    next_week = generate_next_week_deterministic(conn)
    print(f"Week {next_week} generated deterministically and loaded into DB.")

    conn.close()

    # 3. Optional AI review
    if use_ai_review:
        review = ai_review(current_week, next_week)
        if review and review.get("suggestions"):
            apply_ai_suggestions(next_week, review["suggestions"])

    return next_week


if __name__ == "__main__":
    run_weekly_update()

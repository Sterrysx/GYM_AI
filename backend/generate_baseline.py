#!/usr/bin/env python3
"""
generate_baseline.py — Defines the Week 1 programme baseline.

Contains:
  - Equipment weight increments / valid steps
  - The 5-day schedule (exercises, sets, target reps, supersets, links)
  - Week 1 baseline weights per exercise (per set)
  - snap_weight() to enforce equipment-specific weight steps

This file is the SINGLE SOURCE OF TRUTH for programme structure.
exercises.json only holds the exercise catalog (name, equipment, muscles).
"""

import json
from pathlib import Path

EXERCISES_JSON = Path(__file__).resolve().parent / "exercises.json"

# ══════════════════════════════════════════════════════════════════════════════
# EQUIPMENT WEIGHT CONSTRAINTS
# ══════════════════════════════════════════════════════════════════════════════
# Each equipment type defines a sorted list of valid weight increments.
# snap_weight() rounds to the nearest valid value from this list.

EQUIPMENT_INCREMENTS = {
    # Cable with 1 pulley: pin select from 1.25 to 100 in 1.25 steps
    "cable_1_pulley": [round(1.25 * i, 2) for i in range(1, 81)],

    # Cable with 2 pulleys: pin select from 5 to 100 in 5 steps
    "cable_2_pulley": [round(5 * i, 1) for i in range(1, 21)],

    # Disks (plates): 1.25, 2.5, 5, 10, 15, 20 kg
    # Actual loadable: any combination, so in practice the minimum step is 1.25
    # We list all reachable values from 1.25 to 60 in 1.25 steps
    "disk": [round(1.25 * i, 2) for i in range(1, 49)],

    # Dumbbells: pairs typically go 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36...
    "dumbbells": list(range(1, 11)) + list(range(10, 51, 2)),

    # Barbell: bar (20kg) + plates. Min step 2.5 (two 1.25kg plates).
    # List from 20 to 200 in 2.5 steps
    "barbell": [round(20 + 2.5 * i, 1) for i in range(0, 73)],

    # Machines: typically 5 or 7 kg steps depending on machine
    # Generic list from 5 to 200 in 5 steps (some machines differ; rounding handles it)
    "machine": list(range(5, 201, 5)),

    # Bodyweight: no external weight
    "bodyweight": [0],
}


def snap_weight(weight: float, equipment: str) -> float:
    """Round a weight to the nearest valid value for the equipment type."""
    if weight <= 0:
        return 0.0
    increments = EQUIPMENT_INCREMENTS.get(equipment, [])
    if not increments:
        return weight
    # Find closest valid weight
    closest = min(increments, key=lambda v: abs(v - weight))
    return float(closest)


# ══════════════════════════════════════════════════════════════════════════════
# 5-DAY SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
# Each entry: exercise_id, sets, target_reps (integer), strategy,
#             superset_group, linked_to (optional)
#
# target_reps is always a SINGLE INTEGER for tracked exercises.
# For static (abs) exercises, target_reps is a duration string ("30s", "60s").
# For bodyweight to-failure exercises, target_reps is the string "Failure".

SCHEDULE = {
    1: {
        "day_name": "Push",
        "exercises": [
            {"exercise_id": "barbell_bench_press",      "sets": 5, "target_reps": 5,   "strategy": "periodized_bench", "superset_group": None},
            {"exercise_id": "low_cable_flyes",           "sets": 3, "target_reps": 8,   "strategy": "linear",           "superset_group": "A"},
            {"exercise_id": "frontal_plate_raises",      "sets": 3, "target_reps": 8,   "strategy": "linear",           "superset_group": "A"},
            {"exercise_id": "overhead_cable_tricep_ext", "sets": 3, "target_reps": 10,  "strategy": "linear",           "superset_group": "B",
             "linked_to": {"day": 5, "exercise_id": "overhead_cable_tricep_ext"}},
            {"exercise_id": "lateral_dumbbell_raises",   "sets": 3, "target_reps": 12,  "strategy": "linear",           "superset_group": "B",
             "linked_to": {"day": 5, "exercise_id": "lateral_dumbbell_raises"}},
            {"exercise_id": "tricep_pushdowns",          "sets": 3, "target_reps": 12,  "strategy": "linear",           "superset_group": "C",
             "linked_to": {"day": 5, "exercise_id": "tricep_rope_pulldowns"}},
            {"exercise_id": "lateral_cable_raises",      "sets": 3, "target_reps": 12,  "strategy": "linear",           "superset_group": "C",
             "linked_to": {"day": 5, "exercise_id": "lateral_cable_raises"}},
            # Abs circuit
            {"exercise_id": "abs_figure_8s",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_hands_back_raises", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_lower_abs_up_down", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_left",    "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_right",   "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_scissor_v_ups",     "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_21_crunch",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
        ],
    },
    2: {
        "day_name": "Pull",
        "exercises": [
            {"exercise_id": "lat_pulldowns",              "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": None},
            {"exercise_id": "machine_closed_row",         "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "A"},
            {"exercise_id": "standing_finger_plate_curls", "sets": 3, "target_reps": 20, "strategy": "linear", "superset_group": "A"},
            {"exercise_id": "cable_bicep_open_curls",     "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "B",
             "linked_to": {"day": 5, "exercise_id": "cable_bicep_open_curls"}},
            {"exercise_id": "reverse_cable_flyes",        "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "B",
             "linked_to": {"day": 5, "exercise_id": "reverse_cable_flyes"}},
            {"exercise_id": "dumbbell_hammer_curls",      "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "C",
             "linked_to": {"day": 5, "exercise_id": "dumbbell_hammer_curls"}},
            {"exercise_id": "trapezoid_raises",           "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "C"},
            # Abs circuit
            {"exercise_id": "abs_figure_8s",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_hands_back_raises", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_lower_abs_up_down", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_left",    "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_right",   "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_scissor_v_ups",     "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_21_crunch",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
        ],
    },
    3: {
        "day_name": "Lower Body",
        "exercises": [
            {"exercise_id": "hip_abduction_machine",   "sets": 3, "target_reps": 20,  "strategy": "linear", "superset_group": "A"},
            {"exercise_id": "glute_machine",           "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "A"},
            {"exercise_id": "lying_leg_curls",         "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "B"},
            {"exercise_id": "leg_extensions",          "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "B"},
            {"exercise_id": "machine_calf_extensions", "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "C"},
            {"exercise_id": "weighted_back_extensions","sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "C"},
            {"exercise_id": "abdominal_crunch_machine","sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": None},
        ],
    },
    4: {
        "day_name": "Chest & Back",
        "exercises": [
            {"exercise_id": "flat_dumbbell_bench_press",    "sets": 3, "target_reps": 10,       "strategy": "linear", "superset_group": None},
            {"exercise_id": "incline_dumbbell_bench_press", "sets": 3, "target_reps": 12,       "strategy": "linear", "superset_group": None},
            {"exercise_id": "machine_open_row",             "sets": 3, "target_reps": 12,       "strategy": "linear", "superset_group": None},
            {"exercise_id": "closed_grip_lat_pulldown",     "sets": 3, "target_reps": 12,       "strategy": "linear", "superset_group": None},
            {"exercise_id": "push_ups",                     "sets": 3, "target_reps": "Failure", "strategy": "linear", "superset_group": "A"},
            {"exercise_id": "pull_ups",                     "sets": 3, "target_reps": "Failure", "strategy": "linear", "superset_group": "A"},
            # Abs circuit
            {"exercise_id": "abs_figure_8s",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_hands_back_raises", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_lower_abs_up_down", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_left",    "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_right",   "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_scissor_v_ups",     "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_21_crunch",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
        ],
    },
    5: {
        "day_name": "Arms",
        "exercises": [
            {"exercise_id": "overhead_cable_tricep_ext", "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "A",
             "linked_to": {"day": 1, "exercise_id": "overhead_cable_tricep_ext"}},
            {"exercise_id": "cable_bicep_open_curls",    "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "A",
             "linked_to": {"day": 2, "exercise_id": "cable_bicep_open_curls"}},
            {"exercise_id": "tricep_rope_pulldowns",     "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "B",
             "linked_to": {"day": 1, "exercise_id": "tricep_pushdowns"}},
            {"exercise_id": "dumbbell_hammer_curls",     "sets": 3, "target_reps": 12,  "strategy": "linear", "superset_group": "B",
             "linked_to": {"day": 2, "exercise_id": "dumbbell_hammer_curls"}},
            {"exercise_id": "lateral_dumbbell_raises",   "sets": 3, "target_reps": 20,  "strategy": "linear", "superset_group": "C",
             "linked_to": {"day": 1, "exercise_id": "lateral_dumbbell_raises"}},
            {"exercise_id": "cable_face_pulls",          "sets": 3, "target_reps": 20,  "strategy": "linear", "superset_group": "C"},
            {"exercise_id": "lateral_cable_raises",      "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "D",
             "linked_to": {"day": 1, "exercise_id": "lateral_cable_raises"}},
            {"exercise_id": "reverse_cable_flyes",       "sets": 3, "target_reps": 15,  "strategy": "linear", "superset_group": "D",
             "linked_to": {"day": 2, "exercise_id": "reverse_cable_flyes"}},
            # Abs circuit
            {"exercise_id": "abs_figure_8s",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_hands_back_raises", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_lower_abs_up_down", "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_left",    "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_seated_8s_right",   "sets": 1, "target_reps": "60s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_scissor_v_ups",     "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
            {"exercise_id": "abs_21_crunch",         "sets": 1, "target_reps": "30s", "strategy": "static", "superset_group": "Abs"},
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# WEEK 1 BASELINE WEIGHTS (per set, drop-set style where applicable)
# ══════════════════════════════════════════════════════════════════════════════
# Key: (day, exercise_id) → list of weights (one per set)
# Static/bodyweight exercises default to [0] × sets.

WEEK1_BASELINES = {
    # ── Day 1: Push ──────────────────────────────────────────────────────────
    (1, "barbell_bench_press"):       [67.5, 67.5, 67.5, 67.5, 67.5],
    (1, "low_cable_flyes"):           [7.5, 7.5, 5],
    (1, "frontal_plate_raises"):      [10, 5, 5],
    (1, "overhead_cable_tricep_ext"): [65, 60, 55],
    (1, "lateral_dumbbell_raises"):   [8, 7, 6],
    (1, "tricep_pushdowns"):          [85, 80, 75],
    (1, "lateral_cable_raises"):      [3.75, 3.75, 2.5],

    # ── Day 2: Pull ──────────────────────────────────────────────────────────
    (2, "lat_pulldowns"):              [70, 60, 50],
    (2, "machine_closed_row"):         [47, 42, 37],
    (2, "standing_finger_plate_curls"):[5, 5, 5],
    (2, "cable_bicep_open_curls"):     [20, 17.5, 15],
    (2, "reverse_cable_flyes"):        [3.75, 2.5, 2.5],
    (2, "dumbbell_hammer_curls"):      [18, 18, 16],
    (2, "trapezoid_raises"):           [24, 22, 20],

    # ── Day 3: Lower Body ────────────────────────────────────────────────────
    (3, "hip_abduction_machine"):      [105, 95, 85],
    (3, "glute_machine"):              [45, 35, 35],
    (3, "lying_leg_curls"):            [21, 21, 14],
    (3, "leg_extensions"):             [40, 35, 30],
    (3, "machine_calf_extensions"):    [50, 45, 40],
    (3, "weighted_back_extensions"):   [10, 5, 5],
    (3, "abdominal_crunch_machine"):   [50, 45, 40],

    # ── Day 4: Chest & Back ──────────────────────────────────────────────────
    (4, "flat_dumbbell_bench_press"):    [26, 26, 22],
    (4, "incline_dumbbell_bench_press"): [22, 20, 20],
    (4, "machine_open_row"):             [47, 42, 37],
    (4, "closed_grip_lat_pulldown"):     [50, 45, 40],
    (4, "push_ups"):                     [0, 0, 0],
    (4, "pull_ups"):                     [0, 0, 0],

    # ── Day 5: Arms ──────────────────────────────────────────────────────────
    (5, "overhead_cable_tricep_ext"):  [65, 60, 55],
    (5, "cable_bicep_open_curls"):     [20, 20, 17.5],
    (5, "tricep_rope_pulldowns"):      [85, 75, 70],
    (5, "dumbbell_hammer_curls"):      [18, 18, 16],
    (5, "lateral_dumbbell_raises"):    [8, 7, 6],
    (5, "cable_face_pulls"):           [55, 50, 45],
    (5, "lateral_cable_raises"):       [3.75, 2.5, 2.5],
    (5, "reverse_cable_flyes"):        [3.75, 2.5, 2.5],
}


def load_exercises_catalog() -> dict:
    """Load the exercises.json catalog (names, equipment, muscles)."""
    with open(EXERCISES_JSON) as f:
        return json.load(f)


def get_equipment_rounding(equipment: str) -> float:
    """Return the minimum weight step for a given equipment type."""
    rounding_map = {
        "cable_1_pulley": 1.25,
        "cable_2_pulley": 5,
        "disk": 1.25,
        "dumbbells": 1,
        "barbell": 2.5,
        "machine": 5,
        "bodyweight": 0,
    }
    return rounding_map.get(equipment, 2.5)


def build_week1_data() -> dict:
    """
    Build the full data structure for Week 1 that init_db.py can consume.

    Returns a dict with:
      - "exercises": the catalog from exercises.json
      - "schedule":  the SCHEDULE dict enriched with baseline_weights and rounding
    """
    catalog = load_exercises_catalog()

    enriched_schedule = {}
    for day_id, day_info in SCHEDULE.items():
        day_str = str(day_id)
        enriched_exercises = []

        for entry in day_info["exercises"]:
            ex_id = entry["exercise_id"]
            ex_def = catalog.get(ex_id, {})
            equipment = ex_def.get("equipment", "unknown")
            rounding = get_equipment_rounding(equipment)

            # Get baseline weights or default to zeros
            raw_weights = WEEK1_BASELINES.get((day_id, ex_id), [0] * entry["sets"])
            # Snap each weight to the nearest valid equipment value
            snapped_weights = [snap_weight(w, equipment) for w in raw_weights]

            enriched = {
                "exercise_id": ex_id,
                "sets": entry["sets"],
                "target_reps": entry["target_reps"],
                "baseline_weights": snapped_weights,
                "strategy": entry["strategy"],
                "rounding": rounding,
                "superset_group": entry.get("superset_group"),
            }
            if entry.get("linked_to"):
                enriched["linked_to"] = entry["linked_to"]

            enriched_exercises.append(enriched)

        enriched_schedule[day_str] = {
            "day_name": day_info["day_name"],
            "exercises": enriched_exercises,
        }

    return {"exercises": catalog, "schedule": enriched_schedule}


def validate_baseline():
    """Check that every exercise in the schedule exists in the catalog."""
    catalog = load_exercises_catalog()
    errors = []
    for day_id, day_info in SCHEDULE.items():
        for entry in day_info["exercises"]:
            ex_id = entry["exercise_id"]
            if ex_id not in catalog:
                errors.append(f"  Day {day_id}: '{ex_id}' not in exercises.json")
            # Check weights match sets count
            weights = WEEK1_BASELINES.get((day_id, ex_id))
            if weights and len(weights) != entry["sets"]:
                errors.append(
                    f"  Day {day_id}: '{ex_id}' has {entry['sets']} sets but "
                    f"{len(weights)} baseline weights"
                )
    return errors


def print_summary():
    """Print a human-readable summary of the Week 1 baseline."""
    catalog = load_exercises_catalog()
    data = build_week1_data()

    print("═" * 70)
    print("  WEEK 1 BASELINE SUMMARY")
    print("═" * 70)

    for day_str in sorted(data["schedule"].keys(), key=int):
        day = data["schedule"][day_str]
        print(f"\n  Day {day_str}: {day['day_name']}")
        print(f"  {'─' * 60}")
        for ex in day["exercises"]:
            ex_id = ex["exercise_id"]
            name = catalog.get(ex_id, {}).get("name", ex_id)
            equipment = catalog.get(ex_id, {}).get("equipment", "?")
            reps = ex["target_reps"]
            weights_str = ", ".join(f"{w}kg" for w in ex["baseline_weights"])

            if ex["strategy"] == "static":
                print(f"    {name:<40} {reps:>6}")
            else:
                print(f"    {name:<40} {ex['sets']}×{reps} reps │ [{weights_str}]  ({equipment})")

    errors = validate_baseline()
    if errors:
        print(f"\n  ⚠  VALIDATION ERRORS:")
        for e in errors:
            print(e)
    else:
        print(f"\n  ✓ All exercises validated against catalog.")


if __name__ == "__main__":
    print_summary()

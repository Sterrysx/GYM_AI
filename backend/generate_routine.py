#!/usr/bin/env python3
"""
generate_routine.py — Builds the initial workout plan from generate_baseline.py
and seeds the database.

Usage:
    python generate_routine.py         # Seeds DB from baseline
    python generate_routine.py --xlsx   # Also exports to Excel for reference
"""

import json
import sys
from pathlib import Path

from generate_baseline import build_week1_data


def build_flat_plan(data, week_id=1):
    """
    Convert the enriched baseline data into a flat list of rows
    suitable for inserting into workout_plan / exporting to Excel.
    """
    exercises_catalog = data["exercises"]
    schedule = data["schedule"]
    rows = []

    for day_str, day_info in schedule.items():
        day_id = int(day_str)
        day_name = day_info["day_name"]

        for order, entry in enumerate(day_info["exercises"], start=1):
            ex_id = entry["exercise_id"]
            ex_def = exercises_catalog.get(ex_id, {})
            ex_name = ex_def.get("name", ex_id)
            equipment = ex_def.get("equipment", "unknown")
            weights = entry["baseline_weights"]
            linked = entry.get("linked_to")

            rows.append({
                "Week": week_id,
                "Day": day_id,
                "Day Name": day_name,
                "Order": order,
                "Exercise ID": ex_id,
                "Exercise": ex_name,
                "Equipment": equipment,
                "Sets": entry["sets"],
                "Target Reps": entry["target_reps"],
                "target_weight_json": json.dumps(weights),
                "Strategy": entry["strategy"],
                "Rounding": entry["rounding"],
                "Superset Group": entry.get("superset_group"),
                "Linked Day": linked["day"] if linked else None,
                "Linked Exercise": linked["exercise_id"] if linked else None,
            })

    return rows


def export_xlsx(rows, filename="gym_routine_master.xlsx"):
    """Optional: export to Excel for easy review."""
    try:
        import pandas as pd
        df = pd.DataFrame(rows)
        cols = [
            "Week", "Day", "Day Name", "Order", "Exercise ID", "Exercise",
            "Equipment", "Sets", "Target Reps", "target_weight_json",
            "Strategy", "Rounding", "Superset Group",
            "Linked Day", "Linked Exercise"
        ]
        df = df[cols]
        df.to_excel(filename, index=False)
        print(f"✓ Exported to {filename}")
    except ImportError:
        print("⚠ pandas/openpyxl not installed — skipping Excel export.")


def main():
    data = build_week1_data()
    rows = build_flat_plan(data)

    print(f"✓ Built plan: {len(rows)} exercise slots across 5 days")

    # List linked exercises
    linked = [(r["Exercise"], r["Day"], r["Linked Day"], r["Linked Exercise"])
              for r in rows if r["Linked Day"] is not None]
    if linked:
        print(f"\n🔗 Linked exercises (same exercise across days):")
        for name, day, lday, lex in linked:
            print(f"   Day {day}: {name} ↔ Day {lday}: {lex}")

    if "--xlsx" in sys.argv:
        export_xlsx(rows)

    # Seed DB
    from init_db import init_db
    init_db()


if __name__ == "__main__":
    main()

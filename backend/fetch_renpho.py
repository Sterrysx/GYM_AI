#!/usr/bin/env python3
"""
fetch_renpho.py  —  Fetch today's Renpho body‐composition reading and
append it to the data‐lake CSV at /data/metrics/body_composition.csv.

Usage:
    python fetch_renpho.py                  # interactive prompt
    python fetch_renpho.py --weight 82.3 --bf 18.2 --mm 35.1   # CLI args
    python fetch_renpho.py --demo           # writes a sample row for testing

The CSV has columns: Date, Weight_kg, BodyFat_pct, MuscleMass_kg
"""

import argparse
import csv
import os
from datetime import date
from pathlib import Path

# ── Resolve paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = PROJECT_ROOT / "data" / "metrics"
CSV_PATH = METRICS_DIR / "body_composition.csv"

FIELDNAMES = ["Date", "Weight_kg", "BodyFat_pct", "MuscleMass_kg"]


def ensure_csv():
    """Create the CSV with headers if it doesn't already exist."""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
        print(f"Created {CSV_PATH}")


def append_row(weight_kg: float, bodyfat_pct: float, muscle_mass_kg: float):
    """Append a single row to the CSV with today's date."""
    ensure_csv()
    today = date.today().isoformat()

    # Check for duplicate date
    if CSV_PATH.stat().st_size > 0:
        with open(CSV_PATH, newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row["Date"] == today:
                    print(f"⚠  Entry for {today} already exists — skipping.")
                    return

    with open(CSV_PATH, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writerow({
            "Date": today,
            "Weight_kg": round(weight_kg, 2),
            "BodyFat_pct": round(bodyfat_pct, 2),
            "MuscleMass_kg": round(muscle_mass_kg, 2),
        })
    print(f"✓  Logged: {today}  |  {weight_kg} kg  |  {bodyfat_pct}% BF  |  {muscle_mass_kg} kg MM")


def interactive_prompt():
    """Prompt for values interactively."""
    print("── Renpho Body Composition Logger ──")
    weight = float(input("Weight (kg): "))
    bf = float(input("Body Fat (%): "))
    mm = float(input("Muscle Mass (kg): "))
    append_row(weight, bf, mm)


def main():
    parser = argparse.ArgumentParser(description="Log Renpho body composition to data lake CSV")
    parser.add_argument("--weight", type=float, help="Body weight in kg")
    parser.add_argument("--bf", type=float, help="Body fat percentage")
    parser.add_argument("--mm", type=float, help="Muscle mass in kg")
    parser.add_argument("--demo", action="store_true", help="Write a demo row (82.5 kg, 18.0%%, 35.2 kg)")
    args = parser.parse_args()

    if args.demo:
        append_row(82.5, 18.0, 35.2)
    elif args.weight and args.bf and args.mm:
        append_row(args.weight, args.bf, args.mm)
    else:
        interactive_prompt()


if __name__ == "__main__":
    main()

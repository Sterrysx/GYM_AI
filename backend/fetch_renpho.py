#!/usr/bin/env python3
"""
fetch_renpho.py — A "Full Refresh" pipeline.
Fetches all historical data from Renpho, filters for the new baseline 
(Feb 16, 2026 onwards), extracts all advanced metrics, and overwrites the CSV.
"""

import os
from datetime import date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from renpho import RenphoClient 

# ── Resolve paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / "backend" / ".env"
METRICS_DIR = PROJECT_ROOT / "data" / "metrics"
CSV_PATH = METRICS_DIR / "body_composition.csv"

# Load credentials from .env
load_dotenv(ENV_PATH)
EMAIL = os.getenv("RENPHO_EMAIL")
PASSWORD = os.getenv("RENPHO_PASSWORD")

# ── The Baseline ─────────────────────────────────────────────────────────────
CUTOFF_DATE = "2026-02-16"

def fetch_from_cloud():
    if not EMAIL or not PASSWORD:
        print("❌ Error: RENPHO_EMAIL or RENPHO_PASSWORD not found in .env file.")
        return

    print(f"Authenticating with Renpho Cloud as {EMAIL}...")
    try:
        client = RenphoClient(EMAIL, PASSWORD)
        client.login()
        print("✓ Login successful. Fetching ALL historical measurements...")

        measurements = client.get_all_measurements()
        
        if not measurements:
            print("No measurements found in this account.")
            return

        processed_data = []

        for m in measurements:
            # FIX: ONLY use the universal UNIX integer. Ignore Renpho's timezone-shifted text strings.
            raw_time = m.get("timeStamp")
            
            if not raw_time:
                continue
                
            # Translate universal epoch time directly to your computer's local timezone (Spain)
            weigh_in_date = date.fromtimestamp(raw_time).isoformat()
            
            # Apply the Baseline filter
            if weigh_in_date >= CUTOFF_DATE:
                processed_data.append({
                    "Date": weigh_in_date,
                    "Weight_kg": m.get("weight"),
                    "BMI": m.get("bmi"),
                    "BodyFat_pct": m.get("bodyfat"),
                    "Water_pct": m.get("water"),
                    "MuscleMass_kg": m.get("muscle"),
                    "BoneMass_kg": m.get("bone"),
                    "BMR_kcal": m.get("bmr"),
                    "VisceralFat": m.get("visfat"),
                    "SubcutaneousFat_pct": m.get("subfat"),
                    "Protein_pct": m.get("protein"),
                    "MetabolicAge": m.get("bodyage"),
                    # Temporarily store exact seconds for mathematically perfect sorting
                    "_exact_time": raw_time 
                })

        if not processed_data:
            print(f"No measurements found on or after {CUTOFF_DATE}.")
            return

        df = pd.DataFrame(processed_data)
        df = df.fillna(0)
        
        # Sort by the exact second you stepped on the scale, oldest to newest
        df = df.sort_values(by="_exact_time")
        
        # Now if there are duplicates for the same day, keep="last" accurately keeps the latest one
        df = df.drop_duplicates(subset=["Date"], keep="last")
        
        # Remove the hidden sorting column before saving
        df = df.drop(columns=["_exact_time"])

        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(CSV_PATH, index=False)

        print(f"✓ Success! Data Lake Refreshed.")
        print(f"✓ Saved {len(df)} daily records starting from {CUTOFF_DATE}.")

    except Exception as e:
        print(f"❌ Failed to fetch from Renpho: {e}")

if __name__ == "__main__":
    fetch_from_cloud()
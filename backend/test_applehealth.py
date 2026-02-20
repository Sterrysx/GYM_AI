import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional, Any

app = FastAPI()

# Matches your "Good Names" exactly from the JSON payload
class WatchPayload(BaseModel):
    date: str
    active_energy: Optional[float] = 0.0
    resting_energy: Optional[float] = 0.0
    steps: Optional[float] = 0.0
    km_distance: Optional[Any] = 0.0  # Captures the string with comma
    sleep_awake: Optional[float] = 0.0
    sleep_rem: Optional[float] = 0.0
    sleep_core: Optional[float] = 0.0
    sleep_deep: Optional[float] = 0.0

@app.post("/webhook/apple-health")
async def receive_test_data(request: Request, payload: WatchPayload):
    # Capture raw body for one last sanity check
    raw_body = await request.body()
    
    # 1. European Comma Fix (string "1,08" -> float 1.08)
    clean_dist = 0.0
    if isinstance(payload.km_distance, str):
        clean_dist = float(payload.km_distance.replace(',', '.'))
    else:
        clean_dist = float(payload.km_distance)

    # 2. Convert raw seconds to minutes for readability
    m_awake = round(payload.sleep_awake / 60, 1)
    m_rem = round(payload.sleep_rem / 60, 1)
    m_core = round(payload.sleep_core / 60, 1)
    m_deep = round(payload.sleep_deep / 60, 1)
    
    # 3. Calculate Total Sleep Hours (Excluding Awake)
    total_sleep_h = round((m_rem + m_core + m_deep) / 60, 2)

    print("\n" + "="*50)
    print("⌚ VERIDICAL APPLE WATCH TRANSMISSION ⌚")
    print("="*50)
    print(f"📅 Date:          {payload.date}")
    print(f"🔥 Active Energy: {payload.active_energy} kcal")
    print(f"🛋️  Resting Energy:{payload.resting_energy} kcal")
    print(f"👟 Steps:         {int(payload.steps)}")
    print(f"🏃 Distance:      {round(clean_dist, 2)} km")
    print("-" * 50)
    print(f"👀 Awake:         {m_awake} min")
    print(f"🧠 REM Sleep:     {m_rem} min")
    print(f"🫀 Core Sleep:    {m_core} min")
    print(f"💪 Deep Sleep:    {m_deep} min")
    print(f"💤 TOTAL SLEEP:   {total_sleep_h} hrs")
    print("="*50)
    print("🐛 DEBUG RAW JSON:")
    print(raw_body.decode('utf-8'))
    print("="*50 + "\n")

    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
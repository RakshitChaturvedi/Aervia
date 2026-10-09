import sys
import os

# Add parent backend directory to sys.path to resolve 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app import models

# Recreate database tables to ensure clean state
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def run_integration_demo():
    print("=" * 60)
    print(" AERVIA END-TO-END INTEGRATION DEMO")
    print("=" * 60)

    # 1. Ingest telemetry for a highly polluted winter trash burning scenario
    print("\n[STEP 1] Ingesting telemetry (Winter Trash Burning Scenario)...")
    payload = {
        "station_id": "esp32_winter_alpha",
        "timestamp": "2026-07-13T22:30:00Z",
        "pm25": 280.0,
        "pm10": 310.0,
        "temp": 12.0,
        "humidity": 85.0,
        "pressure": 1016.0
    }
    ingest_res = client.post("/ingest", json=payload)
    print(f"Response: {ingest_res.status_code} - {ingest_res.json()}")

    # Verify telemetry is in SQLite
    db = SessionLocal()
    reading = db.query(models.SensorReading).filter_by(station_id="esp32_winter_alpha").first()
    print(f"Database Verification: Telemetry successfully logged for {reading.station_id} in SQLite.")
    db.close()

    # 2. Get Source Attribution (runs weak-supervision Random Forest)
    print("\n[STEP 2] Querying /attribution (Runs Random Forest on ingested telemetry)...")
    attr_res = client.get("/attribution")
    print(f"Response Status: {attr_res.status_code}")
    print(f"Attribution Output Contract Shape: {attr_res.json()}")

    # 3. Get Forecast (runs XGBoost with MAPIE conformal intervals)
    print("\n[STEP 3] Querying /forecast (Runs XGBoost forecaster with conformal bands)...")
    forecast_res = client.get("/forecast")
    print(f"Response Status: {forecast_res.status_code}")
    print(f"Forecast Output Contract Shape: {forecast_res.json()}")

    # 4. Run Vehicle Routing Optimization (runs Google OR-Tools CVRPTW solver)
    print("\n[STEP 4] Querying /optimize (Runs OR-Tools optimization based on hotspots)...")
    optimize_res = client.get("/optimize")
    print(f"Response Status: {optimize_res.status_code}")
    print(f"Routing Solver Output: {optimize_res.json()}")
    
    print("\n" + "=" * 60)
    print(" END-TO-END INTEGRATION DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_integration_demo()

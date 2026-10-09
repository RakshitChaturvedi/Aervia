# Aervia: FastAPI Backend & Atmospheric Data Engine

The backend layer for **Aervia** provides high-throughput telemetry ingestion, physics-informed forecasting, satellite data assimilation, and analytical decision pipelines.

## Key Features

1. **FastAPI High-Performance Async REST API**:
   - Live telemetry and historical station observations across monitored cities.
   - 72-hour MAPIE conformal forecasting with XGBoost and CatBoost.
   - CAMS satellite atmospheric NO₂ and aerosol overlays.
   - Comprehensive urban air quality audit and NCAP report generation.

2. **Automated Ingestion Workers**:
   - Background periodic telemetry ingestion from CPCB CAAQMS with resilient fallback to Open-Meteo CAMS network.
   - OpenAQ v3 secondary validation ingestion.
   - Replay mechanics and simulated baseline sensors.

3. **Database & Storage**:
   - SQLite development engine with WAL mode (`aervia.db`).
   - Production PostgreSQL / TimescaleDB continuous aggregates and hypertables.
   - Redis 7 caching and rate limiting with graceful in-memory fallback.

## Getting Started

```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

# Analytical Data Pipeline

```text
1. Data Ingestion
        ↓
2. Data Preprocessing
        ↓
3. Event Detection
        ↓
4. Recovery Profile
        ↓
5. Exposure Burden
        ↓
6. Activity Association
        ↓
7. Intervention Check
        ↓
8. Orchestration + Report Generation
        ↓
9. UI
```

The analytical modules 3–7 are decoupled, independent components for robust testing and operational decision support.

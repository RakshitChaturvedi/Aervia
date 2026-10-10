# 🌍 Aervia

> **Next-Generation Urban Air Quality Intelligence, Forecasting & Atmospheric Analytics Platform**  
> *Physics-Informed Atmospheric Modeling • 72-Hour Conformal Forecasting • Satellite Telemetry Assimilation*

---

Hardware prototype: [complete hardware guide, firmware, wiring and cloud setup](hardware/README.md).

## 🌟 Overview

**Aervia** is an enterprise-grade urban air quality intelligence and predictive atmospheric platform designed for municipal environmental authorities, policymakers, and public citizens. Built with a central operational focus on **Hyderabad** and extensible to major metropolitan clusters nationwide, Aervia combines real-time ground-station telemetry, physics-informed machine learning, and satellite atmospheric composition modeling.

Rather than providing simple static AQI gauges, Aervia models the underlying atmospheric physics—including boundary layer dynamics, thermal inversions, and ventilation indices—to forecast air quality stagnation events before severe pollution accumulates at ground level.

---

## 🚀 Key Capabilities

### 1. 📡 Comprehensive Telemetry Assimilation
* **Multi-Source Data Pipelines**: Continuously ingests official CPCB CAAQMS ground-truth stations from `data.gov.in`, cross-verified with OpenAQ v3 feeds.
* **Resilient Failover**: Automatic fallback to Open-Meteo European Centre for Medium-Range Weather Forecasts (ECMWF) CAMS global atmospheric network during government portal maintenance.
* **Dual AQI Standards**: Dynamic switching between India National Air Quality Index (NAQI, CPCB 2014) and US EPA standards with exact sub-index breakpoint calculations.

### 2. 🌪️ Physics-Informed Hyperlocal Forecasting
* **Multi-Horizon Forecasts**: 24h, 48h, and 72h lead-time predictions for PM2.5 and AQI.
* **Planetary Boundary Layer Height (PBLH)**: Quantifies atmospheric ceiling compression and thermal inversion risks.
* **Ventilation Index ($VI$)**: Computes $VI = \text{PBLH} \times \text{Wind Speed}$, identifying critical air stagnation days before pollutant buildup occurs.
* **Closed-Loop Online Learning**: Exponential Moving Average (EMA) bias correction comparing real incoming observations with historical forecasts to minimize model drift.

### 3. 🛰️ Satellite Geospatial Layers & 3D Telemetry
* **Deck.gl & MapLibre Integration**: High-performance WebGL 3D hex-column layers displaying real-time particulate concentrations.
* **Dynamic Wind Animation**: Particle flow simulations and directional vectors illustrating local dispersion pathways.
* **Sentinel-5P NO₂ Overlay**: Satellite tropospheric vertical column density mapping across urban emission corridors.

### 4. 📊 Multi-City Comparative Synthesis
* **Side-by-Side Metros**: Direct comparison of Hyderabad, Delhi NCR, Bengaluru, Mumbai, and Tier-1 cities.
* **Pollutant Fingerprinting**: 5-axis radar charts showing specific particulate-to-gas distributions (PM2.5, PM10, NO₂, SO₂, O₃).
* **SHAP Explainability**: TreeExplainer attribution detailing the top meteorological and emission drivers of current AQI spikes.

### 5. 🌿 Citizen Health Exposure & Multilingual Advisory
* **Inhaled Dose Calculation**: Translates ambient $\mu g/m^3$ readings into physiological inhaled dose ($\mu g/h$) according to physical activity (resting, walking, cycling, running).
* **Multilingual AI Guidance**: Actionable health advisories generated in English, Hindi, Telugu, and Kannada.

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph INGESTION ["📡 Telemetry & Atmospheric Ingestion"]
        CPCB["CPCB CAAQMS (data.gov.in)"]
        OPENAQ["OpenAQ v3 API"]
        CAMS["Copernicus CAMS / Open-Meteo"]
        INGEST_WORKER["Background Scheduler Worker\n(15-min periodic cycle)"]
        CPCB --> INGEST_WORKER
        OPENAQ --> INGEST_WORKER
        CAMS --> INGEST_WORKER
    end

    subgraph BACKEND ["⚙️ Aervia Core Engine (FastAPI)"]
        DB[("PostgreSQL 16 + TimescaleDB\n/ SQLite WAL (aervia.db)")]
        CACHE[("Redis 7 Cache / Memory Fallback")]
        ML_SERVICE["Physics-Informed ML Service\n(XGBoost + LightGBM + PBLH)"]
        REST_API["FastAPI REST Endpoints\n(4-Tier RBAC + DPDP Act Compliance)"]
        
        INGEST_WORKER --> DB
        DB --> REST_API
        CACHE <--> REST_API
        ML_SERVICE <--> REST_API
    end

    subgraph FRONTEND ["🖥️ Aervia Geospatial Portal (Next.js 13)"]
        DASHBOARD["Executive Command Home (/)"]
        LIVEMAP["3D Deck.gl Live Map (/live-map)"]
        FORECAST["72h Atmospheric Forecast (/forecast)"]
        COMPARE["Multi-City Analytics (/compare)"]
        ADVISORY["Citizen Health Advisory (/advisory)"]
        
        REST_API --> FRONTEND
    end
```

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend Framework** | Next.js 13 (App Router), React 18, TypeScript |
| **Geospatial & 3D Maps** | Deck.gl 8.9, MapLibre GL 5.2, Mapbox GL |
| **Data Visualization** | Recharts, Lucide Icons |
| **Styling & Design** | Vanilla CSS Tokens, Sleek Glassmorphism, Dual Light/Dark System |
| **Backend Framework** | FastAPI (Python 3.11), Uvicorn, Pydantic v2 |
| **Databases** | SQLite 3 (WAL mode) / PostgreSQL 16 with TimescaleDB |
| **Caching & Queues** | Redis 7 with thread-safe in-memory fallback |
| **Machine Learning** | XGBoost, LightGBM, Scikit-Learn, SHAP, Joblib |
| **Authentication** | JWT with 4-Tier RBAC (`super_admin`, `city_officer`, `field_inspector`, `public_viewer`) |

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Git

### 2. Environment Setup
Create a `.env` file in the root directory (or use `.env.example`):
```env
DATAGOV_API_KEY=your_datagov_api_key
CPCB_RESOURCE_ID=3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69
OPENAQ_API_KEY=
JWT_SECRET_KEY=your_secret_key_here
POSTGRES_DB=aervia
POSTGRES_USER=aerviauser
POSTGRES_PASSWORD=your_password_here
DATABASE_URL=sqlite:///./aervia.db
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Backend Setup
```bash
# From repository root
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at `http://127.0.0.1:8000/docs`.

### 4. Frontend Setup
```bash
# In a new terminal, from repository root
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.


---

## 🏛️ Monitored Urban Clusters

1. **Hyderabad (Central Operational Hub)**: 33+ telemetry stations covering Gachibowli, Charminar, Madhapur, Sanathnagar, Secunderabad, and greater GHMC industrial corridors.
2. **Delhi NCR**: Anand Vihar, ITO, Punjabi Bagh, Dwarka, Mandir Marg, Rohini, RK Puram.
3. **Bengaluru**: Silk Board, BTM Layout, Whitefield, Peenya Industrial, Hebbal.
4. **Tier-1 Nationwide Network**: Mumbai, Chennai, Kolkata, Pune, Ahmedabad, Jaipur, Lucknow, Chandigarh, Thiruvananthapuram, Guwahati, Kanpur, Nagpur, Indore, Bhopal, Patna.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

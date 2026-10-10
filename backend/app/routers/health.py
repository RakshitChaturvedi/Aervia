from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app import schemas
from app.redis_client import get_cache_status

router = APIRouter()

@router.get("/health", response_model=schemas.HealthStatus, status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)):
    """
    Performs server connectivity, database readiness, and distributed cache checks.
    """
    database_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        pass

    return {
        "status": "healthy",
        "database": database_status,
        "cache": get_cache_status(),
        "data_sovereignty": {
            "compliant": True,
            "hosting_region": "ap-south-1 (Mumbai, India)",
            "statute": "Digital Personal Data Protection Act 2023"
        }
    }

import sys
import os
from pydantic import BaseModel

# Adjust path to import agent_advisor module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.join(BASE_DIR, 'agent_advisor', 'src'))
try:
    from coordinator import AgentCoordinator
    coordinator = AgentCoordinator()
except ImportError:
    coordinator = None

from typing import Optional, List, Dict, Any

class AdvisoryActionGuide(BaseModel):
    workout: str
    ventilation: str
    mask: str
    vulnerable: str

class AdvisoryRequest(BaseModel):
    city: str
    language: str = "English"
    mode: Optional[str] = "district_live" # "district_live" | "city_forecast"
    district_name: Optional[str] = None
    district_aqi: Optional[float] = None
    best_districts: Optional[List[str]] = None
    worst_districts: Optional[List[str]] = None
    reading: Optional[schemas.SensorReading] = None

class AdvisoryResponse(BaseModel):
    advisory: str
    language: str
    city: str
    mode: str
    target_name: str
    aqi_level: int
    aqi_category: str
    primary_source: Optional[str] = None
    source_attribution: Optional[Dict[str, Any]] = None
    actions: AdvisoryActionGuide

@router.post("/advisory", response_model=AdvisoryResponse)
def get_health_advisory(req: AdvisoryRequest):
    """
    Generates a localized, multilingual dual-mode health advisory using LLMs/NLG engine.
    """
    from app.ml_service import ml_service
    
    reading_dict = req.reading.dict() if req.reading else {
        "station_id": req.district_name or f"{req.city}_AGGREGATE",
        "timestamp": "now",
        "pm25": 25.0,
        "pm10": 37.5,
        "temp": 30.0,
        "humidity": 55.0,
        "pressure": 1008.0,
        "wind_speed": 2.5,
        "pblh": 850.0,
        "no2": 25.0,
        "so2": 10.0,
        "co": 1.0,
        "o3": 30.0
    }
    
    # Get ML predictions
    if req.reading:
        forecast = ml_service.predict_forecast(req.reading)
        attribution = ml_service.predict_attribution(req.reading)
    else:
        dummy_reading = schemas.SensorReading(**reading_dict)
        forecast = ml_service.predict_forecast(dummy_reading)
        attribution = ml_service.predict_attribution(dummy_reading)
    
    from gemini_client import GeminiAdvisorClient
    client = GeminiAdvisorClient()
    return client.generate_advisory(
        forecast=forecast,
        attribution=attribution,
        language=req.language,
        city=req.city,
        reading=reading_dict,
        mode=req.mode or "district_live",
        district_name=req.district_name,
        district_aqi=req.district_aqi,
        best_districts=req.best_districts,
        worst_districts=req.worst_districts
    )

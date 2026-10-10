from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.iot_service import iot_service

router = APIRouter(prefix="/iot", tags=["iot"])

class SensorPublishPayload(BaseModel):
    device_id: Optional[str] = "aervia-54a91ed9b4dc"
    pm1: Optional[float] = None
    pm25: Optional[float] = None
    pm4: Optional[float] = None
    pm10: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    voc_index: Optional[float] = None
    nox_index: Optional[float] = None
    quality_flag: Optional[str] = "OK"

@router.get("/latest")
def get_latest_telemetry():
    """Returns the latest sensor reading received from AWS IoT Core."""
    return iot_service.get_latest()

@router.get("/history")
def get_telemetry_history(limit: int = 50):
    """Returns time-series telemetry buffer of the last N sensor readings."""
    return {"history": iot_service.get_telemetry_history(limit=limit)}

@router.get("/status")
def get_iot_status():
    """Returns current AWS IoT Core MQTT connection status and packet statistics."""
    return iot_service.get_status()

@router.post("/publish")
def publish_sensor_telemetry(payload: SensorPublishPayload):
    """Publishes a test sensor payload to AWS IoT Core MQTT topic."""
    data = payload.model_dump(exclude_unset=True)
    success = iot_service.publish_telemetry(data)
    return {
        "status": "SENT" if success else "ERROR",
        "topic": iot_service.topic,
        "endpoint": iot_service.endpoint,
        "payload": data
    }

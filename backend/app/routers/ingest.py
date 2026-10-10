from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app import schemas

router = APIRouter()

@router.post("/ingest", response_model=schemas.IngestResponse, status_code=status.HTTP_200_OK)
def ingest_reading(reading: schemas.SensorReading, db: Session = Depends(get_db)):
    """
    Ingest live telemetry from the ESP32 weather station.
    Accepts Contract 1 JSON shape, stores it in SQLite, and returns received confirmation.
    """
    db_reading = models.SensorReading(
        station_id=reading.station_id,
        timestamp=reading.timestamp,
        pm25=reading.pm25,
        pm10=reading.pm10,
        temp=reading.temp,
        humidity=reading.humidity,
        pressure=reading.pressure
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return {"status": "received"}

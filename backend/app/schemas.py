from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Contract 1: Sensor -> Backend
class SensorReading(BaseModel):
    station_id: Optional[str] = Field(default="sensor_01", examples=["esp32_01"])
    timestamp: Optional[str] = Field(default="now", examples=["2026-07-07T10:15:00Z"])
    pm25: Optional[float] = Field(default=35.0, examples=[142.3])
    pm10: Optional[float] = Field(default=50.0, examples=[168.9])
    temp: Optional[float] = Field(default=28.0, examples=[31.2])
    humidity: Optional[float] = Field(default=55.0, examples=[58.4])
    pressure: Optional[float] = Field(default=1008.0, examples=[1008.1])
    wind_speed: Optional[float] = Field(default=3.0, examples=[2.5])
    wind_dir: Optional[float] = Field(default=0.0, examples=[180.0])
    pblh: Optional[float] = Field(default=1000.0, examples=[800.0])
    lat: Optional[float] = Field(default=28.6139, examples=[28.6139])
    lon: Optional[float] = Field(default=77.2090, examples=[77.2090])
    no2: Optional[float] = Field(default=25.0, examples=[25.0])
    so2: Optional[float] = Field(default=10.0, examples=[10.0])
    co: Optional[float] = Field(default=1.0, examples=[1.0])
    o3: Optional[float] = Field(default=35.0, examples=[35.0])

# Contract 2: ML -> Backend (Attribution)
class AttributionOutput(BaseModel):
    prediction_set: List[str] = Field(..., examples=[["biomass_burning"]])
    set_size: int = Field(..., examples=[1])
    confidence: float = Field(..., examples=[0.90])
    probabilities: Dict[str, float] = Field(..., examples=[{"biomass_burning": 0.82, "vehicular": 0.11}])
    geospatial_evidence: Dict[str, str] = Field(default=None, description="Correlated geospatial data from TomTom, NASA FIRMS, etc.")
    pinn_source: Dict[str, float] = Field(default=None, description="Plume Inversion PINN origin estimation")

# Contract 3: ML -> Backend/Frontend (Forecast)
class ForecastOutput(BaseModel):
    horizon_h: int = Field(..., examples=[72])
    points: List[float] = Field(..., examples=[[210.0, 215.0, 190.0]])
    intervals: List[List[float]] = Field(..., examples=[[[180.0, 245.0], [185.0, 250.0], [170.0, 210.0]]])
    ventilation_index: float = Field(..., examples=[850.0])

# Contract 4: Dispersion Model
class DispersionPoint(BaseModel):
    lat: float
    lon: float
    aqi: float

class DispersionOutput(BaseModel):
    center_lat: float
    center_lon: float
    grid: List[DispersionPoint]

# New Contract: SHAP Explainability
class SHAPFeature(BaseModel):
    feature: str
    value: float

class SHAPOutput(BaseModel):
    horizon_h: int
    base_value: float
    features: List[SHAPFeature]


# Contract 5: Backend -> Frontend (Optimizer)
class RouteStop(BaseModel):
    source_id: str = Field(..., examples=["s7"])
    lat: float = Field(..., examples=[28.6])
    lon: float = Field(..., examples=[77.2])
    eta: str = Field(..., examples=["10:45"])
    action: str = Field(..., examples=["FULL_INSPECTION"])
    roi: float = Field(..., examples=[54.2])

class RoutePlan(BaseModel):
    route_id: str = Field(..., examples=["inspector_1"])
    stops: List[RouteStop]

# Ingest Response
class IngestResponse(BaseModel):
    status: str = Field(..., examples=["received"])

# Health Endpoint Response
class HealthStatus(BaseModel):
    status: str = Field(..., examples=["healthy"])
    database: str = Field(..., examples=["connected"])
    cache: Optional[Dict[str, Any]] = None
    data_sovereignty: Optional[Dict[str, Any]] = None

# Contract 6: Mobile dispatch alert
class DispatchAlertRequest(BaseModel):
    station_id: str = Field(..., examples=["ST_0"])
    station_name: str = Field(..., examples=["Anand Vihar"])
    lat: float = Field(..., examples=[28.6468])
    lon: float = Field(..., examples=[77.316])
    city: Optional[str] = Field(default="Delhi", examples=["Delhi"])
    aqi: Optional[float] = Field(default=None, examples=[259])
    pm25: Optional[float] = Field(default=None, examples=[57.5])
    stage: Optional[str] = Field(default="dispatched", examples=["dispatched"])
    attribution_set: Optional[List[str]] = Field(default=None, examples=[["vehicular", "biomass_burning"]])
    confidence: Optional[float] = Field(default=None, examples=[0.92])
    message: Optional[str] = Field(
        default=None,
        examples=["AQI spike detected — enforcement dispatched to Anand Vihar"],
    )

class DispatchAlertResponse(BaseModel):
    status: str = Field(..., examples=["sent"])
    notification_id: Optional[str] = Field(default=None, examples=["notif_20260824_001"])
    channel: Optional[str] = Field(default=None, examples=["webhook"])
    delivered_at: Optional[str] = Field(default=None, examples=["2026-08-24T18:30:00Z"])
    error: Optional[str] = Field(default=None)

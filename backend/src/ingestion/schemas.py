"""Validated schemas for Aervia's live IoT payload and auxiliary streams."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


def _first(d: dict[str, Any], *keys: str):
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return None

class RawBase(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    timestamp: datetime | None = None
    source_id: str = "unknown"
    raw_payload: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_common(cls, value):
        if not isinstance(value, dict): return value
        d = dict(value)
        d.setdefault("timestamp", _first(d, "timestamp_ist", "timestamp", "recorded_at"))
        d.setdefault("source_id", _first(d, "device_id", "source_id", "station_id") or "unknown")
        if "raw_payload" not in d: d["raw_payload"] = dict(value)
        return d

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware_if_present(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamp must be timezone-aware when provided")
        return value

class SensorReading(RawBase):
    stream: Literal["sensor"] = "sensor"
    device_id: str | None = None
    boot_id: str | None = None
    sequence: int | None = None
    uptime_s: float | None = None
    pm1: float | None = None
    pm25: float | None = None
    pm4: float | None = None
    pm10: float | None = None
    nc0_5_per_cm3: float | None = None
    nc1_0_per_cm3: float | None = None
    nc2_5_per_cm3: float | None = None
    nc4_per_cm3: float | None = None
    nc10_per_cm3: float | None = None
    typical_particle_size_um: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    voc_index: float | None = None
    nox_index: float | None = None
    sraw_voc: float | None = None
    sraw_nox: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    battery_v: float | None = None
    battery_pct: float | None = None
    wifi_rssi_dbm: float | None = None
    restart_count: int | None = None
    boot_reason: str | None = None
    sps30_state: str | None = None
    bme280_state: str | None = None
    sgp41_state: str | None = None
    sps30_status_raw: int | str | None = None
    fan_fault: bool | None = None
    laser_fault: bool | None = None
    fan_speed_warning: bool | None = None
    quality_flag: str | None = None
    quality_flags: Any = None
    clock_source: str | None = None
    clock_sync_age_s: float | None = None
    usb_packets_sent: int | None = None
    usb_packets_dropped_local: int | None = None
    packets_lost: int | None = None
    queued_samples: int | None = None
    uploaded_samples: int | None = None
    storage_dropped_samples: int | None = None
    # Legacy/internal names retained for downstream compatibility.
    particle_count: float | None = None
    typical_particle_size: float | None = None
    signal_dbm: float | None = None
    packet_seq: int | None = None
    health: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_sensor_fields(cls, value):
        if not isinstance(value, dict): return value
        d = dict(value)
        aliases = {
          "device_id": ("device_id", "source_id"), "sequence": ("sequence", "packet_seq"),
          "pm1": ("pm1_ug_m3", "pm1"), "pm25": ("pm2_5_ug_m3", "pm25", "pm2_5"),
          "pm4": ("pm4_ug_m3", "pm4"), "pm10": ("pm10_ug_m3", "pm10"),
          "typical_particle_size_um": ("typical_particle_size_um", "typical_particle_size"),
          "temperature_c": ("temp_c", "temperature_c"), "humidity_pct": ("humidity_rh_pct", "humidity_pct"),
          "pressure_hpa": ("pressure_hpa",), "wifi_rssi_dbm": ("wifi_rssi_dbm", "signal_dbm"),
        }
        for target, keys in aliases.items():
            v = _first(d, *keys)
            if v is not None: d[target] = v
        if d.get("particle_count") is None:
            d["particle_count"] = _first(d, "nc2_5_per_cm3", "nc1_0_per_cm3")
        if d.get("health") is None: d["health"] = d.get("quality_flag")
        return d

class ActivityObservation(RawBase):
    stream: Literal["activity"] = "activity"
    vehicle_class: str | None = None
    vehicle_count: int | None = Field(default=None, ge=0)
    bus_event: Literal["arrival", "departure", "idling"] | None = None
    bus_id: str | None = None
    crowd_level: str | None = None
    pedestrian_count: int | None = Field(default=None, ge=0)
    dust: bool | None = None
    sweeping: bool | None = None
    construction: bool | None = None
    notes: str | None = None

class WeatherObservation(RawBase):
    stream: Literal["weather"] = "weather"
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    wind_speed_ms: float | None = None
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)

class ReferenceObservation(RawBase):
    stream: Literal["reference"] = "reference"
    station_id: str = "unknown"
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    source_timestamp: datetime | None = None

RawRecord = SensorReading | ActivityObservation | WeatherObservation | ReferenceObservation

class MQTTEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")
    stream: Literal["sensor", "activity", "weather", "reference"]
    payload: dict[str, Any]
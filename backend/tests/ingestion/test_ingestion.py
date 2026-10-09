import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.ingestion import JsonlRawStore, SensorIngestor
from src.ingestion.mqtt_consumer import MQTTIngestionConsumer
from src.ingestion.schemas import SensorReading


def live_payload(**updates):
    row = {
        "sequence": 1,
        "timestamp_ist": "2026-10-09T14:24:46.879+05:30",
        "device_id": "aervia-test",
        "boot_id": "boot-a",
        "pm1_ug_m3": 12.2,
        "pm2_5_ug_m3": 22.4,
        "pm4_ug_m3": 25.0,
        "pm10_ug_m3": 29.1,
        "temp_c": 34.2,
        "humidity_rh_pct": 31.0,
        "pressure_hpa": 944.7,
        "voc_index": 58,
        "nox_index": 1,
        "quality_flag": "ok",
        "quality_flags": [],
        "sps30_state": "READY",
        "sgp41_state": "READY",
    }
    row.update(updates)
    return row


def test_live_iot_schema_maps_fields_and_preserves_payload():
    record = SensorReading.model_validate(live_payload())
    assert record.pm25 == 22.4 and record.pm10 == 29.1
    assert record.temperature_c == 34.2 and record.humidity_pct == 31.0
    assert record.device_id == "aervia-test" and record.sequence == 1
    assert record.raw_payload["pm2_5_ug_m3"] == 22.4


def test_unsynced_timestamp_is_allowed_and_raw_payload_preserved():
    row = live_payload(timestamp_ist=None, clock_source="uptime")
    record = SensorReading.model_validate(row)
    assert record.timestamp is None
    assert record.raw_payload["clock_source"] == "uptime"


def test_missing_timestamp_fields_are_allowed():
    row = live_payload()
    row.pop("timestamp_ist")
    row.pop("timestamp", None)
    record = SensorReading.model_validate(row)
    assert record.timestamp is None


def test_pressure_must_be_numeric_or_null():
    with pytest.raises(ValidationError):
        SensorReading.model_validate(live_payload(pressure_hpa="2026-10-09T14:33:18.878+05:30"))
    assert SensorReading.model_validate(live_payload(pressure_hpa=None)).pressure_hpa is None


def test_sensor_packet_persisted(tmp_path):
    store = JsonlRawStore(tmp_path / "raw")
    ingestor = SensorIngestor(store)
    assert ingestor.ingest(live_payload()) is True
    row = json.loads((tmp_path / "raw/sensor/sensor.jsonl").read_text().splitlines()[0])
    assert row["pm25"] == 22.4 and row["raw_payload"]["pm2_5_ug_m3"] == 22.4


def test_duplicate_sequence_suppressed_within_boot(tmp_path):
    ingestor = SensorIngestor(JsonlRawStore(tmp_path / "raw"))
    row = live_payload()
    assert ingestor.ingest(row) is True and ingestor.ingest(row) is False


def test_same_sequence_on_new_boot_is_not_duplicate(tmp_path):
    ingestor = SensorIngestor(JsonlRawStore(tmp_path / "raw"))
    assert ingestor.ingest(live_payload(boot_id="boot-a")) is True
    assert ingestor.ingest(live_payload(boot_id="boot-b")) is True


def test_timestamp_without_timezone_rejected():
    with pytest.raises(ValidationError):
        SensorReading.model_validate(live_payload(timestamp_ist="2026-10-09T14:24:46"))


def test_mqtt_consumer_accepts_raw_live_sensor_payload(tmp_path):
    consumer = MQTTIngestionConsumer(JsonlRawStore(tmp_path / "raw"))
    assert consumer.handle_message("aervia/sensor", json.dumps(live_payload()).encode()) is True
    assert len((tmp_path / "raw/sensor/sensor.jsonl").read_text().splitlines()) == 1


def test_mqtt_consumer_routes_weather_envelope(tmp_path):
    consumer = MQTTIngestionConsumer(JsonlRawStore(tmp_path / "raw"))
    message = {
        "stream": "weather",
        "payload": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_id": "open-meteo",
            "wind_speed_ms": 2.4,
        },
    }
    assert consumer.handle_message("aervia/weather", json.dumps(message).encode()) is True
    assert len((tmp_path / "raw/weather/weather.jsonl").read_text().splitlines()) == 1
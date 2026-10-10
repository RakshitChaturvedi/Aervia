"""Thin MQTT adapter: parse, validate, persist; never run analytics in callback."""
from __future__ import annotations
import json, logging
from typing import Any
from pydantic import ValidationError
from .activity import ActivityIngestor
from .loaders import JsonlRawStore
from .reference import ReferenceIngestor
from .schemas import MQTTEnvelope
from .sensor import SensorIngestor
from .weather import WeatherIngestor
logger = logging.getLogger(__name__)

class MQTTIngestionConsumer:
    def __init__(self, store: JsonlRawStore) -> None:
        self.sensor = SensorIngestor(store); self.activity = ActivityIngestor(store)
        self.weather = WeatherIngestor(store); self.reference = ReferenceIngestor(store)
    def handle_message(self, topic: str, payload_bytes: bytes | str) -> bool:
        try:
            raw = payload_bytes.decode("utf-8") if isinstance(payload_bytes, bytes) else payload_bytes
            payload: Any = json.loads(raw)
            # Accept either an explicit envelope or a raw sensor payload on sensor topics.
            if isinstance(payload, dict) and "stream" in payload and "payload" in payload:
                envelope = MQTTEnvelope.model_validate(payload); stream, data = envelope.stream, envelope.payload
            else:
                stream = topic.strip("/").split("/")[-1]
                if stream not in {"sensor", "activity", "weather", "reference"}:
                    stream = "sensor" if any(k in payload for k in ("pm2_5_ug_m3", "pm25", "sequence")) else ""
                if not stream: raise ValueError(f"Cannot infer stream from topic {topic!r}")
                data = payload
            if stream == "sensor": return self.sensor.ingest(data)
            if stream == "activity": self.activity.ingest(data)
            elif stream == "weather": self.weather.ingest(data)
            elif stream == "reference": self.reference.ingest(data)
            return True
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, ValueError, TypeError):
            logger.exception("Rejected invalid MQTT message: topic=%s", topic)
            raise
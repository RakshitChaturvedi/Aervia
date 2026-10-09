"""Sensor ingestion, normalization and process-local duplicate suppression."""
from __future__ import annotations
import hashlib, json
from typing import Any
from .loaders import JsonlRawStore
from .schemas import SensorReading

class SensorIngestor:
    def __init__(self, store: JsonlRawStore) -> None:
        self.store = store
        self._seen: set[str] = set()

    @staticmethod
    def packet_key(payload: dict[str, Any]) -> str:
        device = payload.get("device_id", payload.get("source_id", "unknown"))
        boot = payload.get("boot_id", "")
        seq = payload.get("sequence", payload.get("packet_seq"))
        # Sequence only identifies a packet within one device boot.
        if seq is not None:
            identity = f"{device}|{boot}|{seq}"
        else:
            identity = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(identity.encode()).hexdigest()

    def ingest(self, payload: dict[str, Any]) -> bool:
        record = SensorReading.model_validate(payload)
        key = self.packet_key(payload)
        if key in self._seen: return False
        self.store.append(record)
        self._seen.add(key)
        return True
"""External weather observation ingestion."""
from .loaders import JsonlRawStore
from .schemas import WeatherObservation
class WeatherIngestor:
    def __init__(self, store: JsonlRawStore) -> None: self.store = store
    def ingest(self, payload: dict) -> WeatherObservation:
        record = WeatherObservation.model_validate(payload); self.store.append(record); return record
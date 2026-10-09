"""Observer activity-log ingestion."""
from .loaders import JsonlRawStore
from .schemas import ActivityObservation
class ActivityIngestor:
    def __init__(self, store: JsonlRawStore) -> None: self.store = store
    def ingest(self, payload: dict) -> ActivityObservation:
        record = ActivityObservation.model_validate(payload); self.store.append(record); 
        return record
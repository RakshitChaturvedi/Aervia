"""Regional/reference-station ingestion."""
from .loaders import JsonlRawStore
from .schemas import ReferenceObservation
class ReferenceIngestor:
    def __init__(self, store: JsonlRawStore) -> None: self.store = store
    def ingest(self, payload: dict) -> ReferenceObservation:
        record = ReferenceObservation.model_validate(payload); self.store.append(record); return record
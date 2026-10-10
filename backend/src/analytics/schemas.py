from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
import hashlib, json
import pandas as pd

class AnalysisStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INSUFFICIENT_CONTEXT_DATA = "INSUFFICIENT_CONTEXT_DATA"
    NOT_RUN = "NOT_RUN"
    FAILED_VALIDATION = "FAILED_VALIDATION"

@dataclass
class Coverage:
    expected_minutes: float | None = None
    observed_minutes: float | None = None
    eligible_minutes: float | None = None
    coverage_fraction: float | None = None
    notes: list[str] = field(default_factory=list)

@dataclass
class Provenance:
    dataset_id: str
    config: dict[str, Any]
    algorithm_version: str
    time_start_utc: str | None
    time_end_utc: str | None
    input_rows: int
    output_rows: int
    exclusions: list[str] = field(default_factory=list)
    input_fingerprint: str | None = None

@dataclass
class AnalysisResult:
    module: str
    status: AnalysisStatus
    units: dict[str, str]
    time_range: dict[str, str | None]
    coverage: Coverage
    provenance: Provenance
    results: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    valid_outputs: list[str] = field(default_factory=list)

    def to_dict(self):
        obj = asdict(self)
        obj["status"] = self.status.value
        return obj

def fingerprint_dataframe(df):
    return hashlib.sha256(df.to_csv(index=False, na_rep="<NA>").encode()).hexdigest()

def _safe(x):
    if isinstance(x, dict): return {str(k): _safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_safe(v) for v in x]
    if isinstance(x, Enum): return x.value
    if hasattr(x, "item"):
        try: x = x.item()
        except Exception: pass
    if x is None: return None
    try:
        if pd.isna(x): return None
    except (TypeError, ValueError): pass
    return x

def write_json(path, value):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_safe(value), f, indent=2, ensure_ascii=False, default=str)
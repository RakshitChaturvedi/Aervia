"""Append-only JSONL raw storage and robust delimited-file loading."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from .schemas import RawRecord

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$")
_DELIMITERS = ("\t", ",", ";", "|")


class JsonlRawStore:
    """Append validated raw records to one JSONL file per stream."""

    def __init__(self, root: str | Path = "data/raw") -> None:
        self.root = Path(root)
        self._lock = Lock()

    def _path_for(self, stream: str) -> Path:
        directory = self.root / stream
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{stream}.jsonl"

    def append(self, record: RawRecord) -> None:
        path = self._path_for(record.stream)
        line = json.dumps(record.model_dump(mode="json"), separators=(",", ":"), default=str)
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def append_many(self, records: Iterable[RawRecord]) -> int:
        count = 0
        for record in records:
            self.append(record)
            count += 1
        return count


def _detect_delimiter(header: str) -> str:
    """Choose the delimiter with the most occurrences in the header row."""
    counts = {delimiter: header.count(delimiter) for delimiter in _DELIMITERS}
    delimiter, count = max(counts.items(), key=lambda item: item[1])
    if count == 0:
        raise ValueError("Could not detect a delimiter in the file header")
    return delimiter


def _add_quality_flag(row: dict[str, Any], flag: str) -> None:
    existing = row.get("quality_flags")
    if isinstance(existing, str):
        try:
            existing = json.loads(existing)
        except json.JSONDecodeError:
            existing = [part.strip() for part in existing.split(",") if part.strip()]
    if not isinstance(existing, list):
        existing = [] if existing in (None, "") else [str(existing)]
    if flag not in existing:
        existing.append(flag)
    row["quality_flags"] = existing
    row["quality_flag"] = "review"


def _normalize_known_export_corruption(row: dict[str, Any]) -> dict[str, Any]:
    """Quarantine a timestamp accidentally placed in pressure_hpa.

    This is deliberately narrow: only when timestamp_ist is blank and pressure_hpa
    looks like an ISO timestamp. The timestamp is NOT moved to the timestamp field;
    the original row is retained under _raw_csv_row for auditability.
    """
    pressure = row.get("pressure_hpa")
    timestamp = row.get("timestamp_ist")
    if (
        isinstance(pressure, str)
        and pressure.strip()
        and not (timestamp or "").strip()
        and _TIMESTAMP_RE.fullmatch(pressure.strip())
    ):
        original = dict(row)
        row["_raw_csv_row"] = original
        row["pressure_hpa"] = None
        _add_quality_flag(row, "invalid_pressure_field")
    return row


def load_tabular(path: str | Path) -> list[dict[str, Any]]:
    """Load CSV/TSV/semicolon/pipe-delimited files, preserving blank cells as None.

    The sole data repair is the narrowly identified timestamp-in-pressure export
    corruption described in `_normalize_known_export_corruption`; source files are
    never modified.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        first_line = next((line for line in sample.splitlines() if line.strip()), "")
        if not first_line:
            raise ValueError(f"No header found in {path}")
        delimiter = _detect_delimiter(first_line)
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"No header found in {path}")

        rows: list[dict[str, Any]] = []
        for source_row in reader:
            if not any(value not in (None, "") for value in source_row.values()):
                continue
            row = {
                key: (value if value not in (None, "") else None)
                for key, value in source_row.items()
                if key is not None
            }
            rows.append(_normalize_known_export_corruption(row))
        return rows
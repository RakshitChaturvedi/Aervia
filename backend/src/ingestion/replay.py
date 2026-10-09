"""Replay JSONL streams or real CSV/TSV IoT exports through ingestion."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .loaders import load_tabular
from .mqtt_consumer import MQTTIngestionConsumer

STREAMS = ("sensor", "activity", "weather", "reference")
TABULAR_SUFFIXES = {".csv", ".tsv", ".txt"}


@dataclass
class ReplaySummary:
    attempted: int = 0
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "accepted": self.accepted,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "errors": list(self.errors),
        }


def _timestamp(row: dict[str, Any]) -> str:
    value = row.get("timestamp_ist") or row.get("timestamp") or row.get("recorded_at")
    return str(value or "")


def _sort_messages(messages: list[tuple[str, dict[str, Any]]]) -> Iterator[tuple[str, dict[str, Any]]]:
    # Unsynced startup rows stay first in original file order; timed rows sort by
    # their timestamp and remain stable when timestamps are equal.
    indexed = list(enumerate(messages))
    indexed.sort(key=lambda pair: (0 if not pair[1][0] else 1, pair[1][0], pair[0]))
    for _, message in indexed:
        yield message


def iter_messages(input_path: str | Path) -> Iterator[tuple[str, dict[str, Any]]]:
    path = Path(input_path)
    messages: list[tuple[str, dict[str, Any]]] = []

    if path.is_file() and path.suffix.lower() in TABULAR_SUFFIXES:
        for row in load_tabular(path):
            envelope = {"stream": "sensor", "payload": row}
            messages.append((_timestamp(row), envelope))
    elif path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    # Keep a malformed JSONL line as a replayable invalid payload
                    # so the replay loop can count and report it without aborting.
                    obj = {"stream": "__invalid__", "payload": {"_replay_error": f"line {line_number}: {exc}"}}
                    messages.append(("", obj))
                    continue
                stream = obj.get("stream", "sensor") if isinstance(obj, dict) else "sensor"
                envelope = obj if isinstance(obj, dict) and "payload" in obj and "stream" in obj else {"stream": stream, "payload": obj}
                payload = envelope.get("payload")
                messages.append((_timestamp(payload) if isinstance(payload, dict) else "", envelope))
    else:
        found_stream_file = False
        for stream in STREAMS:
            file = path / f"{stream}.jsonl"
            if not file.exists():
                file = path / stream / f"{stream}.jsonl"
            if not file.exists():
                continue
            found_stream_file = True
            with file.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as exc:
                        messages.append(("", {"stream": "__invalid__", "payload": {"_replay_error": f"{file}:{line_number}: {exc}"}}))
                        continue
                    env = obj if isinstance(obj, dict) and obj.get("stream") == stream and "payload" in obj else {"stream": stream, "payload": obj}
                    payload = env.get("payload")
                    messages.append((_timestamp(payload) if isinstance(payload, dict) else "", env))
        if not found_stream_file:
            raise FileNotFoundError(f"No supported stream JSONL files found in {path}")

    yield from _sort_messages(messages)


def replay_directory(input_root: str | Path, consumer: MQTTIngestionConsumer) -> ReplaySummary:
    """Replay every row, count outcomes, and continue after per-record failures."""
    summary = ReplaySummary()
    for _, envelope in iter_messages(input_root):
        summary.attempted += 1
        stream = envelope.get("stream", "sensor") if isinstance(envelope, dict) else "__invalid__"
        topic = f"aervia/{stream}"
        try:
            result = consumer.handle_message(topic, json.dumps(envelope, default=str).encode("utf-8"))
            if result is False:
                summary.duplicates += 1
            else:
                summary.accepted += 1
        except Exception as exc:  # record-level validation errors must not stop replay
            summary.rejected += 1
            payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
            seq = payload.get("sequence") if isinstance(payload, dict) else None
            summary.errors.append(f"record {summary.attempted} (stream={stream}, sequence={seq!r}): {type(exc).__name__}: {exc}")
    return summary
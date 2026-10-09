"""Replay JSONL directories or actual CSV/TSV/TXT exports through ingestion."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.ingestion import JsonlRawStore
from src.ingestion.mqtt_consumer import MQTTIngestionConsumer
from src.ingestion.replay import replay_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="IoT CSV/TSV/TXT export or JSONL stream directory/file")
    parser.add_argument("--output", default="data/raw_replay", help="output root for per-stream JSONL files")
    args = parser.parse_args(argv)

    store = JsonlRawStore(args.output)
    consumer = MQTTIngestionConsumer(store)
    try:
        summary = replay_directory(args.input, consumer)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Replay could not start: {exc}", file=sys.stderr)
        return 2

    print(f"Input:     {args.input}")
    print(f"Output:    {args.output}")
    print(f"Attempted: {summary.attempted}")
    print(f"Accepted:  {summary.accepted}")
    print(f"Duplicates:{summary.duplicates:>4}")
    print(f"Rejected:  {summary.rejected}")
    if summary.errors:
        print("\nRejected record details:", file=sys.stderr)
        for error in summary.errors:
            print(f"- {error}", file=sys.stderr)
    # The replay is complete even when records were rejected; nonzero makes
    # automation/CI notice that the resulting dataset needs review.
    return 1 if summary.rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
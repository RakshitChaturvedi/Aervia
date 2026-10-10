#!/usr/bin/env python3
"""Run Aervia preprocessing against raw CSV or ingestion replay output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Supports `python scripts/preprocess_dataset.py ...` from backend root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.preprocessing.pipeline import PreprocessConfig, preprocess_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="CSV/JSONL file or replay output directory containing sensor.jsonl")
    parser.add_argument("--output", default="data/processed/ft1", help="Output directory")
    parser.add_argument("--baseline-window-min", type=int, default=120)
    parser.add_argument("--baseline-percentile", type=float, default=10.0)
    parser.add_argument("--centered-baseline", action="store_true",
                        help="Sensitivity mode only; uses future samples and is not suitable for live alerts")
    parser.add_argument("--pm-max", type=float, default=1000.0)
    parser.add_argument("--min-valid-fraction", type=float, default=0.8)
    args = parser.parse_args()

    config = PreprocessConfig(
        baseline_window_min=20,
        baseline_percentile=args.baseline_percentile,
        baseline_causal=not args.centered_baseline,
        pm_max=args.pm_max,
        min_valid_fraction_per_minute=args.min_valid_fraction,
    )
    result = preprocess_dataset(args.input, args.output, config)
    print(json.dumps(result.summary, indent=2, default=str))
    print(f"Output written to: {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
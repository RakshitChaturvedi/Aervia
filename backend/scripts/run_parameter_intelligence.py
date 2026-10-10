#!/usr/bin/env python3
"""Run Layer 3A feature engineering on preprocessing outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC = BACKEND_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.parameter_intelligence import FeatureConfig, build_parameter_features  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minute", required=True, help="Path to preprocessing minute.csv")
    parser.add_argument("--samples", help="Optional path to aligned/samples.csv for additional channels")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--rolling-window-min", type=int, default=5)
    parser.add_argument("--min-count-valid-points", type=int, default=3)
    parser.add_argument("--pm-ordering-tolerance", type=float, default=5.0)
    parser.add_argument("--high-humidity-pct", type=float, default=90.0)
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    minute = pd.read_csv(args.minute)
    samples = pd.read_csv(args.samples) if args.samples else None
    config = FeatureConfig(
        rolling_window_min=args.rolling_window_min,
        min_count_valid_points=args.min_count_valid_points,
        pm_ordering_tolerance=args.pm_ordering_tolerance,
        high_humidity_pct=args.high_humidity_pct,
    )
    features, manifest = build_parameter_features(minute, samples=samples, config=config)
    features.to_csv(out_dir / "features.csv", index=False)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out_dir), "rows": len(features), "manifest": manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
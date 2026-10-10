"""Run Layer 4 from Layer 3B JSON outputs."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.warning_engine import WarningConfig, build_warnings


def read_json(path: str | None):
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: str | None):
    if not path:
        return None
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analytics-dir", required=True, help="Directory containing Layer 3B JSON outputs")
    p.add_argument("--features", help="Optional Layer 3A features.csv for diagnostic readiness context")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--dataset-id", help="Optional dataset ID override")
    p.add_argument("--watch-excess", type=float, default=15.0)
    p.add_argument("--elevated-excess", type=float, default=30.0)
    p.add_argument("--severe-excess", type=float, default=75.0)
    args = p.parse_args()

    source = Path(args.analytics_dir)
    event_doc = read_json(str(source / "event_detection.json"))
    if event_doc is None:
        p.error("event_detection.json is required in --analytics-dir")
    recovery_doc = read_json(str(source / "recovery_profile.json"))
    exposure_doc = read_json(str(source / "exposure_burden.json"))
    cfg = WarningConfig(
        watch_excess_ug_m3=args.watch_excess,
        elevated_excess_ug_m3=args.elevated_excess,
        severe_excess_ug_m3=args.severe_excess,
    )
    if not (0 <= cfg.watch_excess_ug_m3 <= cfg.elevated_excess_ug_m3 <= cfg.severe_excess_ug_m3):
        p.error("Thresholds must satisfy 0 <= watch <= elevated <= severe")

    result = build_warnings(event_doc, recovery_doc, exposure_doc,
                            features_rows=read_csv(args.features), config=cfg,
                            dataset_id=args.dataset_id)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "warnings.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = result["warnings"]
    columns = ["warning_id", "event_id", "status", "severity", "priority_score", "warning_type",
               "start_utc", "end_utc", "peak_utc", "peak_pm2_5_ug_m3", "peak_excess_pm2_5_ug_m3",
               "duration_elapsed_minutes", "coverage_fraction", "lifecycle", "recovery_status",
               "positive_excess_integral_ug_h_m3"]
    with (out / "warnings.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": result["status"], "warning_count": result["warning_count"],
                      "issued_warning_count": result["issued_warning_count"], "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
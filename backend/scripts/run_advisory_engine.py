#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, os, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Load backend/.env when python-dotenv is installed; process environment always remains supported.
def load_backend_env():
    env_path = BACKEND / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    parser = argparse.ArgumentParser(description="Generate evidence-grounded Aervia advisories from Layer 4 warnings.")
    parser.add_argument("--warnings", type=Path, required=True, help="Path to Layer 4 warnings.json")
    parser.add_argument("--analytics-dir", type=Path, default=None, help="Optional Layer 3B analytics output directory")
    parser.add_argument("--features", type=Path, default=None, help="Optional Layer 3A features.csv")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--language", default=None, help="Override AERVIA_ADVISORY_LANGUAGE (en, hi, kn, etc.)")
    parser.add_argument("--disable-llm", action="store_true", help="Force deterministic advice, without Gemini")
    args = parser.parse_args()
    load_backend_env()
    from src.advisory.config import AdvisoryConfig
    from src.advisory.engine import AdvisoryEngine

    with args.warnings.open("r", encoding="utf-8") as f:
        warning_payload = json.load(f)
    if not isinstance(warning_payload, dict) or not isinstance(warning_payload.get("warnings"), list):
        raise SystemExit("warnings.json must be an object containing a 'warnings' list")
    config = AdvisoryConfig.from_env()
    if args.language:
        from dataclasses import replace
        config = replace(config, language=args.language)
    if args.disable_llm:
        from dataclasses import replace
        config = replace(config, llm_enabled=False)
    engine = AdvisoryEngine(config)
    records = [engine.generate(w, args.analytics_dir, args.features) for w in warning_payload["warnings"] if isinstance(w, dict) and w.get("status", "ISSUED") == "ISSUED"]
    args.output.mkdir(parents=True, exist_ok=True)
    output_json = args.output / "advisories.json"
    with output_json.open("w", encoding="utf-8") as f:
        json.dump({"layer": "5", "module": "advisory_engine", "status": "OK", "algorithm_version": config.version, "dataset_id": warning_payload.get("dataset_id"), "warning_input_count": len(warning_payload["warnings"]), "advisory_count": len(records), "llm_enabled": config.llm_enabled, "language": config.language, "advisories": records}, f, ensure_ascii=False, indent=2)
    output_csv = args.output / "advisories.csv"
    fields = ["advisory_id", "warning_id", "event_id", "status", "language", "summary", "reasoning", "severity", "generation_mode", "actions_json", "evidence_json", "uncertainty_json", "limitations_json"]
    warning_by_id = {w.get("warning_id"): w for w in warning_payload["warnings"] if isinstance(w, dict)}
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for rec in records:
            warning = warning_by_id.get(rec["warning_id"], {})
            writer.writerow({"advisory_id": rec["advisory_id"], "warning_id": rec["warning_id"], "event_id": rec["event_id"], "status": rec["status"], "language": rec["language"], "summary": rec["summary"], "reasoning": rec["reasoning"], "severity": warning.get("severity"), "generation_mode": rec["generation_mode"], "actions_json": json.dumps(rec["actions"], ensure_ascii=False), "evidence_json": json.dumps(rec["evidence"], ensure_ascii=False), "uncertainty_json": json.dumps(rec["uncertainty"], ensure_ascii=False), "limitations_json": json.dumps(rec["limitations"], ensure_ascii=False)})
    print(json.dumps({"status": "OK", "advisory_count": len(records), "generation_modes": {m: sum(1 for r in records if r["generation_mode"] == m) for m in sorted({r["generation_mode"] for r in records})}, "output": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
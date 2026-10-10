import argparse
from pathlib import Path
from src.orchestration.pipeline import PipelinePaths, PipelineOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Run Aervia layers 3A, 3B, 4, 5, and 6 in dependency order."
    )
    parser.add_argument("--minute", required=True, help="Preprocessed minute.csv")
    parser.add_argument("--samples", required=True, help="Preprocessed aligned samples.csv")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--run-root", required=True, help="Root directory for all outputs")
    parser.add_argument("--backend-dir", default=".", help="Backend root; default is current directory")
    parser.add_argument("--skip-advisories", action="store_true")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--disable-llm", action="store_true", help="Force deterministic advisories")
    parser.add_argument("--report-type", choices=["event", "hourly", "daily", "weekly", "custom"], default="daily")
    parser.add_argument("--start-utc")
    parser.add_argument("--end-utc")
    parser.add_argument("--audience", choices=["operator", "admin", "technical"], default="operator")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    backend = Path(args.backend_dir).resolve()

    def from_backend(value):
        path = Path(value)
        return path if path.is_absolute() else (backend / path).resolve()

    paths = PipelinePaths(
        backend_dir=backend,
        dataset_id=args.dataset_id,
        run_root=from_backend(args.run_root),
        minute_csv=from_backend(args.minute),
        samples_csv=from_backend(args.samples),
    )
    orchestrator = PipelineOrchestrator(
        paths,
        run_advisories=not args.skip_advisories,
        run_reports=not args.skip_report,
        disable_llm=args.disable_llm,
        report_type=args.report_type,
        start_utc=args.start_utc,
        end_utc=args.end_utc,
        audience=args.audience,
        dry_run=args.dry_run,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
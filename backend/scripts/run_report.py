import argparse
from pathlib import Path
from src.reporting import ReportConfig, build_report
from src.reporting.report_builder import write_json, write_csv, write_html
from src.reporting.pdf_exporter import write_pdf

def main():
    p = argparse.ArgumentParser(description="Generate deterministic Aervia reports from existing layer outputs.")
    p.add_argument("--analytics-dir", required=True)
    p.add_argument("--warnings", required=True)
    p.add_argument("--advisories")
    p.add_argument("--features")
    p.add_argument("--output", required=True)
    p.add_argument("--dataset-id", required=True)
    p.add_argument("--type", dest="report_type", choices=["event","hourly","daily","weekly","custom"], default="daily")
    p.add_argument("--start-utc")
    p.add_argument("--end-utc")
    p.add_argument("--audience", choices=["operator","admin","technical"], default="operator")
    p.add_argument("--no-advisories", action="store_true")
    p.add_argument("--no-environmental-context", action="store_true")
    p.add_argument("--no-data-quality", action="store_true")
    p.add_argument("--pdf", action="store_true", help="also export PDF; requires reportlab")
    args = p.parse_args()

    config = ReportConfig(
        dataset_id=args.dataset_id, report_type=args.report_type,
        start_utc=args.start_utc, end_utc=args.end_utc, audience=args.audience,
        include_advisories=not args.no_advisories,
        include_environmental_context=not args.no_environmental_context,
        include_data_quality=not args.no_data_quality,
    )
    report = build_report(config, args.analytics_dir, args.warnings, args.advisories, args.features)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    write_json(report, out / "report.json")
    write_csv(report, out / "warnings.csv")
    write_html(report, out / "report.html")
    if args.pdf:
        write_pdf(report, out / "report.pdf")
    print(f"Report generated: {out.resolve()}")
    print(f"Warnings: {report['summary']['warning_count']}; advisories: {report['summary']['advisory_count']}; events: {report['summary']['event_count']}")

if __name__ == "__main__":
    main()
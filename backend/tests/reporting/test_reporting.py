import json
from pathlib import Path
from src.reporting import ReportConfig, build_report
from src.reporting.report_builder import write_json, write_csv, write_html

def test_report_builds_with_empty_context(tmp_path):
    analytics = tmp_path / "analytics"
    analytics.mkdir()
    (analytics / "event_detection.json").write_text(json.dumps({"status":"OK","events":[{"event_id":"e1","start_utc":"2026-10-09T09:00:00Z","end_utc":"2026-10-09T09:03:00Z"}]}))
    (analytics / "recovery_profile.json").write_text(json.dumps({"status":"PARTIAL","records":[]}))
    (analytics / "exposure_burden.json").write_text(json.dumps({"status":"OK","records":[]}))
    warnings = tmp_path / "warnings.json"
    warnings.write_text(json.dumps({"status":"OK","warnings":[{"warning_id":"w1","start_utc":"2026-10-09T09:00:00Z","end_utc":"2026-10-09T09:03:00Z","severity":"Elevated","peak_pm2_5_ug_m3":50.0,"peak_excess_pm2_5_ug_m3":30.0,"summary":"Test warning"}]}))
    report = build_report(ReportConfig(dataset_id="test"), analytics, warnings)
    assert report["summary"]["warning_count"] == 1
    assert report["summary"]["warnings_by_severity"] == {"Elevated": 1}
    assert report["limitations"]
    write_json(report, tmp_path / "report.json")
    write_csv(report, tmp_path / "warnings.csv")
    write_html(report, tmp_path / "report.html")
    assert (tmp_path / "report.json").exists()
    assert "Aervia air-quality report" in (tmp_path / "report.html").read_text()

def test_custom_window_filters_records(tmp_path):
    analytics = tmp_path / "analytics"
    analytics.mkdir()
    (analytics / "event_detection.json").write_text(json.dumps({"status":"OK","events":[]}))
    warnings = tmp_path / "warnings.json"
    warnings.write_text(json.dumps({"status":"OK","warnings":[
        {"warning_id":"w1","start_utc":"2026-10-09T09:00:00Z","severity":"Elevated"},
        {"warning_id":"w2","start_utc":"2026-10-09T11:00:00Z","severity":"Severe"}]}))
    report = build_report(ReportConfig(dataset_id="test", report_type="custom", start_utc="2026-10-09T10:00:00Z", end_utc="2026-10-09T12:00:00Z"), analytics, warnings)
    assert report["summary"]["warning_count"] == 1
    assert report["warnings"][0]["warning_id"] == "w2"
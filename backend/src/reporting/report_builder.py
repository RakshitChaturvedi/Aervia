from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import pandas as pd

from .aggregator import load_json, rows_from_payload, filter_window, load_feature_summary, stable_id
from .config import ReportConfig

def _status(payload):
    return payload.get("status", "UNKNOWN") if isinstance(payload, dict) else "NOT_PROVIDED"

def _module_rows(payload, keys):
    return rows_from_payload(payload, keys)

def _time_bounds(report_type, start_utc, end_utc):
    if start_utc or end_utc:
        return start_utc, end_utc
    return None, None

def build_report(config: ReportConfig, analytics_dir, warnings_path, advisories_path=None, features_path=None):
    config.validate()
    analytics_dir = Path(analytics_dir)
    warnings_payload = load_json(warnings_path)
    advisories_payload = load_json(advisories_path) if advisories_path else None

    event_payload = load_json(analytics_dir / "event_detection.json") if (analytics_dir / "event_detection.json").exists() else None
    recovery_payload = load_json(analytics_dir / "recovery_profile.json") if (analytics_dir / "recovery_profile.json").exists() else None
    exposure_payload = load_json(analytics_dir / "exposure_burden.json") if (analytics_dir / "exposure_burden.json").exists() else None
    activity_payload = load_json(analytics_dir / "activity_association.json") if (analytics_dir / "activity_association.json").exists() else None
    intervention_payload = load_json(analytics_dir / "intervention_check.json") if (analytics_dir / "intervention_check.json").exists() else None

    start, end = _time_bounds(config.report_type, config.start_utc, config.end_utc)
    warnings = filter_window(rows_from_payload(warnings_payload, ("warnings", "items", "results")), start, end)
    advisories = filter_window(rows_from_payload(advisories_payload, ("advisories", "items", "results")), start, end) if config.include_advisories else []
    events = filter_window(rows_from_payload(event_payload, ("events", "items", "results")), start, end)
    recoveries = rows_from_payload(recovery_payload, ("recoveries", "recovery_profiles", "results"))
    exposures = rows_from_payload(exposure_payload, ("exposure_burden", "integrals", "results", "events"))
    activity_rows = rows_from_payload(activity_payload, ("associations", "results"))
    intervention_rows = rows_from_payload(intervention_payload, ("interventions", "results"))

    # A single-window report can only summarize event-like records with timestamps.
    # Recovery/exposure records are retained as source module outputs and referenced by event ID where available.
    feature_summary = load_feature_summary(features_path, start, end) if config.include_data_quality else {"status": "OMITTED"}
    severities = {}
    for item in warnings:
        severity = str(item.get("severity", item.get("level", "UNSPECIFIED")))
        severities[severity] = severities.get(severity, 0) + 1

    peaks = [x.get("peak_pm2_5_ug_m3", x.get("peak_pm2_5")) for x in warnings]
    peaks = [float(x) for x in peaks if isinstance(x, (int, float))]
    excesses = [x.get("peak_excess_pm2_5_ug_m3", x.get("peak_excess_pm2_5")) for x in warnings]
    excesses = [float(x) for x in excesses if isinstance(x, (int, float))]

    source_statuses = {
        "warnings": _status(warnings_payload),
        "advisories": _status(advisories_payload) if config.include_advisories else "OMITTED",
        "event_detection": _status(event_payload),
        "recovery_profile": _status(recovery_payload),
        "exposure_burden": _status(exposure_payload),
        "activity_association": _status(activity_payload),
        "intervention_check": _status(intervention_payload),
        "feature_summary": feature_summary.get("status", "UNKNOWN"),
    }

    limitations = [
        "Prototype report; results depend on a single monitoring node and the supplied capture window.",
        "A single node does not establish campus-wide air quality or identify a pollution source.",
        "Rule-based warning levels are prototype triage categories, not official AQI categories or medical thresholds.",
        "Concentration-time integrals are not personal inhaled dose or population exposure.",
        "Activity association and intervention results are descriptive and require synchronized context; they do not establish causality.",
        "Gas indices are not calibrated gas concentrations; report only gas-readiness status where available.",
        "This report does not interpolate missing measurements or infer missing timestamps."
    ]
    report = {
        "report_id": stable_id(config.dataset_id, config.report_type, start, end, datetime.now(timezone.utc).isoformat()),
        "report_version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": config.dataset_id,
        "report_type": config.report_type,
        "audience": config.audience,
        "window": {"start_utc": start, "end_utc": end},
        "summary": {
            "warning_count": len(warnings),
            "warnings_by_severity": severities,
            "advisory_count": len(advisories),
            "event_count": len(events),
            "max_warning_peak_pm2_5_ug_m3": max(peaks) if peaks else None,
            "max_warning_peak_excess_pm2_5_ug_m3": max(excesses) if excesses else None,
            "feature_data_quality": feature_summary,
        },
        "warnings": warnings,
        "advisories": advisories,
        "analytics": {
            "event_detection": {"status": source_statuses["event_detection"], "records": events},
            "recovery_profile": {"status": source_statuses["recovery_profile"], "records": recoveries},
            "exposure_burden": {"status": source_statuses["exposure_burden"], "records": exposures},
            "activity_association": {"status": source_statuses["activity_association"], "records": activity_rows},
            "intervention_check": {"status": source_statuses["intervention_check"], "records": intervention_rows},
        },
        "source_statuses": source_statuses,
        "limitations": limitations,
        "provenance": {
            "input_paths": {
                "analytics_dir": str(analytics_dir),
                "warnings": str(warnings_path),
                "advisories": str(advisories_path) if advisories_path and config.include_advisories else None,
                "features": str(features_path) if features_path else None,
            },
            "aggregation": "deterministic",
            "no_new_severity_classification": True,
        },
    }
    return report

def write_json(report: dict, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

def write_csv(report: dict, output_path):
    rows = []
    for w in report.get("warnings", []):
        rows.append({
            "record_type": "warning",
            "record_id": w.get("warning_id", w.get("event_id", "")),
            "start_utc": w.get("start_utc", w.get("event_start_utc", "")),
            "end_utc": w.get("end_utc", w.get("event_end_utc", "")),
            "severity": w.get("severity", w.get("level", "")),
            "peak_pm2_5_ug_m3": w.get("peak_pm2_5_ug_m3", w.get("peak_pm2_5", "")),
            "peak_excess_pm2_5_ug_m3": w.get("peak_excess_pm2_5_ug_m3", w.get("peak_excess_pm2_5", "")),
            "summary": w.get("summary", ""),
        })
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["record_type","record_id","start_utc","end_utc","severity","peak_pm2_5_ug_m3","peak_excess_pm2_5_ug_m3","summary"]).to_csv(output_path, index=False)

def write_html(report: dict, output_path):
    import html
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    s = report["summary"]
    rows = []
    for w in report["warnings"]:
        rows.append("<tr>" + "".join(
            f"<td>{html.escape(str(v if v is not None else '—'))}</td>" for v in [
                w.get("start_utc", w.get("event_start_utc", "—")),
                w.get("end_utc", w.get("event_end_utc", "—")),
                w.get("severity", w.get("level", "—")),
                w.get("peak_pm2_5_ug_m3", w.get("peak_pm2_5", "—")),
                w.get("peak_excess_pm2_5_ug_m3", w.get("peak_excess_pm2_5", "—")),
                w.get("summary", "—")
            ]) + "</tr>")
    limitation_html = "".join(f"<li>{html.escape(x)}</li>" for x in report["limitations"])
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Aervia report</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#20252b}}
h1,h2{{line-height:1.2}}.metrics{{display:flex;gap:12px;flex-wrap:wrap}}.metric{{border:1px solid #ddd;border-radius:8px;padding:12px 16px;min-width:130px}}
table{{width:100%;border-collapse:collapse;margin:12px 0}}th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}th{{background:#f4f5f6}}
.small{{color:#555;font-size:13px}}@media print{{body{{margin:0;max-width:none}}}}</style></head><body>
<h1>Aervia air-quality report</h1><p><b>Dataset:</b> {html.escape(str(report['dataset_id']))} ·
<b>Type:</b> {html.escape(str(report['report_type']))} · <b>Generated:</b> {html.escape(report['generated_at_utc'])}</p>
<p><b>Window (UTC):</b> {html.escape(str(report['window'].get('start_utc') or 'source range'))} — {html.escape(str(report['window'].get('end_utc') or 'source range'))}</p>
<div class="metrics"><div class="metric"><b>Warnings</b><br>{s['warning_count']}</div>
<div class="metric"><b>Advisories</b><br>{s['advisory_count']}</div><div class="metric"><b>Detected events</b><br>{s['event_count']}</div>
<div class="metric"><b>Max PM2.5 peak</b><br>{html.escape(str(s['max_warning_peak_pm2_5_ug_m3'] if s['max_warning_peak_pm2_5_ug_m3'] is not None else '—'))} µg/m³</div>
<div class="metric"><b>Max excess</b><br>{html.escape(str(s['max_warning_peak_excess_pm2_5_ug_m3'] if s['max_warning_peak_excess_pm2_5_ug_m3'] is not None else '—'))} µg/m³</div></div>
<h2>Warnings</h2><table><thead><tr><th>Start UTC</th><th>End UTC</th><th>Severity</th><th>Peak PM2.5 (µg/m³)</th><th>Peak excess (µg/m³)</th><th>Summary</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="6">No warnings in the selected window.</td></tr>'}</tbody></table>
<h2>Module status</h2><table><thead><tr><th>Module</th><th>Status</th></tr></thead><tbody>{''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>' for k,v in report['source_statuses'].items())}</tbody></table>
<h2>Limitations</h2><ul>{limitation_html}</ul>
<p class="small">Generated deterministically from supplied Aervia outputs. This report does not independently validate sensor calibration or establish source attribution, personal dose, or causality.</p>
</body></html>"""
    Path(output_path).write_text(doc, encoding="utf-8")
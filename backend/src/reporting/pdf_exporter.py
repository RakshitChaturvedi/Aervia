"""Optional PDF export using ReportLab. HTML export works without this dependency."""
from pathlib import Path

def write_pdf(report, output_path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("PDF export requires reportlab: pip install reportlab") from exc
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output_path), pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    story = [Paragraph("Aervia Air-Quality Report", styles["Title"]),
             Paragraph(f"Dataset: {report['dataset_id']} | Type: {report['report_type']} | Generated UTC: {report['generated_at_utc']}", styles["Normal"]),
             Spacer(1, 12)]
    s = report["summary"]
    story.append(Paragraph(f"Warnings: {s['warning_count']} | Advisories: {s['advisory_count']} | Detected events: {s['event_count']}", styles["Heading2"]))
    data = [["Start UTC", "End UTC", "Severity", "Peak PM2.5", "Peak excess", "Summary"]]
    for w in report.get("warnings", []):
        data.append([str(w.get("start_utc", w.get("event_start_utc", "—"))),
                     str(w.get("end_utc", w.get("event_end_utc", "—"))),
                     str(w.get("severity", w.get("level", "—"))),
                     str(w.get("peak_pm2_5_ug_m3", w.get("peak_pm2_5", "—"))),
                     str(w.get("peak_excess_pm2_5_ug_m3", w.get("peak_excess_pm2_5", "—"))),
                     str(w.get("summary", "—"))[:180]])
    table = Table(data, repeatRows=1, colWidths=[105,105,60,75,75,260])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("GRID",(0,0),(-1,-1),0.4,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)]))
    story.extend([table, Spacer(1, 12), Paragraph("Limitations", styles["Heading2"])])
    for item in report.get("limitations", []):
        story.append(Paragraph("• " + item, styles["BodyText"]))
    doc.build(story)
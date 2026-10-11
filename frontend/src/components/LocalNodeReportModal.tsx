'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, Download, FileText, MapPin, X } from 'lucide-react';

const API = 'http://127.0.0.1:8000/api/analytics/report/local-capture';

type Report = {
  title?: string;
  location?: string;
  capture_window?: { start_ist?: string; end_ist?: string; duration_minutes?: number; is_full_day?: boolean };
  summary?: any;
  metrics?: any;
  analytics?: { event_detection?: { records?: any[] } };
  event_summaries?: any[];
  parameters?: Record<string, { unit: string; samples: number; minimum: number | null; mean: number | null; maximum: number | null }>;
  events?: any[];
  warnings?: any[];
  advisories?: any[];
  limitations?: string[];
};

const field = (value: any) => typeof value === 'number' ? value.toLocaleString('en-IN', { maximumFractionDigits: 1 }) : (value ?? '—');

const timeIST = (value: any) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false }).format(date);
};

const eventLabel = (event: any, index: number) => {
  const raw = event.event_id || event.warning_id || '';
  const suffix = String(raw).split(':').filter(Boolean).pop();
  return event.short_id || event.short_event_id || (suffix && /^\d{4}$/.test(suffix) ? `E-${suffix}` : `Episode ${index + 1}`);
};

export default function LocalNodeReportModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    setLoading(true);
    setError('');
    fetch(API).then(async response => {
      if (!response.ok) throw new Error(`Report request failed (${response.status})`);
      return response.json();
    }).then(data => { if (active) setReport(data); })
      .catch(e => { if (active) setError(e.message || 'Could not generate the local capture report.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isOpen]);

  if (!isOpen) return null;
  const metrics = report?.summary || report?.metrics || {};
  const events = report?.events || report?.event_summaries || report?.analytics?.event_detection?.records || [];
  const warnings = report?.warnings || [];
  const advisories = report?.advisories || [];

  return <div onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }} style={{ position: 'fixed', inset: 0, zIndex: 3000, display: 'grid', placeItems: 'center', padding: 18, background: 'rgba(7,12,20,.72)', backdropFilter: 'blur(5px)' }}>
    <style>{`@media print { body * { visibility: hidden !important; } #local-node-report, #local-node-report * { visibility: visible !important; } #local-node-report { position: fixed !important; inset: 0 !important; width: 100% !important; max-height: none !important; overflow: visible !important; box-shadow: none !important; border: 0 !important; } .local-report-controls { display: none !important; } }`}</style>
    <section id="local-node-report" role="dialog" aria-modal="true" aria-labelledby="local-report-title" style={{ width: 'min(980px, 100%)', maxHeight: '92vh', overflow: 'auto', borderRadius: 16, border: '1px solid var(--border-primary)', background: 'var(--bg-primary)', color: 'var(--text-primary)', boxShadow: '0 24px 70px rgba(0,0,0,.35)' }}>
      <header style={{ position: 'sticky', top: 0, zIndex: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, padding: '16px 20px', borderBottom: '1px solid var(--border-primary)', background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}><span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 11, color: '#0f766e', background: '#ccfbf1' }}><FileText size={20} /></span><div><h2 id="local-report-title" style={{ margin: 0, fontSize: '1rem' }}>VNR local node report</h2><span style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 3, color: 'var(--text-muted)', fontSize: '.72rem' }}><MapPin size={12} />College Gate · field capture</span></div></div>
        <div className="local-report-controls" style={{ display: 'flex', gap: 8 }}><button onClick={() => window.print()} disabled={!report} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border-primary)', background: 'var(--bg-primary)', color: 'var(--text-primary)', cursor: report ? 'pointer' : 'not-allowed', fontSize: '.72rem', fontWeight: 800 }}><Download size={14} />Print / Save PDF</button><button onClick={onClose} aria-label="Close report" style={{ display: 'grid', placeItems: 'center', width: 33, borderRadius: 8, border: '1px solid var(--border-primary)', background: 'var(--bg-primary)', color: 'var(--text-primary)', cursor: 'pointer' }}><X size={16} /></button></div>
      </header>
      <div style={{ display: 'grid', gap: 16, padding: 20 }}>
        {loading && <div style={{ padding: 25, textAlign: 'center', color: 'var(--text-muted)' }}>Building report from the field-capture records…</div>}
        {error && <div role="alert" style={{ padding: 13, borderRadius: 9, border: '1px solid #fecaca', background: '#fff1f2', color: '#991b1b' }}>{error}</div>}
        {report && <>
          <div><div style={{ color: '#0f766e', fontSize: '.68rem', fontWeight: 900, letterSpacing: '.08em', textTransform: 'uppercase' }}>Field capture · FT1</div><h3 style={{ margin: '5px 0', fontSize: '1.25rem' }}>{report.title || 'Local node field-capture report'}</h3><p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '.77rem' }}>{report.location || 'VNR VJIET campus · College Gate'} · {report.capture_window?.start_ist || '9 Oct 2026'} — {report.capture_window?.end_ist || 'capture end'}</p></div>
          <div role="note" style={{ display: 'flex', gap: 9, padding: 12, borderRadius: 9, border: '1px solid #fed7aa', background: '#fff7ed', color: '#9a3412', fontSize: '.75rem', lineHeight: 1.45 }}><AlertTriangle size={17} style={{ flex: '0 0 auto' }} /><span><strong>Partial recording:</strong> {report.capture_window?.duration_minutes ?? 99} minute bins. This is a field-capture summary, not a full-day campus assessment.</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: 9 }}>
            {[
              ['Detected episodes', metrics.events_count ?? metrics.event_count ?? events.length],
              ['Warnings issued', metrics.warnings_count ?? metrics.warning_count ?? warnings.length],
              ['Severe warnings', metrics.severe_warnings ?? metrics.severe_count ?? warnings.filter(w => w.severity === 'SEVERE').length],
              ['Peak PM2.5', `${field(metrics.peak_pm25 ?? metrics.max_warning_peak_pm2_5_ug_m3 ?? metrics.peak_pm2_5_ug_m3 ?? metrics.peak_pm2_5)} µg/m³`],
            ].map(([label, value]) => <div key={String(label)} style={{ padding: 12, borderRadius: 10, border: '1px solid var(--border-primary)', background: 'var(--bg-surface)' }}><span style={{ display: 'block', color: 'var(--text-muted)', fontSize: '.66rem', textTransform: 'uppercase', fontWeight: 800 }}>{label}</span><strong style={{ display: 'block', marginTop: 5, fontSize: '1.05rem' }}>{value}</strong></div>)}
          </div>
          <section><h4 style={{ margin: '0 0 8px', fontSize: '.83rem' }}>Observed parameters</h4><div style={{ overflowX: 'auto', border: '1px solid var(--border-primary)', borderRadius: 9 }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.73rem' }}><thead><tr style={{ background: 'var(--bg-surface)', textAlign: 'left' }}>{['Parameter', 'Samples', 'Minimum', 'Mean', 'Maximum'].map(x => <th key={x} style={{ padding: '9px 11px', color: 'var(--text-muted)', fontSize: '.65rem', textTransform: 'uppercase' }}>{x}</th>)}</tr></thead><tbody>{Object.entries(report.parameters || {}).map(([name, p]) => <tr key={name} style={{ borderTop: '1px solid var(--border-primary)' }}><td style={{ padding: '9px 11px', fontWeight: 700 }}>{name}</td><td style={{ padding: '9px 11px' }}>{p.samples}</td><td style={{ padding: '9px 11px' }}>{field(p.minimum)} {p.unit}</td><td style={{ padding: '9px 11px' }}>{field(p.mean)} {p.unit}</td><td style={{ padding: '9px 11px', fontWeight: 800 }}>{field(p.maximum)} {p.unit}</td></tr>)}</tbody></table></div></section>
          <section><h4 style={{ margin: '0 0 8px', fontSize: '.83rem' }}>Episodes & warnings</h4><div style={{ display: 'grid', gap: 7 }}>{(events.length ? events : warnings).map((event: any, i: number) => { const severity = event.severity || event.warning_severity || 'UNSPECIFIED'; const start = event.start_ist || timeIST(event.start_utc || event.start_time_utc); const end = event.end_ist || timeIST(event.end_utc || event.end_time_utc); return <div key={event.event_id || event.warning_id || i} style={{ display: 'grid', gridTemplateColumns: 'minmax(115px, .6fr) minmax(130px, 1fr) minmax(150px, 1.2fr)', gap: 10, alignItems: 'center', padding: '10px 11px', borderRadius: 9, border: `1px solid ${severity === 'SEVERE' ? '#fecaca' : '#fed7aa'}`, background: severity === 'SEVERE' ? '#fff1f2' : '#fff7ed' }}><strong style={{ color: severity === 'SEVERE' ? '#b91c1c' : '#b45309', fontSize: '.75rem' }}>{eventLabel(event, i)} · {severity}</strong><span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '.69rem' }}>{start}–{end} IST</span><span style={{ color: 'var(--text-primary)', fontSize: '.7rem' }}>Peak {field(event.peak_pm2_5_ug_m3 ?? event.peak_pm25)} µg/m³ · +{field(event.peak_excess_pm2_5_ug_m3 ?? event.peak_excess)} over baseline</span></div>; })}{!events.length && !warnings.length && <p style={{ color: 'var(--text-muted)', fontSize: '.75rem' }}>No event records are available in the report payload.</p>}</div></section>
          {advisories.length > 0 && <section><h4 style={{ margin: '0 0 8px', fontSize: '.83rem' }}>Recommended follow-up</h4><div style={{ display: 'grid', gap: 8 }}>{advisories.map((ad: any, i: number) => <div key={ad.advisory_id || i} style={{ padding: 11, borderRadius: 9, border: '1px solid var(--border-primary)', background: 'var(--bg-surface)' }}><strong style={{ fontSize: '.75rem' }}>{eventLabel(ad, i)} · {ad.severity || 'ADVISORY'}</strong><p style={{ margin: '5px 0 0', color: 'var(--text-secondary)', fontSize: '.72rem', lineHeight: 1.45 }}>{ad.actions?.[0]?.instruction || ad.summary || 'Review the episode and verify subsequent measurements.'}</p></div>)}</div></section>}
          {report.limitations?.length ? <section><h4 style={{ margin: '0 0 6px', fontSize: '.77rem' }}>Interpretation limits</h4><ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-muted)', fontSize: '.7rem', lineHeight: 1.5 }}>{report.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul></section> : null}
        </>}
      </div>
    </section>
  </div>;
}

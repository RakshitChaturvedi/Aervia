'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, MapPin, ShieldAlert } from 'lucide-react';
import { apiUrl } from '@/utils/api';

const getApi = () => apiUrl('/api/analytics/advisories');

type Advisory = {
  advisory_id: string;
  event_id: string;
  short_event_id: string;
  status: string;
  severity: string;
  start_ist: string;
  end_ist: string;
  peak_pm2_5_ug_m3?: number;
  peak_excess_pm2_5_ug_m3?: number;
  duration_elapsed_minutes?: number;
  lifecycle?: string;
  summary?: string;
  reasoning?: string;
  actions?: { title: string; instruction: string; rationale?: string; urgency?: string; audience?: string }[];
  uncertainty?: string[];
  limitations?: string[];
};

const tone = (severity: string) => severity === 'SEVERE'
  ? { color: '#b91c1c', border: '#fecaca', bg: '#fff1f2', label: 'SEVERE WARNING' }
  : severity === 'ELEVATED'
    ? { color: '#b45309', border: '#fed7aa', bg: '#fff7ed', label: 'ELEVATED WARNING' }
    : { color: '#475569', border: '#cbd5e1', bg: '#f8fafc', label: 'ADVISORY' };

const toMinutes = (clock: string) => {
  const [hour, minute] = clock.split(':').map(Number);
  return hour * 60 + minute;
};

function scheduleContext(item: Advisory) {
  const start = toMinutes(item.start_ist || '00:00');
  const end = toMinutes(item.end_ist || item.start_ist || '00:00');
  const intersects = (from: string, to: string) => start <= toMinutes(to) && end >= toMinutes(from);

  if (intersects('15:40', '16:10')) {
    return {
      label: 'Year 1 dismissal & buses · 15:40–16:10',
      note: 'Years 2–4 remain in class until 16:40.',
      actions: [
        { title: 'Security', instruction: `Check the gate log at ${item.start_ist}–${item.end_ist}.` },
        { title: 'Transport', instruction: 'Review bus staging and idling records for this window.' },
        { title: 'Admin', instruction: item.lifecycle === 'OPEN_AT_CAPTURE_END' ? 'Get a fresh reading; the capture ended during this event.' : 'Check follow-up readings for recovery.' },
      ],
    };
  }

  if (intersects('12:00', '12:40') || intersects('13:00', '13:40')) {
    const firstYearLunch = intersects('12:00', '12:40');
    return {
      label: `${firstYearLunch ? 'Year 1' : 'Years 2–4'} lunch · ${firstYearLunch ? '12:00–12:40' : '13:00–13:40'}`,
      note: 'Episode occurred during the scheduled lunch window.',
      actions: [
        { title: 'Security', instruction: `Check gate observations at ${item.start_ist}–${item.end_ist}.` },
        { title: 'Facilities', instruction: 'Review maintenance or cleaning near the node.' },
        { title: 'Admin', instruction: 'Compare the next reading with the event peak.' },
      ],
    };
  }

  const firstYearClass = intersects('09:00', '15:39');
  const seniorClass = intersects('10:00', '16:39');
  const cohorts = [firstYearClass ? '1st-year' : '', seniorClass ? '2nd–4th-year' : ''].filter(Boolean).join(' and ');
  return {
    label: cohorts ? `Scheduled classes · ${cohorts}` : 'Outside scheduled class, lunch or bus windows',
    note: 'No listed lunch or dismissal overlap.',
    actions: [
      { title: 'Security', instruction: `Review gate activity at ${item.start_ist}–${item.end_ist}.` },
      { title: 'Facilities', instruction: 'Check nearby maintenance or cleaning logs.' },
      { title: 'Admin', instruction: 'Compare follow-up readings with the event peak.' },
    ],
  };
}

export default function LocalCaptureAdvisories() {
  const [items, setItems] = useState<Advisory[]>([]);
  const [location, setLocation] = useState('VNR VJIET campus · College Gate node');
  const [windowLabel, setWindowLabel] = useState('9 Oct 2026 · 14:24–16:02 IST');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetch(getApi()).then(async response => {
      if (!response.ok) throw new Error(`Advisories request failed (${response.status})`);
      return response.json();
    }).then(payload => {
      if (!active) return;
      setItems(Array.isArray(payload.advisories) ? payload.advisories : []);
      setLocation(payload.location || location);
      if (payload.capture_window) setWindowLabel(payload.capture_window);
      setError('');
    }).catch(e => { if (active) setError(e.message || 'Could not load the captured advisories.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  // location is a fallback only; fetch once on page entry.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <section style={{ display: 'grid', gap: 12 }}>
    <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b91c1c', fontWeight: 900, fontSize: '.7rem', letterSpacing: '.08em', textTransform: 'uppercase' }}><ShieldAlert size={15} />Schedule-aware response</div>
        <h1 style={{ margin: '5px 0 3px', color: 'var(--text-primary)', fontSize: '1.3rem' }}>Campus advisories</h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '.78rem' }}>Each episode is matched to the VNR class, lunch and bus schedule.</p>
      </div>
        <div style={{ display: 'grid', gap: 5, padding: '10px 13px', border: '1px solid var(--border-primary)', borderRadius: 10, background: 'var(--bg-surface)', color: 'var(--text-secondary)', fontSize: '.74rem' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><MapPin size={13} />{location}</span><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><Clock3 size={13} />{windowLabel}</span></div>
    </header>

    <div role="note" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 11px', border: '1px solid #fed7aa', borderLeft: '4px solid #d97706', borderRadius: 9, background: '#fff7ed', color: '#9a3412', fontSize: '.72rem' }}><Clock3 size={14} />Schedule overlap helps teams choose what to check; it does not identify a cause.</div>

    {loading && <div style={{ padding: 24, borderRadius: 12, border: '1px solid var(--border-primary)', background: 'var(--bg-surface)', color: 'var(--text-muted)' }}>Loading event-linked advisories…</div>}
    {error && <div role="alert" style={{ padding: 16, borderRadius: 10, border: '1px solid #fecaca', background: '#fff1f2', color: '#991b1b' }}>{error}</div>}
    {!loading && !error && items.length === 0 && <div style={{ padding: 20, border: '1px solid var(--border-primary)', borderRadius: 12, background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>No advisories were generated for this capture.</div>}

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 480px), 1fr))', gap: 12 }}>
    {items.map(item => {
      const style = tone(item.severity);
      const schedule = scheduleContext(item);
      return <article key={item.advisory_id} style={{ overflow: 'hidden', border: `1px solid ${style.border}`, borderLeft: `5px solid ${style.color}`, borderRadius: 12, background: 'var(--bg-surface)', boxShadow: '0 4px 14px rgba(15,23,42,.045)' }}>
        <div style={{ padding: '12px 14px 10px', borderBottom: `1px solid ${style.border}`, background: style.bg }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}><strong style={{ color: style.color, fontSize: '.88rem' }}>{item.short_event_id} · PM2.5</strong><span style={{ padding: '4px 8px', borderRadius: 999, color: style.color, background: '#fff', border: `1px solid ${style.border}`, fontSize: '.63rem', fontWeight: 900 }}>{style.label}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', marginTop: 4, color: '#475569', fontSize: '.7rem' }}><span>{item.start_ist}–{item.end_ist} IST · {item.duration_elapsed_minutes ?? '—'} min</span><span><strong>Peak</strong> {Number(item.peak_pm2_5_ug_m3 ?? 0).toFixed(1)} µg/m³ · <strong>+{Number(item.peak_excess_pm2_5_ug_m3 ?? 0).toFixed(1)}</strong> over baseline</span></div>
        </div>
        <div style={{ padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9, color: style.color, fontSize: '.73rem', fontWeight: 850 }}><Clock3 size={14} />{schedule.label}<span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>· {schedule.note}</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 7 }}>
            {schedule.actions.map(action => <div key={action.title} style={{ minWidth: 0, padding: '8px 9px', borderRadius: 8, background: 'var(--bg-primary)', border: '1px solid var(--border-primary)' }}><strong style={{ display: 'block', marginBottom: 3, color: 'var(--text-primary)', fontSize: '.68rem' }}>{action.title}</strong><span style={{ color: 'var(--text-secondary)', fontSize: '.67rem', lineHeight: 1.35 }}>{action.instruction}</span></div>)}
          </div>
          {item.lifecycle === 'OPEN_AT_CAPTURE_END' && <div style={{ marginTop: 8, color: '#b91c1c', fontSize: '.67rem', fontWeight: 800 }}>Capture ended during this event · check a current reading.</div>}
        </div>
      </article>;
    })}
    </div>
  </section>;
}

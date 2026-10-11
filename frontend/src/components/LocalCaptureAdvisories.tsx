'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, MapPin, ShieldAlert } from 'lucide-react';

const API = 'http://127.0.0.1:8000/api/analytics/advisories';

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
      label: 'Overlaps first-year dismissal & bus dispatch',
      description: 'This episode falls within the 1st-year class-end and bus window (15:40–16:10). The 2nd–4th-year cohort is still in class until its 16:40 dismissal. Security and transport can review gate queueing, bus staging, and idling records for this time; timing overlap is a lead to check, not proof of cause.',
      actions: [
        { title: 'Security · check the gate log', urgency: item.severity === 'SEVERE' ? 'PRIORITY' : 'REVIEW', instruction: `Check vehicle queue length and visible activity at ${item.start_ist}–${item.end_ist} IST. Note what was present and whether it coincided with the sensor rise.` },
        { title: 'Transport · review bus staging', urgency: 'FOLLOW-UP', instruction: 'Check dispatch and staging records for idling or a queue near the College Gate. If the pattern repeats, trial engine-off waiting or move the holding point away from the sensor and pedestrian queue.' },
        { title: 'Admin · verify current conditions', urgency: item.lifecycle === 'OPEN_AT_CAPTURE_END' ? 'IMMEDIATE' : 'FOLLOW-UP', instruction: `The recorded peak was ${Number(item.peak_pm2_5_ug_m3 || 0).toFixed(1)} µg/m³. Take a current reading before treating this past capture as an active or resolved incident.` },
      ],
    };
  }

  if (intersects('12:00', '12:40') || intersects('13:00', '13:40')) {
    const firstYearLunch = intersects('12:00', '12:40');
    return {
      label: `Overlaps ${firstYearLunch ? 'first-year' : '2nd–4th-year'} lunch period`,
      description: `The event overlaps the ${firstYearLunch ? '1st-year' : '2nd–4th-year'} lunch window. Admin and security can check whether student movement or nearby service activity changed around the College Gate; a single-node reading does not identify the source.`,
      actions: [
        { title: 'Security · check movement and activity', urgency: item.severity === 'SEVERE' ? 'PRIORITY' : 'REVIEW', instruction: `Review gate observations for ${item.start_ist}–${item.end_ist} IST, including pedestrian or vehicle movement. Record observations without assigning cause from timing alone.` },
        { title: 'Facilities · inspect the sensor area', urgency: 'FOLLOW-UP', instruction: 'Check for visible dust, nearby maintenance, or other conditions at the node; note the time and whether the activity was ongoing during the elevated reading.' },
        { title: 'Admin · check follow-up readings', urgency: item.lifecycle === 'OPEN_AT_CAPTURE_END' ? 'IMMEDIATE' : 'FOLLOW-UP', instruction: `Compare the next available PM2.5 readings with the ${Number(item.peak_pm2_5_ug_m3 || 0).toFixed(1)} µg/m³ event peak and the estimated local baseline.` },
      ],
    };
  }

  const firstYearClass = intersects('09:00', '15:39');
  const seniorClass = intersects('10:00', '16:39');
  const cohorts = [firstYearClass ? '1st-year' : '', seniorClass ? '2nd–4th-year' : ''].filter(Boolean).join(' and ');
  return {
    label: cohorts ? `During ${cohorts} scheduled classes` : 'Outside the supplied class windows',
    description: cohorts
      ? `The event time falls during scheduled ${cohorts} classes, away from the listed lunch and bus-release windows. Check campus operations or maintenance activity near the node before attributing the reading to student movement.`
      : 'The event does not overlap a class, lunch, or bus window in the supplied schedule. Review facilities and security logs around the node for other activity.',
    actions: [
      { title: 'Security · review nearby activity', urgency: item.severity === 'SEVERE' ? 'PRIORITY' : 'REVIEW', instruction: `Check security observations and access activity around ${item.start_ist}–${item.end_ist} IST for the College Gate area. Treat any match as context to investigate, not source attribution.` },
      { title: 'Facilities · check site conditions', urgency: 'FOLLOW-UP', instruction: 'Review maintenance, cleaning, construction, or delivery activity near the sensor during this period and log any time-aligned observations.' },
      { title: 'Admin · verify recovery', urgency: item.lifecycle === 'OPEN_AT_CAPTURE_END' ? 'IMMEDIATE' : 'FOLLOW-UP', instruction: `Compare subsequent PM2.5 readings with the ${Number(item.peak_pm2_5_ug_m3 || 0).toFixed(1)} µg/m³ peak and estimated baseline before closing follow-up.` },
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
    fetch(API).then(async response => {
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

  return <section style={{ display: 'grid', gap: 18 }}>
    <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b91c1c', fontWeight: 900, fontSize: '.72rem', letterSpacing: '.08em', textTransform: 'uppercase' }}><ShieldAlert size={16} />Event-linked operator advisories</div>
        <h1 style={{ margin: '7px 0 4px', color: 'var(--text-primary)', fontSize: '1.35rem' }}>Recommended response for each detected episode</h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '.82rem' }}>Actions are tied to each event’s level, timing, peak, and whether the capture showed recovery.</p>
      </div>
        <div style={{ display: 'grid', gap: 5, padding: '10px 13px', border: '1px solid var(--border-primary)', borderRadius: 10, background: 'var(--bg-surface)', color: 'var(--text-secondary)', fontSize: '.74rem' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><MapPin size={13} />{location}</span><span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><Clock3 size={13} />{windowLabel}</span></div>
    </header>

    <div role="note" style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 14px', border: '1px solid #fecaca', borderLeft: '5px solid #dc2626', borderRadius: 10, background: '#fff1f2', color: '#7f1d1d' }}><AlertTriangle size={18} style={{ flex: '0 0 auto', marginTop: 1 }} /><div><strong style={{ display: 'block', fontSize: '.8rem' }}>Warnings need follow-up</strong><span style={{ display: 'block', marginTop: 3, fontSize: '.75rem', lineHeight: 1.45 }}>These are prototype triage advisories from one campus node. They do not identify a pollution source, describe the whole campus, or replace official health guidance.</span></div></div>

    <section style={{ display: 'grid', gap: 8, padding: '13px 15px', border: '1px solid var(--border-primary)', borderRadius: 11, background: 'var(--bg-surface)' }}>
      <strong style={{ color: 'var(--text-primary)', fontSize: '.75rem' }}>VNR schedule reference · supplied for advisory context</strong>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, color: 'var(--text-secondary)', fontSize: '.69rem' }}>
        {['1st year · classes 09:00–15:40 · lunch 12:00–12:40 · buses 15:40–16:10', '2nd–4th year · classes 10:00–16:40 · lunch 13:00–13:40 · buses 16:40–17:10'].map(line => <span key={line} style={{ padding: '6px 9px', borderRadius: 7, background: 'var(--bg-primary)', border: '1px solid var(--border-primary)' }}>{line}</span>)}
      </div>
    </section>

    {loading && <div style={{ padding: 24, borderRadius: 12, border: '1px solid var(--border-primary)', background: 'var(--bg-surface)', color: 'var(--text-muted)' }}>Loading event-linked advisories…</div>}
    {error && <div role="alert" style={{ padding: 16, borderRadius: 10, border: '1px solid #fecaca', background: '#fff1f2', color: '#991b1b' }}>{error}</div>}
    {!loading && !error && items.length === 0 && <div style={{ padding: 20, border: '1px solid var(--border-primary)', borderRadius: 12, background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>No advisories were generated for this capture.</div>}

    {items.map(item => {
      const style = tone(item.severity);
      const schedule = scheduleContext(item);
      return <article key={item.advisory_id} style={{ overflow: 'hidden', border: `1px solid ${style.border}`, borderRadius: 13, background: 'var(--bg-surface)', boxShadow: '0 5px 18px rgba(15,23,42,.055)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, padding: '13px 16px', borderBottom: `1px solid ${style.border}`, background: style.bg }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span style={{ display: 'grid', placeItems: 'center', width: 35, height: 35, borderRadius: 10, color: '#fff', background: style.color, fontWeight: 900 }}>{item.short_event_id?.slice(-1) || '!'}</span><div><strong style={{ display: 'block', color: style.color, fontSize: '.9rem' }}>{item.short_event_id} · PM2.5 episode</strong><span style={{ display: 'block', marginTop: 2, color: '#64748b', fontSize: '.73rem' }}>{item.start_ist}–{item.end_ist} IST · {item.duration_elapsed_minutes ?? '—'} min observed</span></div></div>
          <span style={{ padding: '5px 9px', borderRadius: 999, color: style.color, background: '#fff', border: `1px solid ${style.border}`, fontSize: '.67rem', fontWeight: 900, letterSpacing: '.04em' }}>{style.label}</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9, marginBottom: 12 }}><span style={{ padding: '6px 9px', borderRadius: 7, background: '#f1f5f9', color: '#334155', fontFamily: 'var(--font-mono)', fontSize: '.74rem', fontWeight: 800 }}>Peak {Number(item.peak_pm2_5_ug_m3 ?? 0).toFixed(1)} µg/m³</span><span style={{ padding: '6px 9px', borderRadius: 7, background: style.bg, color: style.color, fontFamily: 'var(--font-mono)', fontSize: '.74rem', fontWeight: 800 }}>+{Number(item.peak_excess_pm2_5_ug_m3 ?? 0).toFixed(1)} µg/m³ over baseline</span><span style={{ padding: '6px 9px', borderRadius: 7, background: '#f8fafc', color: '#475569', fontSize: '.7rem', fontWeight: 700 }}>{item.lifecycle === 'OPEN_AT_CAPTURE_END' ? 'Capture ended during event · check current reading' : 'Event ended in recorded capture'}</span></div>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9, marginBottom: 14, padding: '10px 12px', borderRadius: 9, border: `1px solid ${style.border}`, background: style.bg, color: style.color }}><Clock3 size={16} style={{ flex: '0 0 auto', marginTop: 1 }} /><div><strong style={{ display: 'block', fontSize: '.75rem' }}>{schedule.label}</strong><span style={{ display: 'block', marginTop: 3, fontSize: '.72rem', lineHeight: 1.45 }}>{schedule.description}</span></div></div>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: 7, margin: '0 0 9px', fontSize: '.76rem', textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--text-secondary)' }}><CheckCircle2 size={15} />What to do</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 9 }}>
            {schedule.actions.map((action, index) => <div key={`${action.title}-${index}`} style={{ padding: '11px 12px', borderRadius: 9, border: '1px solid var(--border-primary)', background: 'var(--bg-primary)' }}><div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}><strong style={{ color: 'var(--text-primary)', fontSize: '.77rem' }}>{action.title}</strong><span style={{ color: action.urgency === 'IMMEDIATE' || action.urgency === 'PRIORITY' ? '#b91c1c' : '#64748b', fontSize: '.61rem', fontWeight: 900 }}>{action.urgency}</span></div><p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: '.72rem', lineHeight: 1.48 }}>{action.instruction}</p></div>)}
          </div>
          {(item.uncertainty?.length || item.limitations?.length) ? <details style={{ marginTop: 12, color: 'var(--text-muted)', fontSize: '.72rem' }}><summary style={{ cursor: 'pointer', fontWeight: 800 }}>Evidence limits</summary><ul style={{ margin: '7px 0 0', paddingLeft: 20, lineHeight: 1.5 }}>{Array.from(new Set([...(item.uncertainty || []), ...(item.limitations || [])])).map((entry, i) => <li key={i}>{entry}</li>)}</ul></details> : null}
        </div>
      </article>;
    })}
  </section>;
}

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  Flame,
  CheckCircle,
  Clock,
  Search,
  Check,
  ChevronRight,
  Info,
  SlidersHorizontal,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Activity,
  ArrowRight,
  FileText,
  Sparkles
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceArea } from 'recharts';
import { EventItem, TimelinePoint, WarningItem } from '@/types/analytics';
import {
  fetchEvents,
  fetchWarnings,
  fetchTimeline,
  acknowledgeWarningApi,
  FALLBACK_EVENTS
} from '@/utils/analyticsApi';
import ReportModal from '@/components/ReportModal';

export default function AlertsPage() {
  const [events, setEvents] = useState<EventItem[]>(FALLBACK_EVENTS);
  const [warnings, setWarnings] = useState<WarningItem[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter & interaction state
  const [activeTab, setActiveTab] = useState<'events' | 'warnings'>('warnings');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<string>('ft1_final_v2:PM25:0004');
  const [acknowledgedWarnings, setAcknowledgedWarnings] = useState<Record<string, boolean>>({});

  // Compliance Report Modal state
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  // Toast feedback
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [evs, warns, points] = await Promise.all([
        fetchEvents(),
        fetchWarnings(),
        fetchTimeline()
      ]);
      setEvents(evs);
      setWarnings(warns);
      setTimeline(points);
    } catch (e) {
      console.warn('Failed to fetch events data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatToIST = (ts?: string | null): string => {
    if (!ts) return '--';
    if (ts.endsWith('IST')) return ts;
    try {
      let clean = ts.replace(' ', 'T');
      if (clean.endsWith('Z')) clean = clean.slice(0, -1) + '+00:00';
      const d = new Date(clean);
      if (isNaN(d.getTime())) return ts;
      const dateStr = d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
      const timeStr = d.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false });
      return `${dateStr} ${timeStr} IST`;
    } catch {
      return ts;
    }
  };

  const formatToISTTimeOnly = (ts?: string | null): string => {
    if (!ts) return '--';
    if (ts.endsWith('IST')) {
      const m = ts.match(/(\d{2}:\d{2})/);
      return m ? m[1] : ts;
    }
    try {
      let clean = ts.replace(' ', 'T');
      if (clean.endsWith('Z')) clean = clean.slice(0, -1) + '+00:00';
      const d = new Date(clean);
      if (isNaN(d.getTime())) return ts.slice(11, 16) || ts;
      return d.toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return ts.slice(11, 16) || ts;
    }
  };

  const handleAcknowledge = async (id: string) => {
    setAcknowledgedWarnings(prev => ({ ...prev, [id]: true }));
    try {
      await acknowledgeWarningApi(id);
      showToast(`Warning ${id} acknowledged and archived in incident log.`);
    } catch {
      showToast(`Warning ${id} marked locally.`);
    }
  };

  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const matchesSev = severityFilter === 'ALL' || e.warning_severity.toUpperCase() === severityFilter;
      const matchesSearch =
        searchQuery === '' ||
        e.short_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.lifecycle.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSev && matchesSearch;
    });
  }, [events, severityFilter, searchQuery]);

  const filteredWarnings = useMemo(() => {
    return warnings.filter(w => {
      const matchesSev = severityFilter === 'ALL' || w.severity.toUpperCase() === severityFilter;
      const matchesSearch =
        searchQuery === '' ||
        w.short_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        w.short_event_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSev && matchesSearch;
    });
  }, [warnings, severityFilter, searchQuery]);

  const selectedEvent = useMemo(() => {
    return events.find(e => e.event_id === selectedEventId) || events[0];
  }, [events, selectedEventId]);

  const chartData = useMemo(() => timeline.map(point => ({
    ...point,
    minute: point.time,
    pm25: point.pm2_5,
    baseline: point.baseline_pm2_5,
  })), [timeline]);
  const peakPm25 = events.length ? Math.max(...events.map(event => event.peak_pm25)) : 0;
  const severeCount = warnings.filter(warning => warning.severity.toUpperCase() === 'SEVERE').length;
  const elevatedCount = warnings.filter(warning => warning.severity.toUpperCase() === 'ELEVATED').length;
  const unacknowledgedCount = warnings.filter(warning => !acknowledgedWarnings[warning.warning_id] && !warning.acknowledged).length;
  return (
    <div className="view-container" style={{ padding: '24px 28px 90px 28px', maxWidth: 1440, margin: '0 auto', minHeight: '100%', overflowY: 'visible' }}>
      
      {/* Toast Notification */}
      {toastMsg && (
        <div style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)',
          color: 'var(--text-primary)',
          padding: '12px 20px',
          borderRadius: 8,
          boxShadow: 'var(--shadow-lg)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          fontSize: '0.85rem'
        }}>
          <CheckCircle size={16} color="var(--accent-emerald)" />
          {toastMsg}
        </div>
      )}

      {/* Header Section */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 20,
        flexWrap: 'wrap',
        gap: 16
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'rgba(239, 68, 68, 0.12)',
              color: 'var(--accent-red)'
            }}>
              <AlertTriangle size={18} />
            </span>
            <h1 style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Episode Warnings & Alerts Queue
            </h1>
          </div>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', margin: 0 }}>
            Review collected campus sensor data, detected episodes, and linked warnings
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <button
            onClick={() => setIsReportModalOpen(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              borderRadius: 'var(--radius-pill)',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              color: '#ffffff',
              fontSize: '0.82rem',
              fontWeight: 700,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(16, 185, 129, 0.25)',
              transition: 'all 0.2s ease'
            }}
          >
            <Sparkles size={14} />
            <span>Compliance Report Generator</span>
          </button>

          <Link
            href="/telemetry"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              textDecoration: 'none'
            }}
          >
            <Activity size={14} color="var(--accent-cyan)" />
            <span>Live Telemetry</span>
          </Link>

          <button
            onClick={loadData}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        
        {/* Notice Banner */}
        <div style={{
          padding: '14px 18px',
          borderRadius: 10,
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12
        }}>
          <AlertTriangle size={18} color="var(--accent-amber)" style={{ marginTop: 2, flexShrink: 0 }} />
          <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              <strong>Recorded field capture review · 9 Oct 2026 · College campus.</strong>
            {' '}This page aligns the collected sensor record and detected episodes from 14:24–16:02 IST. Events are computed from the capture; this is a static review, not a live replay or source attribution.
          </div>
        </div>

        {/* Top KPI Metrics Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 16
        }}>
          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Detected Episodes
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--text-primary)', margin: '6px 0 2px' }}>
              {events.length}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Provisional baseline excess criteria</div>
          </div>

          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Peak Concentration
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-red)', margin: '6px 0 2px' }}>
              {peakPm25.toFixed(1)} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>µg/m³</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Highest detected episode in this capture</div>
          </div>

          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Unacknowledged Warnings
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-amber)', margin: '6px 0 2px' }}>
              {unacknowledgedCount}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{severeCount} Severe · {elevatedCount} Elevated priority</div>
          </div>

          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Recovery Complete
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-emerald)', margin: '6px 0 2px' }}>
              {events.filter(event => event.recovery_status === 'RECOVERY_OBSERVED').length} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>/ {events.length}</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{events.filter(event => event.boundary_at_end).length} reaches capture boundary</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', padding: '12px 14px', borderRadius: 12, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={() => setActiveTab('warnings')} aria-pressed={activeTab === 'warnings'} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 16px', borderRadius: 'var(--radius-pill)', border: `1px solid ${activeTab === 'warnings' ? '#991b1b' : 'rgba(220,38,38,.35)'}`, color: activeTab === 'warnings' ? '#fff' : '#991b1b', background: activeTab === 'warnings' ? '#b91c1c' : 'rgba(254,226,226,.5)', fontSize: '.82rem', fontWeight: 800, cursor: 'pointer' }}><AlertTriangle size={15} />Warnings <span style={{ padding: '1px 7px', borderRadius: 99, background: activeTab === 'warnings' ? 'rgba(255,255,255,.2)' : '#fee2e2' }}>{warnings.length}</span></button>
            <button onClick={() => setActiveTab('events')} aria-pressed={activeTab === 'events'} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 16px', borderRadius: 'var(--radius-pill)', border: `1px solid ${activeTab === 'events' ? 'var(--accent-emerald)' : 'var(--border-primary)'}`, color: activeTab === 'events' ? '#fff' : 'var(--text-secondary)', background: activeTab === 'events' ? 'var(--accent-emerald)' : 'var(--bg-surface)', fontSize: '.82rem', fontWeight: 800, cursor: 'pointer' }}><Activity size={15} />Event Catalogue <span style={{ padding: '1px 7px', borderRadius: 99, background: activeTab === 'events' ? 'rgba(255,255,255,.2)' : 'var(--bg-secondary)' }}>{events.length}</span></button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: unacknowledgedCount ? '#991b1b' : 'var(--accent-emerald)', fontSize: '.76rem', fontWeight: 800 }}><span className={unacknowledgedCount ? 'live-pulse' : ''} style={{ width: 8, height: 8, borderRadius: '50%', background: unacknowledgedCount ? '#dc2626' : 'var(--accent-emerald)' }} />{unacknowledgedCount} unacknowledged</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-pill)', padding: '5px 11px' }}><Search size={13} color="var(--text-muted)" /><input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder={activeTab === 'warnings' ? 'Search warnings…' : 'Search episodes…'} style={{ border: 'none', background: 'transparent', color: 'var(--text-primary)', fontSize: '.78rem', outline: 'none', width: 150 }} /></div>
            <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} aria-label="Filter by severity" style={{ padding: '6px 12px', borderRadius: 'var(--radius-pill)', background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', color: 'var(--text-primary)', fontSize: '.78rem', fontWeight: 700, outline: 'none', cursor: 'pointer' }}><option value="ALL">All severities</option><option value="SEVERE">Severe</option><option value="ELEVATED">Elevated</option></select>
          </div>
        </div>
        {activeTab === 'warnings' && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
          {[
            { label: 'Severe warnings', value: severeCount, note: 'High priority review', color: '#b91c1c', bg: 'rgba(254,226,226,.65)' },
            { label: 'Elevated warnings', value: elevatedCount, note: 'Review episode evidence', color: '#b45309', bg: 'rgba(255,237,213,.7)' },
            { label: 'Need acknowledgement', value: unacknowledgedCount, note: unacknowledgedCount ? 'Operator action pending' : 'Queue reviewed', color: unacknowledgedCount ? '#991b1b' : '#166534', bg: unacknowledgedCount ? 'rgba(254,226,226,.65)' : 'rgba(220,252,231,.65)' },
          ].map(item => <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 15px', borderRadius: 10, border: `1px solid ${item.color}33`, background: item.bg }}><div style={{ display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: 9, color: item.color, background: '#ffffffb8' }}><AlertTriangle size={17} /></div><div><div style={{ fontSize: '.69rem', textTransform: 'uppercase', letterSpacing: '.04em', fontWeight: 800, color: item.color }}>{item.label}</div><div style={{ fontSize: '1.3rem', lineHeight: 1.1, fontWeight: 900, color: item.color }}>{item.value} <span style={{ fontSize: '.68rem', fontWeight: 600 }}>{item.note}</span></div></div></div>)}
        </div>}


        {/* Main Content Layout: Table & Selected Evidence Drawer */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: selectedEvent ? 'minmax(0, 1.4fr) minmax(340px, 1fr)' : '1fr',
          gap: 20,
          alignItems: 'start'
        }}>
          
          {/* Left Column: Events or Warnings Table */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-primary)',
            borderRadius: 12,
            overflow: 'hidden',
            boxShadow: 'var(--shadow-sm)'
          }}>
            {activeTab === 'events' ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                      <th style={{ padding: '12px 16px' }}>Event</th>
                      <th style={{ padding: '12px 14px' }}>Time (IST)</th>
                      <th style={{ padding: '12px 14px' }}>Duration</th>
                      <th style={{ padding: '12px 14px' }}>Peak PM2.5</th>
                      <th style={{ padding: '12px 14px' }}>Peak Excess</th>
                      <th style={{ padding: '12px 14px' }}>Integral</th>
                      <th style={{ padding: '12px 14px' }}>Recovery</th>
                      <th style={{ padding: '12px 16px' }}>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEvents.map(event => {
                      const isSelected = selectedEventId === event.event_id;
                      return (
                        <tr
                          key={event.event_id}
                          onClick={() => setSelectedEventId(event.event_id)}
                          style={{
                            borderBottom: '1px solid var(--border-subtle)',
                            background: isSelected ? 'rgba(16, 185, 129, 0.08)' : 'transparent',
                            cursor: 'pointer',
                            transition: 'background 0.15s ease'
                          }}
                        >
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                              {event.short_id}
                              {isSelected && <ChevronRight size={14} color="var(--accent-emerald)" />}
                            </div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>PM2.5 episode</div>
                          </td>
                          <td style={{ padding: '12px 14px', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                            {event.start_ist || formatToISTTimeOnly(event.start_utc)} – {event.end_ist || formatToISTTimeOnly(event.end_utc)}
                          </td>
                          <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)' }}>
                            {event.duration_min} min
                          </td>
                          <td style={{ padding: '12px 14px', fontWeight: 700, color: event.peak_pm25 > 100 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                            {event.peak_pm25} µg/m³
                          </td>
                          <td style={{ padding: '12px 14px', fontWeight: 600, color: 'var(--accent-peach)' }}>
                            +{event.peak_excess} µg/m³
                          </td>
                          <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                            {event.integrated_excess_ug_h_m3.toFixed(3)}
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              color: event.recovery_status === 'RECOVERY_OBSERVED' ? 'var(--accent-emerald)' : 'var(--accent-amber)'
                            }}>
                              {event.recovery_status === 'RECOVERY_OBSERVED' ? `✓ ${event.recovery_label}` : '⏳ INCOMPLETE'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 'var(--radius-pill)',
                              background: event.warning_severity.toUpperCase() === 'SEVERE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: event.warning_severity.toUpperCase() === 'SEVERE' ? 'var(--accent-red)' : 'var(--accent-amber)',
                              border: event.warning_severity.toUpperCase() === 'SEVERE' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
                            }}>
                              {event.warning_severity}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Warnings Queue Table */
              <div style={{ overflowX: 'auto', borderTop: '3px solid #b91c1c' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', background: 'linear-gradient(90deg, rgba(127,29,29,.96), rgba(185,28,28,.92))', color: '#fff' }}>
                  <ShieldAlert size={18} />
                  <div style={{ flex: 1 }}><strong style={{ display: 'block', fontSize: '0.84rem', letterSpacing: '.03em' }}>WARNING QUEUE</strong><span style={{ display: 'block', fontSize: '0.72rem', opacity: .88 }}>Detected conditions requiring review · {warnings.filter(w => !acknowledgedWarnings[w.warning_id] && !w.acknowledged).length} unacknowledged</span></div>
                  <span style={{ fontSize: '0.72rem', fontWeight: 800, padding: '4px 9px', borderRadius: 99, color: '#7f1d1d', background: '#fff' }}>{severeCount} SEVERE</span>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-primary)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                      <th style={{ padding: '12px 16px' }}>Severity</th>
                      <th style={{ padding: '12px 14px' }}>Warning Rule</th>
                      <th style={{ padding: '12px 14px' }}>Trigger Time (IST)</th>
                      <th style={{ padding: '12px 14px' }}>Condition Value</th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                      <th style={{ padding: '12px 16px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredWarnings.map(warn => {
                      const isAck = acknowledgedWarnings[warn.warning_id] || warn.acknowledged;
                      return (
                        <tr key={warn.warning_id} style={{ borderBottom: '1px solid rgba(220,38,38,.12)', background: isAck ? 'var(--bg-surface)' : warn.severity === 'SEVERE' ? 'rgba(254,226,226,.55)' : 'rgba(255,247,237,.8)', boxShadow: isAck ? 'none' : 'inset 4px 0 0 ' + (warn.severity === 'SEVERE' ? '#dc2626' : '#d97706') }}>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 'var(--radius-pill)',
                              background: warn.severity === 'SEVERE' ? '#b91c1c' : '#b45309',
                              color: '#fff',
                              border: '1px solid transparent',
                              boxShadow: warn.severity === 'SEVERE' ? '0 2px 7px rgba(185,28,28,.25)' : '0 2px 7px rgba(180,83,9,.2)'
                            }}>
                              {warn.severity}
                            </span>
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{warn.short_event_id} · PM2.5 episode</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{warn.short_id} · recorded warning</div>
                          </td>
                          <td style={{ padding: '12px 14px', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                            {warn.start_ist || formatToISTTimeOnly(warn.start_utc)} IST
                          </td>
                          <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                            {warn.peak_pm25.toFixed(1)} µg/m³ · +{warn.peak_excess.toFixed(1)} excess
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 5,
                              fontSize: '0.7rem',
                              fontWeight: 800,
                              letterSpacing: '.03em',
                              padding: '5px 8px',
                              borderRadius: 6,
                              color: isAck ? '#166534' : '#991b1b',
                              background: isAck ? '#dcfce7' : '#fee2e2',
                              border: `1px solid ${isAck ? '#86efac' : '#fca5a5'}`
                            }}>
                              {isAck ? <><CheckCircle size={13} /> ACKNOWLEDGED</> : <><AlertTriangle size={13} /> ACTIVE WARNING</>}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {!isAck ? (
                              <button
                                onClick={() => handleAcknowledge(warn.warning_id)}
                                style={{
                                  padding: '4px 10px',
                                  borderRadius: 'var(--radius-pill)',
                                  background: '#b91c1c',
                                  border: '1px solid #991b1b',
                                  color: '#fff',
                                  fontSize: '0.75rem',
                                  fontWeight: 800,
                                  cursor: 'pointer'
                                }}
                              >
                                Acknowledge
                              </button>
                            ) : (
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Archived</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right Column: Selected Episode Evidence & Diagnostics */}
          {selectedEvent && (
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              borderRadius: 12,
              padding: 20,
              boxShadow: 'var(--shadow-sm)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-emerald)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Evidence & Diagnostics
                  </div>
                  <h3 style={{ margin: '4px 0 0', fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {selectedEvent.short_id}: PM2.5 episode
                  </h3>
                </div>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: 20,
                  background: selectedEvent.warning_severity.toUpperCase() === 'SEVERE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: selectedEvent.warning_severity.toUpperCase() === 'SEVERE' ? 'var(--accent-red)' : 'var(--accent-amber)'
                }}>
                  {selectedEvent.warning_severity}
                </span>
              </div>

              {/* Event Attributes Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
                <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Interval (IST)</span>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                    {selectedEvent.start_ist || formatToISTTimeOnly(selectedEvent.start_utc)} – {selectedEvent.end_ist || formatToISTTimeOnly(selectedEvent.end_utc)}
                  </div>
                </div>

                <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Duration</span>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                    {selectedEvent.duration_min} minutes
                  </div>
                </div>

                <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Peak PM2.5</span>
                  <div style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--accent-red)', marginTop: 2 }}>
                    {selectedEvent.peak_pm25} µg/m³
                  </div>
                </div>

                <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Peak Excess</span>
                  <div style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--accent-peach)', marginTop: 2 }}>
                    +{selectedEvent.peak_excess} µg/m³
                  </div>
                </div>
              </div>

              {/* Interpretation Framework */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Interpretation Framework
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-xs)', background: 'var(--bg-secondary)', borderLeft: '3px solid var(--accent-emerald)', fontSize: '0.78rem' }}>
                    <strong style={{ color: 'var(--accent-emerald)' }}>Measured:</strong> PM2.5 reached {selectedEvent.peak_pm25} µg/m³ at College Gate sensor node.
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-xs)', background: 'var(--bg-secondary)', borderLeft: '3px solid var(--accent-blue)', fontSize: '0.78rem' }}>
                    <strong style={{ color: 'var(--accent-blue)' }}>Calculated:</strong> Peak excess of +{selectedEvent.peak_excess} µg/m³ above time-filtered baseline.
                  </div>
                  <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-xs)', background: 'var(--bg-secondary)', borderLeft: '3px solid var(--accent-amber)', fontSize: '0.78rem' }}>
                    <strong style={{ color: 'var(--accent-amber)' }}>Interpretation limit:</strong> This sensor record flags a PM2.5 episode, but does not establish its source or campus-wide impact.
                  </div>
                </div>
              </div>

              {/* Operational Check & Compliance Report Action */}
              <div style={{ paddingTop: 14, borderTop: '1px solid var(--border-primary)', display: 'flex', gap: 10 }}>
                <button
                  onClick={() => setIsReportModalOpen(true)}
                  style={{
                    flex: 1,
                    textAlign: 'center',
                    padding: '10px 14px',
                    borderRadius: 20,
                    background: 'var(--accent-emerald)',
                    color: '#ffffff',
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    border: 'none',
                    cursor: 'pointer',
                    boxShadow: '0 2px 6px rgba(16, 185, 129, 0.25)',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6
                  }}
                >
                  <Sparkles size={14} />
                  <span>View Compliance Report →</span>
                </button>

                <button
                  onClick={() => showToast(`Operational check record saved for ${selectedEvent.short_id}.`)}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-pill)',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-primary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Confirm Check
                </button>
              </div>

            </div>
          )}

        </div>

        {/* Recorded field capture: static sensor timeline */}
        <section style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 12, padding: 18, boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-emerald)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Field capture · FT1</div>
              <h2 style={{ margin: '3px 0 0', fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)' }}>Sensor record & detected episodes</h2>
              <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '0.78rem' }}>9 Oct 2026 · 14:24–16:02 IST · minute aggregates from the collected dataset</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--text-muted)', fontSize: '0.74rem' }}><Activity size={14} color="var(--accent-cyan)" /> Static time series · select an episode to inspect</div>
          </div>
          <div style={{ minWidth: 0, height: 310, padding: '10px 8px 4px 0', background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 10 }}>
              {chartData.length ? <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 14, left: 0, bottom: 4 }}>
                  <defs><linearGradient id="pm25Fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ef4444" stopOpacity={0.25} /><stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} /></linearGradient></defs>
                  <CartesianGrid stroke="var(--border-primary)" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="minute" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={28} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} width={42} unit="" />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 12 }} formatter={(value: number, name: string) => [`${Number(value).toFixed(1)} µg/m³`, name === 'pm25' ? 'PM2.5' : 'Baseline']} labelFormatter={label => `${label} IST`} />
                  {events.map(event => {
                    const startTime = event.start_ist || formatToISTTimeOnly(event.start_utc);
                    const endTime = event.end_ist || formatToISTTimeOnly(event.end_utc);
                    const active = event.event_id === selectedEvent?.event_id;
                    const severe = String(event.warning_severity).toUpperCase() === 'SEVERE';
                    const tint = severe ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.13)';
                    const edge = severe ? '#dc2626' : '#d97706';
                    return <ReferenceArea key={event.event_id} x1={startTime} x2={endTime} fill={active ? (severe ? 'rgba(239,68,68,.22)' : 'rgba(245,158,11,.25)') : tint} fillOpacity={1} stroke={edge} strokeOpacity={active ? 1 : 0.8} strokeWidth={active ? 2 : 1} onClick={() => setSelectedEventId(event.event_id)} />;
                  })}
                  <ReferenceLine y={60} stroke="var(--accent-amber)" strokeDasharray="4 4" />
                  <Area type="monotone" dataKey="baseline" stroke="#0d9488" strokeWidth={2} fill="transparent" connectNulls={false} dot={false} name="Baseline" />
                  <Area type="monotone" dataKey="pm25" stroke="#ef4444" strokeWidth={2} fill="url(#pm25Fill)" connectNulls={false} dot={false} name="PM2.5" />
                </AreaChart>
              </ResponsiveContainer> : <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>Loading collected minute series…</div>}
          </div>
          <div style={{ display: 'flex', gap: 16, padding: '8px 12px 0', fontSize: '0.72rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}><span><i style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#ef4444', marginRight: 6 }} />Measured PM2.5</span><span><i style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#0d9488', marginRight: 6 }} />Baseline</span><span><i style={{ display: 'inline-block', width: 12, borderTop: '2px dashed var(--accent-amber)', margin: '0 6px 3px 0' }} />60 µg/m³ guide</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(205px, 1fr))', gap: 8, marginTop: 12 }}>
            {events.map(event => {
              const selected = event.event_id === selectedEvent?.event_id;
              const severe = String(event.warning_severity).toUpperCase() === 'SEVERE';
              const color = severe ? '#b91c1c' : '#b45309';
              return <button key={event.event_id} onClick={() => setSelectedEventId(event.event_id)} style={{ minWidth: 0, display: 'flex', alignItems: 'center', gap: 9, padding: '9px 11px', textAlign: 'left', borderRadius: 9, border: `1px solid ${selected ? color : 'var(--border-primary)'}`, background: selected ? (severe ? 'rgba(254,226,226,.75)' : 'rgba(255,237,213,.75)') : 'var(--bg-surface)', boxShadow: selected ? `0 0 0 2px ${color}22` : 'none', cursor: 'pointer' }}>
                <span style={{ flex: '0 0 auto', display: 'grid', placeItems: 'center', width: 28, height: 28, borderRadius: 7, color: '#fff', background: color, fontSize: '.66rem', fontWeight: 900 }}>{event.short_id.slice(-1)}</span>
                <span style={{ minWidth: 0, display: 'block' }}><strong style={{ display: 'block', color, fontSize: '.73rem', lineHeight: 1.2 }}>{event.short_id} · {event.warning_severity}</strong><span style={{ display: 'block', marginTop: 3, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '.68rem', whiteSpace: 'nowrap' }}>{event.start_ist || formatToISTTimeOnly(event.start_utc)}–{event.end_ist || formatToISTTimeOnly(event.end_utc)} IST</span></span>
              </button>;
            })}
          </div>
        </section>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: -8 }}>
          <div style={{ padding: '12px 14px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)' }}><div style={{ fontSize: '.69rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '.04em' }}>Capture coverage</div><div style={{ marginTop: 3, fontSize: '.9rem', fontWeight: 800, color: 'var(--text-primary)' }}>80.8% eligible minutes</div><div style={{ marginTop: 2, fontSize: '.72rem', color: 'var(--text-muted)' }}>99 one-minute bins · 80 eligible for PM analysis</div></div>
          <div style={{ padding: '12px 14px', borderRadius: 10, background: 'rgba(255,247,237,.75)', border: '1px solid rgba(217,119,6,.25)' }}><div style={{ fontSize: '.69rem', fontWeight: 800, textTransform: 'uppercase', color: '#b45309', letterSpacing: '.04em' }}>How to read severity</div><div style={{ marginTop: 3, fontSize: '.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>Exploratory triage labels</div><div style={{ marginTop: 2, fontSize: '.72rem', lineHeight: 1.45, color: 'var(--text-muted)' }}>Based on provisional baseline-excess criteria; not official AQI categories or a health assessment.</div></div>
          <div style={{ padding: '12px 14px', borderRadius: 10, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)' }}><div style={{ fontSize: '.69rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '.04em' }}>Attribution limit</div><div style={{ marginTop: 3, fontSize: '.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>One campus sensor node</div><div style={{ marginTop: 2, fontSize: '.72rem', lineHeight: 1.45, color: 'var(--text-muted)' }}>An episode alone does not identify its source or represent exposure across the campus.</div></div>
        </div>

      </div>

      {/* Compliance Report Modal (Powered by Gemini AI) */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        initialCity="Hyderabad"
        initialDistrict="Kukatpally"
        initialMode="district_audit"
      />

    </div>
  );
}

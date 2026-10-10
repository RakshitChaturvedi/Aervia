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
import { EventItem, WarningItem } from '@/types/analytics';
import {
  fetchEvents,
  fetchWarnings,
  acknowledgeWarningApi,
  FALLBACK_EVENTS
} from '@/utils/analyticsApi';
import ReportModal from '@/components/ReportModal';

export default function AlertsPage() {
  const [events, setEvents] = useState<EventItem[]>(FALLBACK_EVENTS);
  const [warnings, setWarnings] = useState<WarningItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter & interaction state
  const [activeTab, setActiveTab] = useState<'events' | 'warnings'>('events');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEventId, setSelectedEventId] = useState<string>('E-0004');
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
      const [evs, warns] = await Promise.all([
        fetchEvents(),
        fetchWarnings()
      ]);
      setEvents(evs);
      setWarnings(warns);
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
      const matchesSev = severityFilter === 'ALL' || e.warning_severity === severityFilter;
      const matchesSearch =
        searchQuery === '' ||
        e.short_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.event_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.lifecycle.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSev && matchesSearch;
    });
  }, [events, severityFilter, searchQuery]);

  const filteredWarnings = useMemo(() => {
    return warnings.filter(w => {
      const matchesSev = severityFilter === 'ALL' || w.severity === severityFilter;
      const matchesSearch =
        searchQuery === '' ||
        w.short_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        w.warning_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        w.event_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSev && matchesSearch;
    });
  }, [warnings, severityFilter, searchQuery]);

  const selectedEvent = useMemo(() => {
    return events.find(e => e.id === selectedEventId) || events[0];
  }, [events, selectedEventId]);

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
            Automated sensor incident detection, multi-threshold triage, and AI regulatory compliance audit
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
            <strong>Continuous local incident tracking and triage queue.</strong>
            {' '}Monitors detected PM2.5 baseline excess spikes, rapid onset thermal boundary layer accumulations, and recovery intervals. To generate a CPCB/NAAQS compliance report for this episode, use the <strong>View Compliance Report</strong> action in Evidence & Diagnostics below.
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
              201.5 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>µg/m³</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Measured during Event E-004</div>
          </div>

          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Warnings Active
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-amber)', margin: '6px 0 2px' }}>
              {warnings.length}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>2 Severe · 2 Elevated priority</div>
          </div>

          <div className="stat-card" style={{ padding: 18, background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 10 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Recovery Complete
            </div>
            <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-emerald)', margin: '6px 0 2px' }}>
              2 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>/ 4</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>1 Open at capture boundary</div>
          </div>
        </div>

        {/* Tab & Controls Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          padding: '8px 0',
          borderBottom: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setActiveTab('events')}
              style={{
                padding: '8px 18px',
                borderRadius: 'var(--radius-pill)',
                background: activeTab === 'events' ? 'var(--accent-emerald)' : 'var(--bg-surface)',
                color: activeTab === 'events' ? '#ffffff' : 'var(--text-secondary)',
                border: '1px solid var(--border-primary)',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Event Catalogue ({events.length})
            </button>
            <button
              onClick={() => setActiveTab('warnings')}
              style={{
                padding: '8px 18px',
                borderRadius: 'var(--radius-pill)',
                background: activeTab === 'warnings' ? 'var(--accent-emerald)' : 'var(--bg-surface)',
                color: activeTab === 'warnings' ? '#ffffff' : 'var(--text-secondary)',
                border: '1px solid var(--border-primary)',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Warning Queue ({warnings.length})
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Search */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-pill)',
              padding: '4px 12px',
              gap: 8
            }}>
              <Search size={14} color="var(--text-muted)" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search event, ID, lifecycle..."
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text-primary)',
                  fontSize: '0.82rem',
                  outline: 'none',
                  width: 170
                }}
              />
            </div>

            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={e => setSeverityFilter(e.target.value)}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-pill)',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-primary)',
                color: 'var(--text-primary)',
                fontSize: '0.82rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value="ALL">All Severities</option>
              <option value="SEVERE">Severe Only</option>
              <option value="ELEVATED">Elevated Only</option>
            </select>
          </div>
        </div>

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
                      const eventKey = event.event_id || event.id || event.short_id;
                      const isSelected = selectedEventId === eventKey;
                      return (
                        <tr
                          key={eventKey}
                          onClick={() => setSelectedEventId(eventKey)}
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
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{event.title}</div>
                          </td>
                          <td style={{ padding: '12px 14px', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                            {formatToISTTimeOnly(event.start_time)} – {formatToISTTimeOnly(event.end_time)}
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
                            {event.integrated_excess_ug_h_m3}
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              color: event.recovery_status === 'RECOVERED' ? 'var(--accent-emerald)' : 'var(--accent-amber)'
                            }}>
                              {event.recovery_status === 'RECOVERED' ? '✓ RECOVERED' : '⏳ ACTIVE'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 'var(--radius-pill)',
                              background: event.severity === 'SEVERE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: event.severity === 'SEVERE' ? 'var(--accent-red)' : 'var(--accent-amber)',
                              border: event.severity === 'SEVERE' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
                            }}>
                              {event.severity}
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
              <div style={{ overflowX: 'auto' }}>
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
                      const warnKey = warn.warning_id || warn.id || warn.short_id;
                      const isAck = acknowledgedWarnings[warnKey] || warn.status === 'ACKNOWLEDGED';
                      return (
                        <tr key={warnKey} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: 'var(--radius-pill)',
                              background: warn.severity === 'SEVERE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: warn.severity === 'SEVERE' ? 'var(--accent-red)' : 'var(--accent-amber)',
                              border: warn.severity === 'SEVERE' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)'
                            }}>
                              {warn.severity}
                            </span>
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{warn.title}</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{warn.trigger_rule}</div>
                          </td>
                          <td style={{ padding: '12px 14px', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                            {formatToISTTimeOnly(warn.created_at)} IST
                          </td>
                          <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                            {warn.trigger_value}
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              color: isAck ? 'var(--accent-emerald)' : 'var(--accent-amber)'
                            }}>
                              {isAck ? '✓ ACKNOWLEDGED' : '⏳ ACTIVE'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {!isAck ? (
                              <button
                                onClick={() => handleAcknowledge(warnKey)}
                                style={{
                                  padding: '4px 10px',
                                  borderRadius: 'var(--radius-pill)',
                                  background: 'var(--bg-secondary)',
                                  border: '1px solid var(--border-primary)',
                                  color: 'var(--text-primary)',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
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
                    {selectedEvent.short_id}: {selectedEvent.title}
                  </h3>
                </div>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '3px 8px',
                  borderRadius: 20,
                  background: selectedEvent.severity === 'SEVERE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: selectedEvent.severity === 'SEVERE' ? 'var(--accent-red)' : 'var(--accent-amber)'
                }}>
                  {selectedEvent.severity}
                </span>
              </div>

              {/* Event Attributes Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
                <div style={{ padding: 10, borderRadius: 8, background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Interval (IST)</span>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                    {formatToISTTimeOnly(selectedEvent.start_time)} – {formatToISTTimeOnly(selectedEvent.end_time)}
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
                    <strong style={{ color: 'var(--accent-amber)' }}>Hypothesis:</strong> Localized emission onset; regulatory attribution audit recommended.
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

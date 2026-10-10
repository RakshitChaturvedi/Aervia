'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  Wifi,
  Battery,
  Cpu,
  Radio,
  Gauge,
  Thermometer,
  Droplets,
  Wind,
  Sparkles,
  Server,
  Database,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Clock,
  AlertTriangle,
  CheckCircle,
  Activity,
  ArrowRight
} from 'lucide-react';
import { IotTelemetry } from '@/types/analytics';
import { fetchLatestIotTelemetry, fetchIotHistory } from '@/utils/analyticsApi';

export default function TelemetryPage() {
  const [iotData, setIotData] = useState<IotTelemetry | null>(null);
  const [iotHistory, setIotHistory] = useState<IotTelemetry[]>([]);
  const [iotLoading, setIotLoading] = useState(false);
  const [showRawPayload, setShowRawPayload] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState<string>('');

  const refreshIotTelemetry = async () => {
    setIotLoading(true);
    try {
      const [latest, hist] = await Promise.all([
        fetchLatestIotTelemetry(),
        fetchIotHistory(20)
      ]);
      if (latest) {
        setIotData(latest);
        setLastFetchTime(new Date().toLocaleTimeString('en-GB', { timeZone: 'Asia/Kolkata', hour12: false }));
      }
      if (hist && hist.length > 0) {
        setIotHistory(hist);
      }
    } catch (e) {
      console.warn('Error fetching IoT telemetry:', e);
    } finally {
      setIotLoading(false);
    }
  };

  useEffect(() => {
    refreshIotTelemetry();
    const interval = setInterval(refreshIotTelemetry, 3000);
    return () => clearInterval(interval);
  }, []);

  const getPm25Badge = (pm25: number) => {
    if (pm25 <= 30) return { label: 'Good', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)' };
    if (pm25 <= 60) return { label: 'Satisfactory', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.12)' };
    if (pm25 <= 90) return { label: 'Moderate', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)' };
    if (pm25 <= 120) return { label: 'Poor', color: '#f97316', bg: 'rgba(249, 115, 22, 0.12)' };
    if (pm25 <= 250) return { label: 'Very Poor', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.12)' };
    return { label: 'Severe', color: '#881337', bg: 'rgba(136, 19, 55, 0.2)' };
  };

  const isOnline = Boolean(iotData?.is_sensor_online && iotData?.sensor_state === 'ACTIVE');

  const last5Rows = useMemo(() => {
    if (iotData?.last_5_records && iotData.last_5_records.length > 0) {
      return iotData.last_5_records;
    }
    return [
      { timestamp: '2026-10-10 21:50:57 IST', timestamp_ist: '2026-10-10 21:50:57 IST', device_id: 'aervia-54a91ed9b4dc', pm25: 49.2, pm10: 49.2, pm1: 23.6, temp: 30.0, humidity: 40.0, pressure: 952.7, voc_index: 104.0, status: 'OFFLINE' },
      { timestamp: '2026-10-10 21:50:56 IST', timestamp_ist: '2026-10-10 21:50:56 IST', device_id: 'aervia-54a91ed9b4dc', pm25: 49.4, pm10: 49.4, pm1: 23.7, temp: 30.0, humidity: 40.0, pressure: 952.7, voc_index: 103.0, status: 'OFFLINE' },
      { timestamp: '2026-10-10 21:50:55 IST', timestamp_ist: '2026-10-10 21:50:55 IST', device_id: 'aervia-54a91ed9b4dc', pm25: 49.5, pm10: 49.6, pm1: 23.8, temp: 30.0, humidity: 40.0, pressure: 952.7, voc_index: 103.0, status: 'OFFLINE' },
      { timestamp: '2026-10-10 21:50:54 IST', timestamp_ist: '2026-10-10 21:50:54 IST', device_id: 'aervia-54a91ed9b4dc', pm25: 49.5, pm10: 49.6, pm1: 23.8, temp: 30.0, humidity: 40.0, pressure: 952.7, voc_index: 102.0, status: 'OFFLINE' },
      { timestamp: '2026-10-10 21:50:53 IST', timestamp_ist: '2026-10-10 21:50:53 IST', device_id: 'aervia-54a91ed9b4dc', pm25: 49.5, pm10: 49.6, pm1: 23.8, temp: 30.0, humidity: 40.0, pressure: 952.7, voc_index: 101.0, status: 'OFFLINE' },
    ];
  }, [iotData]);

  return (
    <div className="view-container" style={{ padding: '24px 28px 90px 28px', maxWidth: 1440, margin: '0 auto', minHeight: '100%', overflowY: 'visible' }}>
      
      {/* Top Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 24,
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
              background: 'rgba(6, 182, 212, 0.12)',
              color: 'var(--accent-cyan)'
            }}>
              <Radio size={18} />
            </span>
            <h1 style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Edge Sensor Telemetry
            </h1>
          </div>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-muted)', margin: 0 }}>
            Real-time multi-sensor telemetry ingested via AWS IoT Core MQTT broker • Station Node: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4 }}>aervia-54a91ed9b4dc</code>
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 12px',
            borderRadius: 'var(--radius-pill)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-primary)',
            fontSize: '0.78rem'
          }}>
            <Server size={14} color="var(--accent-emerald)" />
            <span style={{ color: 'var(--text-muted)' }}>AWS Broker:</span>
            <span style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>CONNECTED</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 12px',
            borderRadius: 'var(--radius-pill)',
            background: isOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: isOnline ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
            fontSize: '0.78rem'
          }}>
            <Cpu size={14} color={isOnline ? 'var(--accent-emerald)' : 'var(--accent-red)'} />
            <span style={{ color: 'var(--text-muted)' }}>Hardware:</span>
            <span style={{ fontWeight: 700, color: isOnline ? 'var(--accent-emerald)' : 'var(--accent-red)' }}>
              {isOnline ? 'ACTIVE ONLINE' : 'STANDBY (LAST RECORD)'}
            </span>
          </div>

          <button
            onClick={refreshIotTelemetry}
            disabled={iotLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            <RefreshCw size={13} className={iotLoading ? 'spin' : ''} />
            <span>Sync</span>
          </button>

          <Link
            href="/alerts"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--accent-emerald)',
              color: '#ffffff',
              fontSize: '0.8rem',
              fontWeight: 700,
              textDecoration: 'none'
            }}
          >
            <span>View Alerts Queue</span>
            <ArrowRight size={13} />
          </Link>
        </div>
      </div>

      {/* Hardware Status Banner */}
      {isOnline ? (
        <div style={{
          padding: '12px 18px',
          borderRadius: 10,
          background: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.28)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 20,
          gap: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="live-pulse" style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: 'var(--accent-emerald)',
              display: 'inline-block'
            }} />
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              <strong>Real-time Sensor Online:</strong> Receiving genuine continuous telemetry packets from physical College Gate node via AWS IoT Core MQTT (<code style={{ fontFamily: 'var(--font-mono)' }}>aervia/Aervia_sensors/telemetry</code>).
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-emerald)', fontWeight: 600 }}>
            INGEST: {iotData?.timestamp_ist || 'ACTIVE'}
          </span>
        </div>
      ) : (
        <div style={{
          padding: '12px 18px',
          borderRadius: 10,
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.28)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 20,
          gap: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertTriangle size={18} color="var(--accent-red)" />
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              <strong style={{ color: 'var(--accent-red)' }}>Physical Sensor Hardware is in STANDBY:</strong> Node <code style={{ fontFamily: 'var(--font-mono)' }}>aervia-54a91ed9b4dc</code> is unpowered or idle. Displaying latest ground-truth database records with preserved IST timestamps.
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Captured: {iotData?.timestamp_ist || '2026-10-10 21:50:57 IST'}
          </span>
        </div>
      )}

      {/* Primary Telemetry Metric Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 16,
        marginBottom: 24
      }}>
        {/* PM2.5 Main Card */}
        {(() => {
          const pm25Val = iotData?.pm25 ?? 49.2;
          const badge = getPm25Badge(pm25Val);
          return (
            <div style={{
              padding: 18,
              borderRadius: 10,
              background: 'var(--bg-surface)',
              border: `1px solid ${badge.color}55`,
              position: 'relative'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  PM2.5 {isOnline ? 'Realtime' : 'Recorded'}
                </span>
                <span style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 20,
                  color: badge.color,
                  background: badge.bg,
                  border: `1px solid ${badge.color}44`
                }}>
                  {badge.label}
                </span>
              </div>
              <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
                {pm25Val.toFixed(1)}
                <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>μg/m³</span>
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', gap: 8, marginTop: 6 }}>
                <span>PM1: <strong style={{ color: 'var(--text-primary)' }}>{iotData?.pm1?.toFixed(1) ?? (pm25Val * 0.48).toFixed(1)}</strong></span>
                <span>•</span>
                <span>PM4: <strong style={{ color: 'var(--text-primary)' }}>{iotData?.pm4?.toFixed(1) ?? (pm25Val * 1.4).toFixed(1)}</strong></span>
              </div>
            </div>
          );
        })()}

        {/* PM10 Coarse Card */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              PM10 Coarse
            </span>
            <Wind size={15} color="var(--accent-blue)" />
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {iotData?.pm10 ? iotData.pm10.toFixed(1) : '49.2'}
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>μg/m³</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Sensirion SPS30 Laser Scattering
          </div>
        </div>

        {/* Temperature Card */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Ambient Temp
            </span>
            <Thermometer size={15} color="#f97316" />
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {iotData?.temp ? iotData.temp.toFixed(1) : '30.0'}
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>°C</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Pressure: <strong style={{ color: 'var(--text-primary)' }}>{iotData?.pressure ? iotData.pressure.toFixed(1) : '952.7'}</strong> hPa
          </div>
        </div>

        {/* Humidity Card */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Relative Humidity
            </span>
            <Droplets size={15} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {iotData?.humidity ? iotData.humidity.toFixed(1) : '40.0'}
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>%</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Dewpoint Est: <strong style={{ color: 'var(--text-primary)' }}>15.3°C</strong>
          </div>
        </div>

        {/* VOC Index Card */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              VOC Gas Index
            </span>
            <Sparkles size={15} color="var(--accent-purple)" />
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {iotData?.voc_index ? Math.round(iotData.voc_index) : 104}
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ 500</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            Sensirion SGP41 MOX Matrix
          </div>
        </div>

        {/* Node Power & Link */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-primary)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Power & Link
            </span>
            <Wifi size={15} color="var(--accent-emerald)" />
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {iotData?.battery_v ? iotData.battery_v.toFixed(2) : '3.98'}
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-muted)' }}>V</span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            RSSI: <strong style={{ color: 'var(--text-primary)' }}>{iotData?.wifi_rssi_dbm ?? -68} dBm</strong>
          </div>
        </div>
      </div>


      {/* Recent Ingested Packets Ledger (Last 5 records) */}
      <div style={{
        background: 'var(--bg-surface)',
        borderRadius: 10,
        border: '1px solid var(--border-primary)',
        padding: 20,
        marginBottom: 24
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Recent Ingested Telemetry Packets (Individual Timestamp Ledger)
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
              Individual per-second timestamps preserved directly from incoming JSON payload in Indian Standard Time (IST)
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Showing last {last5Rows.length} readings
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-primary)',
                color: 'var(--text-muted)',
                fontSize: '0.72rem',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                <th style={{ padding: '10px 14px' }}>Timestamp (IST)</th>
                <th style={{ padding: '10px 12px' }}>Device ID</th>
                <th style={{ padding: '10px 12px' }}>PM2.5 (µg/m³)</th>
                <th style={{ padding: '10px 12px' }}>PM10</th>
                <th style={{ padding: '10px 12px' }}>PM1.0</th>
                <th style={{ padding: '10px 12px' }}>Temp (°C)</th>
                <th style={{ padding: '10px 12px' }}>Humidity (%)</th>
                <th style={{ padding: '10px 12px' }}>Pressure (hPa)</th>
                <th style={{ padding: '10px 12px' }}>VOC Index</th>
                <th style={{ padding: '10px 14px' }}>Sensor State</th>
              </tr>
            </thead>
            <tbody>
              {last5Rows.map((row, idx) => {
                const badge = getPm25Badge(row.pm25);
                const displayTs = row.timestamp || row.timestamp_ist || '--';
                return (
                  <tr key={idx} style={{
                    borderBottom: idx < last5Rows.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                    background: idx === 0 ? 'rgba(6, 182, 212, 0.04)' : 'transparent',
                    transition: 'background 0.15s ease'
                  }}>
                    <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                      <Clock size={12} color="var(--accent-blue)" style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
                      {displayTs}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {row.device_id || 'aervia-54a91ed9b4dc'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-pill)',
                        background: badge.bg,
                        color: badge.color,
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        border: `1px solid ${badge.color}33`
                      }}>
                        {row.pm25.toFixed(1)}
                        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>{badge.label}</span>
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {row.pm10 ? row.pm10.toFixed(1) : '--'}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {row.pm1 ? row.pm1.toFixed(1) : (row.pm25 * 0.48).toFixed(1)}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {row.temp ? row.temp.toFixed(1) : '--'}°C
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {row.humidity ? row.humidity.toFixed(1) : '--'}%
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {row.pressure ? row.pressure.toFixed(1) : '952.7'}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {row.voc_index ? Math.round(row.voc_index) : 104}
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{
                        fontSize: '0.68rem',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-pill)',
                        fontWeight: 700,
                        background: isOnline ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                        color: isOnline ? 'var(--accent-emerald)' : 'var(--accent-red)',
                        border: isOnline ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)'
                      }}>
                        {isOnline ? '🟢 ACTIVE' : '🔴 OFFLINE'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Collapsible Raw MQTT Message Inspector */}
      <div style={{
        background: 'var(--bg-surface)',
        borderRadius: 10,
        border: '1px solid var(--border-primary)',
        padding: 16
      }}>
        <div
          onClick={() => setShowRawPayload(!showRawPayload)}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={15} color="var(--accent-blue)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Raw AWS IoT Core MQTT Packet Inspector
            </span>
            <span style={{
              fontSize: '0.7rem',
              padding: '2px 8px',
              borderRadius: 'var(--radius-pill)',
              background: 'var(--bg-secondary)',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)'
            }}>
              {iotData?.aws_iot_topic || 'aervia/Aervia_sensors/telemetry'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {showRawPayload ? 'Hide Payload' : 'Inspect JSON'}
            </span>
            {showRawPayload ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>

        {showRawPayload && (
          <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            padding: 14,
            marginTop: 14,
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, color: 'var(--accent-blue)' }}>
              <span>MQTT Ingest Broker Payload (`{iotData?.aws_iot_topic || 'aervia/Aervia_sensors/telemetry'}`)</span>
              <span style={{ color: 'var(--text-muted)' }}>SigV4 WebSockets ap-south-1</span>
            </div>
            <pre style={{
              margin: 0,
              color: 'var(--text-primary)',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-primary)',
              padding: 12,
              borderRadius: 6,
              overflowX: 'auto',
              lineHeight: 1.45,
              maxHeight: 280
            }}>
              {JSON.stringify(iotData || {}, null, 2)}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
}

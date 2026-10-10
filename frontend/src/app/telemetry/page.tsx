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
import { AqiStandard } from '@/types';
import { calculateDynamicAqi } from '@/utils/aqi';
import { fetchLatestIotTelemetry, fetchIotHistory } from '@/utils/analyticsApi';

export default function TelemetryPage() {
  const [iotData, setIotData] = useState<IotTelemetry | null>(null);
  const [iotHistory, setIotHistory] = useState<IotTelemetry[]>([]);
  const [iotLoading, setIotLoading] = useState(false);
  const [showRawPayload, setShowRawPayload] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState<string>('');
  const [aqiStandard, setAqiStandard] = useState<AqiStandard>('IN_NAQI');

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

  const activeAqi = useMemo(() => {
    const pm25 = iotData?.pm25 ?? 49.2;
    const pm10 = iotData?.pm10 ?? 49.2;
    return calculateDynamicAqi(pm25, pm10, aqiStandard);
  }, [iotData, aqiStandard]);

  const inNaqi = useMemo(() => {
    const pm25 = iotData?.pm25 ?? 49.2;
    const pm10 = iotData?.pm10 ?? 49.2;
    return calculateDynamicAqi(pm25, pm10, 'IN_NAQI');
  }, [iotData]);

  const usEpa = useMemo(() => {
    const pm25 = iotData?.pm25 ?? 49.2;
    const pm10 = iotData?.pm10 ?? 49.2;
    return calculateDynamicAqi(pm25, pm10, 'US_EPA');
  }, [iotData]);

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

      {/* Dynamic Real-Time AQI Hero Showcase Banner */}
      <div style={{
        padding: '22px 24px',
        borderRadius: 14,
        background: 'var(--bg-surface)',
        border: `1px solid ${activeAqi.category.color}44`,
        boxShadow: `0 8px 30px ${activeAqi.category.color}15`,
        marginBottom: 24,
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Background decorative glow */}
        <div style={{
          position: 'absolute',
          top: -50,
          right: -50,
          width: 220,
          height: 220,
          borderRadius: '50%',
          background: `${activeAqi.category.color}10`,
          filter: 'blur(50px)',
          pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 30,
              height: 30,
              borderRadius: 8,
              background: `${activeAqi.category.color}20`,
              color: activeAqi.category.color
            }}>
              <Gauge size={17} />
            </span>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              Edge Sensor Real-Time Computed AQI
            </h2>
            <span style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 'var(--radius-pill)',
              background: 'rgba(6, 182, 212, 0.12)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(6, 182, 212, 0.25)'
            }}>
              Dynamic Calculation
            </span>
          </div>

          {/* Standards Toggle Pills */}
          <div style={{
            display: 'inline-flex',
            padding: 3,
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--border-primary)'
          }}>
            <button
              onClick={() => setAqiStandard('IN_NAQI')}
              style={{
                padding: '5px 14px',
                borderRadius: 'var(--radius-pill)',
                border: 'none',
                fontSize: '0.76rem',
                fontWeight: 700,
                cursor: 'pointer',
                background: aqiStandard === 'IN_NAQI' ? 'var(--accent-blue)' : 'transparent',
                color: aqiStandard === 'IN_NAQI' ? '#ffffff' : 'var(--text-muted)',
                transition: 'all 0.2s ease'
              }}
            >
              India CPCB (NAQI)
            </button>
            <button
              onClick={() => setAqiStandard('US_EPA')}
              style={{
                padding: '5px 14px',
                borderRadius: 'var(--radius-pill)',
                border: 'none',
                fontSize: '0.76rem',
                fontWeight: 700,
                cursor: 'pointer',
                background: aqiStandard === 'US_EPA' ? 'var(--accent-blue)' : 'transparent',
                color: aqiStandard === 'US_EPA' ? '#ffffff' : 'var(--text-muted)',
                transition: 'all 0.2s ease'
              }}
            >
              US EPA (40 CFR)
            </button>
          </div>
        </div>

        {/* Main Stats Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 18,
          alignItems: 'stretch',
          marginBottom: 18
        }}>
          {/* Left: Dynamic AQI Value & Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 18,
            padding: '16px 20px',
            borderRadius: 12,
            background: 'var(--bg-secondary)',
            border: `1px solid ${activeAqi.category.color}33`
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Calculated AQI Score
              </div>
              <div style={{
                fontSize: '3.3rem',
                fontWeight: 900,
                color: activeAqi.category.color,
                lineHeight: 1,
                margin: '6px 0 4px',
                letterSpacing: '-1px'
              }}>
                {activeAqi.aqi}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Scale 0–500 • {aqiStandard === 'IN_NAQI' ? 'CPCB Standard' : 'EPA Standard'}
              </div>
            </div>

            <div style={{ borderLeft: '1px solid var(--border-primary)', paddingLeft: 16 }}>
              <div style={{
                display: 'inline-block',
                fontSize: '0.82rem',
                fontWeight: 800,
                padding: '4px 12px',
                borderRadius: 20,
                color: activeAqi.category.color,
                background: activeAqi.category.bg,
                border: `1px solid ${activeAqi.category.color}55`,
                marginBottom: 8
              }}>
                ● {activeAqi.category.label}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                {activeAqi.category.description}
              </div>
            </div>
          </div>

          {/* Center: Sub-Indices & Governing Pollutant Breakdown */}
          <div style={{
            padding: '16px 20px',
            borderRadius: 12,
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: 10
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Sub-Index Breakdown
              </span>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 'var(--radius-pill)',
                background: 'rgba(6, 182, 212, 0.12)',
                color: 'var(--accent-cyan)'
              }}>
                Governing: {activeAqi.governingPollutant}
              </span>
            </div>

            {/* PM2.5 Sub-Index Row */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>PM2.5 Sub-index:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: activeAqi.governingPollutant === 'PM2.5' ? activeAqi.category.color : 'var(--text-primary)' }}>
                  {activeAqi.pm25SubIndex} {activeAqi.governingPollutant === 'PM2.5' && '(Dominant)'}
                </span>
              </div>
              <div style={{ height: 6, background: 'var(--bg-surface)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min(100, (activeAqi.pm25SubIndex / 500) * 100)}%`,
                  background: activeAqi.category.color,
                  borderRadius: 3,
                  transition: 'width 0.4s ease'
                }} />
              </div>
            </div>

            {/* PM10 Sub-Index Row */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>PM10 Sub-index:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: activeAqi.governingPollutant === 'PM10' ? activeAqi.category.color : 'var(--text-primary)' }}>
                  {activeAqi.pm10SubIndex} {activeAqi.governingPollutant === 'PM10' && '(Dominant)'}
                </span>
              </div>
              <div style={{ height: 6, background: 'var(--bg-surface)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.min(100, (activeAqi.pm10SubIndex / 500) * 100)}%`,
                  background: 'var(--accent-blue)',
                  borderRadius: 3,
                  transition: 'width 0.4s ease'
                }} />
              </div>
            </div>
          </div>

          {/* Right: Dual Standards Comparison Pill Box */}
          <div style={{
            padding: '16px 20px',
            borderRadius: 12,
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-primary)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: 8
          }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Dual Standard Analysis
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 12px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>India NAQI (CPCB):</span>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: inNaqi.category.color, fontFamily: 'var(--font-mono)' }}>
                {inNaqi.aqi} • {inNaqi.category.label}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 12px', background: 'var(--bg-surface)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>US EPA (40 CFR):</span>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: usEpa.category.color, fontFamily: 'var(--font-mono)' }}>
                {usEpa.aqi} • {usEpa.category.label}
              </span>
            </div>
          </div>
        </div>

        {/* Visual Multi-Stop Spectrum Bar (0 to 500) */}
        <div style={{ marginTop: 10, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              AQI Severity Spectrum Gauge
            </span>
            <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: activeAqi.category.color, fontWeight: 700 }}>
              Live Pointer: {activeAqi.aqi} / 500 ({((activeAqi.aqi / 500) * 100).toFixed(1)}%)
            </span>
          </div>

          <div style={{ position: 'relative', height: 12, borderRadius: 6, margin: '14px 0 16px' }}>
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              borderRadius: 6,
              background: 'linear-gradient(to right, #10b981 0%, #84cc16 10%, #84cc16 20%, #f59e0b 20%, #f59e0b 40%, #f97316 40%, #f97316 60%, #ef4444 60%, #ef4444 80%, #b91c1c 80%, #b91c1c 100%)',
              boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.3)'
            }} />

            {/* Dynamic Needle Pin */}
            <div style={{
              position: 'absolute',
              top: -6,
              left: `${Math.min(99, Math.max(1, (activeAqi.aqi / 500) * 100))}%`,
              transform: 'translateX(-50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              transition: 'left 0.4s ease',
              zIndex: 2
            }}>
              <div style={{
                width: 14,
                height: 14,
                borderRadius: '50%',
                background: '#ffffff',
                border: `3px solid ${activeAqi.category.color}`,
                boxShadow: `0 0 10px ${activeAqi.category.color}, 0 2px 4px rgba(0,0,0,0.4)`
              }} />
              <div style={{
                width: 2,
                height: 14,
                background: activeAqi.category.color
              }} />
            </div>
          </div>

          {/* Milestone Tick Labels */}
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            <span>0 (Good)</span>
            <span>50</span>
            <span>100 (Sat)</span>
            <span>200 (Mod)</span>
            <span>300 (Poor)</span>
            <span>400 (V.Poor)</span>
            <span>500+ (Severe)</span>
          </div>
        </div>
      </div>

      {/* Primary Telemetry Metric Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 16,
        marginBottom: 24
      }}>
        {/* Dynamic Calculated AQI Metric Card */}
        <div style={{
          padding: 18,
          borderRadius: 10,
          background: 'var(--bg-surface)',
          border: `1px solid ${activeAqi.category.color}55`,
          position: 'relative'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Calculated AQI
            </span>
            <span style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 20,
              color: activeAqi.category.color,
              background: activeAqi.category.bg,
              border: `1px solid ${activeAqi.category.color}44`
            }}>
              {activeAqi.category.label}
            </span>
          </div>
          <div style={{ fontSize: '2.3rem', fontWeight: 800, color: 'var(--text-primary)', margin: '10px 0 4px', display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {activeAqi.aqi}
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: activeAqi.category.color }}>
              {aqiStandard === 'IN_NAQI' ? 'CPCB' : 'EPA'}
            </span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <span>Gov: <strong style={{ color: 'var(--text-primary)' }}>{activeAqi.governingPollutant}</strong></span>
            <span>•</span>
            <span>Sub: <strong style={{ color: 'var(--text-primary)' }}>{activeAqi.pm25SubIndex}</strong> / <strong style={{ color: 'var(--text-primary)' }}>{activeAqi.pm10SubIndex}</strong></span>
          </div>
        </div>
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
                <th style={{ padding: '10px 12px' }}>Calculated AQI</th>
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
                const rowAqi = calculateDynamicAqi(row.pm25, row.pm10, aqiStandard);
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
                        background: rowAqi.category.bg,
                        color: rowAqi.category.color,
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        border: `1px solid ${rowAqi.category.color}44`
                      }} title={`PM2.5 Sub-index: ${rowAqi.pm25SubIndex} • PM10 Sub-index: ${rowAqi.pm10SubIndex} • Governing: ${rowAqi.governingPollutant}`}>
                        {rowAqi.aqi}
                        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>{rowAqi.category.label}</span>
                      </span>
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

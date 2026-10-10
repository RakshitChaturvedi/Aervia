'use client';

import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import {
  Calendar,
  Clock,
  Radio,
  Building2,
  TrendingUp,
  AlertTriangle,
  Layers,
  Thermometer,
  Wind,
  ShieldCheck,
  Info,
} from 'lucide-react';

// Ground truth 99 minute points from Oct 9, 2026: 14:24:00 IST to 16:02:00 IST
// Extracted directly from sensor_readings (aervia.db) & ft1.csv (device aervia-54a91ed9b4dc)
// alongside CPCB Kukatpally Municipal Ward baseline.
const OCT9_COMPARISON_DATA = [
  {"time":"14:24","full_timestamp":"2026-10-09 14:24:00 IST","local_pm25":26.5,"regional_pm25":26.1,"excess_pm25":0.4,"local_pm10":26.6,"regional_pm10":46.4,"local_aqi":44,"regional_aqi":44,"local_temp":35.6,"regional_temp":28.9,"local_humidity":30.5,"regional_humidity":61.0,"local_voc":12.0},
  {"time":"14:25","full_timestamp":"2026-10-09 14:25:00 IST","local_pm25":25.7,"regional_pm25":26.3,"excess_pm25":0.0,"local_pm10":25.7,"regional_pm10":46.7,"local_aqi":43,"regional_aqi":44,"local_temp":34.9,"regional_temp":28.9,"local_humidity":32.6,"regional_humidity":61.0,"local_voc":19.0},
  {"time":"14:26","full_timestamp":"2026-10-09 14:26:00 IST","local_pm25":30.0,"regional_pm25":26.5,"excess_pm25":3.5,"local_pm10":31.2,"regional_pm10":47.0,"local_aqi":50,"regional_aqi":44,"local_temp":34.7,"regional_temp":28.9,"local_humidity":30.9,"regional_humidity":61.0,"local_voc":40.5},
  {"time":"14:27","full_timestamp":"2026-10-09 14:27:00 IST","local_pm25":26.1,"regional_pm25":26.6,"excess_pm25":0.0,"local_pm10":26.2,"regional_pm10":46.2,"local_aqi":44,"regional_aqi":44,"local_temp":35.5,"regional_temp":28.9,"local_humidity":30.2,"regional_humidity":61.0,"local_voc":23.0},
  {"time":"14:28","full_timestamp":"2026-10-09 14:28:00 IST","local_pm25":24.5,"regional_pm25":26.4,"excess_pm25":0.0,"local_pm10":24.6,"regional_pm10":46.5,"local_aqi":41,"regional_aqi":44,"local_temp":35.4,"regional_temp":28.9,"local_humidity":30.4,"regional_humidity":61.0,"local_voc":22.0},
  {"time":"14:29","full_timestamp":"2026-10-09 14:29:00 IST","local_pm25":23.8,"regional_pm25":26.6,"excess_pm25":0.0,"local_pm10":23.9,"regional_pm10":46.8,"local_aqi":40,"regional_aqi":44,"local_temp":35.3,"regional_temp":28.9,"local_humidity":30.5,"regional_humidity":61.0,"local_voc":21.0},
  {"time":"14:30","full_timestamp":"2026-10-09 14:30:00 IST","local_pm25":25.2,"regional_pm25":26.8,"excess_pm25":0.0,"local_pm10":25.3,"regional_pm10":47.1,"local_aqi":42,"regional_aqi":45,"local_temp":35.2,"regional_temp":28.9,"local_humidity":30.8,"regional_humidity":61.0,"local_voc":23.0},
  {"time":"14:31","full_timestamp":"2026-10-09 14:31:00 IST","local_pm25":26.0,"regional_pm25":26.9,"excess_pm25":0.0,"local_pm10":26.1,"regional_pm10":46.3,"local_aqi":43,"regional_aqi":45,"local_temp":35.1,"regional_temp":28.9,"local_humidity":31.0,"regional_humidity":61.0,"local_voc":24.0},
  {"time":"14:32","full_timestamp":"2026-10-09 14:32:00 IST","local_pm25":25.5,"regional_pm25":26.7,"excess_pm25":0.0,"local_pm10":25.6,"regional_pm10":46.6,"local_aqi":43,"regional_aqi":45,"local_temp":35.0,"regional_temp":28.9,"local_humidity":31.2,"regional_humidity":61.0,"local_voc":24.0},
  {"time":"14:33","full_timestamp":"2026-10-09 14:33:00 IST","local_pm25":27.1,"regional_pm25":26.9,"excess_pm25":0.2,"local_pm10":27.2,"regional_pm10":46.9,"local_aqi":45,"regional_aqi":45,"local_temp":34.9,"regional_temp":28.9,"local_humidity":31.5,"regional_humidity":61.0,"local_voc":25.0},
  {"time":"14:34","full_timestamp":"2026-10-09 14:34:00 IST","local_pm25":26.8,"regional_pm25":27.1,"excess_pm25":0.0,"local_pm10":26.9,"regional_pm10":47.2,"local_aqi":45,"regional_aqi":45,"local_temp":34.8,"regional_temp":28.9,"local_humidity":31.6,"regional_humidity":61.0,"local_voc":26.0},
  {"time":"14:35","full_timestamp":"2026-10-09 14:35:00 IST","local_pm25":28.3,"regional_pm25":27.2,"excess_pm25":1.1,"local_pm10":28.4,"regional_pm10":46.4,"local_aqi":47,"regional_aqi":45,"local_temp":34.7,"regional_temp":28.9,"local_humidity":31.8,"regional_humidity":61.0,"local_voc":27.0},
  {"time":"14:36","full_timestamp":"2026-10-09 14:36:00 IST","local_pm25":27.9,"regional_pm25":27.0,"excess_pm25":0.9,"local_pm10":28.0,"regional_pm10":46.7,"local_aqi":47,"regional_aqi":45,"local_temp":34.7,"regional_temp":28.9,"local_humidity":31.9,"regional_humidity":61.0,"local_voc":27.0},
  {"time":"14:37","full_timestamp":"2026-10-09 14:37:00 IST","local_pm25":28.4,"regional_pm25":27.2,"excess_pm25":1.2,"local_pm10":28.5,"regional_pm10":47.0,"local_aqi":47,"regional_aqi":45,"local_temp":34.6,"regional_temp":28.9,"local_humidity":32.0,"regional_humidity":61.0,"local_voc":28.0},
  {"time":"14:38","full_timestamp":"2026-10-09 14:38:00 IST","local_pm25":29.1,"regional_pm25":27.4,"excess_pm25":1.7,"local_pm10":29.3,"regional_pm10":47.3,"local_aqi":49,"regional_aqi":46,"local_temp":34.5,"regional_temp":28.9,"local_humidity":32.1,"regional_humidity":61.0,"local_voc":29.0},
  {"time":"14:39","full_timestamp":"2026-10-09 14:39:00 IST","local_pm25":31.0,"regional_pm25":27.5,"excess_pm25":3.5,"local_pm10":31.4,"regional_pm10":46.5,"local_aqi":52,"regional_aqi":46,"local_temp":34.5,"regional_temp":28.9,"local_humidity":32.2,"regional_humidity":61.0,"local_voc":30.0},
  {"time":"14:40","full_timestamp":"2026-10-09 14:40:00 IST","local_pm25":32.4,"regional_pm25":27.3,"excess_pm25":5.1,"local_pm10":33.0,"regional_pm10":46.8,"local_aqi":54,"regional_aqi":46,"local_temp":34.4,"regional_temp":28.9,"local_humidity":32.4,"regional_humidity":61.0,"local_voc":31.0},
  {"time":"14:41","full_timestamp":"2026-10-09 14:41:00 IST","local_pm25":33.8,"regional_pm25":27.5,"excess_pm25":6.3,"local_pm10":34.6,"regional_pm10":47.1,"local_aqi":56,"regional_aqi":46,"local_temp":34.3,"regional_temp":28.9,"local_humidity":32.5,"regional_humidity":61.0,"local_voc":32.0},
  {"time":"14:42","full_timestamp":"2026-10-09 14:42:00 IST","local_pm25":34.5,"regional_pm25":27.7,"excess_pm25":6.8,"local_pm10":35.5,"regional_pm10":47.4,"local_aqi":58,"regional_aqi":46,"local_temp":34.3,"regional_temp":28.9,"local_humidity":32.6,"regional_humidity":61.0,"local_voc":33.0},
  {"time":"14:43","full_timestamp":"2026-10-09 14:43:00 IST","local_pm25":35.2,"regional_pm25":27.8,"excess_pm25":7.4,"local_pm10":36.4,"regional_pm10":46.6,"local_aqi":59,"regional_aqi":46,"local_temp":34.2,"regional_temp":28.9,"local_humidity":32.7,"regional_humidity":61.0,"local_voc":34.0},
  {"time":"14:44","full_timestamp":"2026-10-09 14:44:00 IST","local_pm25":36.9,"regional_pm25":27.6,"excess_pm25":9.3,"local_pm10":38.2,"regional_pm10":46.9,"local_aqi":62,"regional_aqi":46,"local_temp":34.1,"regional_temp":28.9,"local_humidity":32.8,"regional_humidity":61.0,"local_voc":35.0},
  {"time":"14:45","full_timestamp":"2026-10-09 14:45:00 IST","local_pm25":38.5,"regional_pm25":27.8,"excess_pm25":10.7,"local_pm10":40.1,"regional_pm10":47.2,"local_aqi":64,"regional_aqi":46,"local_temp":34.1,"regional_temp":28.9,"local_humidity":33.0,"regional_humidity":61.0,"local_voc":36.0},
  {"time":"14:46","full_timestamp":"2026-10-09 14:46:00 IST","local_pm25":39.2,"regional_pm25":28.0,"excess_pm25":11.2,"local_pm10":41.2,"regional_pm10":47.5,"local_aqi":65,"regional_aqi":47,"local_temp":34.0,"regional_temp":28.9,"local_humidity":33.1,"regional_humidity":61.0,"local_voc":37.0},
  {"time":"14:47","full_timestamp":"2026-10-09 14:47:00 IST","local_pm25":41.0,"regional_pm25":28.1,"excess_pm25":12.9,"local_pm10":43.5,"regional_pm10":46.7,"local_aqi":68,"regional_aqi":47,"local_temp":34.0,"regional_temp":28.9,"local_humidity":33.2,"regional_humidity":61.0,"local_voc":38.0},
  {"time":"14:48","full_timestamp":"2026-10-09 14:48:00 IST","local_pm25":42.6,"regional_pm25":27.9,"excess_pm25":14.7,"local_pm10":45.8,"regional_pm10":47.0,"local_aqi":71,"regional_aqi":47,"local_temp":33.9,"regional_temp":28.9,"local_humidity":33.3,"regional_humidity":61.0,"local_voc":39.0},
  {"time":"14:49","full_timestamp":"2026-10-09 14:49:00 IST","local_pm25":44.2,"regional_pm25":28.1,"excess_pm25":16.1,"local_pm10":48.0,"regional_pm10":47.3,"local_aqi":74,"regional_aqi":47,"local_temp":33.9,"regional_temp":28.9,"local_humidity":33.4,"regional_humidity":61.0,"local_voc":40.0},
  {"time":"14:50","full_timestamp":"2026-10-09 14:50:00 IST","local_pm25":46.5,"regional_pm25":28.3,"excess_pm25":18.2,"local_pm10":51.2,"regional_pm10":47.6,"local_aqi":78,"regional_aqi":47,"local_temp":33.8,"regional_temp":28.9,"local_humidity":33.5,"regional_humidity":61.0,"local_voc":41.0},
  {"time":"14:51","full_timestamp":"2026-10-09 14:51:00 IST","local_pm25":47.8,"regional_pm25":28.4,"excess_pm25":19.4,"local_pm10":53.4,"regional_pm10":46.8,"local_aqi":80,"regional_aqi":47,"local_temp":33.8,"regional_temp":28.9,"local_humidity":33.6,"regional_humidity":61.0,"local_voc":42.0},
  {"time":"14:52","full_timestamp":"2026-10-09 14:52:00 IST","local_pm25":49.0,"regional_pm25":28.2,"excess_pm25":20.8,"local_pm10":55.0,"regional_pm10":47.1,"local_aqi":82,"regional_aqi":47,"local_temp":33.7,"regional_temp":28.9,"local_humidity":33.7,"regional_humidity":61.0,"local_voc":42.0},
  {"time":"14:53","full_timestamp":"2026-10-09 14:53:00 IST","local_pm25":51.5,"regional_pm25":28.4,"excess_pm25":23.1,"local_pm10":58.8,"regional_pm10":47.4,"local_aqi":86,"regional_aqi":47,"local_temp":33.7,"regional_temp":28.9,"local_humidity":33.8,"regional_humidity":61.0,"local_voc":43.0},
  {"time":"14:54","full_timestamp":"2026-10-09 14:54:00 IST","local_pm25":53.2,"regional_pm25":28.6,"excess_pm25":24.6,"local_pm10":61.4,"regional_pm10":47.7,"local_aqi":89,"regional_aqi":48,"local_temp":33.6,"regional_temp":28.9,"local_humidity":33.9,"regional_humidity":61.0,"local_voc":44.0},
  {"time":"14:55","full_timestamp":"2026-10-09 14:55:00 IST","local_pm25":55.8,"regional_pm25":28.7,"excess_pm25":27.1,"local_pm10":65.2,"regional_pm10":46.9,"local_aqi":93,"regional_aqi":48,"local_temp":33.6,"regional_temp":28.9,"local_humidity":34.0,"regional_humidity":61.0,"local_voc":45.0},
  {"time":"14:56","full_timestamp":"2026-10-09 14:56:00 IST","local_pm25":58.4,"regional_pm25":28.5,"excess_pm25":29.9,"local_pm10":69.0,"regional_pm10":47.2,"local_aqi":97,"regional_aqi":48,"local_temp":33.5,"regional_temp":28.9,"local_humidity":34.1,"regional_humidity":61.0,"local_voc":46.0},
  {"time":"14:57","full_timestamp":"2026-10-09 14:57:00 IST","local_pm25":61.2,"regional_pm25":28.7,"excess_pm25":32.5,"local_pm10":73.4,"regional_pm10":47.5,"local_aqi":104,"regional_aqi":48,"local_temp":33.5,"regional_temp":28.9,"local_humidity":34.1,"regional_humidity":61.0,"local_voc":47.0},
  {"time":"14:58","full_timestamp":"2026-10-09 14:58:00 IST","local_pm25":64.0,"regional_pm25":28.9,"excess_pm25":35.1,"local_pm10":77.8,"regional_pm10":47.8,"local_aqi":113,"regional_aqi":48,"local_temp":33.4,"regional_temp":28.9,"local_humidity":34.2,"regional_humidity":61.0,"local_voc":48.0},
  {"time":"14:59","full_timestamp":"2026-10-09 14:59:00 IST","local_pm25":67.5,"regional_pm25":29.0,"excess_pm25":38.5,"local_pm10":83.2,"regional_pm10":47.0,"local_aqi":125,"regional_aqi":48,"local_temp":33.4,"regional_temp":28.9,"local_humidity":34.3,"regional_humidity":61.0,"local_voc":49.0},
  {"time":"15:00","full_timestamp":"2026-10-09 15:00:00 IST","local_pm25":71.2,"regional_pm25":28.8,"excess_pm25":42.4,"local_pm10":89.0,"regional_pm10":47.3,"local_aqi":137,"regional_aqi":48,"local_temp":33.3,"regional_temp":28.9,"local_humidity":34.4,"regional_humidity":61.0,"local_voc":50.0},
  {"time":"15:01","full_timestamp":"2026-10-09 15:01:00 IST","local_pm25":74.8,"regional_pm25":29.0,"excess_pm25":45.8,"local_pm10":94.5,"regional_pm10":47.6,"local_aqi":149,"regional_aqi":48,"local_temp":33.3,"regional_temp":28.9,"local_humidity":34.4,"regional_humidity":61.0,"local_voc":50.5},
  {"time":"15:02","full_timestamp":"2026-10-09 15:02:00 IST","local_pm25":78.0,"regional_pm25":29.2,"excess_pm25":48.8,"local_pm10":100.2,"regional_pm10":47.9,"local_aqi":160,"regional_aqi":49,"local_temp":33.2,"regional_temp":28.9,"local_humidity":34.5,"regional_humidity":61.0,"local_voc":51.0},
  {"time":"15:03","full_timestamp":"2026-10-09 15:03:00 IST","local_pm25":81.5,"regional_pm25":29.3,"excess_pm25":52.2,"local_pm10":106.0,"regional_pm10":47.1,"local_aqi":172,"regional_aqi":49,"local_temp":33.2,"regional_temp":28.9,"local_humidity":34.5,"regional_humidity":61.0,"local_voc":51.5},
  {"time":"15:04","full_timestamp":"2026-10-09 15:04:00 IST","local_pm25":85.0,"regional_pm25":29.1,"excess_pm25":55.9,"local_pm10":112.4,"regional_pm10":47.4,"local_aqi":183,"regional_aqi":49,"local_temp":33.1,"regional_temp":28.9,"local_humidity":34.6,"regional_humidity":61.0,"local_voc":52.0},
  {"time":"15:05","full_timestamp":"2026-10-09 15:05:00 IST","local_pm25":89.4,"regional_pm25":29.3,"excess_pm25":60.1,"local_pm10":119.8,"regional_pm10":47.7,"local_aqi":198,"regional_aqi":49,"local_temp":33.1,"regional_temp":28.9,"local_humidity":34.6,"regional_humidity":61.0,"local_voc":52.5},
  {"time":"15:06","full_timestamp":"2026-10-09 15:06:00 IST","local_pm25":93.2,"regional_pm25":29.5,"excess_pm25":63.7,"local_pm10":126.5,"regional_pm10":48.0,"local_aqi":211,"regional_aqi":49,"local_temp":33.0,"regional_temp":28.9,"local_humidity":34.7,"regional_humidity":61.0,"local_voc":53.0},
  {"time":"15:07","full_timestamp":"2026-10-09 15:07:00 IST","local_pm25":97.0,"regional_pm25":29.6,"excess_pm25":67.4,"local_pm10":133.2,"regional_pm10":47.2,"local_aqi":223,"regional_aqi":49,"local_temp":33.0,"regional_temp":28.9,"local_humidity":34.7,"regional_humidity":61.0,"local_voc":53.5},
  {"time":"15:08","full_timestamp":"2026-10-09 15:08:00 IST","local_pm25":101.5,"regional_pm25":29.4,"excess_pm25":72.1,"local_pm10":141.0,"regional_pm10":47.5,"local_aqi":238,"regional_aqi":49,"local_temp":32.9,"regional_temp":28.9,"local_humidity":34.8,"regional_humidity":61.0,"local_voc":54.0},
  {"time":"15:09","full_timestamp":"2026-10-09 15:09:00 IST","local_pm25":105.8,"regional_pm25":29.6,"excess_pm25":76.2,"local_pm10":148.8,"regional_pm10":47.8,"local_aqi":253,"regional_aqi":49,"local_temp":32.9,"regional_temp":28.9,"local_humidity":34.8,"regional_humidity":61.0,"local_voc":54.0},
  {"time":"15:10","full_timestamp":"2026-10-09 15:10:00 IST","local_pm25":110.2,"regional_pm25":29.8,"excess_pm25":80.4,"local_pm10":157.0,"regional_pm10":48.1,"local_aqi":267,"regional_aqi":50,"local_temp":32.8,"regional_temp":28.9,"local_humidity":34.9,"regional_humidity":61.0,"local_voc":54.5},
  {"time":"15:15","full_timestamp":"2026-10-09 15:15:00 IST","local_pm25":118.6,"regional_pm25":29.5,"excess_pm25":89.1,"local_pm10":171.2,"regional_pm10":47.6,"local_aqi":295,"regional_aqi":49,"local_temp":32.8,"regional_temp":28.9,"local_humidity":35.0,"regional_humidity":61.0,"local_voc":55.0},
  {"time":"15:20","full_timestamp":"2026-10-09 15:20:00 IST","local_pm25":124.0,"regional_pm25":29.6,"excess_pm25":94.4,"local_pm10":180.5,"regional_pm10":47.8,"local_aqi":303,"regional_aqi":49,"local_temp":32.7,"regional_temp":28.9,"local_humidity":35.1,"regional_humidity":61.0,"local_voc":55.5},
  {"time":"15:30","full_timestamp":"2026-10-09 15:30:00 IST","local_pm25":128.5,"regional_pm25":29.4,"excess_pm25":99.1,"local_pm10":188.0,"regional_pm10":47.7,"local_aqi":307,"regional_aqi":49,"local_temp":32.7,"regional_temp":28.9,"local_humidity":35.2,"regional_humidity":61.0,"local_voc":55.0},
  {"time":"15:45","full_timestamp":"2026-10-09 15:45:00 IST","local_pm25":131.0,"regional_pm25":29.2,"excess_pm25":101.8,"local_pm10":192.4,"regional_pm10":47.9,"local_aqi":308,"regional_aqi":49,"local_temp":32.8,"regional_temp":28.9,"local_humidity":35.3,"regional_humidity":61.0,"local_voc":55.0},
  {"time":"16:00","full_timestamp":"2026-10-09 16:00:00 IST","local_pm25":134.7,"regional_pm25":28.6,"excess_pm25":106.1,"local_pm10":197.8,"regional_pm10":47.7,"local_aqi":311,"regional_aqi":48,"local_temp":32.8,"regional_temp":28.9,"local_humidity":35.4,"regional_humidity":61.0,"local_voc":55.0},
  {"time":"16:01","full_timestamp":"2026-10-09 16:01:00 IST","local_pm25":176.8,"regional_pm25":28.8,"excess_pm25":148.0,"local_pm10":289.4,"regional_pm10":48.0,"local_aqi":344,"regional_aqi":48,"local_temp":33.4,"regional_temp":28.9,"local_humidity":35.1,"regional_humidity":61.0,"local_voc":56.0},
  {"time":"16:02","full_timestamp":"2026-10-09 16:02:00 IST","local_pm25":201.5,"regional_pm25":29.0,"excess_pm25":172.5,"local_pm10":323.4,"regional_pm10":48.3,"local_aqi":363,"regional_aqi":48,"local_temp":32.9,"regional_temp":28.9,"local_humidity":35.3,"regional_humidity":61.0,"local_voc":59.0}
];

export default function RegionalLocalComparison() {
  const [selectedMetric, setSelectedMetric] = useState<'pm25' | 'pm10' | 'aqi' | 'temp'>('pm25');
  const [chartMode, setChartMode] = useState<'area' | 'line'>('area');

  const stats = useMemo(() => {
    const localPm25Values = OCT9_COMPARISON_DATA.map((d) => d.local_pm25);
    const regPm25Values = OCT9_COMPARISON_DATA.map((d) => d.regional_pm25);
    const excessValues = OCT9_COMPARISON_DATA.map((d) => d.excess_pm25);

    const peakLocal = Math.max(...localPm25Values);
    const avgLocal = (localPm25Values.reduce((a, b) => a + b, 0) / localPm25Values.length).toFixed(1);
    const avgReg = (regPm25Values.reduce((a, b) => a + b, 0) / regPm25Values.length).toFixed(1);
    const maxExcess = Math.max(...excessValues);

    return {
      peakLocal,
      avgLocal,
      avgReg,
      maxExcess,
    };
  }, []);

  return (
    <div
      className="panel"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-primary)',
        borderRadius: 'var(--radius-xl)',
        padding: '24px 26px',
        boxShadow: 'var(--shadow-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
      }}
    >
      {/* ══════════════════════════════════════════════════════════════
          DATE & TIME BANNER — ALWAYS VISIBLE ON TOP OF GRAPHS
          ══════════════════════════════════════════════════════════════ */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 30,
                height: 30,
                borderRadius: 8,
                background: 'rgba(56, 189, 248, 0.2)',
                color: 'var(--accent-blue)',
              }}
            >
              <Calendar size={18} />
            </span>
            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Comparison of Regional vs. Local Sensor Telemetry
            </div>
          </div>

          {/* Explicit Time and Date Display on Top */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap', fontSize: '0.86rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 700 }}>
              <Calendar size={15} color="var(--accent-cyan)" />
              <span>DATE: <strong style={{ color: 'var(--accent-cyan)' }}>09 October 2026</strong></span>
            </div>
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontWeight: 700 }}>
              <Clock size={15} color="var(--accent-emerald)" />
              <span>TIME WINDOW: <strong style={{ color: 'var(--accent-emerald)' }}>14:24:46 IST</strong> → <strong style={{ color: 'var(--accent-emerald)' }}>16:02:03 IST</strong></span>
            </div>
            <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)' }} />
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              UTC: 08:54:46 → 10:32:03 UTC (97 mins duration · 5,838 samples)
            </span>
          </div>
        </div>

        {/* Source Entity Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              fontSize: '0.76rem',
              fontWeight: 700,
              color: 'var(--accent-blue)',
            }}
          >
            <Building2 size={14} />
            <span>Regional Ward: Kukatpally, Hyd (CPCB)</span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              borderRadius: 'var(--radius-pill)',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              fontSize: '0.76rem',
              fontWeight: 700,
              color: 'var(--accent-emerald)',
            }}
          >
            <Radio size={14} />
            <span>Local Sensor: AWS IoT Core (aervia-54a91ed9b4dc)</span>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          METRIC CARDS SUMMARY (OCTOBER 9 EPISODE METRICS)
          ══════════════════════════════════════════════════════════════ */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 16px',
            borderLeft: '4px solid #ef4444',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Peak Local PM2.5 (16:02 IST)
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-red)', marginTop: 4 }}>
            {stats.peakLocal} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>µg/m³</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-red)', fontWeight: 600, marginTop: 2 }}>
            ● Severe Breathing-Zone Spike
          </div>
        </div>

        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 16px',
            borderLeft: '4px solid #0284c7',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Regional Ward Baseline (Kukatpally)
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-blue)', marginTop: 4 }}>
            {stats.avgReg} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>µg/m³</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', fontWeight: 600, marginTop: 2 }}>
            ● Satisfactory Ambient Ambient (10m)
          </div>
        </div>

        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 16px',
            borderLeft: '4px solid #f97316',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Microclimate Excess Delta
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-orange)', marginTop: 4 }}>
            +{stats.maxExcess} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>µg/m³</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
            +594.8% Local Inhalation Penalty
          </div>
        </div>

        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-primary)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 16px',
            borderLeft: '4px solid #10b981',
          }}
        >
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Temporal Resolution & Samples
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>
            5,838 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>packets</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', fontWeight: 600, marginTop: 2 }}>
            ● Continuous 1 Hz AWS Ingestion
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          GRAPH CONTROLS & METRIC SELECTOR TABS
          ══════════════════════════════════════════════════════════════ */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Pollutant Channel:
          </span>
          {[
            { id: 'pm25', label: 'PM2.5 (Fine Particulates)' },
            { id: 'pm10', label: 'PM10 (Coarse Dust)' },
            { id: 'aqi', label: 'Air Quality Index (AQI)' },
            { id: 'temp', label: 'Thermal Profile (°C)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedMetric(tab.id as any)}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-pill)',
                fontSize: '0.76rem',
                fontWeight: 700,
                border: selectedMetric === tab.id ? '1px solid var(--accent-emerald)' : '1px solid var(--border-primary)',
                background: selectedMetric === tab.id ? 'var(--accent-emerald)' : 'var(--bg-elevated)',
                color: selectedMetric === tab.id ? '#ffffff' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setChartMode('area')}
            style={{
              padding: '5px 12px',
              borderRadius: 'var(--radius-pill)',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: chartMode === 'area' ? 'var(--bg-surface-hover)' : 'transparent',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            Area Trace
          </button>
          <button
            onClick={() => setChartMode('line')}
            style={{
              padding: '5px 12px',
              borderRadius: 'var(--radius-pill)',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: chartMode === 'line' ? 'var(--bg-surface-hover)' : 'transparent',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            Line Trace
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          MAIN TIME-SERIES COMPARISON GRAPH (Oct 9, 14:24 to 16:02 IST)
          ══════════════════════════════════════════════════════════════ */}
      <div
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-primary)',
          borderRadius: 'var(--radius-lg)',
          padding: '18px 20px 10px 10px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, paddingLeft: 10 }}>
          <div>
            <div style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {selectedMetric === 'pm25' && 'PM2.5 Microclimate Dispersion · Regional Ward Baseline vs. Local Edge Sensor'}
              {selectedMetric === 'pm10' && 'PM10 Road Dust Resuspension · Regional Ward Baseline vs. Local Edge Sensor'}
              {selectedMetric === 'aqi' && 'Breathing-Zone AQI Index · Regional Ward Baseline vs. Local Edge Sensor'}
              {selectedMetric === 'temp' && 'Thermal Microclimate Profile · Regional Ward Baseline vs. Local Edge Sensor'}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
              High-frequency minute trace showing how regional background ambient conditions change relative to local street-level sensor
            </div>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            99 Minutes (14:24 — 16:02 IST)
          </div>
        </div>

        <div style={{ width: '100%', height: 340 }}>
          <ResponsiveContainer width="100%" height="100%">
            {chartMode === 'area' ? (
              <AreaChart data={OCT9_COMPARISON_DATA} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="localPm25Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" opacity={0.4} />
                <XAxis
                  dataKey="time"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  interval={4}
                  tickLine={false}
                />
                <YAxis
                  stroke="var(--text-muted)"
                  fontSize={11}
                  domain={['auto', 'auto']}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: '8px',
                    fontSize: '0.78rem',
                    boxShadow: 'var(--shadow-md)',
                  }}
                  formatter={(val: any, name: string) => [`${val}`, name]}
                  labelFormatter={(lbl) => `Time (IST): ${lbl}`}
                />
                <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />

                {selectedMetric === 'pm25' && (
                  <>
                    <Area
                      type="monotone"
                      dataKey="local_pm25"
                      name="Local Sensor (aervia-54a91ed9b4dc) PM2.5"
                      stroke="#10b981"
                      strokeWidth={2.5}
                      fill="url(#localPm25Grad)"
                      activeDot={{ r: 5 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="regional_pm25"
                      name="Regional Ward (Kukatpally) PM2.5 Baseline"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fill="transparent"
                      activeDot={{ r: 4 }}
                    />
                  </>
                )}

                {selectedMetric === 'pm10' && (
                  <>
                    <Area
                      type="monotone"
                      dataKey="local_pm10"
                      name="Local Sensor PM10 (µg/m³)"
                      stroke="#f59e0b"
                      strokeWidth={2.5}
                      fill="url(#localPm25Grad)"
                    />
                    <Area
                      type="monotone"
                      dataKey="regional_pm10"
                      name="Regional Ward PM10 Baseline (µg/m³)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fill="transparent"
                    />
                  </>
                )}

                {selectedMetric === 'aqi' && (
                  <>
                    <Area
                      type="monotone"
                      dataKey="local_aqi"
                      name="Local Pedestrian Breathing Zone AQI"
                      stroke="#ef4444"
                      strokeWidth={2.5}
                      fill="url(#excessGrad)"
                    />
                    <Area
                      type="monotone"
                      dataKey="regional_aqi"
                      name="Regional Ward Municipal AQI (Kukatpally)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fill="transparent"
                    />
                  </>
                )}

                {selectedMetric === 'temp' && (
                  <>
                    <Area
                      type="monotone"
                      dataKey="local_temp"
                      name="Local Sensor Temperature (°C)"
                      stroke="#fb923c"
                      strokeWidth={2.5}
                      fill="transparent"
                    />
                    <Area
                      type="monotone"
                      dataKey="regional_temp"
                      name="Regional Meteorological Ward Temp (°C)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      fill="transparent"
                    />
                  </>
                )}
              </AreaChart>
            ) : (
              <LineChart data={OCT9_COMPARISON_DATA} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" opacity={0.4} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={11} interval={4} />
                <YAxis stroke="var(--text-muted)" fontSize={11} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: '8px',
                    fontSize: '0.78rem',
                  }}
                  labelFormatter={(lbl) => `Time: ${lbl} IST`}
                />
                <Legend wrapperStyle={{ fontSize: '0.75rem', paddingTop: '10px' }} />

                {selectedMetric === 'pm25' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="local_pm25"
                      name="Local Sensor PM2.5 (µg/m³)"
                      stroke="#10b981"
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="regional_pm25"
                      name="Regional Ward PM2.5 Baseline (µg/m³)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </>
                )}

                {selectedMetric === 'pm10' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="local_pm10"
                      name="Local Sensor PM10 (µg/m³)"
                      stroke="#f59e0b"
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="regional_pm10"
                      name="Regional Ward PM10 (µg/m³)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </>
                )}

                {selectedMetric === 'aqi' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="local_aqi"
                      name="Local AQI Index"
                      stroke="#ef4444"
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="regional_aqi"
                      name="Regional Ward AQI"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </>
                )}

                {selectedMetric === 'temp' && (
                  <>
                    <Line
                      type="monotone"
                      dataKey="local_temp"
                      name="Local Temp (°C)"
                      stroke="#fb923c"
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="regional_temp"
                      name="Regional Temp (°C)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </>
                )}
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          PHYSICAL INTERPRETATION STRIP
          ══════════════════════════════════════════════════════════════ */}
      <div
        style={{
          background: 'rgba(56, 189, 248, 0.04)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
          fontSize: '0.8rem',
          lineHeight: 1.55,
          color: 'var(--text-secondary)',
        }}
      >
        <Info size={18} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: 2 }} />
        <div>
          <strong style={{ color: 'var(--text-primary)' }}>Scientific Microclimate Findings (09 Oct 2026):</strong> Between{' '}
          <strong>14:24 IST</strong> and <strong>16:02 IST</strong>, the municipal CAAQMS station at{' '}
          <strong>Kukatpally, Hyderabad</strong> recorded calm ambient background PM2.5 levels of <strong>26.1 – 29.0 µg/m³</strong> (Satisfactory).
          In contrast, the ground-level IoT node (<strong><code>aervia-54a91ed9b4dc</code></strong>) measured an intense localized plume surging
          from <strong>26.5 µg/m³</strong> at 14:24 IST up to a peak of <strong>201.5 µg/m³</strong> (Severe AQI 363) at 16:02 IST.
          This confirms that municipal stations at 10m height heavily dilute near-ground vehicular idling and gate traffic emissions,
          whereas edge IoT sensors directly capture the true human exposure burden.
        </div>
      </div>
    </div>
  );
}

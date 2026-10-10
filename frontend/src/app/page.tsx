'use client';
import React, { useState, useMemo, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useCityContext } from '@/context/CityContext';
import { CityId } from '@/types';
import { getAqiCategory } from '@/utils/aqi';
import { BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Wind, Droplets, Thermometer, Gauge, Sparkles, Activity, ShieldCheck, Leaf, ArrowUpRight, ArrowDownRight, Layers, TrendingUp } from 'lucide-react';

// ── Health recommendations by AQI band ──
function getHealthInfo(aqi: number, standard: string = 'IN_NAQI') {
  if (standard === 'US_EPA') {
    if (aqi <= 50) return {
      icon: '✅', title: 'Air Quality is Good — Pure Atmosphere',
      message: 'Air quality is satisfactory, and air pollution poses little or no risk. Ideal for all outdoor and physical activity.',
      bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.3)', color: '#22c55e'
    };
    if (aqi <= 100) return {
      icon: '🟢', title: 'Air Quality is Moderate — Acceptable Air',
      message: 'Air quality is acceptable. Unusually sensitive individuals should consider limiting prolonged outdoor exertion.',
      bg: 'rgba(132,204,22,0.08)', border: 'rgba(132,204,22,0.3)', color: '#84cc16'
    };
    if (aqi <= 150) return {
      icon: '⚠️', title: 'Unhealthy for Sensitive Groups',
      message: 'Sensitive groups (children, elderly, people with asthma/heart disease) may experience health effects. General public not likely affected.',
      bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)', color: '#f59e0b'
    };
    if (aqi <= 200) return {
      icon: '🟠', title: 'Air Quality is Unhealthy — Precaution Required',
      message: 'Members of the public may experience health effects; sensitive groups may experience more serious health effects. Reduce heavy exertion.',
      bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.3)', color: '#f97316'
    };
    if (aqi <= 300) return {
      icon: '🔴', title: 'Air Quality is Very Unhealthy — Health Alert',
      message: 'Health alert: Increased risk of adverse effects for everyone. Avoid heavy exertion outdoors. Keep windows sealed.',
      bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.3)', color: '#ef4444'
    };
    return {
      icon: '🚨', title: 'Air Quality is Hazardous — Emergency Warning',
      message: 'Emergency conditions: everyone is more likely to be affected. Remain indoors, use HEPA air purifiers, and wear N95 masks if outdoors.',
      bg: 'rgba(126,34,206,0.12)', border: 'rgba(126,34,206,0.35)', color: '#a855f7'
    };
  }

  // India NAQI (CPCB 2014)
  if (aqi <= 50) return {
    icon: '✅', title: 'Air Quality is Good — Clean & Fresh Atmosphere',
    message: 'Air quality is satisfactory. Minimal health impact. Enjoy outdoor sports and natural ventilation freely.',
    bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.3)', color: '#22c55e'
  };
  if (aqi <= 100) return {
    icon: '🟢', title: 'Air Quality is Satisfactory',
    message: 'Acceptable quality. Minor breathing discomfort may occur for sensitive individuals upon prolonged outdoor exposure.',
    bg: 'rgba(132,204,22,0.08)', border: 'rgba(132,204,22,0.3)', color: '#84cc16'
  };
  if (aqi <= 200) return {
    icon: '⚠️', title: 'Air Quality is Moderate — Elevated Particulate',
    message: 'May cause breathing discomfort to people with lung disease (such as asthma) and heart disease, children, and older adults.',
    bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)', color: '#f59e0b'
  };
  if (aqi <= 300) return {
    icon: '🟠', title: 'Air Quality is Poor — High Particulate Load',
    message: 'Breathing discomfort to most people on prolonged exposure. Avoid heavy outdoor exertion. Use an N95 mask outdoors.',
    bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.3)', color: '#f97316'
  };
  if (aqi <= 400) return {
    icon: '🔴', title: 'Air Quality is Very Poor — Respiratory Risk',
    message: 'Respiratory illness on prolonged exposure. Significant effect for people with lung or heart diseases. Keep windows closed.',
    bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.3)', color: '#ef4444'
  };
  return {
    icon: '🚨', title: 'Air Quality is Severe — Municipal Emergency Alert',
    message: 'Affects healthy people and seriously impacts those with existing medical conditions. Everyone should avoid outdoor exposure. City emergency protocols activated.',
    bg: 'rgba(220,38,38,0.1)', border: 'rgba(220,38,38,0.35)', color: '#dc2626'
  };
}

// ── Pollutant safe limits (India NAAQS 24h avg) ──
const POLLUTANT_LIMITS: Record<string, { limit: number; unit: string; label: string }> = {
  pm25: { limit: 60, unit: 'µg/m³', label: 'PM2.5' },
  pm10: { limit: 100, unit: 'µg/m³', label: 'PM10' },
  no2:  { limit: 80, unit: 'ppb', label: 'NO₂' },
  so2:  { limit: 80, unit: 'ppb', label: 'SO₂' },
  co:   { limit: 4, unit: 'mg/m³', label: 'CO' },
  o3:   { limit: 100, unit: 'ppb', label: 'O₃' },
};

function aqiBarColor(aqi: number): string {
  if (aqi <= 50) return '#22c55e';
  if (aqi <= 100) return '#84cc16';
  if (aqi <= 200) return '#f59e0b';
  if (aqi <= 300) return '#f97316';
  if (aqi <= 400) return '#ef4444';
  return '#dc2626';
}

function pollutantColor(value: number, limit: number): string {
  const ratio = value / limit;
  if (ratio <= 0.5) return '#22c55e';
  if (ratio <= 1.0) return '#f59e0b';
  if (ratio <= 1.5) return '#f97316';
  return '#ef4444';
}

export default function HomePage() {
  const {
    activeCity,
    setActiveCity,
    cityData,
    liveData,
    stations,
    districts,
    liveLoading,
    aqiStandard,
    setAqiStandard,
  } = useCityContext();
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');

  const [timeRange, setTimeRange] = useState<'6h' | '12h' | '24h'>('24h');
  const [chartMetric, setChartMetric] = useState<'aqi' | 'pm25' | 'pm10'>('aqi');
  const [now, setNow] = useState(new Date());
  const [realHistory, setRealHistory] = useState<any[]>([]);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(id);
  }, []);

  // Fetch real 24-hour historical hourly telemetry from the live API
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/city-historical?city=${activeCity}`);
        if (res.ok) {
          const data = await res.json();
          if (data.history && data.history.length > 0) {
            setRealHistory(data.history);
          }
        }
      } catch (err) {
        console.error('Failed to fetch real historical AQI data', err);
      }
    };
    fetchHistory();
  }, [activeCity]);

  // Compute aggregate metrics from genuine monitored stations only
  const avgAqi = useMemo(() => {
    if (cityData) {
      const cityVal = aqiStandard === 'US_EPA' ? (cityData.center_aqi_us ?? cityData.aqi_us) : (cityData.center_aqi_in ?? cityData.aqi_in);
      if (typeof cityVal === 'number' && cityVal > 0) {
        return Math.round(cityVal);
      }
    }
    const monitored = stations.filter((s: any) => s.monitored !== false);
    const pool = monitored.length > 0 ? monitored : stations;
    const validStations = pool.filter((st: any) => {
      const v = aqiStandard === 'US_EPA' ? (st.aqi_us ?? st.aqi) : (st.aqi_in ?? st.aqi);
      return typeof v === 'number' && !isNaN(v);
    });
    if (validStations.length === 0) return 0;
    return Math.round(
      validStations.reduce((s: number, st: any) => {
        const val = aqiStandard === 'US_EPA' ? (st.aqi_us ?? st.aqi ?? 0) : (st.aqi_in ?? st.aqi ?? 0);
        return s + val;
      }, 0) / validStations.length
    );
  }, [cityData, stations, aqiStandard]);

  const avgPm25 = useMemo(() => {
    const valid = stations.filter((s: any) => s.monitored !== false && typeof s.pm25 === 'number' && !isNaN(s.pm25));
    if (valid.length === 0) return 0;
    return Math.round(valid.reduce((s, st) => s + (st.pm25 ?? 0), 0) / valid.length);
  }, [stations]);

  const avgPm10 = useMemo(() => {
    const valid = stations.filter((s: any) => s.monitored !== false && typeof s.pm10 === 'number' && !isNaN(s.pm10));
    if (valid.length === 0) return 0;
    return Math.round(valid.reduce((s, st) => s + (st.pm10 ?? 0), 0) / valid.length);
  }, [stations]);

  const avgPollutants = useMemo(() => {
    const valid = stations.filter((s: any) => s.monitored !== false);
    if (valid.length === 0) return { no2: 0, so2: 0, co: 0, o3: 0, pm25: 0, pm10: 0 };
    const getAvg = (field: string) => {
      const items = valid.filter((s: any) => typeof s[field] === 'number' && !isNaN(s[field]));
      if (items.length === 0) return 0;
      return items.reduce((acc, it: any) => acc + it[field], 0) / items.length;
    };
    return {
      pm25: Math.round(getAvg('pm25')),
      pm10: Math.round(getAvg('pm10')),
      no2: Math.round(getAvg('no2')),
      so2: Math.round(getAvg('so2')),
      co: +getAvg('co').toFixed(1),
      o3: Math.round(getAvg('o3')),
    };
  }, [stations]);

  // Weather: avg from stations that have weather data
  const weather = useMemo(() => {
    const withWeather = stations.filter((s: any) => s.temp !== undefined);
    if (withWeather.length === 0) return null;
    const n = withWeather.length;
    return {
      temp: +(withWeather.reduce((s: number, st: any) => s + (st.temp ?? 0), 0) / n).toFixed(1),
      humidity: Math.round(withWeather.reduce((s: number, st: any) => s + (st.humidity ?? 0), 0) / n),
      wind_speed: +(withWeather.reduce((s: number, st: any) => s + (st.wind_speed ?? 0), 0) / n).toFixed(1),
      pressure: Math.round(withWeather.reduce((s: number, st: any) => s + (st.pressure ?? 0), 0) / n),
      pblh: Math.round(withWeather.reduce((s: number, st: any) => s + (st.pblh ?? 520), 0) / n),
      inversion: 2.4,
      ventilation: Math.round((withWeather.reduce((s: number, st: any) => s + (st.pblh ?? 520), 0) / n) * (withWeather.reduce((s: number, st: any) => s + (st.wind_speed ?? 0), 0) / n)),
    };
  }, [stations]);

  // Prefer real live hourly API telemetry over model extrapolation
  const rawHistoricalData = useMemo(() => {
    if (realHistory.length > 0) {
      const copy = realHistory.map((item) => ({
        ...item,
        aqi: Math.round(item.aqi),
        pm25: typeof item.pm25 === 'number' ? Math.round(item.pm25 * 10) / 10 : Math.round(item.aqi * 0.45),
        pm10: typeof item.pm10 === 'number' ? Math.round(item.pm10 * 10) / 10 : Math.round(item.aqi * 0.85),
      }));
      if (copy.length > 0 && avgAqi > 0) {
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          aqi: avgAqi,
          pm25: avgPm25 > 0 ? avgPm25 : copy[copy.length - 1].pm25,
          pm10: avgPm10 > 0 ? avgPm10 : copy[copy.length - 1].pm10
        };
      }
      return copy;
    }
    return [];
  }, [realHistory, avgAqi, avgPm25, avgPm10]);

  const historicalData = useMemo(() => {
    const count = timeRange === '6h' ? 7 : timeRange === '12h' ? 13 : 24;
    return rawHistoricalData.slice(-count);
  }, [rawHistoricalData, timeRange]);

  const minPoint = useMemo(() => {
    if (historicalData.length === 0) return { val: 0, time: '--' };
    return historicalData.reduce((m, d) => {
      const v = Math.round(d[chartMetric] ?? d.aqi);
      return v < m.val ? { val: v, time: d.time } : m;
    }, { val: Math.round(historicalData[0][chartMetric] ?? historicalData[0].aqi), time: historicalData[0].time });
  }, [historicalData, chartMetric]);

  const maxPoint = useMemo(() => {
    if (historicalData.length === 0) return { val: 0, time: '--' };
    return historicalData.reduce((m, d) => {
      const v = Math.round(d[chartMetric] ?? d.aqi);
      return v > m.val ? { val: v, time: d.time } : m;
    }, { val: Math.round(historicalData[0][chartMetric] ?? historicalData[0].aqi), time: historicalData[0].time });
  }, [historicalData, chartMetric]);

  const forecastData = useMemo(() => {
    if (liveData?.forecast?.points && Array.isArray(liveData.forecast.points) && liveData.forecast.points.length >= 3) {
      return [
        { hour: 'Now', aqi: Math.round(avgAqi) },
        { hour: '+24h', aqi: Math.round(liveData.forecast.points[0]) },
        { hour: '+48h', aqi: Math.round(liveData.forecast.points[1]) },
        { hour: '+72h', aqi: Math.round(liveData.forecast.points[2]) }
      ];
    }
    return [
      { hour: 'Now', aqi: Math.round(avgAqi) }
    ];
  }, [liveData, avgAqi]);

  const forecastEnd = forecastData[forecastData.length - 1]?.aqi ?? avgAqi;
  const trendUp = forecastEnd > avgAqi;

  const aqiCat = getAqiCategory(avgAqi, aqiStandard);
  const healthInfo = getHealthInfo(avgAqi, aqiStandard);

  const scalePosition = useMemo(() => {
    if (avgAqi <= 50) return (avgAqi / 50) * 16.66;
    if (avgAqi <= 100) return 16.66 + ((avgAqi - 50) / 50) * 16.66;
    if (avgAqi <= 150) return 33.33 + ((avgAqi - 100) / 50) * 16.66;
    if (avgAqi <= 200) return 50.0 + ((avgAqi - 150) / 50) * 16.66;
    if (avgAqi <= 300) return 66.66 + ((avgAqi - 200) / 100) * 16.66;
    return Math.min(100, 83.33 + ((avgAqi - 300) / 200) * 16.66);
  }, [avgAqi]);

  const monitoredDistricts = useMemo(() => {
    return districts.filter((d: any) => {
      if (d.monitored === false) return false;
      const v = aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi) : (d.aqi_in ?? d.aqi);
      return typeof v === 'number' && !isNaN(v);
    });
  }, [districts, aqiStandard]);

  const unmonitoredWardsCount = useMemo(() => {
    return districts.filter((d: any) => d.monitored === false).length;
  }, [districts]);

  const sortedDistricts = useMemo(() => {
    return [...monitoredDistricts].sort((a, b) => {
      const aVal = aqiStandard === 'US_EPA' ? (a.aqi_us ?? a.aqi ?? 0) : (a.aqi_in ?? a.aqi ?? 0);
      const bVal = aqiStandard === 'US_EPA' ? (b.aqi_us ?? b.aqi ?? 0) : (b.aqi_in ?? b.aqi ?? 0);
      return aVal - bVal;
    });
  }, [monitoredDistricts, aqiStandard]);

  const best5 = sortedDistricts.slice(0, 5);
  const worst5 = [...sortedDistricts].reverse().slice(0, 5);

  if (liveLoading && stations.length === 0) {
    return (
      <div className="home-page">
        <div className="home-loading">
          <div className="home-loading-spinner" />
          <div style={{ fontWeight: 600 }}>Calibrating Atmospheric Sensors for {activeCity}...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      <div className="home-inner">

        {/* ═══ Top Floating Capsule: Branding + City + Standard Switch ═══ */}
        <div className="home-brand-row">
          <div className="home-brand-left">
            <span className="brand-text-logo">Aervia</span>

            {/* Curvy City Selector Dropdown */}
            <div className="home-city-select-wrap">
              <span style={{ fontSize: '0.85rem' }}>📍</span>
              <select
                className="home-city-select"
                value={activeCity}
                onChange={(e) => setActiveCity(e.target.value as CityId)}
                aria-label="Select City"
              >
                <optgroup label="Core Monitored Cities">
                  <option value="Hyderabad">Hyderabad</option>
                  <option value="Delhi">Delhi NCR</option>
                  <option value="Bengaluru">Bengaluru</option>
                </optgroup>
                <optgroup label="Tier 1 Cities">
                  <option value="Mumbai">Mumbai</option>
                  <option value="Chennai">Chennai</option>
                  <option value="Kolkata">Kolkata</option>
                  <option value="Pune">Pune</option>
                  <option value="Ahmedabad">Ahmedabad</option>
                  <option value="Jaipur">Jaipur</option>
                  <option value="Lucknow">Lucknow</option>
                  <option value="Chandigarh">Chandigarh</option>
                  <option value="Thiruvananthapuram">Thiruvananthapuram</option>
                </optgroup>
                <optgroup label="Tier 2 Cities">
                  <option value="Guwahati">Guwahati</option>
                  <option value="Kanpur">Kanpur</option>
                  <option value="Nagpur">Nagpur</option>
                  <option value="Indore">Indore</option>
                  <option value="Bhopal">Bhopal</option>
                  <option value="Patna">Patna</option>
                </optgroup>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Curvy Standard Toggle */}
            <div style={{
              display: 'flex',
              background: '#f1f5f9',
              borderRadius: 'var(--radius-pill)',
              border: '1px solid var(--border-primary)',
              padding: 3,
            }}>
              <button
                onClick={() => setAqiStandard('IN_NAQI')}
                style={{
                  padding: '5px 14px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  border: 'none',
                  borderRadius: 'var(--radius-pill)',
                  cursor: 'pointer',
                  background: aqiStandard === 'IN_NAQI' ? '#0f172a' : 'transparent',
                  color: aqiStandard === 'IN_NAQI' ? '#ffffff' : 'var(--text-muted)',
                  boxShadow: aqiStandard === 'IN_NAQI' ? '0 1px 3px rgba(15, 23, 42, 0.2)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                🇮🇳 India NAQI
              </button>
              <button
                onClick={() => setAqiStandard('US_EPA')}
                style={{
                  padding: '5px 14px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  border: 'none',
                  borderRadius: 'var(--radius-pill)',
                  cursor: 'pointer',
                  background: aqiStandard === 'US_EPA' ? '#0f172a' : 'transparent',
                  color: aqiStandard === 'US_EPA' ? '#ffffff' : 'var(--text-muted)',
                  boxShadow: aqiStandard === 'US_EPA' ? '0 1px 3px rgba(15, 23, 42, 0.2)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                🇺🇸 US EPA
              </button>
            </div>

            {/* Curvy Live Pulse Badge */}
            <div className="home-live-badge">
              <div className="dot" /> Telemetry Active
            </div>
          </div>
        </div>

        {/* ═══ Header Title & Atmosphere Subtitle ═══ */}
        <div style={{ padding: '0 4px' }}>
          <h1 className="home-title">{activeCity} Urban Air Quality Command</h1>
          <p className="home-subtitle">
            Calibrated real-time particulate surveillance & atmospheric monitoring for {activeCity} ({aqiStandard === 'IN_NAQI' ? 'CPCB India NAQI Standard' : 'US EPA 40 CFR Standard'})
          </p>
          <div className="home-timestamp" suppressHydrationWarning>
            <Activity size={14} />
            <span>Telemetry Refreshed: {now.toLocaleDateString('en-IN')} {now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })} IST</span>
          </div>
        </div>

        {/* ═══ Section 1: Hero AQI Spherical Command Hub ═══ */}
        <div className="home-hero">
          {/* Left Column: Spherical Breathing Gauge Orb */}
          <div className="home-hero-orb-column">
            <div
              className="home-spherical-orb"
              style={{
                borderColor: aqiCat.color,
                boxShadow: `0 4px 16px -2px rgba(0, 0, 0, 0.08)`
              }}
            >
              <div className="home-orb-content">
                <div className="home-aqi-pill-indicator">
                  <span className="dot" style={{ width: 6, height: 6, borderRadius: '50%', background: aqiCat.color, display: 'inline-block' }} />
                  <span style={{ color: aqiCat.color }}>Live AQI</span>
                </div>
                <div className="home-aqi-value" style={{ color: aqiCat.color }}>{avgAqi}</div>
                <div className="home-aqi-unit-pill">
                  {aqiStandard === 'IN_NAQI' ? 'CPCB NAQI' : 'US EPA 40 CFR'}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Curvy Stats & Environmental Directives */}
          <div className="home-hero-right">
            <div className="home-hero-header-row">
              <div
                className="home-aqi-status-pill"
                style={{
                  background: aqiCat.bg,
                  color: aqiCat.color,
                  border: `1.5px solid ${aqiCat.color}55`,
                }}
              >
                <span className="home-status-dot" style={{ background: aqiCat.color }} />
                <span className="home-status-category">{aqiCat.label}</span>
              </div>
              <div className="home-status-context-pill">
                <Leaf size={14} style={{ color: 'var(--accent-emerald)' }} />
                <span>Clean Air Target: ≤50 AQI</span>
              </div>
            </div>

            {/* PM2.5 and PM10 Curvy Glass Pods */}
            <div className="home-pm-values">
              <div className="home-pm-curvy-item">
                <div className="home-pm-top">
                  <div className="home-pm-label">PM2.5 Concentration</div>
                  <span className="home-pm-limit-badge">Safe: ≤60 µg/m³</span>
                </div>
                <div className="home-pm-reading">
                  <span className="home-pm-val">{avgPm25}</span>
                  <span className="home-pm-unit">µg/m³</span>
                </div>
                <div className="home-pm-track">
                  <div
                    className="home-pm-fill"
                    style={{
                      width: `${Math.min(100, (avgPm25 / 60) * 100)}%`,
                      background: pollutantColor(avgPm25, 60),
                    }}
                  />
                </div>
              </div>

              <div className="home-pm-curvy-item">
                <div className="home-pm-top">
                  <div className="home-pm-label">PM10 Concentration</div>
                  <span className="home-pm-limit-badge">Safe: ≤100 µg/m³</span>
                </div>
                <div className="home-pm-reading">
                  <span className="home-pm-val">{avgPm10}</span>
                  <span className="home-pm-unit">µg/m³</span>
                </div>
                <div className="home-pm-track">
                  <div
                    className="home-pm-fill"
                    style={{
                      width: `${Math.min(100, (avgPm10 / 100) * 100)}%`,
                      background: pollutantColor(avgPm10, 100),
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* AQI Curvy Spectrum Track */}
          <div className="home-scale">
            <div className="home-scale-bar-wrapper">
              <div className="home-scale-bar">
                <div style={{ background: '#22c55e' }} />
                <div style={{ background: '#84cc16' }} />
                <div style={{ background: '#eab308' }} />
                <div style={{ background: '#f59e0b' }} />
                <div style={{ background: '#f97316' }} />
                <div style={{ background: '#ef4444' }} />
                <div style={{ background: '#dc2626' }} />
              </div>
              <div className="home-scale-marker" style={{ left: `${scalePosition}%` }} />
            </div>
            <div className="home-scale-labels">
              {aqiStandard === 'IN_NAQI' ? (
                <>
                  <span>Good (0-50)</span>
                  <span>Satisfactory (51-100)</span>
                  <span>Moderate (101-200)</span>
                  <span>Poor (201-300)</span>
                  <span>Very Poor (301-400)</span>
                  <span>Severe (401-500+)</span>
                </>
              ) : (
                <>
                  <span>Good (0-50)</span>
                  <span>Moderate (51-100)</span>
                  <span>USG (101-150)</span>
                  <span>Unhealthy (151-200)</span>
                  <span>Very Unhealthy (201-300)</span>
                  <span>Hazardous (301+)</span>
                </>
              )}
            </div>
            <div className="home-scale-numbers">
              <span>0</span><span>50</span><span>100</span><span>150</span><span>200</span><span>300</span><span>500+</span>
            </div>
          </div>
        </div>

        {/* ═══ Section 2: Curvy Health Impact Advisory Banner ═══ */}
        <div
          className="home-health-banner"
          style={{
            background: healthInfo.bg,
            borderColor: healthInfo.border,
            color: healthInfo.color
          }}
        >
          <div className="home-health-icon">{healthInfo.icon}</div>
          <div style={{ flex: 1 }}>
            <div className="home-health-title">{healthInfo.title}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: 1.5 }}>
              {healthInfo.message}
            </div>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 14px',
            borderRadius: 'var(--radius-pill)',
            background: 'var(--bg-surface)',
            border: `1px solid ${healthInfo.border}`,
            fontSize: '0.75rem',
            fontWeight: 700,
            color: healthInfo.color,
            flexShrink: 0
          }}>
            <ShieldCheck size={16} />
            <span>CPCB Health Protocol</span>
          </div>
        </div>

        {/* ═══ Section 3: Critical Pollutant Spectrum Pods ═══ */}
        <div className="home-section-header-wrap">
          <div className="home-section-title">
            <span style={{ fontSize: '1.1rem' }}>🧪</span>
            Critical Pollutant Spectrum & Chemical Sensors
          </div>
          <span className="home-section-badge">India NAAQS 24-Hour Thresholds</span>
        </div>

        <div className="home-grid-6">
          {Object.entries(POLLUTANT_LIMITS).map(([key, info]) => {
            const value = (avgPollutants as any)[key] ?? 0;
            const pct = Math.min(100, (value / info.limit) * 100);
            const clr = pollutantColor(value, info.limit);
            const statusLabel = pct <= 50 ? 'Safe' : pct <= 100 ? 'Moderate' : pct <= 150 ? 'Elevated' : 'Critical';
            return (
              <div className="home-pollutant-card" key={key}>
                <div
                  className="home-pollutant-bubble"
                  style={{
                    background: `${clr}15`,
                    color: clr,
                    borderColor: `${clr}45`,
                  }}
                >
                  {info.label}
                </div>
                <div className="home-pollutant-value" style={{ color: clr }}>{value}</div>
                <span className="home-pollutant-unit">{info.unit}</span>
                <div
                  className="home-pollutant-pill-status"
                  style={{
                    background: `${clr}12`,
                    color: clr,
                    borderColor: `${clr}35`,
                  }}
                >
                  {statusLabel}
                </div>
                <div className="home-pollutant-bar">
                  <div
                    className="home-pollutant-bar-fill"
                    style={{ width: `${pct}%`, background: clr }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* ═══ Section 4: Weather Conditions & 24h Forecast Sparkline ═══ */}
        <div className="home-grid-2">
          {/* Weather Card */}
          <div className="home-card">
            <div className="home-card-header">
              <div className="home-card-title">
                <Wind size={16} style={{ color: 'var(--accent-cyan)' }} />
                Atmospheric Weather Vector
              </div>
              <span className="home-section-badge">Boundary Layer Dynamics</span>
            </div>

            {weather ? (
              <div className="home-weather-grid">
                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <Thermometer size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Ambient Temp</div>
                    <div className="home-weather-val">{weather.temp}°C</div>
                  </div>
                </div>

                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <Droplets size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Relative Humidity</div>
                    <div className="home-weather-val">{weather.humidity}%</div>
                  </div>
                </div>

                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <Wind size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Wind Velocity</div>
                    <div className="home-weather-val">{weather.wind_speed} m/s</div>
                  </div>
                </div>

                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <Gauge size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Barometric Press</div>
                    <div className="home-weather-val">{weather.pressure} hPa</div>
                  </div>
                </div>

                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <Layers size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Boundary Layer (PBLH)</div>
                    <div className="home-weather-val">{weather.pblh} m</div>
                  </div>
                </div>

                <div className="home-weather-item">
                  <div className="home-weather-circle-icon">
                    <TrendingUp size={20} />
                  </div>
                  <div>
                    <div className="home-weather-label">Inversion Proxy</div>
                    <div className="home-weather-val">+{weather.inversion} °C/km</div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '20px 0' }}>Weather data unavailable</div>
            )}
          </div>

          {/* 24h Forecast Card */}
          <div className="home-card">
            <div className="home-card-header">
              <div className="home-card-title">
                <Sparkles size={16} style={{ color: 'var(--accent-cyan)' }} />
                24-Hour AI Predictive Trajectory
              </div>
              <span className="home-section-badge">XGBoost Horizon</span>
            </div>

            <div style={{ width: '100%', height: 110 }}>
              <ResponsiveContainer>
                <AreaChart data={forecastData}>
                  <defs>
                    <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={aqiCat.color} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={aqiCat.color} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="aqi"
                    stroke={aqiCat.color}
                    fill="url(#forecastGrad)"
                    strokeWidth={3}
                    dot={{ r: 4, fill: aqiCat.color, stroke: '#ffffff', strokeWidth: 2 }}
                  />
                  <XAxis dataKey="hour" hide />
                  <YAxis hide domain={['dataMin - 20', 'dataMax + 20']} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.75rem',
                      color: 'var(--text-primary)',
                      boxShadow: 'var(--shadow-md)',
                    }}
                    itemStyle={{ color: 'var(--accent-blue)', fontWeight: 700 }}
                    labelStyle={{ color: 'var(--text-secondary)' }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="home-forecast-trend">
              <span className="home-trend-arrow" style={{ color: trendUp ? '#ef4444' : '#22c55e' }}>
                {trendUp ? <ArrowUpRight size={20} /> : <ArrowDownRight size={20} />}
              </span>
              <span className="home-trend-text" style={{ color: trendUp ? '#ef4444' : '#22c55e' }}>
                {trendUp ? 'Worsening pollution trend' : 'Improving air quality trend'} — predicted {forecastEnd} AQI at 24h mark
              </span>
            </div>
          </div>
        </div>

        {/* ═══ Section 5: Historical Air Quality Telemetry ═══ */}
        <div className="home-historical">
          <div className="home-historical-header">
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700, marginBottom: 2 }}>
                Time-Series Telemetry
              </div>
              <div className="home-historical-title">Historical Atmospheric Dispersion</div>
              <div className="home-historical-subtitle">Municipal Sensor Station Log: {activeCity}</div>
            </div>

            <div className="home-historical-controls">
              <button
                className={`home-chart-toggle ${chartType === 'line' ? 'active' : ''}`}
                onClick={() => setChartType('line')}
                title="Line Chart View"
              >
                Line View
              </button>
              <button
                className={`home-chart-toggle ${chartType === 'bar' ? 'active' : ''}`}
                onClick={() => setChartType('bar')}
                title="Bar Chart View"
              >
                Bar View
              </button>
              <select
                className="home-chart-select"
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as any)}
                aria-label="Select Historical Time Range"
              >
                <option value="6h">Past 6 Hours</option>
                <option value="12h">Past 12 Hours</option>
                <option value="24h">Past 24 Hours</option>
              </select>
              <select
                className="home-chart-select"
                value={chartMetric}
                onChange={(e) => setChartMetric(e.target.value as any)}
                aria-label="Select Air Quality Metric"
              >
                <option value="aqi">Air Quality Index (AQI)</option>
                <option value="pm25">PM2.5 Particulate (µg/m³)</option>
                <option value="pm10">PM10 Particulate (µg/m³)</option>
              </select>
            </div>
          </div>

          {/* Min/Max Floating Badges */}
          <div className="home-minmax-row">
            <div className="home-minmax-badge" style={{ background: 'rgba(34,197,94,0.08)', borderColor: 'rgba(34,197,94,0.3)', color: '#22c55e' }}>
              <span className="home-minmax-value" style={{ background: 'rgba(34,197,94,0.18)', color: '#22c55e' }}>{minPoint.val}</span>
              <div className="home-minmax-info">
                <span className="home-minmax-label" style={{ color: '#22c55e' }}>
                  &darr; Min {chartMetric === 'aqi' ? 'AQI' : chartMetric.toUpperCase()}
                </span>
                <span className="home-minmax-time">at {minPoint.time}</span>
              </div>
            </div>
            <div className="home-minmax-badge" style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.3)', color: '#ef4444' }}>
              <span className="home-minmax-value" style={{ background: 'rgba(239,68,68,0.18)', color: '#ef4444' }}>{maxPoint.val}</span>
              <div className="home-minmax-info">
                <span className="home-minmax-label" style={{ color: '#ef4444' }}>
                  &uarr; Max {chartMetric === 'aqi' ? 'AQI' : chartMetric.toUpperCase()}
                </span>
                <span className="home-minmax-time">at {maxPoint.time}</span>
              </div>
            </div>
          </div>

          {/* Chart Wrapper */}
          <div className="home-chart-wrapper">
            <ResponsiveContainer>
              {chartType === 'bar' ? (
                <BarChart data={historicalData}>
                  <XAxis dataKey="time" tick={{ fill: '#8b949e', fontSize: 11 }} interval={timeRange === '6h' ? 0 : 2} />
                  <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 'dataMax + 20']} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.78rem',
                      color: 'var(--text-primary)',
                      boxShadow: 'var(--shadow-md)',
                    }}
                    itemStyle={{ color: 'var(--accent-blue)', fontWeight: 700 }}
                    labelStyle={{ color: 'var(--text-secondary)' }}
                    formatter={(value: any) => [
                      `${value} ${chartMetric === 'aqi' ? 'AQI' : 'µg/m³'}`,
                      chartMetric === 'aqi' ? 'Air Quality Index' : chartMetric.toUpperCase()
                    ]}
                  />
                  <Bar dataKey={chartMetric} radius={[8, 8, 0, 0]}>
                    {historicalData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={
                          chartMetric === 'aqi'
                            ? aqiBarColor(entry.aqi)
                            : chartMetric === 'pm25'
                            ? pollutantColor(entry.pm25 ?? entry.aqi * 0.45, 60)
                            : pollutantColor(entry.pm10 ?? entry.aqi * 0.85, 100)
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              ) : (
                <LineChart data={historicalData}>
                  <XAxis dataKey="time" tick={{ fill: '#8b949e', fontSize: 11 }} interval={timeRange === '6h' ? 0 : 2} />
                  <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} domain={[0, 'dataMax + 20']} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-primary)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '0.78rem',
                      color: 'var(--text-primary)',
                      boxShadow: 'var(--shadow-md)',
                    }}
                    itemStyle={{ color: 'var(--accent-blue)', fontWeight: 700 }}
                    labelStyle={{ color: 'var(--text-secondary)' }}
                    formatter={(value: any) => [
                      `${value} ${chartMetric === 'aqi' ? 'AQI' : 'µg/m³'}`,
                      chartMetric === 'aqi' ? 'Air Quality Index' : chartMetric.toUpperCase()
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey={chartMetric}
                    stroke={chartMetric === 'aqi' ? aqiCat.color : '#38bdf8'}
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#ffffff', stroke: chartMetric === 'aqi' ? aqiCat.color : '#38bdf8', strokeWidth: 2 }}
                  />
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* ═══ Section 6: Municipal Ward Leaderboards ═══ */}
        {sortedDistricts.length > 0 && (
          <div className="home-leaderboard">
            {/* Cleanest Wards */}
            <div className="home-leaderboard-section">
              <div className="home-leaderboard-title">
                <span style={{ fontSize: '1rem' }}>🟢</span>
                Cleanest Municipal Wards ({aqiStandard === 'IN_NAQI' ? 'India NAQI' : 'US EPA'})
              </div>
              {best5.map((d, i) => {
                const wardAqi = Math.round(aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi ?? 0) : (d.aqi_in ?? d.aqi ?? 0));
                const cat = getAqiCategory(wardAqi, aqiStandard);
                return (
                  <div className="home-leaderboard-item" key={d.id}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span className="home-leaderboard-rank">{i + 1}</span>
                      <span className="home-leaderboard-name">{d.name}</span>
                    </div>
                    <span className="home-leaderboard-aqi" style={{ color: cat.color }}>
                      {wardAqi} AQI
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Most Polluted Wards */}
            <div className="home-leaderboard-section">
              <div className="home-leaderboard-title">
                <span style={{ fontSize: '1rem' }}>🔴</span>
                Highest Risk Municipal Wards ({aqiStandard === 'IN_NAQI' ? 'India NAQI' : 'US EPA'})
              </div>
              {worst5.map((d, i) => {
                const wardAqi = Math.round(aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi ?? 0) : (d.aqi_in ?? d.aqi ?? 0));
                const cat = getAqiCategory(wardAqi, aqiStandard);
                return (
                  <div className="home-leaderboard-item" key={d.id}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span className="home-leaderboard-rank">{i + 1}</span>
                      <span className="home-leaderboard-name">{d.name}</span>
                    </div>
                    <span className="home-leaderboard-aqi" style={{ color: cat.color }}>
                      {wardAqi} AQI
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {unmonitoredWardsCount > 0 && (
          <div style={{ textAlign: 'center', marginTop: 8, marginBottom: 20, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            ℹ️ {unmonitoredWardsCount} municipal wards currently have no active CAAQMS center and are excluded from rankings (shaded grey on the live map referencing nearest centers).
          </div>
        )}

      </div>
    </div>
  );
}

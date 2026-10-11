'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface AtmosphericPoint {
  time: string;
  forecast_hour: number;
  aqi_in_estimate: number | null;
  primary_pollutant: string | null;
  pm25_ug_m3: number | null;
  pm10_ug_m3: number | null;
  no2_ug_m3: number | null;
  so2_ug_m3: number | null;
  co_ug_m3: number | null;
  o3_ug_m3: number | null;
  temperature_c: number | null;
  humidity_pct: number | null;
  pressure_hpa: number | null;
  wind_speed_ms: number | null;
  wind_direction_deg: number | null;
  pblh_m: number | null;
  ventilation_index_m2_s: number | null;
  inversion_strength_c_per_km: number | null;
  inversion_detected: boolean;
  aerosol_optical_depth: number | null;
  dust_ug_m3: number | null;
}

interface AtmosphericForecast {
  city: string;
  generated_at: string;
  horizon_hours: number;
  forecast_points: number;
  points: AtmosphericPoint[];
  sources: {
    air_quality: string;
    air_quality_grid_km: number;
    air_quality_native_interval_hours: number;
    weather: string;
    spatial_scope: string;
    weather_and_air_quality_coupled: boolean;
    aqi_method: string;
    nox_available: boolean;
    inversion_method: string;
    inversion_profile_levels_hpa: number[];
  };
}

type SeriesKey =
  | 'aqi_in_estimate'
  | 'pm25_ug_m3'
  | 'pm10_ug_m3'
  | 'o3_ug_m3'
  | 'no2_ug_m3'
  | 'so2_ug_m3'
  | 'temperature_c'
  | 'humidity_pct'
  | 'pressure_hpa'
  | 'wind_speed_ms'
  | 'wind_direction_deg'
  | 'pblh_m'
  | 'ventilation_index_m2_s'
  | 'inversion_strength_c_per_km'
  | 'aerosol_optical_depth'
  | 'dust_ug_m3'
  | 'co_ug_m3';

const SERIES: { key: SeriesKey; label: string; unit: string }[] = [
  { key: 'aqi_in_estimate', label: 'Estimated India AQI', unit: 'AQI' },
  { key: 'pm25_ug_m3', label: 'PM2.5', unit: 'µg/m³' },
  { key: 'pm10_ug_m3', label: 'PM10', unit: 'µg/m³' },
  { key: 'o3_ug_m3', label: 'Ozone (O₃)', unit: 'µg/m³' },
  { key: 'no2_ug_m3', label: 'Nitrogen dioxide (NO₂)', unit: 'µg/m³' },
  { key: 'so2_ug_m3', label: 'Sulphur dioxide (SO₂)', unit: 'µg/m³' },
  { key: 'temperature_c', label: 'Temperature', unit: '°C' },
  { key: 'humidity_pct', label: 'Relative humidity', unit: '%' },
  { key: 'pressure_hpa', label: 'Surface pressure', unit: 'hPa' },
  { key: 'wind_speed_ms', label: 'Wind speed', unit: 'm/s' },
  { key: 'wind_direction_deg', label: 'Wind direction', unit: '°' },
  { key: 'pblh_m', label: 'Boundary layer height', unit: 'm' },
  { key: 'ventilation_index_m2_s', label: 'Ventilation index', unit: 'm²/s' },
  { key: 'inversion_strength_c_per_km', label: 'Low-level inversion proxy', unit: '°C/km' },
  { key: 'aerosol_optical_depth', label: 'Aerosol optical depth', unit: 'AOD' },
  { key: 'dust_ug_m3', label: 'Dust', unit: 'µg/m³' },
  { key: 'co_ug_m3', label: 'Carbon monoxide (CO)', unit: 'µg/m³' },
];

import { apiUrl } from '@/utils/api';

const API_BASE = {
  toString() {
    return apiUrl('');
  }
};

function formatValue(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined || !Number.isFinite(value)
    ? '—'
    : value.toFixed(digits);
}

function formatHour(value: string | number): string {
  return new Date(String(value)).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    hour: '2-digit',
  });
}

export default function AtmosphericForecastPanel({
  city = 'Delhi',
  coordinates,
}: {
  city?: string;
  coordinates?: { lat: number; lon: number } | null;
}) {
  const [forecast, setForecast] = useState<AtmosphericForecast | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<SeriesKey>('aqi_in_estimate');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    if (city === 'My Location' && !coordinates) {
      setLoading(true);
      return () => controller.abort();
    }
    const params = new URLSearchParams({ city });
    if (city === 'My Location' && coordinates) {
      params.set('lat', String(coordinates.lat));
      params.set('lon', String(coordinates.lon));
    }

    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/api/atmospheric-forecast?${params.toString()}`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Forecast feed is unavailable.');
        return payload as AtmosphericForecast;
      })
      .then((payload) => setForecast(payload))
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setError(fetchError.message || 'Could not load the atmospheric forecast.');
          setForecast(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [city, coordinates?.lat, coordinates?.lon]);

  const selected = SERIES.find((item) => item.key === selectedSeries) || SERIES[0];
  const chartData = useMemo(
    () => forecast?.points.map((point) => ({ ...point, value: point[selectedSeries] })) || [],
    [forecast, selectedSeries],
  );
  const horizonRows = [24, 48, 72]
    .map((hour) => forecast?.points.find((point) => point.forecast_hour === hour))
    .filter((point): point is AtmosphericPoint => Boolean(point));
  const peakInversion24h = forecast?.points
    .slice(0, 24)
    .map((point) => point.inversion_strength_c_per_km)
    .filter((value): value is number => value !== null && value !== undefined)
    .reduce((peak, value) => Math.max(peak, value), 0);
  const aqi24 = forecast?.points.find((point) => point.forecast_hour === 24)?.aqi_in_estimate;
  const point48 = forecast?.points.find((point) => point.forecast_hour === 48);
  const point72 = forecast?.points.find((point) => point.forecast_hour === 72);

  return (
    <section className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div className="panel-title">72-Hour Atmospheric Forecast · {city}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 4 }}>
            Hourly pollutant and weather outlook from external forecast models
          </div>
          {forecast && (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem', marginTop: 3 }}>
              {forecast.horizon_hours}h outlook · {forecast.forecast_points} hourly points · Updated {new Date(forecast.generated_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST
            </div>
          )}
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Show
          <select
            value={selectedSeries}
            onChange={(event) => setSelectedSeries(event.target.value as SeriesKey)}
            style={{ padding: '6px 9px', borderRadius: 6, background: 'var(--bg-surface)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)' }}
          >
            {SERIES.map((series) => <option key={series.key} value={series.key}>{series.label}</option>)}
          </select>
        </label>
      </div>

      {loading && <div style={{ padding: 26, textAlign: 'center', color: 'var(--text-muted)' }}>Loading forecast feed…</div>}
      {error && !loading && (
        <div role="alert" style={{ padding: 14, borderRadius: 8, color: 'var(--accent-red)', background: 'rgba(239,68,68,0.08)' }}>
          {error}
        </div>
      )}

      {forecast && !loading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))', gap: 10 }}>
            {[
              { label: 'Estimated India AQI · +24h', value: aqi24 == null ? '—' : formatValue(aqi24, 0), unit: 'CAMS-derived estimate' },
              { label: 'PM2.5 · +48h', value: formatValue(point48?.pm25_ug_m3), unit: 'µg/m³ · CAMS Global' },
              { label: 'PM2.5 · +72h', value: formatValue(point72?.pm25_ug_m3), unit: 'µg/m³ · CAMS Global' },
              { label: 'Peak inversion proxy · 24h', value: peakInversion24h == null ? '—' : formatValue(peakInversion24h), unit: '°C/km · weather profile' },
              { label: 'Ventilation index · +24h', value: formatValue(forecast.points.find((point) => point.forecast_hour === 24)?.ventilation_index_m2_s, 0), unit: 'm²/s · PBLH × wind' },
            ].map((metric) => (
              <div key={metric.label} style={{ padding: '12px 14px', borderRadius: 9, border: '1px solid var(--border-primary)', background: 'var(--bg-elevated)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.65rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{metric.label}</div>
                <div style={{ color: 'var(--text-primary)', fontSize: '1.15rem', fontWeight: 700, marginTop: 5, fontVariantNumeric: 'tabular-nums' }}>{metric.value}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.64rem', marginTop: 2 }}>{metric.unit}</div>
              </div>
            ))}
          </div>

          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-primary)" vertical={false} />
                <XAxis
                  dataKey="time"
                  tickFormatter={formatHour}
                  interval={11}
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  axisLine={false}
                  tickLine={false}
                  width={48}
                  label={{ value: selected.unit, angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 10 }}
                />
                <Tooltip
                  labelFormatter={(label) => new Date(String(label)).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                  formatter={(value: unknown) => [formatValue(typeof value === 'number' ? value : null), `${selected.label} (${selected.unit})`]}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-primary)', borderRadius: 8, fontSize: 12 }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name={selected.label}
                  stroke="#38bdf8"
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: 900, borderCollapse: 'collapse', fontSize: '0.78rem' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textAlign: 'right' }}>
                  <th style={{ textAlign: 'left', padding: '9px 8px' }}>Horizon</th>
                  <th style={{ padding: '9px 8px' }}>India AQI*</th>
                  <th style={{ padding: '9px 8px' }}>PM2.5</th>
                  <th style={{ padding: '9px 8px' }}>PM10</th>
                  <th style={{ padding: '9px 8px' }}>O₃</th>
                  <th style={{ padding: '9px 8px' }}>NO₂</th>
                  <th style={{ padding: '9px 8px' }}>SO₂</th>
                  <th style={{ padding: '9px 8px' }}>CO</th>
                  <th style={{ padding: '9px 8px' }}>PBLH</th>
                  <th style={{ padding: '9px 8px' }}>Inversion proxy</th>
                  <th style={{ padding: '9px 8px' }}>Wind</th>
                </tr>
              </thead>
              <tbody>
                {horizonRows.map((point) => (
                  <tr key={point.forecast_hour} style={{ borderTop: '1px solid var(--border-primary)', textAlign: 'right' }}>
                    <td style={{ textAlign: 'left', padding: '9px 8px', fontWeight: 600 }}>+{point.forecast_hour}h</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.aqi_in_estimate, 0)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.pm25_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.pm10_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.o3_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.no2_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.so2_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.co_ug_m3)}</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.pblh_m, 0)} m</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.inversion_strength_c_per_km)} °C/km</td>
                    <td style={{ padding: '9px 8px' }}>{formatValue(point.wind_speed_ms)} m/s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ color: 'var(--text-muted)', fontSize: '0.69rem', lineHeight: 1.5, borderTop: '1px solid var(--border-primary)', paddingTop: 10 }}>
            Air quality: <a href="https://open-meteo.com/en/docs/air-quality-api" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-cyan)' }}>CAMS Global via Open-Meteo</a> (~45 km native grid, 3-hour model steps). Weather: <a href="https://open-meteo.com/en/docs" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-cyan)' }}>separate Open-Meteo feed</a>; these feeds are not coupled. This is a city-centre grid cell, not a district-resolution forecast. AQI is an estimate using available pollutants and CPCB averaging windows. NOx is unavailable. The inversion value is a low-level proxy derived from modeled pressure-level temperatures and should not be interpreted as a sounding observation. PBLH and ventilation index are dispersion indicators.
          </div>
        </>
      )}
    </section>
  );
}

'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Map, { Layer, Marker, NavigationControl, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Flame, MapPin, Wind } from 'lucide-react';

interface FireDetection {
  latitude: number;
  longitude: number;
  frp_mw: number;
  confidence: string;
  acquired_at: string;
  satellite: string;
}

interface WindTrack extends FireDetection {
  trajectory: { forecast_hour: number; latitude: number; longitude: number }[];
  closest_approach_km: number;
  closest_approach_hour: number;
  within_50km_of_delhi: boolean;
}

interface FireTransport {
  available: boolean;
  reason?: string;
  queried_at?: string;
  region?: string;
  fire_source?: string;
  fire_count?: number;
  trajectory_source_count?: number;
  fire_detections: FireDetection[];
  wind_tracks: WindTrack[];
  transport_method?: string;
  assumptions?: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const DELHI = { latitude: 28.6139, longitude: 77.2090 };

function localTime(value: string): string {
  return new Date(value).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function StubbleTransportPanel() {
  const [result, setResult] = useState<FireTransport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/stubble-fire-transport`, { signal: controller.signal })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Fire transport data is unavailable.');
        return payload as FireTransport;
      })
      .then(setResult)
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') setError(fetchError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const tracks = result?.wind_tracks ?? [];
  const lineData = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: tracks
      .filter((track) => track.trajectory.length > 1)
      .map((track, index) => ({
        type: 'Feature' as const,
        properties: { id: index, frp: track.frp_mw },
        geometry: {
          type: 'LineString' as const,
          coordinates: track.trajectory.map((point) => [point.longitude, point.latitude]),
        },
      })),
  }), [tracks]);

  return (
    <section className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="panel-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Flame size={16} color="#fb923c" /> Northwest India fire transport watch
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 4 }}>
            Recent NASA VIIRS thermal detections with 72-hour, wind-only trajectories toward Delhi
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="page-city-badge" style={{ color: result?.available ? '#fb923c' : 'var(--text-muted)' }}>
            {loading ? 'CONNECTING' : result?.available ? 'SATELLITE FEED' : 'FEED NOT CONFIGURED'}
          </span>
          {result?.available && <span className="page-city-badge">{result.fire_count} detections · last 3 days</span>}
        </div>
      </div>

      {loading && <div style={{ height: 220, display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}>Loading satellite fire detections and source-area winds…</div>}
      {error && !loading && <div role="alert" style={{ padding: 14, color: 'var(--accent-red)' }}>{error}</div>}
      {!loading && result && !result.available && (
        <div style={{ padding: '20px 18px', borderRadius: 10, background: 'var(--bg-elevated)', border: '1px solid var(--border-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, marginBottom: 6 }}>
            <MapPin size={16} color="var(--text-muted)" /> Real fire detections are not configured
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', lineHeight: 1.55 }}>
            {result.reason} Add <code>NASA_FIRMS_MAP_KEY</code> to the root <code>.env</code> and restart the backend. This panel intentionally does not invent hotspots.
          </div>
        </div>
      )}

      {!loading && result?.available && tracks.length === 0 && (
        <div style={{ padding: 18, borderRadius: 10, background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
          {result.fire_count
            ? `${result.fire_count} detections were returned for the last three days, but there were no fresh, non-low-confidence detections from the last 24 hours to project forward.`
            : 'NASA FIRMS returned no thermal detections in the focus region for the last three days.'} This does not prove no burning occurred; satellites can miss events between overpasses or under cloud cover.
        </div>
      )}

      {!loading && result?.available && tracks.length > 0 && (
        <>
          <div style={{ width: '100%', height: 340, overflow: 'hidden', borderRadius: 10, border: '1px solid var(--border-primary)' }}>
            <Map
              initialViewState={{ longitude: 76.1, latitude: 30.3, zoom: 5.7, pitch: 0 }}
              mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
              style={{ width: '100%', height: '100%' }}
              attributionControl={{}}
            >
              <NavigationControl position="top-right" showCompass={false} />
              <Source id="fire-transport-lines" type="geojson" data={lineData as any}>
                <Layer
                  id="fire-transport-lines-layer"
                  type="line"
                  layout={{ 'line-cap': 'round', 'line-join': 'round' }}
                  paint={{ 'line-color': '#fb923c', 'line-width': 2.5, 'line-opacity': 0.8, 'line-dasharray': [1.5, 1.5] }}
                />
              </Source>
              {tracks.map((track, index) => (
                <Marker key={`${track.latitude}-${track.longitude}-${index}`} latitude={track.latitude} longitude={track.longitude} anchor="center">
                  <div title={`${track.confidence} confidence · ${track.frp_mw.toFixed(1)} MW`} style={{ width: 11, height: 11, borderRadius: '50%', background: '#fb923c', border: '2px solid #fff7ed', boxShadow: '0 0 12px rgba(251,146,60,0.85)' }} />
                </Marker>
              ))}
              <Marker latitude={DELHI.latitude} longitude={DELHI.longitude} anchor="bottom">
                <div style={{ padding: '4px 7px', borderRadius: 5, color: 'white', background: '#2563eb', fontSize: 10, fontWeight: 800, letterSpacing: 0.5 }}>DELHI</div>
              </Marker>
            </Map>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', color: 'var(--text-muted)', fontSize: '0.72rem' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: '#fb923c' }} />VIIRS thermal detection</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><span style={{ width: 18, borderTop: '2px dashed #fb923c' }} />Wind-only path (up to 72h)</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}><Wind size={13} />Nearest paths within 50 km of Delhi: {tracks.filter((track) => track.within_50km_of_delhi).length}</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', minWidth: 650, borderCollapse: 'collapse', fontSize: '0.76rem' }}>
              <thead><tr style={{ color: 'var(--text-muted)', textAlign: 'right' }}>
                <th style={{ textAlign: 'left', padding: '8px' }}>Detection (IST)</th>
                <th style={{ padding: '8px' }}>Satellite</th>
                <th style={{ padding: '8px' }}>Confidence</th>
                <th style={{ padding: '8px' }}>FRP</th>
                <th style={{ padding: '8px' }}>Closest Delhi approach</th>
              </tr></thead>
              <tbody>{tracks.slice(0, 6).map((track, index) => (
                <tr key={`${track.acquired_at}-${index}`} style={{ borderTop: '1px solid var(--border-primary)', textAlign: 'right' }}>
                  <td style={{ textAlign: 'left', padding: '8px' }}>{localTime(track.acquired_at)}</td>
                  <td style={{ padding: '8px' }}>{track.satellite}</td>
                  <td style={{ padding: '8px', textTransform: 'capitalize' }}>{track.confidence}</td>
                  <td style={{ padding: '8px' }}>{track.frp_mw.toFixed(1)} MW</td>
                  <td style={{ padding: '8px' }}>{track.closest_approach_km.toFixed(1)} km · +{track.closest_approach_hour}h</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </>
      )}

      <div style={{ borderTop: '1px solid var(--border-primary)', paddingTop: 10, color: 'var(--text-muted)', fontSize: '0.69rem', lineHeight: 1.5 }}>
        Source: <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-cyan)' }}>NASA FIRMS VIIRS</a>; winds: Open-Meteo. Only fresh, non-low-confidence detections are projected. A thermal hotspot is not proof of stubble burning. Dashed tracks are conditional near-surface wind advection from detected points; they assume the source persists and do not estimate smoke concentration, chemistry, or AQI impact. {result?.queried_at && `Updated ${localTime(result.queried_at)} IST.`}
      </div>
    </section>
  );
}

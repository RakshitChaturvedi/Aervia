import React, { useState, useEffect } from 'react';
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell, ReferenceLine,
  PieChart, Pie, Legend,
  LineChart, Line
} from 'recharts';
import ReportModal from './ReportModal';
import { useCityContext } from '@/context/CityContext';
import { getAqiCategory } from '@/utils/aqi';
import { apiUrl } from '@/utils/api';

export default function DeepDivePanel({ district, city, onReset, recommendedDeployments = [] }: { district: any, city: string, onReset: () => void, recommendedDeployments?: any[] }) {
  const { aqiStandard } = useCityContext();
  const [attribution, setAttribution] = useState<any>(null);
  const [fingerprint, setFingerprint] = useState<any>(null);
  const [shap, setShap] = useState<any>(null);
  const [diurnal, setDiurnal] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  

  useEffect(() => {
    if (!district) return;
    
    setLoading(true);
    const payload = {
      station_id: district.id,
      timestamp: new Date().toISOString(),
      pm25: district.pm25,
      pm10: district.pm10 || (district.pm25 * 1.5),
      temp: district.temp || 32.5,
      humidity: district.humidity || 55.0,
      pressure: district.pressure || 1008.2,
      wind_speed: district.wind_speed || 2.5,
      pblh: district.pblh || 850.0,
      lat: district.lat || (district.centroid ? district.centroid[1] : 17.4156),
      lon: district.lon || (district.centroid ? district.centroid[0] : 78.4736),
      no2: district.no2 || 25.0,
      so2: district.so2 || 10.0,
      co: district.co || 1.0,
      o3: district.o3 || 35.0,
    };

    // 1. Fetch Attribution & Geospatial Evidence
    fetch(apiUrl('/api/attribution'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(res => res.json())
      .then(data => setAttribution(data))
      .catch(err => console.error("Failed to fetch ML attribution", err));

    // 2. Fetch Fingerprint Radar
    fetch(apiUrl('/api/attribution/fingerprint'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(res => res.json())
      .then(data => setFingerprint(data))
      .catch(err => console.error("Failed to fetch fingerprint", err));

    // 3. Fetch SHAP values
    fetch(apiUrl('/api/forecast/shap?horizon=24'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(res => res.json())
      .then(data => setShap(data))
      .catch(err => console.error("Failed to fetch SHAP", err));

    // 4. Fetch Diurnal
    fetch(apiUrl(`/api/forecast/diurnal?lat=${payload.lat}&lon=${payload.lon}`), { method: 'POST' })
      .then(res => res.json())
      .then(data => setDiurnal(data))
      .catch(err => console.error("Failed to fetch Diurnal", err));

    setLoading(false);
  }, [district]);


  if (!district) return null;

  // Pie chart data derived directly from the active district pollutant telemetry
  const pieData = [
    { name: 'PM2.5', value: Math.round(district.pm25 || 0), fill: 'var(--accent-red)' },
    { name: 'PM10', value: Math.round(district.pm10 || 0), fill: 'var(--accent-orange)' },
    { name: 'NO2', value: Math.round(district.no2 || 25), fill: 'var(--accent-blue)' },
    { name: 'SO2', value: Math.round(district.so2 || 10), fill: 'var(--accent-yellow)' },
    { name: 'O3', value: Math.round(district.o3 || 35), fill: 'var(--accent-cyan)' }
  ];

  return (
    <div className="fade-in" style={{ padding: '16px 18px 40px', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: 16 }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-primary)', paddingBottom: 12 }}>
        <div>
          <h2 style={{ color: 'var(--text-primary)', margin: '0 0 2px', fontSize: '1.35rem', fontWeight: 800 }}>
            {district.name || district.id}
          </h2>
          <div style={{ fontSize: '0.72rem', color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
            Hyperlocal ML Intelligence
          </div>
          {!district.monitored && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 4, padding: '2px 8px', borderRadius: 4, background: 'rgba(100, 116, 139, 0.2)', border: '1px solid rgba(148, 163, 184, 0.3)', color: '#94a3b8', fontSize: '0.65rem', fontWeight: 600 }}>
              <span>⚪ No CAAQMS Center — Deployment Candidate</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button 
            onClick={() => setIsReportOpen(true)} 
            style={{ 
              background: 'rgba(56, 189, 248, 0.15)', 
              border: '1px solid rgba(56, 189, 248, 0.4)', 
              color: '#38bdf8', 
              padding: '6px 12px', 
              borderRadius: '6px', 
              cursor: 'pointer', 
              fontSize: '0.75rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              transition: 'var(--transition-fast)' 
            }}
          >
            📄 AI Report
          </button>
          <button 
            onClick={onReset} 
            style={{ 
              background: 'var(--bg-elevated)', 
              border: '1px solid var(--border-primary)', 
              color: 'var(--text-primary)', 
              padding: '6px 12px', 
              borderRadius: '6px', 
              cursor: 'pointer', 
              fontSize: '0.75rem',
              fontWeight: 600,
              transition: 'var(--transition-fast)' 
            }}
          >
            ✕ Close
          </button>
        </div>
      </div>

      {recommendedDeployments.length > 0 && (
        <div className="panel" style={{ background: 'var(--bg-surface)', border: '1px solid rgba(251, 191, 36, 0.35)' }}>
          <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
            <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700, color: '#fbbf24' }}>
              Recommended Portable Sensor Sites
            </div>
            <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>
              MCDA · {city} · gold pins on map
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '10px 12px 12px' }}>
            {recommendedDeployments.map((rec: any, i: number) => {
              const sourceColor = rec.dominantSource === 'Traffic' ? '#ef4444' : rec.dominantSource === 'Industrial' ? '#a855f7' : '#eab308';
              const isHere = rec.districtId === district.id;
              return (
                <div key={rec.districtId} style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  background: isHere ? 'rgba(251, 191, 36, 0.12)' : 'var(--bg-elevated)',
                  border: isHere ? '1px solid rgba(251, 191, 36, 0.45)' : '1px solid var(--border-primary)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                    <div>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700 }}>
                        #{i + 1} {rec.name}{isHere ? ' · this district' : ''}
                      </div>
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.4 }}>
                        {rec.reason}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                      <div style={{
                        fontSize: '0.62rem', fontWeight: 700, color: '#fbbf24',
                        background: 'rgba(251, 191, 36, 0.12)', border: '1px solid rgba(251, 191, 36, 0.4)',
                        borderRadius: 4, padding: '2px 6px',
                      }}>
                        {rec.priorityScore.toFixed(1)}
                      </div>
                      <div style={{ fontSize: '0.55rem', fontWeight: 700, color: sourceColor }}>
                        {rec.dominantSource}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Section 1: Headline Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div className="panel" style={{ padding: '14px', background: 'var(--bg-surface)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: 4, textTransform: 'uppercase', fontWeight: 600 }}>
            {district.monitored ? `CURRENT AQI (${aqiStandard === 'IN_NAQI' ? 'NAQI' : 'US EPA'})` : 'CAAQMS STATUS'}
          </div>
          {district.monitored ? (
            (() => {
              const val = Math.round(aqiStandard === 'US_EPA' ? (district.aqi_us ?? district.aqi ?? 0) : (district.aqi_in ?? district.aqi ?? 0));
              const cat = getAqiCategory(val, aqiStandard);
              return (
                <div>
                  <div style={{ fontSize: '2.2rem', fontWeight: 800, color: cat.color, lineHeight: 1.1 }}>
                    {val}
                  </div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 700, color: cat.color, marginTop: 4 }}>
                    {cat.label}
                  </div>
                </div>
              );
            })()
          ) : (
            <div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#94a3b8', lineHeight: 1.2 }}>
                ⚪ No Center
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.3 }}>
                Nearest: <strong style={{ color: 'var(--text-primary)' }}>{district.reference_station || 'Regional Station'}</strong> ({district.reference_distance_km ?? 5.0} km)
              </div>
              <div style={{ fontSize: '0.65rem', color: '#38bdf8', marginTop: 3 }}>
                Ref AQI: <strong>{aqiStandard === 'IN_NAQI' ? (district.reference_aqi_in ?? '--') : (district.reference_aqi_us ?? '--')}</strong> ({aqiStandard === 'IN_NAQI' ? 'India NAQI' : 'US EPA'})
              </div>
            </div>
          )}
        </div>
        <div className="panel" style={{ padding: '14px', background: 'var(--bg-surface)' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: 4, textTransform: 'uppercase', fontWeight: 600 }}>METEOROLOGY</div>
          <div style={{ fontSize: '0.78rem', marginBottom: 2, color: 'var(--text-secondary)' }}>Temp: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{district.temp || 32}°C</span></div>
          <div style={{ fontSize: '0.78rem', marginBottom: 2, color: 'var(--text-secondary)' }}>Wind: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{district.wind_speed || 2.5} m/s</span></div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>PBLH: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{district.pblh || 850} m</span></div>
        </div>
      </div>

      {/* Section 2: Attribution Bars */}
      <div className="panel" style={{ background: 'var(--bg-surface)' }}>
        <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
          <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700 }}>Source Attribution (CatBoost GPU)</div>
        </div>
        <div style={{ padding: '14px' }}>
          {loading ? (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Running classifier...</div>
          ) : attribution ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(attribution.probabilities).sort((a: any, b: any) => b[1] - a[1]).map(([source, prob]: any) => (
                <div key={source}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: 4 }}>
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-primary)', fontWeight: 500 }}>{source.replace('_', ' ')}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{(prob * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ width: '100%', height: 6, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${prob * 100}%`, height: '100%', background: attribution.prediction_set.includes(source) ? 'var(--accent-red)' : 'var(--accent-cyan)', borderRadius: 3 }} />
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>


      {/* Section 4: SHAP Feature Importance */}
      <div className="panel" style={{ background: 'var(--bg-surface)' }}>
        <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
          <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700 }}>SHAP Explainer (Why is AQI high?)</div>
        </div>
        <div style={{ width: '100%', height: 210, padding: '10px 6px' }}>
          {shap ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shap.features.slice(0, 6)} layout="vertical" margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border-primary)" />
                <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                <YAxis dataKey="feature" type="category" width={85} tick={{ fill: 'var(--text-primary)', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 6, fontSize: 11, color: 'var(--text-primary)' }} />
                <Bar dataKey="value" name="SHAP Value (+/- AQI)">
                  {shap.features.slice(0, 6).map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.value > 0 ? 'var(--accent-red)' : 'var(--accent-green)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <div style={{ padding: 20, textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Loading SHAP values...</div>}
        </div>
      </div>

      {/* Section 5: Fingerprint Radar */}
      <div className="panel" style={{ background: 'var(--bg-surface)' }}>
        <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
          <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700 }}>Pollutant Fingerprint Radar</div>
        </div>
        <div style={{ width: '100%', height: 230, padding: '10px 0' }}>
          {fingerprint ? (
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart outerRadius={70} data={Object.keys(fingerprint[0]).filter(k => k !== 'name').map(k => ({ subject: k, A: fingerprint[0][k], B: fingerprint[1][k] }))}>
                <PolarGrid stroke="var(--border-primary)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Current" dataKey="A" stroke="var(--accent-blue)" fill="var(--accent-blue)" fillOpacity={0.4} />
                <Radar name="Reference (Vehicular)" dataKey="B" stroke="var(--accent-red)" fill="none" strokeDasharray="3 3" />
                <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 8, fontSize: 11, color: 'var(--text-primary)' }} />
              </RadarChart>
            </ResponsiveContainer>
          ) : <div style={{ padding: 20, textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Loading Fingerprint...</div>}
        </div>
      </div>

      {/* Section 6: Geospatial Evidence */}
      {attribution?.geospatial_evidence && (
        <div className="panel" style={{ background: 'var(--bg-surface)' }}>
          <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
            <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700 }}>Satellite & Geospatial Cross-Check</div>
          </div>
          <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(attribution.geospatial_evidence).map(([key, val]: any) => (
              <div key={key} style={{ background: 'var(--bg-elevated)', padding: '8px 12px', borderRadius: 6, fontSize: '0.75rem' }}>
                <strong style={{ color: 'var(--accent-blue)', display: 'block', marginBottom: 2 }}>{key.replace(/_/g, ' ')}</strong>
                <span style={{ color: 'var(--text-primary)' }}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 7: Pollutant Breakdown Pie */}
      <div className="panel" style={{ background: 'var(--bg-surface)' }}>
        <div className="panel-header" style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-primary)' }}>
          <div className="panel-title" style={{ fontSize: '0.82rem', fontWeight: 700 }}>Sub-Index Breakdown</div>
        </div>
        <div style={{ width: '100%', height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} innerRadius={42} outerRadius={62} paddingAngle={4} dataKey="value" stroke="none">
                {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-primary)', borderRadius: 6, fontSize: 11, color: 'var(--text-primary)' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Executive AI Report Modal */}
      <ReportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        initialCity={city}
        initialDistrict={district.name || district.id}
        initialMode="district_audit"
        telemetryData={district}
        attributionData={attribution}
      />

    </div>
  );
}

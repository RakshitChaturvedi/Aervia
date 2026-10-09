'use client';
import React, { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useCityContext } from '@/context/CityContext';
import { getAqiCategory } from '@/utils/aqi';
import { recommendDeployments } from '@/utils/mcda';
import { Station, CityId, RecommendedDeployment } from '@/types';

const CityMap = dynamic(() => import('@/components/CityMap'), { ssr: false });
const DeepDivePanel = dynamic(() => import('@/components/DeepDivePanel'), { ssr: false });
const AdvisoryPanel = dynamic(() => import('@/components/AdvisoryPanel'), { ssr: false });
const ReportModal = dynamic(() => import('@/components/ReportModal'), { ssr: false });

function LiveClock() {
  const [time, setTime] = useState('--:--:--');
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-IN', { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span suppressHydrationWarning style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
      {time} IST
    </span>
  );
}

export default function LiveMapPage() {
  const {
    activeCity, setActiveCity,
    cityData, liveData, userCoords, liveLoading,
    stations, districts,
    aqiStandard, setAqiStandard,
  } = useCityContext();

  const [alertStation, setAlertStation] = useState<Station | null>(null);
  const [hoveredLocation, setHoveredLocation] = useState<any>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<any>(null);
  const [monitoringLocation, setMonitoringLocation] = useState<{ lat: number; lon: number; name?: string } | null>(null);
  const [advisoryOpen, setAdvisoryOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  React.useEffect(() => {
    setSelectedDistrict(null);
  }, [activeCity]);

  const recommendedDeployments: RecommendedDeployment[] = useMemo(() => {
    if (!selectedDistrict || districts.length === 0) return [];
    return recommendDeployments(districts, selectedDistrict.id, 5).map((rec) => ({
      districtId: rec.district.id,
      name: rec.district.name,
      priorityScore: rec.priorityScore,
      dominantSource: rec.dominantSource,
      reason: rec.reason,
      benefit: rec.benefit,
      rank: rec.rank,
      aqi: rec.district.aqi,
    }));
  }, [selectedDistrict, districts]);

  // Compute commander header metrics from genuine monitored stations only
  const monitoredStations = useMemo(() => {
    return stations.filter(s => s.monitored !== false && typeof (aqiStandard === 'US_EPA' ? (s.aqi_us ?? s.aqi) : (s.aqi_in ?? s.aqi)) === 'number');
  }, [stations, aqiStandard]);

  let avgAqi = 0;
  let worstStationName = 'N/A';
  let worstStationAqi = 0;
  let alertCount = 0;

  if (activeCity === 'My Location') {
    if (liveData) {
      avgAqi = Math.round(liveData.live_aqi);
      worstStationName = 'Local GPS';
      worstStationAqi = Math.round(liveData.live_aqi);
      alertCount = liveData.live_aqi > 200 ? 1 : 0;
    } else {
      worstStationName = 'Locating...';
    }
  } else if (monitoredStations.length > 0) {
    if (cityData) {
      const cityVal = aqiStandard === 'US_EPA' ? (cityData.center_aqi_us ?? cityData.aqi_us) : (cityData.center_aqi_in ?? cityData.aqi_in);
      if (typeof cityVal === 'number' && cityVal > 0) {
        avgAqi = Math.round(cityVal);
      }
    }
    if (avgAqi === 0) {
      avgAqi = Math.round(
        monitoredStations.reduce((s, st) => {
          const val = aqiStandard === 'US_EPA' ? (st.aqi_us ?? st.aqi ?? 0) : (st.aqi_in ?? st.aqi ?? 0);
          return s + val;
        }, 0) / monitoredStations.length
      );
    }
    const maxStation = monitoredStations.reduce((max, st) => {
      const stVal = aqiStandard === 'US_EPA' ? (st.aqi_us ?? st.aqi ?? 0) : (st.aqi_in ?? st.aqi ?? 0);
      const maxVal = aqiStandard === 'US_EPA' ? (max.aqi_us ?? max.aqi ?? 0) : (max.aqi_in ?? max.aqi ?? 0);
      return stVal > maxVal ? st : max;
    }, monitoredStations[0]);
    worstStationName = maxStation.name;
    worstStationAqi = Math.round(aqiStandard === 'US_EPA' ? (maxStation.aqi_us ?? maxStation.aqi ?? 0) : (maxStation.aqi_in ?? maxStation.aqi ?? 0));
    alertCount = monitoredStations.filter(s => (s.status === 'alert') || ((aqiStandard === 'US_EPA' ? (s.aqi_us ?? s.aqi ?? 0) : (s.aqi_in ?? s.aqi ?? 0)) > 200)).length;
  }

  const avgCat = getAqiCategory(avgAqi, aqiStandard);

  return (
    <div className="livemap-page">
      {/* ── Commander Header ── */}
      <header className="dashboard-header">
        <div className="header-brand">
          <span className="brand-text-logo">Aervia</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500, marginLeft: '10px' }}>
            Live Air Quality Map
          </span>
          <select
            value={activeCity}
            onChange={(e) => setActiveCity(e.target.value as CityId)}
            style={{ marginLeft: '20px', padding: '5px 10px', borderRadius: '6px', background: '#1c2128', color: 'white', border: '1px solid #30363d', cursor: 'pointer', fontSize: '0.8rem' }}
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

        <div className="header-metrics">
          <div className="metric-item">
            <span className="metric-label">City Avg ({aqiStandard === 'IN_NAQI' ? 'NAQI' : 'US EPA'})</span>
            <span className="metric-value" style={{ color: avgCat.color }}>{avgAqi}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Worst Station</span>
            <span className="metric-value" style={{ color: 'var(--accent-red)' }}>{worstStationName} ({worstStationAqi})</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Active Alerts</span>
            <span className="metric-value" style={{ color: 'var(--accent-amber)' }}>{alertCount}</span>
          </div>
        </div>

        <div className="header-status" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Dual AQI Standard Toggle */}
          <div style={{
            display: 'flex',
            background: '#1c2128',
            borderRadius: 6,
            border: '1px solid #30363d',
            overflow: 'hidden',
            padding: 2,
          }}>
            <button
              onClick={() => setAqiStandard('IN_NAQI')}
              style={{
                padding: '4px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                background: aqiStandard === 'IN_NAQI' ? '#3b82f6' : 'transparent',
                color: aqiStandard === 'IN_NAQI' ? '#ffffff' : '#8b949e',
                transition: 'all 0.2s',
              }}
            >
              🇮🇳 NAQI
            </button>
            <button
              onClick={() => setAqiStandard('US_EPA')}
              style={{
                padding: '4px 8px',
                fontSize: '0.68rem',
                fontWeight: 700,
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                background: aqiStandard === 'US_EPA' ? '#3b82f6' : 'transparent',
                color: aqiStandard === 'US_EPA' ? '#ffffff' : '#8b949e',
                transition: 'all 0.2s',
              }}
            >
              🇺🇸 EPA
            </button>
          </div>

          <button
            onClick={() => setIsReportModalOpen(true)}
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
              gap: '6px',
              transition: 'var(--transition-fast)'
            }}
          >
            📄 AI Report
          </button>
          <div className="status-badge live">
            <div className="dot" />
            Live
          </div>
          <LiveClock />
        </div>
      </header>

      {/* ── Body: Map + optional DeepDive panel ── */}
      <div className={`livemap-body${selectedDistrict ? ' with-panel' : ''}`}>
        <CityMap
          alertStation={alertStation}
          city={activeCity}
          userCoords={userCoords}
          liveData={liveData}
          cityData={cityData}
          liveLoading={liveLoading}
          onHover={setHoveredLocation}
          onClick={(d: any) => {
            setSelectedDistrict(d);
          }}
          selectedDistrictId={selectedDistrict?.id}
          onDistrictsComputed={() => {}}
          monitoringLocation={monitoringLocation}
          recommendedDeployments={recommendedDeployments}
        />

        {selectedDistrict && (
          <aside className="livemap-deep-panel">
            <DeepDivePanel
              district={selectedDistrict}
              city={activeCity}
              onReset={() => setSelectedDistrict(null)}
              recommendedDeployments={recommendedDeployments}
            />
          </aside>
        )}
      </div>

      {/* ── Floating Advisory FAB + Popup ── */}
      <button
        className={`advisory-fab${advisoryOpen ? ' active' : ''}`}
        onClick={() => setAdvisoryOpen(!advisoryOpen)}
        aria-label="Toggle Advisory"
        title="Citizen Advisory"
      >
        {advisoryOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
            <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
          </svg>
        )}
        {!advisoryOpen && <span className="advisory-fab-badge">AI</span>}
      </button>

      {advisoryOpen && (
        <div className="advisory-popup">
          <div className="advisory-popup-header">
            <span>Citizen Advisory</span>
            <button
              className="advisory-popup-close"
              onClick={() => setAdvisoryOpen(false)}
              aria-label="Close Advisory"
            >
              ✕
            </button>
          </div>
          <div className="advisory-popup-body">
            <AdvisoryPanel
              city={activeCity}
              userCoords={userCoords}
              liveData={liveData}
              cityData={cityData}
              selectedDistrict={selectedDistrict}
              hoveredLocation={hoveredLocation}
              districts={districts}
            />
          </div>
        </div>
      )}

      {/* Executive AI Report Modal */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        initialCity={activeCity}
        initialMode="city_audit"
        telemetryData={{ aqi: avgAqi, pm25: stations[0]?.pm25 || 42, pm10: stations[0]?.pm10 || 68 }}
        historicalData={cityData}
      />
    </div>
  );
}

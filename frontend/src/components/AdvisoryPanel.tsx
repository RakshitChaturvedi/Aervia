'use client';
import React, { useState, useEffect, useRef } from 'react';
import { ShieldCheck, MapPin, TrendingUp } from 'lucide-react';

export const languageLabels: Record<string, string> = {
  en: 'English',
  te: 'తెలుగు',
  hi: 'हिंदी',
  kn: 'ಕನ್ನಡ',
};

interface AdvisoryPanelProps {
  city?: string;
  userCoords?: { lat: number; lon: number } | null;
  liveData?: any;
  cityData?: any;
  selectedDistrict?: any;
  hoveredLocation?: any;
  districts?: any[];
}

function formatAdvisoryText(text: string) {
  if (!text) return null;
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} style={{ height: 6 }} />;
    
    // Replace **bold** with <strong>
    const parts = line.split(/(\*\*.*?\*\*)/g);
    return (
      <div key={i} style={{ marginBottom: line.startsWith('•') ? 5 : 8, lineHeight: 1.55 }}>
        {parts.map((part, pIdx) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={pIdx} style={{ color: '#ffffff', fontWeight: 700 }}>
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={pIdx} style={{ color: '#e2e8f0' }}>{part}</span>;
        })}
      </div>
    );
  });
}

export default function AdvisoryPanel({
  city = 'Delhi',
  userCoords,
  liveData,
  cityData,
  selectedDistrict,
  hoveredLocation,
  districts = []
}: AdvisoryPanelProps) {
  const [selectedLang, setSelectedLang] = useState<'en' | 'te' | 'hi' | 'kn'>('en');
  const [advisoryData, setAdvisoryData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Maintain locked target so user can comfortably move mouse from map into advisory card to scroll
  const [activeTarget, setActiveTarget] = useState<any>(null);
  const [isHoveringCard, setIsHoveringCard] = useState<boolean>(false);
  const decayTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (hoveredLocation && hoveredLocation.name) {
      if (decayTimerRef.current) clearTimeout(decayTimerRef.current);
      setActiveTarget(hoveredLocation);
    } else if (selectedDistrict && selectedDistrict.name) {
      if (decayTimerRef.current) clearTimeout(decayTimerRef.current);
      setActiveTarget(selectedDistrict);
    } else if (!isHoveringCard) {
      // Grace period before reverting to city forecast to allow smooth cursor transition
      decayTimerRef.current = setTimeout(() => {
        setActiveTarget(null);
      }, 2500);
    }
    return () => {
      if (decayTimerRef.current) clearTimeout(decayTimerRef.current);
    };
  }, [hoveredLocation, selectedDistrict, isHoveringCard]);

  const isDistrictMode = !!(activeTarget && activeTarget.name);
  const targetDistrictName = isDistrictMode ? activeTarget.name : city;

  // Fetch Single-Window Unified Citizen Advisory
  useEffect(() => {
    const langMap = { en: 'English', te: 'Telugu', hi: 'Hindi', kn: 'Kannada' };
    const stations = cityData ? cityData.stations : [];
    
    // Sort districts to find cleanest and most polluted corridors
    const sortedDistricts = [...districts].sort((a, b) => a.aqi - b.aqi);
    const bestDistricts = sortedDistricts.slice(0, 2).map(d => d.name);
    const worstDistricts = sortedDistricts.slice(-2).reverse().map(d => d.name);

    let payload: any = {
      city: city,
      language: langMap[selectedLang],
      mode: isDistrictMode ? 'district_live' : 'city_forecast',
      district_name: isDistrictMode ? activeTarget.name : `${city} Region`,
      district_aqi: isDistrictMode ? (activeTarget.aqi ?? (stations[0]?.aqi || 60)) : undefined,
      best_districts: bestDistricts,
      worst_districts: worstDistricts,
    };

    if (city === 'My Location' && liveData) {
      payload.reading = liveData.reading;
    } else if (isDistrictMode && activeTarget) {
      payload.reading = {
        station_id: activeTarget.name,
        timestamp: new Date().toISOString(),
        pm25: activeTarget.pm25 || 25.0,
        pm10: activeTarget.pm10 || 40.0,
        temp: activeTarget.temp || 30.0,
        humidity: activeTarget.humidity || 55.0,
        pressure: activeTarget.pressure || 1008.0,
        wind_speed: activeTarget.wind_speed || 2.5,
        pblh: activeTarget.pblh || 850.0,
        lat: activeTarget.lat || (activeTarget.centroid ? activeTarget.centroid[1] : 17.425),
        lon: activeTarget.lon || (activeTarget.centroid ? activeTarget.centroid[0] : 78.45),
        no2: activeTarget.no2 || 25.0,
        so2: activeTarget.so2 || 10.0,
        co: activeTarget.co || 1.0,
        o3: activeTarget.o3 || 30.0,
      };
    } else if (stations.length > 0) {
      const avgPm25 = stations.reduce((s: number, st: any) => s + st.pm25, 0) / stations.length;
      const avgPm10 = stations.reduce((s: number, st: any) => s + st.pm10, 0) / stations.length;
      const avgTemp = stations.reduce((s: number, st: any) => s + (st.temp || 28), 0) / stations.length;
      const avgHum = stations.reduce((s: number, st: any) => s + (st.humidity || 55), 0) / stations.length;
      const avgPress = stations.reduce((s: number, st: any) => s + (st.pressure || 1008), 0) / stations.length;
      const avgWind = stations.reduce((s: number, st: any) => s + (st.wind_speed || 2), 0) / stations.length;
      const avgPblh = stations.reduce((s: number, st: any) => s + (st.pblh || 800), 0) / stations.length;
      
      payload.reading = {
        station_id: `${city}_AGGREGATE`,
        timestamp: new Date().toISOString(),
        pm25: avgPm25,
        pm10: avgPm10,
        temp: avgTemp,
        humidity: avgHum,
        pressure: avgPress,
        wind_speed: avgWind,
        pblh: avgPblh
      };
    }

    setLoading(true);
    fetch('http://127.0.0.1:8000/api/advisory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        if (data) {
          setAdvisoryData(data);
        }
      })
      .catch(err => {
        console.error('Failed to fetch unified advisory:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [city, selectedLang, isDistrictMode, activeTarget?.name, activeTarget?.aqi, liveData, cityData, districts]);

  const aqiVal = advisoryData?.aqi_level ?? 60;
  const aqiColor = aqiVal <= 50 ? '#22c55e' : aqiVal <= 100 ? '#eab308' : aqiVal <= 150 ? '#f97316' : aqiVal <= 200 ? '#ef4444' : '#a855f7';

  return (
    <div 
      className="fade-in" 
      style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
      onMouseEnter={() => setIsHoveringCard(true)}
      onMouseLeave={() => setIsHoveringCard(false)}
      onWheel={(e) => e.stopPropagation()}
    >
      <div className="panel" style={{ padding: '14px 16px' }}>
        
        {/* Header with Title, Live Badge & Multilingual Switcher */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <ShieldCheck size={18} style={{ color: 'var(--accent-purple)' }} />
            <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
              Citizen Health Advisory
            </div>
            <div className="panel-badge badge-purple" style={{ fontSize: '0.62rem', padding: '2px 6px', color: '#ffffff', background: '#6d28d9', borderColor: '#7c3aed' }}>
              Gemini AI • NLG
            </div>
          </div>

          {/* Multilingual Selector */}
          <div className="lang-tabs" style={{ margin: 0 }}>
            {(Object.keys(languageLabels) as Array<'en' | 'te' | 'hi' | 'kn'>).map((lang) => (
              <button
                key={lang}
                className={`lang-tab ${selectedLang === lang ? 'active' : ''}`}
                onClick={() => setSelectedLang(lang)}
                style={{ padding: '2px 7px', fontSize: '0.7rem' }}
              >
                {languageLabels[lang]}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Context Status Bar */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: 10,
          padding: '5px 9px',
          background: '#f1f5f9',
          borderRadius: 6,
          border: '1px solid var(--border-primary)',
          fontSize: '0.74rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color: isDistrictMode ? 'var(--accent-blue)' : 'var(--accent-purple)', display: 'inline-flex', alignItems: 'center' }}>
              {isDistrictMode ? <MapPin size={13} /> : <TrendingUp size={13} />}
            </span>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              {isDistrictMode ? `Active: ${targetDistrictName}` : `${city} 24-Hour City Outlook`}
            </span>
            {isDistrictMode && (
              <button
                onClick={() => setActiveTarget(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--accent-blue)',
                  fontSize: '0.68rem',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: 0
                }}
                title="Return to City Forecast"
              >
                (city forecast)
              </button>
            )}
          </div>

          <div style={{ 
            fontSize: '0.7rem', 
            background: `${aqiColor}22`, 
            color: aqiColor, 
            padding: '2px 6px', 
            borderRadius: 4, 
            fontWeight: 700 
          }}>
            {isDistrictMode ? `Live AQI ${aqiVal}` : `Projected AQI ${aqiVal}`} • {advisoryData?.aqi_category || 'Moderate'}
          </div>
        </div>

        {/* Single Unified Formatted Text Card (Scrollable) */}
        <div 
          style={{
            background: '#273244',
            border: `1px solid ${isDistrictMode ? 'rgba(56, 189, 248, 0.4)' : 'rgba(168, 85, 247, 0.4)'}`,
            borderRadius: 8,
            padding: '12px 14px',
            boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
            fontSize: '0.84rem',
            maxHeight: '260px',
            overflowY: 'auto',
            overscrollBehavior: 'contain',
            scrollbarWidth: 'thin',
            scrollbarColor: 'var(--border-primary) transparent',
          }}
          onWheel={(e) => e.stopPropagation()}
        >
          {loading ? (
            <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Translating air quality into natural language with Gemini AI...
            </div>
          ) : (
            <div>
              {formatAdvisoryText(advisoryData?.advisory || 'Hover over any district on the map or view 24h city forecast.')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}



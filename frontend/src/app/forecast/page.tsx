'use client';
import React from 'react';
import dynamic from 'next/dynamic';
import { useCityContext } from '@/context/CityContext';

import { CityId } from '@/types';
import AtmosphericForecastPanel from '@/components/AtmosphericForecastPanel';

const ForecastPanel = dynamic(() => import('@/components/ForecastPanel'), { ssr: false });
const StubbleTransportPanel = dynamic(() => import('@/components/StubbleTransportPanel'), { ssr: false });

export default function ForecastPage() {
  const { activeCity, setActiveCity, userCoords, liveData, cityData } = useCityContext();

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div className="page-header-left">
          <div className="header-brand">
            <span className="brand-text-logo">Aervia</span>
          </div>
          <div className="page-header-divider" />
          <h2 className="page-title">{activeCity} Forecast</h2>
          <select
            value={activeCity}
            onChange={(e) => setActiveCity(e.target.value as CityId)}
            style={{ marginLeft: '16px', padding: '6px 16px', borderRadius: 'var(--radius-pill)', background: 'var(--bg-surface)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '0.82rem', fontWeight: 600, outline: 'none', cursor: 'pointer' }}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div className="page-city-badge">{activeCity}</div>
        </div>
      </div>
      <div className="page-content">
        <AtmosphericForecastPanel
          city={activeCity}
          coordinates={activeCity === 'My Location' ? userCoords : null}
        />
        <StubbleTransportPanel />
        <ForecastPanel city={activeCity} userCoords={userCoords} liveData={liveData} cityData={cityData} hoveredLocation={null} />
      </div>
    </div>
  );
}

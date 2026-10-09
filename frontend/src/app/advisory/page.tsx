'use client';
import React from 'react';
import dynamic from 'next/dynamic';
import { useCityContext } from '@/context/CityContext';

const AdvisoryPanel = dynamic(() => import('@/components/AdvisoryPanel'), { ssr: false });

export default function AdvisoryPage() {
  const { activeCity, userCoords, liveData, cityData, districts } = useCityContext();

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div className="page-header-left">
          <div className="header-brand">
            <span className="brand-text-logo">Aervia</span>
          </div>
          <div className="page-header-divider" />
          <h2 className="page-title">Advisory</h2>
        </div>
        <div className="page-city-badge">{activeCity}</div>
      </div>
      <div className="page-content">
        <AdvisoryPanel city={activeCity} userCoords={userCoords} liveData={liveData} cityData={cityData} districts={districts} />
      </div>
    </div>
  );
}

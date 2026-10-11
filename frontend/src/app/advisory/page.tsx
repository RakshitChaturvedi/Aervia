'use client';

import React from 'react';
import LocalCaptureAdvisories from '@/components/LocalCaptureAdvisories';

export default function AdvisoryPage() {
  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div className="page-header-left">
          <div className="header-brand"><span className="brand-text-logo">Aervia</span></div>
          <div className="page-header-divider" />
          <h2 className="page-title">Local node advisories</h2>
        </div>
        <div className="page-city-badge">VNR VJIET · College Gate</div>
      </div>
      <div className="page-content"><LocalCaptureAdvisories /></div>
    </div>
  );
}

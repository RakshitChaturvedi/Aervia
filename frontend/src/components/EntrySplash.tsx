'use client';
import React, { useState, useEffect } from 'react';
import { Wind, Activity, ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';

export default function EntrySplash({ onEnter }: { onEnter?: () => void }) {
  const [visible, setVisible] = useState<boolean | null>(null);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    setVisible(false);
  }, []);

  const handleEnter = () => {
    setFading(true);
    setTimeout(() => {
      setVisible(false);
      sessionStorage.setItem('aervia_splash_dismissed', 'true');
      if (onEnter) onEnter();
    }, 500);
  };

  // Keyboard shortcut: Press Enter to enter platform
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (visible && e.key === 'Enter') {
        handleEnter();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible]);

  if (visible === null || visible === false) return null;

  return (
    <div className={`entry-splash-overlay ${fading ? 'fade-out' : ''}`}>
      {/* Background Animated Gradient Aura */}
      <div className="entry-splash-bg-glow" />
      <div className="entry-splash-grid-mesh" />

      {/* Main Glassmorphism Portal Card */}
      <div className="entry-splash-card">
        {/* Top Tag */}
        <div className="entry-splash-tag">
          <Sparkles size={14} className="entry-tag-icon" />
          <span>Next-Gen Air Quality Decision System</span>
        </div>

        {/* Brand Text Logo */}
        <div className="entry-logo-text-wrap">
          <h1 className="brand-text-logo entry-logo-text">Aervia</h1>
        </div>

        {/* Platform Purpose Subtitle */}
        <p className="entry-splash-desc">
          Hyperlocal Atmospheric Physics Engine &bull; 72-Hour MAPIE Conformal Forecasting &bull; Real-Time Satellite Telemetry Assimilation
        </p>

        {/* Key Intelligence Pillars */}
        <div className="entry-feature-pills">
          <div className="entry-pill">
            <Wind size={15} />
            <span>Ventilation Physics</span>
          </div>
          <div className="entry-pill">
            <Activity size={15} />
            <span>29-Feature LightGBM</span>
          </div>
          <div className="entry-pill">
            <ShieldCheck size={15} />
            <span>Atmospheric Intelligence</span>
          </div>
        </div>

        {/* Enter Button */}
        <button className="entry-enter-btn" onClick={handleEnter} autoFocus>
          <span>ENTER PLATFORM</span>
          <ArrowRight size={18} className="entry-arrow" />
        </button>

        <span className="entry-keyboard-hint">
          Press <kbd>↵ Enter</kbd> to launch dashboard
        </span>
      </div>
    </div>
  );
}

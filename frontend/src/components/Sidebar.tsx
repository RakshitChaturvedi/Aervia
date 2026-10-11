'use client';
import React, { useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Home, Map, TrendingUp, AlertTriangle, Radio, Menu, PanelLeftClose, ClipboardCheck,
} from 'lucide-react';
import { useCityContext } from '@/context/CityContext';

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: any;
}

const navItems: NavItem[] = [
  { id: 'home', label: 'Command Home', href: '/', icon: Home },
  { id: 'live-map', label: 'Live Map', href: '/live-map', icon: Map },
  { id: 'forecast', label: '72h Forecast', href: '/forecast', icon: TrendingUp },
  { id: 'telemetry', label: 'Live Telemetry', href: '/telemetry', icon: Radio },
  { id: 'alerts', label: 'Episode Alerts', href: '/alerts', icon: AlertTriangle },
  { id: 'advisory', label: 'Node Advisories', href: '/advisory', icon: ClipboardCheck },
];

export default function Sidebar() {
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const pathname = usePathname();
  const { activeCity } = useCityContext();

  const expanded = pinned || hovered;

  return (
    <>
      {/* Invisible spacer that pushes main content when pinned */}
      <div className={`sidebar-spacer${pinned ? ' pinned' : ''}`} />

      {/* Actual sidebar panel (fixed position) */}
      <nav
        className={`sidebar-panel${expanded ? ' expanded' : ''}${pinned ? ' pinned' : ''}`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Header: toggle + brand */}
        <div className="sidebar-header">
          <button
            className="sidebar-toggle"
            onClick={() => setPinned(!pinned)}
            aria-label={pinned ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {pinned ? <PanelLeftClose size={20} /> : <Menu size={20} />}
          </button>
          <div className={`sidebar-brand${expanded ? ' visible' : ''}`}>
            <span className="brand-text-logo">Aervia</span>
          </div>
        </div>

        {/* Navigation links */}
        <div className="sidebar-nav">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                href={item.href}
                className={`sidebar-nav-item${isActive ? ' active' : ''}`}
                title={!expanded ? item.label : undefined}
              >
                <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                <span className={`sidebar-nav-label${expanded ? ' visible' : ''}`}>
                  {item.label}
                </span>
                {isActive && expanded && <div className="sidebar-active-glow-dot" />}
              </Link>
            );
          })}
        </div>

        {/* Footer: current city indicator */}
        <div className={`sidebar-footer${expanded ? ' visible' : ''}`}>
          <div className="sidebar-city-indicator">
            <div className="sidebar-city-dot" />
            <span className="sidebar-city-name">{activeCity}</span>
          </div>
        </div>
      </nav>
    </>
  );
}

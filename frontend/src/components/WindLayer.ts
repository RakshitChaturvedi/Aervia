/**
 * WindLayer.ts — Live wind animation system for Aervia
 * 
 * Provides two visualization modes:
 * 1. Directional arrows at each station (IconLayer with rotated SVG)
 * 2. Animated wind particles flowing across the map (ScatterplotLayer + rAF)
 * 
 * All wind data comes from Open-Meteo via the existing /city-data endpoint.
 * Zero new API calls — purely a visualization layer.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { ScatterplotLayer, IconLayer } from '@deck.gl/layers';

// ─── Types ───────────────────────────────────────────────────────────────────

interface WindStation {
  lat: number;
  lon: number;
  wind_speed?: number;
  wind_dir?: number;
}

interface WindParticle {
  lon: number;
  lat: number;
  vx: number;    // degrees/frame in lon
  vy: number;    // degrees/frame in lat
  age: number;   // 0 → maxAge lifecycle
  maxAge: number;
}

// ─── Constants ───────────────────────────────────────────────────────────────

// Adaptive particle count based on device capability
const MAX_PARTICLES = typeof navigator !== 'undefined' && navigator.hardwareConcurrency > 4 ? 150 : 80;
const PARTICLE_LIFESPAN_MIN = 120; // frames (~4s at 30fps)
const PARTICLE_LIFESPAN_MAX = 240; // frames (~8s at 30fps)
const WIND_SPEED_SCALE = 0.000035; // degrees/frame per m/s of wind speed
const TARGET_FPS = 30;
const FRAME_INTERVAL = 1000 / TARGET_FPS;

// City bounding boxes for particle spawn region [west, south, east, north]
const CITY_BOUNDS: Record<string, [number, number, number, number]> = {
  'Delhi':     [76.90, 28.40, 77.35, 28.88],
  'Hyderabad': [78.20, 17.20, 78.70, 17.60],
  'Bengaluru': [77.40, 12.80, 77.80, 13.15],
  'Guwahati':  [91.55, 26.05, 91.85, 26.25],
};

// Default fallback bounding box (Delhi)
const DEFAULT_BOUNDS: [number, number, number, number] = [76.90, 28.40, 77.35, 28.88];

// ─── Inline SVG Arrow Icon ──────────────────────────────────────────────────

// A simple upward-pointing arrow encoded as data URI.
// deck.gl's IconLayer will rotate it via getAngle.
const ARROW_SVG = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
    <path d="M32 4 L44 28 L36 24 L36 56 L28 56 L28 24 L20 28 Z" 
          fill="rgba(220,230,255,0.85)" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/>
  </svg>`
)}`;

// ─── Wind Vector Interpolation ──────────────────────────────────────────────

/**
 * Interpolate wind vector at a given point using IDW from nearby stations.
 * Returns [vx, vy] in degrees/frame.
 */
function interpolateWindVector(
  lon: number,
  lat: number,
  stations: WindStation[]
): [number, number] {
  if (!stations || stations.length === 0) return [0, 0];

  let wSum = 0;
  let sinSum = 0;
  let cosSum = 0;
  let speedSum = 0;

  for (const s of stations) {
    const dx = (s.lon - lon) * 85; // approximate km
    const dy = (s.lat - lat) * 111;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < 0.01) {
      // Exact match — use this station's wind directly
      const speed = (s.wind_speed || 0) * WIND_SPEED_SCALE;
      // Meteorological wind_dir = direction wind comes FROM
      // Particles move in the direction wind is GOING TO = wind_dir + 180
      const goingToRad = (((s.wind_dir || 0) + 180) * Math.PI) / 180;
      return [
        speed * Math.sin(goingToRad), // vx (longitude change)
        speed * Math.cos(goingToRad), // vy (latitude change)
      ];
    }

    const w = 1 / (dist * dist);
    wSum += w;
    speedSum += w * (s.wind_speed || 0);

    const dirRad = (((s.wind_dir || 0) + 180) * Math.PI) / 180;
    sinSum += w * Math.sin(dirRad);
    cosSum += w * Math.cos(dirRad);
  }

  const avgSpeed = (speedSum / wSum) * WIND_SPEED_SCALE;
  const avgDir = Math.atan2(sinSum / wSum, cosSum / wSum);

  return [
    avgSpeed * Math.sin(avgDir),
    avgSpeed * Math.cos(avgDir),
  ];
}

// ─── Particle System ─────────────────────────────────────────────────────────

function createParticle(bounds: [number, number, number, number], stations: WindStation[]): WindParticle {
  const [west, south, east, north] = bounds;
  const lon = west + Math.random() * (east - west);
  const lat = south + Math.random() * (north - south);
  const [vx, vy] = interpolateWindVector(lon, lat, stations);

  return {
    lon, lat, vx, vy,
    age: Math.floor(Math.random() * PARTICLE_LIFESPAN_MIN), // stagger start ages
    maxAge: PARTICLE_LIFESPAN_MIN + Math.floor(Math.random() * (PARTICLE_LIFESPAN_MAX - PARTICLE_LIFESPAN_MIN)),
  };
}

function resetParticle(p: WindParticle, bounds: [number, number, number, number], stations: WindStation[]): void {
  const [west, south, east, north] = bounds;
  p.lon = west + Math.random() * (east - west);
  p.lat = south + Math.random() * (north - south);
  const [vx, vy] = interpolateWindVector(p.lon, p.lat, stations);
  p.vx = vx;
  p.vy = vy;
  p.age = 0;
  p.maxAge = PARTICLE_LIFESPAN_MIN + Math.floor(Math.random() * (PARTICLE_LIFESPAN_MAX - PARTICLE_LIFESPAN_MIN));
}

function stepParticle(p: WindParticle, bounds: [number, number, number, number], stations: WindStation[]): void {
  p.age++;

  if (p.age >= p.maxAge) {
    resetParticle(p, bounds, stations);
    return;
  }

  // Move particle along wind vector
  p.lon += p.vx;
  p.lat += p.vy;

  // Wrap around if out of bounds
  const [west, south, east, north] = bounds;
  if (p.lon < west || p.lon > east || p.lat < south || p.lat > north) {
    resetParticle(p, bounds, stations);
  }

  // Re-interpolate wind vector every 15 frames for smooth field following
  if (p.age % 15 === 0) {
    const [vx, vy] = interpolateWindVector(p.lon, p.lat, stations);
    // Smooth transition: 70% old + 30% new to avoid jitter
    p.vx = p.vx * 0.7 + vx * 0.3;
    p.vy = p.vy * 0.7 + vy * 0.3;
  }
}

/**
 * Calculate particle alpha based on lifecycle (fade in → full → fade out)
 */
function particleAlpha(age: number, maxAge: number): number {
  const t = age / maxAge; // 0 → 1
  if (t < 0.15) return Math.floor((t / 0.15) * 140);        // fade in
  if (t > 0.85) return Math.floor(((1 - t) / 0.15) * 140);  // fade out
  return 140; // full visibility
}

// ─── Exported: Wind Arrow Layers ─────────────────────────────────────────────

/**
 * Creates deck.gl IconLayer with rotated arrow icons at each station.
 * Arrow points in the direction the wind is GOING (wind_dir + 180).
 * Arrow size scales with wind speed.
 */
export function createWindArrowLayers(stations: WindStation[], visible: boolean): IconLayer[] {
  if (!visible || !stations || stations.length === 0) return [];

  const windStations = stations.filter(s => 
    s.wind_speed !== undefined && s.wind_speed > 0.3
  );

  if (windStations.length === 0) return [];

  return [
    new IconLayer<WindStation>({
      id: 'wind-arrows',
      data: windStations,
      pickable: false,
      iconAtlas: ARROW_SVG,
      iconMapping: {
        arrow: { x: 0, y: 0, width: 64, height: 64, anchorY: 32 },
      },
      getIcon: () => 'arrow',
      getPosition: (d: WindStation) => [d.lon, d.lat],
      // deck.gl IconLayer getAngle rotates clockwise from north
      // Meteorological wind_dir is direction FROM which wind blows
      // Arrow should point in the direction wind is GOING = wind_dir + 180
      getAngle: (d: WindStation) => -((d.wind_dir || 0) + 180) % 360,
      getSize: (d: WindStation) => {
        const speed = d.wind_speed || 0;
        return Math.min(48, Math.max(20, speed * 6));
      },
      sizeScale: 1,
      sizeUnits: 'pixels' as const,
      billboard: true,
    }),
  ];
}

// ─── Exported: Wind Particle Hook ────────────────────────────────────────────

/**
 * React hook that manages an animated particle system.
 * Returns a ScatterplotLayer that updates every frame.
 */
export function useWindParticles(
  stations: WindStation[],
  enabled: boolean,
  city: string = 'Delhi'
): ScatterplotLayer | null {
  const particlesRef = useRef<WindParticle[]>([]);
  const rafRef = useRef<number>(0);
  const lastFrameRef = useRef<number>(0);
  const [layerData, setLayerData] = useState<{ lon: number; lat: number; alpha: number }[]>([]);
  const stationsRef = useRef<WindStation[]>(stations);
  const boundsRef = useRef<[number, number, number, number]>(CITY_BOUNDS[city] || DEFAULT_BOUNDS);

  // Keep refs in sync
  useEffect(() => {
    stationsRef.current = stations;
  }, [stations]);

  useEffect(() => {
    boundsRef.current = CITY_BOUNDS[city] || DEFAULT_BOUNDS;
  }, [city]);

  // Initialize or clear particles when enabled/city changes
  useEffect(() => {
    if (enabled && stationsRef.current.length > 0) {
      const bounds = boundsRef.current;
      particlesRef.current = Array.from({ length: MAX_PARTICLES }, () =>
        createParticle(bounds, stationsRef.current)
      );
    } else {
      particlesRef.current = [];
      setLayerData([]);
    }
  }, [enabled, city]);

  // Animation loop
  const animate = useCallback((timestamp: number) => {
    if (!enabled || particlesRef.current.length === 0) return;

    // Throttle to target FPS
    if (timestamp - lastFrameRef.current < FRAME_INTERVAL) {
      rafRef.current = requestAnimationFrame(animate);
      return;
    }
    lastFrameRef.current = timestamp;

    const bounds = boundsRef.current;
    const currentStations = stationsRef.current;

    // Step all particles
    for (const p of particlesRef.current) {
      stepParticle(p, bounds, currentStations);
    }

    // Build layer data (avoid creating new objects by reusing array)
    const newData = particlesRef.current.map(p => ({
      lon: p.lon,
      lat: p.lat,
      alpha: particleAlpha(p.age, p.maxAge),
    }));

    setLayerData(newData);
    rafRef.current = requestAnimationFrame(animate);
  }, [enabled]);

  useEffect(() => {
    if (enabled && stationsRef.current.length > 0) {
      rafRef.current = requestAnimationFrame(animate);
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [enabled, animate]);

  if (!enabled || layerData.length === 0) return null;

  return new ScatterplotLayer({
    id: 'wind-particles',
    data: layerData,
    pickable: false,
    opacity: 1,
    stroked: false,
    filled: true,
    radiusMinPixels: 1.5,
    radiusMaxPixels: 3,
    getPosition: (d: any) => [d.lon, d.lat],
    getFillColor: (d: any) => [200, 220, 255, d.alpha],
    getRadius: 150,
    // Ensure particles render smoothly on every data update
    updateTriggers: {
      getPosition: [layerData],
      getFillColor: [layerData],
    },
  });
}

// ─── Exported: Wind Compass Data ─────────────────────────────────────────────

/**
 * Compute the dominant (median) wind direction and average speed for a set of stations.
 * Uses circular mean for direction.
 */
export function computeWindSummary(stations: WindStation[]): {
  direction: number;
  speed: number;
  label: string;
} {
  if (!stations || stations.length === 0) {
    return { direction: 0, speed: 0, label: 'Calm' };
  }

  const validStations = stations.filter(s => s.wind_speed !== undefined && s.wind_speed > 0.1);
  if (validStations.length === 0) {
    return { direction: 0, speed: 0, label: 'Calm' };
  }

  let sinSum = 0, cosSum = 0, speedSum = 0;
  for (const s of validStations) {
    const dirRad = ((s.wind_dir || 0) * Math.PI) / 180;
    sinSum += Math.sin(dirRad);
    cosSum += Math.cos(dirRad);
    speedSum += s.wind_speed || 0;
  }

  const avgDir = ((Math.atan2(sinSum / validStations.length, cosSum / validStations.length) * 180) / Math.PI + 360) % 360;
  const avgSpeed = Math.round((speedSum / validStations.length) * 10) / 10;

  // Cardinal direction label
  const cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const label = cardinals[Math.round(avgDir / 22.5) % 16];

  return { direction: avgDir, speed: avgSpeed, label };
}

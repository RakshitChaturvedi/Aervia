'use client';
import React, { useState, useMemo, useCallback } from 'react';
import { getAqiCategory } from '@/utils/aqi';
import { Station, RecommendedDeployment, AqiStandard } from '@/types';
import { computeDelhiDistricts, District } from '@/data/delhiDistricts';
import { computeHyderabadDistricts, computeGuwahatiDistricts, computeBengaluruDistricts } from '@/data/otherDistricts';
import { createWindArrowLayers, useWindParticles, computeWindSummary } from './WindLayer';
import { useCityContext } from '@/context/CityContext';


export interface HexDataPoint {
  lat: number;
  lon: number;
  aqi: number;
  pm25: number;
}

// deck.gl imports
import DeckGL from '@deck.gl/react';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ColumnLayer, PolygonLayer, ScatterplotLayer, TextLayer, BitmapLayer } from '@deck.gl/layers';

const CITY_CENTERS: Record<string, {longitude: number, latitude: number, zoom: number}> = {
  'Delhi': { longitude: 77.17, latitude: 28.62, zoom: 11 },
  'Mumbai': { longitude: 72.85, latitude: 19.08, zoom: 11 },
  'Bengaluru': { longitude: 77.59, latitude: 12.97, zoom: 11 },
  'Hyderabad': { longitude: 78.44, latitude: 17.42, zoom: 11 },
  'Guwahati': { longitude: 91.73, latitude: 26.16, zoom: 11.5 },
  'Chennai': { longitude: 80.27, latitude: 13.08, zoom: 11 },
  'Kolkata': { longitude: 88.36, latitude: 22.57, zoom: 11 },
  'Pune': { longitude: 73.85, latitude: 18.52, zoom: 11 },
  'Ahmedabad': { longitude: 72.57, latitude: 23.02, zoom: 11 },
  'Jaipur': { longitude: 75.78, latitude: 26.91, zoom: 11 },
  'Lucknow': { longitude: 80.94, latitude: 26.84, zoom: 11 },
  'Chandigarh': { longitude: 76.77, latitude: 30.73, zoom: 11.5 },
  'Thiruvananthapuram': { longitude: 76.93, latitude: 8.52, zoom: 11.5 },
  'Kanpur': { longitude: 80.33, latitude: 26.44, zoom: 11 },
  'Nagpur': { longitude: 79.08, latitude: 21.14, zoom: 11 },
  'Indore': { longitude: 75.85, latitude: 22.71, zoom: 11 },
  'Bhopal': { longitude: 77.41, latitude: 23.25, zoom: 11 },
  'Patna': { longitude: 85.13, latitude: 25.59, zoom: 11 },
};

// Bounding boxes for satellite NO₂ overlay: [west, south, east, north]
const CITY_SATELLITE_BOUNDS: Record<string, [number, number, number, number]> = {
  'Delhi':     [76.84, 28.40, 77.35, 28.88],
  'Hyderabad': [78.20, 17.20, 78.65, 17.60],
  'Bengaluru': [77.40, 12.80, 77.80, 13.15],
};

// Cache-busting: refresh satellite image every hour
const getSatelliteHourKey = () => Math.floor(Date.now() / 3600000);


const getInitialViewState = (city: string, userCoords?: { lat: number, lon: number } | null) => {
  if (city === 'My Location' && userCoords) {
    return {
      longitude: userCoords.lon,
      latitude: userCoords.lat,
      zoom: 12,
      pitch: 55,
      bearing: -20,
      minZoom: 9,
      maxZoom: 15,
    };
  }
  const center = CITY_CENTERS[city] || CITY_CENTERS['Delhi'];
  return {
    longitude: center.longitude,
    latitude: center.latitude,
    zoom: center.zoom,
    pitch: 55,
    bearing: -20,
    minZoom: 9,
    maxZoom: 15,
  };
};

// AQI → Color mapping with reduced alpha for translucent overlay
function aqiToColor(aqi: number, alpha: number = 120): [number, number, number, number] {
  if (aqi <= 50)  return [34, 197, 94, alpha];      // green
  if (aqi <= 100) return [132, 204, 22, alpha];      // lime
  if (aqi <= 150) return [234, 179, 8, alpha];       // yellow
  if (aqi <= 200) return [245, 158, 11, alpha];      // amber
  if (aqi <= 250) return [249, 115, 22, alpha];      // orange
  if (aqi <= 300) return [239, 68, 68, alpha];       // red
  if (aqi <= 400) return [220, 38, 38, alpha];       // dark red
  return [185, 28, 28, alpha];                       // deep red
}

function aqiToHeight(aqi: number): number {
  return Math.max(50, aqi * 15);
}

function isDeployed(d: Station): boolean {
  return d.source === 'deployed' || d.source === 'iot';
}

function pointInPolygon(lon: number, lat: number, polygon: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersect = ((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function distKm(lon1: number, lat1: number, lon2: number, lat2: number): number {
  const dx = (lon1 - lon2) * 85;
  const dy = (lat1 - lat2) * 111;
  return Math.sqrt(dx * dx + dy * dy);
}

function nearestDistKm(lon: number, lat: number, points: { lon: number; lat: number }[]): number {
  let min = Infinity;
  for (const p of points) {
    const d = distKm(lon, lat, p.lon, p.lat);
    if (d < min) min = d;
  }
  return min;
}

/** Stable 0–1 hash so pins stay put across re-renders but differ per district. */
function districtSeed(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

/** Keep the pin in-district but offset from CAAQMS in a per-district direction. */
function offsetInsideDistrict(
  district: District,
  avoid: { lon: number; lat: number }[],
  minSepKm = 0.5
): [number, number] {
  const [cLon, cLat] = district.centroid;
  const polygon = district.polygon;
  const seedA = districtSeed(district.id);
  const seedB = districtSeed(`${district.id}:${district.name}`);
  const seedC = districtSeed(`${district.name}|${district.id}`);

  const isClear = (lon: number, lat: number) =>
    pointInPolygon(lon, lat, polygon) && nearestDistKm(lon, lat, avoid) >= minSepKm;

  const preferredAngle = seedA * Math.PI * 2;
  const preferredKm = 0.35 + seedB * 1.25; // 0.35–1.6 km
  const jitter = (seedC - 0.5) * 0.35;

  const dirs: [number, number][] = [];
  for (let a = 0; a < 18; a++) {
    const rad = preferredAngle + jitter + (a / 18) * Math.PI * 2;
    dirs.push([Math.cos(rad), Math.sin(rad)]);
  }

  const steps = [preferredKm, preferredKm * 0.65, preferredKm * 1.2, 0.45, 0.75, 1.05, 1.4];
  for (const stepKm of steps) {
    for (const [ux, uy] of dirs) {
      const lon = cLon + (ux * stepKm) / 85;
      const lat = cLat + (uy * stepKm) / 111;
      if (isClear(lon, lat)) return [lon, lat];
    }
  }

  if (isClear(cLon, cLat)) return [cLon, cLat];

  let best: [number, number] = [cLon, cLat];
  let bestScore = nearestDistKm(cLon, cLat, avoid);
  for (const stepKm of [0.3, 0.55, 0.85, 1.2]) {
    for (const [ux, uy] of dirs) {
      const lon = cLon + (ux * stepKm) / 85;
      const lat = cLat + (uy * stepKm) / 111;
      if (!pointInPolygon(lon, lat, polygon)) continue;
      const score = nearestDistKm(lon, lat, avoid);
      if (score > bestScore) {
        bestScore = score;
        best = [lon, lat];
      }
    }
  }
  return best;
}

export default function CityMap({ 
  alertStation, 
  city = 'Delhi', 
  userCoords, 
  liveData, 
  cityData,
  liveLoading,
  onHover,
  onClick,
  selectedDistrictId,
  onDistrictsComputed,
  monitoringLocation,
  recommendedDeployments = [],
}: { 
  alertStation?: Station | null, 
  city?: string, 
  userCoords?: { lat: number, lon: number } | null, 
  liveData?: any, 
  cityData?: any,
  liveLoading?: boolean,
  onHover?: (data: any) => void,
  onClick?: (data: any) => void,
  selectedDistrictId?: string | null,
  onDistrictsComputed?: (districts: any[]) => void,
  monitoringLocation?: { lat: number; lon: number; name?: string } | null;
  recommendedDeployments?: RecommendedDeployment[];
}) {
  const { aqiStandard, setAqiStandard } = useCityContext();
  const [hoveredHex, setHoveredHex] = useState<HexDataPoint | null>(null);
  const [hoveredDistrict, setHoveredDistrict] = useState<District | null>(null);
  const [hoveredStation, setHoveredStation] = useState<Station | null>(null);
  const [hoveredRecommended, setHoveredRecommended] = useState<any | null>(null);
  const [viewState, setViewState] = useState<any>(getInitialViewState(city, userCoords));
  const [showSatellite, setShowSatellite] = useState(false);
  const [showWind, setShowWind] = useState(false);

  const stations = useMemo(() => {
    if (city === 'My Location' && liveData) {
      return [{
        id: 'USER_GPS',
        name: 'My Location',
        lat: userCoords?.lat ?? 0,
        lon: userCoords?.lon ?? 0,
        pm25: liveData.reading.pm25,
        pm10: liveData.reading.pm10,
        no2: 40, so2: 12, co: 1.5, o3: 30,
        aqi: liveData.live_aqi,
        source: 'deployed' as const,
        status: 'online' as const
      }];
    }
    return cityData ? cityData.stations : [];
  }, [city, liveData, cityData, userCoords]);

  // Wind animation layers (must be after stations is defined)
  const windArrowLayers = useMemo(() => createWindArrowLayers(stations, showWind), [stations, showWind]);
  const windParticleLayer = useWindParticles(stations, showWind, city);
  const windSummary = useMemo(() => computeWindSummary(stations), [stations]);

  const dynamicDistricts = useMemo(() => {
    if (city === 'Delhi') return computeDelhiDistricts(stations, aqiStandard);
    if (city === 'Hyderabad') return computeHyderabadDistricts(stations, aqiStandard);
    if (city === 'Guwahati') return computeGuwahatiDistricts(stations, aqiStandard);
    if (city === 'Bengaluru') return computeBengaluruDistricts(stations, aqiStandard);
    return [];
  }, [city, stations, aqiStandard]);

  const recommendedPins = useMemo(() => {
    if (!recommendedDeployments.length) return [];
    const placed: { lon: number; lat: number }[] = [];
    const avoidBase = [...stations];
    return recommendedDeployments.map((rec) => {
      const district = dynamicDistricts.find((d) => d.id === rec.districtId);
      if (!district) return null;
      const [lon, lat] = offsetInsideDistrict(district, [...avoidBase, ...placed], 0.45);
      placed.push({ lon, lat });
      return {
        ...rec,
        lat,
        lon,
        aqi: rec.aqi || district.aqi,
        pm25: district.pm25,
        pm10: district.pm10,
        no2: district.no2,
        so2: district.so2,
        co: district.co,
        o3: district.o3,
      };
    }).filter(Boolean) as any[];
  }, [recommendedDeployments, dynamicDistricts, stations]);

  React.useEffect(() => {
    if (onDistrictsComputed) {
      onDistrictsComputed(dynamicDistricts);
    }
  }, [dynamicDistricts, onDistrictsComputed]);

  const hexGrid = useMemo(() => {
    if (city === 'My Location' && liveData) {
      return liveData.hex_grid;
    }
    return cityData ? cityData.stations : [];
  }, [city, liveData, cityData]);

  // Track whether this is the first render (skip zoom-out animation on mount)
  const isInitialRender = React.useRef(true);
  const cityTransitionTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Handle fly-to on city or coords change — two-phase zoom-out → zoom-in
  React.useEffect(() => {
    // Clear any pending phase-2 timer from a previous rapid switch
    if (cityTransitionTimer.current) {
      clearTimeout(cityTransitionTimer.current);
      cityTransitionTimer.current = null;
    }

    const target = getInitialViewState(city, userCoords);

    if (isInitialRender.current) {
      // First render: jump directly, no animation
      isInitialRender.current = false;
      setViewState((prev: any) => ({ ...prev, ...target }));
      return;
    }

    // Single-phase direct transition to target city coordinates
    setViewState({
      ...target,
      transitionDuration: 1200,
    });

    return () => {};
  }, [city, userCoords]);

  // Handle fly-to on alert
  React.useEffect(() => {
    if (!alertStation) return;
    setViewState((prev: any) => ({
      ...prev,
      longitude: alertStation.lon,
      latitude: alertStation.lat,
      zoom: 13,
      pitch: 45,
      bearing: -15,
      transitionDuration: 1500,
    }));
  }, [alertStation, city]);

  // Handle camera restoration when Deep Dive panel is dismissed (selectedDistrictId becomes null)
  const prevSelectedDistrictId = React.useRef<string | null | undefined>(selectedDistrictId);
  React.useEffect(() => {
    if (prevSelectedDistrictId.current && !selectedDistrictId) {
      const target = getInitialViewState(city, userCoords);
      setViewState((prev: any) => ({
        ...prev,
        longitude: target.longitude,
        latitude: target.latitude,
        zoom: target.zoom,
        pitch: target.pitch,       // 55 deg slanted 3D perspective
        bearing: target.bearing,   // -20 deg
        transitionDuration: 1200,
      }));
    }
    prevSelectedDistrictId.current = selectedDistrictId;
  }, [selectedDistrictId, city, userCoords]);

  // Build deck.gl layers
  const layers = useMemo(() => {
    // Layer 0: Live NO₂ satellite overlay (from Open-Meteo CAMS via backend)
    const satelliteBounds = CITY_SATELLITE_BOUNDS[city];
    const satelliteLayer = new BitmapLayer({
      id: `sentinel-no2-layer-${city}`,
      bounds: satelliteBounds || [76.84, 28.40, 77.35, 28.88],
      image: satelliteBounds
        ? `http://127.0.0.1:8000/api/satellite/no2?city=${encodeURIComponent(city)}&t=${getSatelliteHourKey()}`
        : '/sentinel_no2.png',
      transparentColor: [0, 0, 0, 0],
      opacity: showSatellite && satelliteBounds ? 0.7 : 0,
      transitions: { opacity: 500 }
    });

    // Layer 1: 3D Hexagonal Columns (fallback for cities without districts)
    const columnLayer = new ColumnLayer<HexDataPoint>({
      id: 'aqi-columns',
      data: dynamicDistricts.length === 0 ? hexGrid : [],
      diskResolution: 6,           // 6 sides = hexagon
      radius: 900,                 // hex radius in meters
      extruded: true,
      pickable: true,
      elevationScale: 1,
      getPosition: (d: HexDataPoint) => [d.lon, d.lat],
      getFillColor: (d: HexDataPoint) => aqiToColor(d.aqi, 220),
      getElevation: (d: HexDataPoint) => aqiToHeight(d.aqi),
      material: {
        ambient: 0.45,
        diffuse: 0.6,
        shininess: 40,
        specularColor: [60, 64, 70],
      },
      transitions: {
        getElevation: { duration: 800 },
        getFillColor: { duration: 800 },
      },
      onHover: (info: any) => setHoveredHex(info.object || null),
      onClick: (info: any) => {
        if (info.object && onClick) {
          onClick({ ...info.object, type: 'District' });
          setViewState((prev: any) => ({
            ...prev,
            longitude: info.object.lon,
            latitude: info.object.lat,
            zoom: 12,
            pitch: 50,
            bearing: -20,
            transitionDuration: 1200,
          }));
        } else if (!info.object && onClick) {
          onClick(null); // Clear selection when clicking off
          const target = getInitialViewState(city, userCoords);
          setViewState((prev: any) => ({
            ...prev,
            longitude: target.longitude,
            latitude: target.latitude,
            zoom: target.zoom,
            pitch: target.pitch,
            bearing: target.bearing,
            transitionDuration: 1200,
          }));
        }
      },
    });

    // Layer 1: District boundary polygons
    const districtLayer = new PolygonLayer<District>({
      id: 'district-polygons',
      data: dynamicDistricts,
      pickable: true,
      stroked: true,
      filled: true,
      extruded: false,
      wireframe: false,
      lineWidthMinPixels: 1.5,
      getPolygon: (d: District) => d.polygon,
      getFillColor: (d: District) => {
        const isSelected = selectedDistrictId === d.id;
        const isHovered = hoveredDistrict && hoveredDistrict.id === d.id;
        
        // Districts without an active CAAQMS center render in neutral slate-grey
        if (!d.monitored || d.aqi == null) {
          return [71, 85, 105, isHovered ? 75 : 35];
        }
        
        // Dim unselected districts if a selection exists
        let alpha = 50;
        if (selectedDistrictId && !isSelected) {
          alpha = 10; // dim drastically
        } else if (isHovered || isSelected) {
          alpha = 90; // bright for hover or selected
        }
        
        const val = aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi ?? 0) : (d.aqi_in ?? d.aqi ?? 0);
        return aqiToColor(val, alpha);
      },
      getLineColor: (d: District) => {
        const isSelected = selectedDistrictId === d.id;
        if (isSelected) return [255, 255, 255, 240];
        if (!d.monitored || d.aqi == null) return [100, 116, 139, 130]; // Clean slate-grey border
        return [59, 130, 246, 180]; // Vibrant cyan/blue for active CAAQMS wards
      },
      getLineWidth: (d: District) => (selectedDistrictId === d.id ? 4 : d.monitored ? 2 : 1.5),
      updateTriggers: {
        getFillColor: [hoveredDistrict?.id, selectedDistrictId, aqiStandard],
        getLineColor: [selectedDistrictId, aqiStandard],
        getLineWidth: [selectedDistrictId],
      },
      onHover: (info: any) => setHoveredDistrict(info.object || null),
      onClick: (info: any) => {
        if (info.object && onClick) {
          onClick({ ...info.object, type: 'District' });
          setViewState((prev: any) => ({
            ...prev,
            longitude: info.object.centroid[0],
            latitude: info.object.centroid[1],
            zoom: 12,
            pitch: 50,
            bearing: -20,
            transitionDuration: 1200,
          }));
        } else if (!info.object && onClick) {
          onClick(null);
          const target = getInitialViewState(city, userCoords);
          setViewState((prev: any) => ({
            ...prev,
            longitude: target.longitude,
            latitude: target.latitude,
            zoom: target.zoom,
            pitch: target.pitch,
            bearing: target.bearing,
            transitionDuration: 1200,
          }));
        }
      },
      transitions: {
        getFillColor: { duration: 400 },
      },
    });

    // Authentic physical CAAQMS stations
    const caaqmsStations = stations.filter((s: Station) => s.monitored !== false);

    // Layer 2: Station glow rings (authentic CAAQMS)
    const stationGlowLayer = new ScatterplotLayer<Station>({
      id: 'station-glow',
      data: caaqmsStations,
      pickable: false,
      opacity: 0.25,
      stroked: false,
      filled: true,
      radiusMinPixels: 6,
      radiusMaxPixels: 16,
      getPosition: (d: Station) => [d.lon, d.lat],
      getFillColor: (d: Station) => {
        const val = aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi ?? 60) : (d.aqi_in ?? d.aqi ?? 60);
        const c = aqiToColor(val, 220);
        return [c[0], c[1], c[2], 50];
      },
      getRadius: 200,
      updateTriggers: {
        getFillColor: [aqiStandard],
      },
    });

    // Layer 3: Clean, crisp station markers
    const stationDotLayer = new ScatterplotLayer<Station>({
      id: 'station-dots',
      data: caaqmsStations,
      pickable: true,
      opacity: 1,
      stroked: true,
      filled: true,
      radiusMinPixels: 4,
      radiusMaxPixels: 8,
      lineWidthMinPixels: 1.5,
      getPosition: (d: Station) => [d.lon, d.lat],
      getFillColor: (d: Station) => {
        const val = aqiStandard === 'US_EPA' ? (d.aqi_us ?? d.aqi ?? 60) : (d.aqi_in ?? d.aqi ?? 60);
        return aqiToColor(val, 240);
      },
      getLineColor: [255, 255, 255, 220] as [number, number, number, number],
      getRadius: 160,
      updateTriggers: {
        getFillColor: [aqiStandard],
      },
      onHover: (info: any) => setHoveredStation(info.object || null),
    });

    // Layer 5: Alert pulse ring
    const alertLayers: any[] = [];
    if (alertStation) {
      alertLayers.push(
        new ScatterplotLayer({
          id: 'alert-pulse',
          data: [alertStation],
          pickable: false,
          opacity: 0.5,
          stroked: true,
          filled: false,
          radiusMinPixels: 20,
          radiusMaxPixels: 50,
          lineWidthMinPixels: 2,
          getPosition: (d: any) => [d.lon, d.lat],
          getLineColor: [248, 81, 73, 200],
          getRadius: 800,
        })
      );
    }

    // Layer 6: Single Blue Portable IoT Sensor Deployment Marker
    const monitoringLayers: any[] = [];
    if (monitoringLocation) {
      monitoringLayers.push(
        new ScatterplotLayer({
          id: 'monitoring-deployment-marker',
          data: [monitoringLocation],
          pickable: true,
          opacity: 0.9,
          stroked: true,
          filled: true,
          radiusMinPixels: 9,
          radiusMaxPixels: 15,
          lineWidthMinPixels: 3,
          getPosition: (d: any) => [d.lon, d.lat],
          getFillColor: [59, 130, 246, 240],
          getLineColor: [255, 255, 255, 255],
          getRadius: 400,
        }),
        new TextLayer({
          id: 'monitoring-deployment-label',
          data: [monitoringLocation],
          pickable: false,
          getPosition: (d: any) => [d.lon, d.lat],
          getText: (d: any) => `📡 Deploy Sensor: ${d.name || ''}`,
          getSize: 12,
          getColor: [59, 130, 246, 255],
          getTextAnchor: 'middle' as const,
          getAlignmentBaseline: 'bottom' as const,
          getPixelOffset: [0, -18],
          fontFamily: 'Inter, system-ui, sans-serif',
          fontWeight: 700,
          outlineWidth: 3,
          outlineColor: [6, 8, 15, 240],
          billboard: true,
        })
      );
    }

    const recommendedLayers: any[] = [];
    if (recommendedPins.length > 0) {
      recommendedLayers.push(
        new ScatterplotLayer({
          id: 'recommended-glow',
          data: recommendedPins,
          pickable: false,
          opacity: 0.4,
          stroked: false,
          filled: true,
          radiusMinPixels: 14,
          radiusMaxPixels: 32,
          getPosition: (d: any) => [d.lon, d.lat],
          getFillColor: [251, 191, 36, 90],
          getRadius: 650,
        }),
        new ScatterplotLayer({
          id: 'recommended-dots',
          data: recommendedPins,
          pickable: true,
          opacity: 1,
          stroked: true,
          filled: true,
          radiusMinPixels: 7,
          radiusMaxPixels: 14,
          lineWidthMinPixels: 2,
          getPosition: (d: any) => [d.lon, d.lat],
          getFillColor: [251, 191, 36, 255],
          getLineColor: [255, 255, 255, 200],
          getRadius: 420,
          onHover: (info: any) => {
            setHoveredRecommended(info.object || null);
            if (info.object) {
              setHoveredStation(null);
              setHoveredDistrict(null);
            }
          },
        }),
        new TextLayer({
          id: 'recommended-labels',
          data: recommendedPins,
          pickable: false,
          getPosition: (d: any) => [d.lon, d.lat],
          getText: (d: any) => `Recommend\n${d.name}`,
          getSize: 7.5,
          getColor: [251, 191, 36, 255],
          getTextAnchor: 'middle' as const,
          getAlignmentBaseline: 'bottom' as const,
          getPixelOffset: [0, -14],
          lineHeight: 1.15,
          fontFamily: 'Inter, system-ui, sans-serif',
          fontWeight: 700,
          outlineWidth: 2,
          outlineColor: [6, 8, 15, 220],
          billboard: true,
        })
      );
    }

    // Wind animation layers
    const windLayers: any[] = [];
    if (showWind) {
      windLayers.push(...windArrowLayers);
      if (windParticleLayer) windLayers.push(windParticleLayer);
    }

    if (dynamicDistricts.length > 0) {
      return [satelliteLayer, districtLayer, stationGlowLayer, stationDotLayer, ...alertLayers, ...monitoringLayers, ...windLayers];
    } else {
      return [satelliteLayer, columnLayer, stationGlowLayer, stationDotLayer, ...alertLayers, ...monitoringLayers, ...windLayers];
    }
  }, [alertStation, stations, hexGrid, city, hoveredDistrict, dynamicDistricts, showSatellite, monitoringLocation, selectedDistrictId, showWind, windArrowLayers, windParticleLayer, aqiStandard]);

  const onViewStateChange = useCallback(({ viewState: vs }: any) => {
    setViewState(vs);
  }, []);

  // Build tooltip data — prefer a hovered physical CAAQMS pin over the district fill
  const tooltipData = hoveredStation
    ? {
          name: hoveredStation.name,
          aqi: Math.round(aqiStandard === 'US_EPA' ? (hoveredStation.aqi_us ?? hoveredStation.aqi ?? 0) : (hoveredStation.aqi_in ?? hoveredStation.aqi ?? 0)),
          pm25: hoveredStation.pm25,
          pm10: hoveredStation.pm10,
          no2: hoveredStation.no2,
          so2: hoveredStation.so2,
          co: hoveredStation.co,
          o3: hoveredStation.o3,
          temp: (hoveredStation as any).temp,
          humidity: (hoveredStation as any).humidity,
          pressure: (hoveredStation as any).pressure,
          wind_speed: (hoveredStation as any).wind_speed,
          pblh: (hoveredStation as any).pblh,
          type: isDeployed(hoveredStation) ? 'Deployed Sensor' : 'CAAQMS Station',
        }
    : hoveredDistrict
    ? {
        name: hoveredDistrict.name,
        aqi: hoveredDistrict.aqi != null ? Math.round(aqiStandard === 'US_EPA' ? (hoveredDistrict.aqi_us ?? hoveredDistrict.aqi) : (hoveredDistrict.aqi_in ?? hoveredDistrict.aqi)) : null,
        aqi_in: hoveredDistrict.aqi_in,
        aqi_us: hoveredDistrict.aqi_us,
        pm25: hoveredDistrict.pm25,
        pm10: hoveredDistrict.pm10,
        no2: hoveredDistrict.no2,
        so2: hoveredDistrict.so2,
        co: hoveredDistrict.co,
        o3: hoveredDistrict.o3,
        temp: hoveredDistrict.temp,
        humidity: hoveredDistrict.humidity,
        pressure: hoveredDistrict.pressure,
        wind_speed: hoveredDistrict.wind_speed,
        pblh: hoveredDistrict.pblh,
        type: 'Municipal Ward',
        monitored: hoveredDistrict.monitored,
        station_name: hoveredDistrict.station_name,
        agency: hoveredDistrict.agency,
        reference_station: hoveredDistrict.reference_station,
        reference_distance_km: hoveredDistrict.reference_distance_km,
        reference_aqi_in: hoveredDistrict.reference_aqi_in,
        reference_aqi_us: hoveredDistrict.reference_aqi_us,
        primary_pollutant: hoveredDistrict.primary_pollutant,
      }
      : null;

  const tooltipCat = (tooltipData && typeof tooltipData.aqi === 'number') ? getAqiCategory(tooltipData.aqi, aqiStandard) : null;


  React.useEffect(() => {
    if (onHover) {
      onHover(tooltipData);
    }
  }, [tooltipData, onHover]);

  return (
    <div className="map-container" style={{ position: 'relative', background: '#080c14' }}>
      <DeckGL
        viewState={viewState}
        onViewStateChange={onViewStateChange}
        controller={true}
        layers={layers}
        style={{ width: '100%', height: '100%' }}
        getTooltip={() => null}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        />
      </DeckGL>

      {/* Overlay Stats & Controls */}
      <div className="map-overlay-stats" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {/* Standard Toggle: India NAQI vs US EPA */}
        <div style={{
          display: 'flex',
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          borderRadius: 6,
          border: '1px solid var(--border-primary)',
          overflow: 'hidden',
          padding: 2,
        }}>
          <button
            onClick={() => setAqiStandard('IN_NAQI')}
            style={{
              padding: '4px 9px',
              fontSize: '0.65rem',
              fontWeight: 700,
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              background: aqiStandard === 'IN_NAQI' ? '#3b82f6' : 'transparent',
              color: aqiStandard === 'IN_NAQI' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s',
            }}
          >
            🇮🇳 India NAQI
          </button>
          <button
            onClick={() => setAqiStandard('US_EPA')}
            style={{
              padding: '4px 9px',
              fontSize: '0.65rem',
              fontWeight: 700,
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              background: aqiStandard === 'US_EPA' ? '#3b82f6' : 'transparent',
              color: aqiStandard === 'US_EPA' ? '#ffffff' : 'var(--text-muted)',
              transition: 'all 0.2s',
            }}
          >
            🇺🇸 US EPA
          </button>
        </div>

        {CITY_SATELLITE_BOUNDS[city] && (
          <button 
            className={`map-stat-chip ${showSatellite ? 'active' : ''}`}
            onClick={() => setShowSatellite(!showSatellite)}
            style={{ 
              cursor: 'pointer', 
              border: showSatellite ? '1px solid var(--accent-cyan)' : '1px solid var(--border-primary)',
              background: showSatellite ? 'rgba(57,210,192,0.1)' : 'var(--bg-secondary)'
            }}
          >
            CAMS NO₂ Overlay: <span className="chip-value" style={{ color: showSatellite ? 'var(--accent-cyan)' : 'inherit' }}>{showSatellite ? 'ON' : 'OFF'}</span>
          </button>
        )}
        <button 
          className={`map-stat-chip ${showWind ? 'active' : ''}`}
          onClick={() => setShowWind(!showWind)}
          style={{ 
            cursor: 'pointer', 
            border: showWind ? '1px solid rgba(200,220,255,0.6)' : '1px solid var(--border-primary)',
            background: showWind ? 'rgba(200,220,255,0.1)' : 'var(--bg-secondary)'
          }}
        >
          🌬️ Wind Flow: <span className="chip-value" style={{ color: showWind ? 'rgba(200,220,255,0.95)' : 'inherit' }}>{showWind ? 'ON' : 'OFF'}</span>
        </button>
        <div className="map-stat-chip">
          Stations Online: <span className="chip-value">{stations.filter((s: Station) => s.monitored !== false && s.status !== 'offline').length}</span>
        </div>
        <div className="map-stat-chip">
          Alerts Active: <span className="chip-value" style={{ color: 'var(--accent-red)' }}>{stations.filter((s: Station) => s.monitored !== false && s.status === 'alert').length}</span>
        </div>
        <div className="map-stat-chip">
          {dynamicDistricts.length > 0 ? (
            <>Districts: <span className="chip-value" style={{ color: 'var(--accent-cyan)' }}>{dynamicDistricts.length}</span></>
          ) : (
            <>Hex Cells: <span className="chip-value" style={{ color: 'var(--accent-cyan)' }}>{hexGrid.length}</span></>
          )}
        </div>
      </div>

      {/* Dual Standard AQI Color Legend */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 5,
        background: 'var(--bg-surface)', backdropFilter: 'blur(12px)',
        border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
        padding: '9px 14px', minWidth: 260
      }}>
        <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
          {aqiStandard === 'IN_NAQI' ? '🇮🇳 CPCB India NAQI Standard Scale' : '🇺🇸 US EPA Standard Scale'}
        </div>
        {aqiStandard === 'IN_NAQI' ? (
          <>
            <div style={{ display: 'flex', height: 8, borderRadius: 3, overflow: 'hidden', position: 'relative' }}>
              <div style={{ width: '10%', background: '#22c55e' }} title="Good (0-50)" />
              <div style={{ width: '10%', background: '#84cc16' }} title="Satisfactory (51-100)" />
              <div style={{ width: '20%', background: '#f59e0b' }} title="Moderate (101-200)" />
              <div style={{ width: '20%', background: '#f97316' }} title="Poor (201-300)" />
              <div style={{ width: '20%', background: '#ef4444' }} title="Very Poor (301-400)" />
              <div style={{ width: '20%', background: '#dc2626' }} title="Severe (401-500+)" />
            </div>
            <div style={{ position: 'relative', height: 16, marginTop: 4, fontSize: '0.55rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              <span style={{ position: 'absolute', left: '0%' }}>0</span>
              <span style={{ position: 'absolute', left: '10%', transform: 'translateX(-50%)' }}>50</span>
              <span style={{ position: 'absolute', left: '20%', transform: 'translateX(-50%)' }}>100</span>
              <span style={{ position: 'absolute', left: '40%', transform: 'translateX(-50%)' }}>200</span>
              <span style={{ position: 'absolute', left: '60%', transform: 'translateX(-50%)' }}>300</span>
              <span style={{ position: 'absolute', left: '80%', transform: 'translateX(-50%)' }}>400</span>
              <span style={{ position: 'absolute', right: '0%', textAlign: 'right' }}>500+</span>
            </div>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', height: 8, borderRadius: 3, overflow: 'hidden', position: 'relative' }}>
              <div style={{ width: '10%', background: '#22c55e' }} title="Good (0-50)" />
              <div style={{ width: '10%', background: '#84cc16' }} title="Moderate (51-100)" />
              <div style={{ width: '10%', background: '#f59e0b' }} title="USG (101-150)" />
              <div style={{ width: '10%', background: '#f97316' }} title="Unhealthy (151-200)" />
              <div style={{ width: '20%', background: '#ef4444' }} title="Very Unhealthy (201-300)" />
              <div style={{ width: '40%', background: '#7e22ce' }} title="Hazardous (301-500+)" />
            </div>
            <div style={{ position: 'relative', height: 16, marginTop: 4, fontSize: '0.55rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              <span style={{ position: 'absolute', left: '0%' }}>0</span>
              <span style={{ position: 'absolute', left: '10%', transform: 'translateX(-50%)' }}>50</span>
              <span style={{ position: 'absolute', left: '20%', transform: 'translateX(-50%)' }}>100</span>
              <span style={{ position: 'absolute', left: '30%', transform: 'translateX(-50%)' }}>150</span>
              <span style={{ position: 'absolute', left: '40%', transform: 'translateX(-50%)' }}>200</span>
              <span style={{ position: 'absolute', left: '60%', transform: 'translateX(-50%)' }}>300</span>
              <span style={{ position: 'absolute', right: '0%', textAlign: 'right' }}>500+</span>
            </div>
          </>
        )}
      </div>


      {/* Wind Compass Legend */}
      {showWind && windSummary.speed > 0 && (
        <div style={{
          position: 'absolute', bottom: 80, left: 12, zIndex: 5,
          background: 'var(--bg-surface)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(200,220,255,0.2)', borderRadius: 'var(--radius-md)',
          padding: '10px 14px', minWidth: 100,
        }}>
          <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
            Wind Direction
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 40, height: 40, borderRadius: '50%',
              border: '1px solid rgba(200,220,255,0.25)',
              background: 'rgba(200,220,255,0.05)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative',
            }}>
              <span style={{ position: 'absolute', top: 1, fontSize: '0.45rem', color: 'rgba(200,220,255,0.5)', fontWeight: 700 }}>N</span>
              <div style={{
                transform: `rotate(${(windSummary.direction + 180) % 360}deg)`,
                transition: 'transform 1s ease',
                fontSize: '1.1rem',
                lineHeight: 1,
                color: 'rgba(200,220,255,0.9)',
              }}>↑</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'rgba(200,220,255,0.9)' }}>
                {windSummary.speed} m/s
              </div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                From {windSummary.label}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Map Legend: Simplified and Authentic */}
      <div className="map-legend" style={{ left: 'auto', right: 12, bottom: 12, gap: '12px' }}>
        <div className="legend-item"><div className="legend-dot" style={{ background: '#3b82f6' }} />Monitored Ward</div>
        <div className="legend-item"><div className="legend-dot" style={{ background: '#64748b' }} />Unmonitored Ward (No Center)</div>
        <div className="legend-item"><div className="legend-dot" style={{ background: '#22c55e', border: '1.5px solid #ffffff', boxShadow: '0 0 6px rgba(34, 197, 94, 0.6)' }} />Active CAAQMS Center (Exact Coords)</div>
      </div>

      {/* Hover tooltip — detailed district/station info */}
      {tooltipData && (
        <div style={{
          position: 'absolute', bottom: 80, right: 12,
          background: 'var(--bg-surface)', backdropFilter: 'blur(14px)',
          border: '1px solid var(--border-primary)', borderRadius: 'var(--radius-md)',
          padding: '12px 16px', zIndex: 10, minWidth: 230, maxWidth: 290,
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}>
          <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 2 }}>{tooltipData.name}</div>
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{tooltipData.type}</div>

          {/* Active CAAQMS vs Unmonitored Ward Representation */}
          {tooltipData.type === 'Municipal Ward' && !tooltipData.monitored ? (
            <div style={{
              background: 'rgba(100, 116, 139, 0.12)',
              border: '1px solid rgba(148, 163, 184, 0.3)',
              borderRadius: 6,
              padding: '10px 12px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8', fontSize: '0.72rem', fontWeight: 700, marginBottom: 6 }}>
                <span>⚪ No Active CAAQMS Center</span>
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', lineHeight: 1.4, marginBottom: 4 }}>
                Nearest Active Center: <strong style={{ color: 'var(--text-primary)' }}>{tooltipData.reference_station || 'Regional Station'}</strong>
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginBottom: 4 }}>
                Distance: <strong style={{ color: 'var(--text-primary)' }}>{tooltipData.reference_distance_km ?? 5.0} km away</strong>
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>
                Nearest Center AQI: <strong style={{ color: '#38bdf8' }}>{aqiStandard === 'IN_NAQI' ? (tooltipData.reference_aqi_in ?? '--') : (tooltipData.reference_aqi_us ?? '--')}</strong> ({aqiStandard === 'IN_NAQI' ? 'India NAQI' : 'US EPA'})
              </div>
            </div>
          ) : (
            <>
              {tooltipData.type === 'Municipal Ward' && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.35)',
                  padding: '4px 8px', borderRadius: 4, marginBottom: 8, fontSize: '0.62rem', color: '#4ade80', fontWeight: 600
                }}>
                  <span>✅ Active CAAQMS: {tooltipData.station_name || tooltipData.name} ({tooltipData.agency || 'CPCB'})</span>
                </div>
              )}

              {/* AQI banner */}
              {tooltipCat && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10,
                  padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                  background: tooltipCat.bg, border: `1px solid ${tooltipCat.color}30`,
                }}>
                  <span style={{ fontSize: '1.3rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: tooltipCat.color }}>{tooltipData.aqi}</span>
                  <div>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: tooltipCat.color }}>{tooltipCat.label}</div>
                    <div style={{ fontSize: '0.55rem', color: 'var(--text-muted)' }}>
                      {aqiStandard === 'IN_NAQI' ? 'India NAQI (CPCB 2014)' : 'US EPA Standard (40 CFR)'}
                    </div>
                    {tooltipData.primary_pollutant && (
                      <div style={{ fontSize: '0.55rem', color: 'var(--accent-cyan)', marginTop: 2 }}>
                        Driver: <strong>{tooltipData.primary_pollutant}</strong>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Pollutant grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4 }}>
                {[
                  { label: 'PM2.5', value: tooltipData.pm25, unit: 'µg/m³' },
                  { label: 'PM10', value: tooltipData.pm10, unit: 'µg/m³' },
                  { label: 'NO₂', value: tooltipData.no2, unit: 'ppb' },
                  { label: 'SO₂', value: tooltipData.so2, unit: 'ppb' },
                  { label: 'CO', value: tooltipData.co, unit: 'mg/m³' },
                  { label: 'O₃', value: tooltipData.o3, unit: 'ppb' },
                ].map((p) => (
                  <div key={p.label} style={{
                    padding: '4px 6px', background: 'var(--bg-elevated)', borderRadius: 4,
                    textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {typeof p.value === 'number' ? (p.value < 10 ? p.value.toFixed(1) : Math.round(p.value)) : p.value || '--'}
                    </div>
                    <div style={{ fontSize: '0.5rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      {p.label} <span style={{ fontSize: '0.42rem', opacity: 0.75 }}>({p.unit})</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

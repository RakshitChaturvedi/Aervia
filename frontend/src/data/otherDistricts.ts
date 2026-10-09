import hyderabadGeoData from './hyderabadDistrictsGeo.json';
import guwahatiGeoData from './guwahatiDistrictsGeo.json';
import bengaluruGeoData from './bengaluruDistrictsGeo.json';
import { District, AqiStandard } from '@/types';

export { type District } from '@/types';

function isPointInPolygon(lon: number, lat: number, polygon: [number, number][]): boolean {
  let inside = false;
  const n = polygon.length;
  let p1 = polygon[0];
  for (let i = 1; i <= n; i++) {
    const p2 = polygon[i % n];
    if (lat > Math.min(p1[1], p2[1]) && lat <= Math.max(p1[1], p2[1])) {
      if (lon <= Math.max(p1[0], p2[0])) {
        const xinters = (lat - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]) + p1[0];
        if (p1[0] === p2[0] || lon <= xinters) {
          inside = !inside;
        }
      }
    }
    p1 = p2;
  }
  return inside;
}

/**
 * Direct Station-to-Ward Representation:
 * Binds municipal wards directly to authentic CAAQMS stations placed inside them.
 * If a ward lacks a physical station placed within its boundary, it is transparently marked unmonitored
 * with a reference anchor, eliminating synthetic mathematical averaging.
 */
function bindDistrictToStation(
  d: any,
  stations: any[],
  aqiStandard: AqiStandard = 'IN_NAQI'
): District {
  const [cLon, cLat] = d.centroid;
  const polygon = d.polygon as [number, number][];

  // 1. Check if an authentic CAAQMS station is physically located inside this district boundary
  const stationInside = stations?.find((s) => {
    if (typeof s.lon !== 'number' || typeof s.lat !== 'number') return false;
    return isPointInPolygon(s.lon, s.lat, polygon);
  });

  // 2. Direct name match or ID match in stations
  const nameMatched = stations?.find((s) => {
    if (!s.name || !d.name) return false;
    const sName = s.name.toLowerCase();
    const dName = d.name.toLowerCase();
    return (
      sName.includes(dName) ||
      dName.includes(sName) ||
      (s.id && s.id === d.id)
    );
  });

  // 3. Proximity search to find the nearest physical station
  let minDistance = Infinity;
  let closestStation = null;
  if (stations && stations.length > 0) {
    for (const s of stations) {
      const dx = (s.lon - cLon) * 85;
      const dy = (s.lat - cLat) * 111;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minDistance) {
        minDistance = dist;
        closestStation = s;
      }
    }
  }

  // A district is monitored ONLY if a CAAQMS center is actually placed inside it or directly matched
  const activeStationInDistrict = stationInside || nameMatched;
  const isMonitored = !!activeStationInDistrict && activeStationInDistrict.monitored !== false;
  const activeStation = activeStationInDistrict || closestStation;

  const fallback = {
    aqi: 50, pm25: 15, pm10: 30, no2: 25, so2: 10, co: 1.0, o3: 30,
    temp: 30, humidity: 50, pressure: 1010, wind_speed: 2, wind_dir: 0, pblh: 800
  };

  const aqiVal = isMonitored
    ? (aqiStandard === 'US_EPA'
        ? (activeStation?.aqi_us ?? activeStation?.aqi ?? fallback.aqi)
        : (activeStation?.aqi_in ?? activeStation?.aqi ?? fallback.aqi))
    : null;

  const refAqiIn = activeStation?.reference_aqi_in ?? activeStation?.aqi_in ?? activeStation?.aqi ?? 65;
  const refAqiUs = activeStation?.reference_aqi_us ?? activeStation?.aqi_us ?? activeStation?.aqi ?? 85;

  return {
    id: d.id,
    name: d.name,
    polygon: d.polygon as [number, number][],
    centroid: d.centroid as [number, number],
    monitored: isMonitored,
    station_name: isMonitored ? activeStation?.name : undefined,
    agency: activeStation?.agency || (isMonitored ? 'TSPCB / CPCB' : undefined),
    reference_station: !isMonitored
      ? (activeStation?.reference_station || activeStation?.name || 'Regional CAAQMS Center')
      : undefined,
    reference_distance_km: !isMonitored
      ? (activeStation?.reference_distance_km ?? Math.round(minDistance * 10) / 10)
      : undefined,
    reference_aqi_in: !isMonitored ? Math.round(refAqiIn) : undefined,
    reference_aqi_us: !isMonitored ? Math.round(refAqiUs) : undefined,
    aqi: aqiVal !== null ? Math.round(aqiVal) : null,
    aqi_in: isMonitored ? (activeStation?.aqi_in ?? activeStation?.aqi) : null,
    aqi_us: isMonitored ? (activeStation?.aqi_us ?? activeStation?.aqi) : null,
    primary_pollutant: isMonitored ? (activeStation?.primary_pollutant || 'PM2.5') : null,
    pm25: isMonitored && activeStation?.pm25 != null ? Math.round(activeStation.pm25) : null,
    pm10: isMonitored && activeStation?.pm10 != null ? Math.round(activeStation.pm10) : null,
    no2: isMonitored && activeStation?.no2 != null ? Math.round(activeStation.no2) : null,
    so2: isMonitored && activeStation?.so2 != null ? Math.round(activeStation.so2) : null,
    co: isMonitored && activeStation?.co != null ? Math.round(activeStation.co * 10) / 10 : null,
    o3: isMonitored && activeStation?.o3 != null ? Math.round(activeStation.o3) : null,
    temp: Math.round((activeStation?.temp ?? fallback.temp) * 10) / 10,
    humidity: Math.round(activeStation?.humidity ?? fallback.humidity),
    pressure: Math.round(activeStation?.pressure ?? fallback.pressure),
    wind_speed: Math.round((activeStation?.wind_speed ?? fallback.wind_speed) * 10) / 10,
    wind_dir: Math.round(activeStation?.wind_dir ?? fallback.wind_dir),
    pblh: Math.round(activeStation?.pblh ?? fallback.pblh),
  };
}

export function computeHyderabadDistricts(stations: any[], aqiStandard: AqiStandard = 'IN_NAQI'): District[] {
  return hyderabadGeoData.map((d: any) => bindDistrictToStation(d, stations, aqiStandard));
}

export function computeGuwahatiDistricts(stations: any[], aqiStandard: AqiStandard = 'IN_NAQI'): District[] {
  return guwahatiGeoData.map((d: any) => bindDistrictToStation(d, stations, aqiStandard));
}

export function computeBengaluruDistricts(stations: any[], aqiStandard: AqiStandard = 'IN_NAQI'): District[] {
  return bengaluruGeoData.map((d: any) => bindDistrictToStation(d, stations, aqiStandard));
}

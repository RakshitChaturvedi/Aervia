/**
 * Delhi NCT Revenue Districts — real boundary polygons from OpenStreetMap.
 * Binds directly to physical DPCC / CPCB CAAQMS stations.
 */
import districtGeoData from './delhiDistrictsGeo.json';
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

function bindDelhiDistrictToStation(
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

  // 2. Direct name or ID match
  const nameMatched = stations?.find(
    (s) =>
      (s.name && s.name.toLowerCase().includes(d.name.toLowerCase())) ||
      (s.id && s.id === d.id) ||
      (d.name && s.name && d.name.toLowerCase().includes(s.name.toLowerCase()))
  );

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

  const activeStationInDistrict = stationInside || nameMatched;
  const isMonitored = !!activeStationInDistrict && activeStationInDistrict.monitored !== false;
  const activeStation = activeStationInDistrict || closestStation;

  const fallback = {
    aqi: 152, pm25: 56, pm10: 142, no2: 38, so2: 12, co: 1.1, o3: 32,
    temp: 29.5, humidity: 42, pressure: 1010, wind_speed: 2.8, wind_dir: 310, pblh: 520
  };

  const aqiVal = isMonitored
    ? (aqiStandard === 'US_EPA'
        ? (activeStation?.aqi_us ?? activeStation?.aqi ?? fallback.aqi)
        : (activeStation?.aqi_in ?? activeStation?.aqi ?? fallback.aqi))
    : null;

  const refAqiIn = activeStation?.reference_aqi_in ?? activeStation?.aqi_in ?? activeStation?.aqi ?? 152;
  const refAqiUs = activeStation?.reference_aqi_us ?? activeStation?.aqi_us ?? activeStation?.aqi ?? 152;

  return {
    id: d.id,
    name: d.name,
    polygon: d.polygon as [number, number][],
    centroid: d.centroid as [number, number],
    monitored: isMonitored,
    station_name: isMonitored ? activeStation?.name : undefined,
    agency: activeStation?.agency || (isMonitored ? 'DPCC / CPCB' : undefined),
    reference_station: !isMonitored
      ? (activeStation?.reference_station || activeStation?.name || 'Delhi Central CAAQMS')
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

export function computeDelhiDistricts(stations: any[], aqiStandard: AqiStandard = 'IN_NAQI'): District[] {
  return districtGeoData.map((d: any) => bindDelhiDistrictToStation(d, stations, aqiStandard));
}

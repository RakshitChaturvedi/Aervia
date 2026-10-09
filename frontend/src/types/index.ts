export interface Station {
  id: string;
  name: string;
  lat: number;
  lon: number;
  pm25?: number | null;
  pm10?: number | null;
  no2?: number | null;
  so2?: number | null;
  co?: number | null;
  o3?: number | null;
  aqi?: number | null;
  aqi_in?: number | null;
  aqi_us?: number | null;
  primary_pollutant?: string | null;
  agency?: string;
  monitored?: boolean;
  reference_station?: string;
  reference_distance_km?: number;
  reference_aqi_in?: number | null;
  reference_aqi_us?: number | null;
  source: string;
  status: string;
  temp?: number;
  humidity?: number;
  pressure?: number;
  wind_speed?: number;
  wind_dir?: number;
  pblh?: number;
  districtName?: string;
}

export interface District {
  id: string;
  name: string;
  polygon: [number, number][]; // closed ring of [lon, lat]
  centroid: [number, number];
  aqi?: number | null;
  aqi_in?: number | null;
  aqi_us?: number | null;
  primary_pollutant?: string | null;
  monitored: boolean;
  station_name?: string;
  agency?: string;
  reference_station?: string;
  reference_distance_km?: number;
  reference_aqi_in?: number | null;
  reference_aqi_us?: number | null;
  pm25?: number | null;
  pm10?: number | null;
  no2?: number | null;
  so2?: number | null;
  co?: number | null;
  o3?: number | null;
  temp?: number;
  humidity?: number;
  pressure?: number;
  wind_speed?: number;
  wind_dir?: number;
  pblh?: number;
}

export type AqiStandard = 'IN_NAQI' | 'US_EPA';

export type CityId = 'Delhi' | 'Hyderabad' | 'Guwahati' | 'Bengaluru' | 'My Location' | string;

export interface RecommendedDeployment {
  districtId: string;
  name: string;
  priorityScore: number;
  dominantSource: 'Traffic' | 'Industrial' | 'Dust';
  reason: string;
  benefit: string;
  rank: number;
  aqi: number;
}


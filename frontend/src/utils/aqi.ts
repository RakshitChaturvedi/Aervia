import { AqiStandard } from '@/types';

export interface AqiBreakdown {
  aqi: number;
  standard: AqiStandard;
  category: {
    label: string;
    color: string;
    bg: string;
    description: string;
  };
  governingPollutant: 'PM2.5' | 'PM10';
  pm25SubIndex: number;
  pm10SubIndex: number;
}

export function getAqiCategory(aqi: number, standard: AqiStandard = 'IN_NAQI'): { label: string; category: string; color: string; bg: string; description: string } {
  if (standard === 'IN_NAQI') {
    // Official CPCB 2014 Categories: Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500+)
    if (aqi <= 50)  return { label: 'Good', category: 'Good', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', description: 'Minimal health impact; clean outdoor air.' };
    if (aqi <= 100) return { label: 'Satisfactory', category: 'Satisfactory', color: '#84cc16', bg: 'rgba(132, 204, 22, 0.15)', description: 'Minor breathing discomfort to sensitive individuals.' };
    if (aqi <= 200) return { label: 'Moderate', category: 'Moderate', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', description: 'Breathing discomfort to people with asthma and heart conditions.' };
    if (aqi <= 300) return { label: 'Poor', category: 'Poor', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)', description: 'Breathing discomfort to most people on prolonged exposure.' };
    if (aqi <= 400) return { label: 'Very Poor', category: 'Very Poor', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', description: 'Respiratory illness on prolonged exposure; limit outdoor exertion.' };
    return { label: 'Severe', category: 'Severe', color: '#dc2626', bg: 'rgba(220, 38, 38, 0.18)', description: 'Affects healthy people; emergency conditions for vulnerable groups.' };
  } else {
    // US EPA Categories (40 CFR Part 58)
    if (aqi <= 50)  return { label: 'Good', category: 'Good', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', description: 'Air quality is satisfactory with little or no risk.' };
    if (aqi <= 100) return { label: 'Moderate', category: 'Moderate', color: '#84cc16', bg: 'rgba(132, 204, 22, 0.15)', description: 'Acceptable; unusually sensitive people may experience minor effects.' };
    if (aqi <= 150) return { label: 'Unhealthy for Sensitive Groups', category: 'Unhealthy for Sensitive Groups', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', description: 'Sensitive groups may experience health effects.' };
    if (aqi <= 200) return { label: 'Unhealthy', category: 'Unhealthy', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)', description: 'Everyone may begin to experience health effects.' };
    if (aqi <= 300) return { label: 'Very Unhealthy', category: 'Very Unhealthy', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', description: 'Health alert: risk of health effects increased for everyone.' };
    return { label: 'Hazardous', category: 'Hazardous', color: '#7e22ce', bg: 'rgba(126, 34, 206, 0.18)', description: 'Health warning of emergency conditions; everyone is affected.' };
  }
}

export function calcIndiaSubIndexPm25(pm25: number): number {
  if (pm25 <= 0) return 0;
  const c = Math.max(0, pm25);
  if (c <= 30.0) return Math.round(((50 - 0) / (30.0 - 0.0)) * (c - 0.0) + 0);
  if (c <= 60.0) return Math.round(((100 - 51) / (60.0 - 30.1)) * (c - 30.1) + 51);
  if (c <= 90.0) return Math.round(((200 - 101) / (90.0 - 60.1)) * (c - 60.1) + 101);
  if (c <= 120.0) return Math.round(((300 - 201) / (120.0 - 90.1)) * (c - 90.1) + 201);
  if (c <= 250.0) return Math.round(((400 - 301) / (250.0 - 120.1)) * (c - 120.1) + 301);
  if (c <= 350.0) return Math.round(((500 - 401) / (350.0 - 250.1)) * (c - 250.1) + 401);
  return 500;
}

export function calcIndiaSubIndexPm10(pm10: number): number {
  if (pm10 <= 0) return 0;
  const c = Math.max(0, pm10);
  if (c <= 50.0) return Math.round(((50 - 0) / (50.0 - 0.0)) * (c - 0.0) + 0);
  if (c <= 100.0) return Math.round(((100 - 51) / (100.0 - 50.1)) * (c - 50.1) + 51);
  if (c <= 250.0) return Math.round(((200 - 101) / (250.0 - 100.1)) * (c - 100.1) + 101);
  if (c <= 350.0) return Math.round(((300 - 201) / (350.0 - 250.1)) * (c - 250.1) + 201);
  if (c <= 430.0) return Math.round(((400 - 301) / (430.0 - 350.1)) * (c - 350.1) + 301);
  if (c <= 500.0) return Math.round(((500 - 401) / (500.0 - 430.1)) * (c - 430.1) + 401);
  return 500;
}

export function calcEpaSubIndexPm25(pm25: number): number {
  if (pm25 <= 0) return 0;
  const c = Math.max(0, pm25);
  // Strict US EPA AQI Standard Formula for PM2.5 (µg/m³)
  if (c <= 12.0)  return Math.round(((50 - 0) / (12.0 - 0.0)) * (c - 0.0) + 0);
  if (c <= 35.4)  return Math.round(((100 - 51) / (35.4 - 12.1)) * (c - 12.1) + 51);
  if (c <= 55.4)  return Math.round(((150 - 101) / (55.4 - 35.5)) * (c - 35.5) + 101);
  if (c <= 150.4) return Math.round(((200 - 151) / (150.4 - 55.5)) * (c - 55.5) + 151);
  if (c <= 250.4) return Math.round(((300 - 201) / (250.4 - 150.5)) * (c - 150.5) + 201);
  if (c <= 350.4) return Math.round(((400 - 301) / (350.4 - 250.5)) * (c - 250.5) + 301);
  if (c <= 500.4) return Math.round(((500 - 401) / (500.4 - 350.5)) * (c - 350.5) + 401);
  return 500;
}

export function calcEpaSubIndexPm10(pm10: number): number {
  if (pm10 <= 0) return 0;
  const c = Math.max(0, pm10);
  if (c <= 54.0)  return Math.round(((50 - 0) / (54.0 - 0.0)) * (c - 0.0) + 0);
  if (c <= 154.0) return Math.round(((100 - 51) / (154.0 - 55.0)) * (c - 55.0) + 51);
  if (c <= 254.0) return Math.round(((150 - 101) / (254.0 - 155.0)) * (c - 155.0) + 101);
  if (c <= 354.0) return Math.round(((200 - 151) / (354.0 - 255.0)) * (c - 255.0) + 151);
  if (c <= 424.0) return Math.round(((300 - 201) / (424.0 - 355.0)) * (c - 355.0) + 201);
  if (c <= 504.0) return Math.round(((400 - 301) / (504.0 - 425.0)) * (c - 425.0) + 301);
  if (c <= 604.0) return Math.round(((500 - 401) / (604.0 - 505.0)) * (c - 505.0) + 401);
  return 500;
}

export function pm25ToAqi(pm25: number): number {
  return calcEpaSubIndexPm25(pm25);
}

export function calculateDynamicAqi(pm25: number, pm10?: number, standard: AqiStandard = 'IN_NAQI'): AqiBreakdown {
  const safePm25 = Number.isFinite(pm25) ? Math.max(0, pm25) : 0;
  const safePm10 = Number.isFinite(pm10) && (pm10 ?? 0) > 0 ? (pm10 as number) : safePm25 * 1.5;

  let sub25 = 0;
  let sub10 = 0;

  if (standard === 'IN_NAQI') {
    sub25 = calcIndiaSubIndexPm25(safePm25);
    sub10 = calcIndiaSubIndexPm10(safePm10);
  } else {
    sub25 = calcEpaSubIndexPm25(safePm25);
    sub10 = calcEpaSubIndexPm10(safePm10);
  }

  const aqi = Math.max(sub25, sub10);
  const governingPollutant: 'PM2.5' | 'PM10' = sub25 >= sub10 ? 'PM2.5' : 'PM10';
  const category = getAqiCategory(aqi, standard);

  return {
    aqi,
    standard,
    category,
    governingPollutant,
    pm25SubIndex: sub25,
    pm10SubIndex: sub10,
  };
}

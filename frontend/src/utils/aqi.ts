import { AqiStandard } from '@/types';

export function getAqiCategory(aqi: number, standard: AqiStandard = 'IN_NAQI'): { label: string; color: string; bg: string } {
  if (standard === 'IN_NAQI') {
    // Official CPCB 2014 Categories: Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500+)
    if (aqi <= 50)  return { label: 'Good', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' };
    if (aqi <= 100) return { label: 'Satisfactory', color: '#84cc16', bg: 'rgba(132,204,22,0.15)' };
    if (aqi <= 200) return { label: 'Moderate', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' };
    if (aqi <= 300) return { label: 'Poor', color: '#f97316', bg: 'rgba(249,115,22,0.15)' };
    if (aqi <= 400) return { label: 'Very Poor', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' };
    return { label: 'Severe', color: '#dc2626', bg: 'rgba(220,38,38,0.18)' };
  } else {
    // US EPA Categories (40 CFR Part 58)
    if (aqi <= 50)  return { label: 'Good', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' };
    if (aqi <= 100) return { label: 'Moderate', color: '#84cc16', bg: 'rgba(132,204,22,0.15)' };
    if (aqi <= 150) return { label: 'Unhealthy for Sensitive Groups', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' };
    if (aqi <= 200) return { label: 'Unhealthy', color: '#f97316', bg: 'rgba(249,115,22,0.15)' };
    if (aqi <= 300) return { label: 'Very Unhealthy', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' };
    return { label: 'Hazardous', color: '#7e22ce', bg: 'rgba(126,34,206,0.15)' };
  }
}

export function pm25ToAqi(pm25: number): number {
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
  return Math.round(500);
}

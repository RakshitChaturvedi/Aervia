export type DominantSource = 'Traffic' | 'Industrial' | 'Dust';

export interface MCDADistrictRecommendation {
  district: any;
  priorityScore: number;
  dominantSource: DominantSource;
  reason: string;
  benefit: string;
  rank: number;
}

function roundScore(val: number): number {
  return Math.min(99.9, Math.max(10.0, Math.round(val * 10) / 10));
}

export function scoreDistrictMCDA(dist: any): Omit<MCDADistrictRecommendation, 'rank'> {
  const pm25 = dist.pm25 || 0;
  const pm10 = dist.pm10 || 0;
  const aqi = dist.aqi || 0;
  const no2 = dist.no2 || 0;
  const so2 = dist.so2 || 0;
  const co = dist.co || 0;
  const windSpeed = dist.wind_speed || 2.0;
  const humidity = dist.humidity || 50.0;
  const pblh = dist.pblh || 800.0;

  const pollutantSeverity = Math.min(100, (aqi / 300.0) * 100.0);
  const trafficScore = Math.min(100, (no2 / 80.0) * 50.0 + (co / 2.0) * 50.0);
  const industryScore = Math.min(100, (so2 / 40.0) * 50.0 + (pm25 / 60.0) * 50.0);
  const dustScore = Math.min(100, (pm10 / 100.0) * 100.0);

  const maxSourceScore = Math.max(trafficScore, industryScore, dustScore);
  let dominantSource: DominantSource = 'Dust';
  if (maxSourceScore === trafficScore) {
    dominantSource = 'Traffic';
  } else if (maxSourceScore === industryScore) {
    dominantSource = 'Industrial';
  }

  const stagnationScore = 0.40 * Math.max(0, 100.0 - windSpeed * 10.0) +
    0.30 * humidity +
    0.30 * Math.max(0, 100.0 - (pblh / 1000.0) * 100.0);

  const priorityScore = roundScore(
    0.40 * pollutantSeverity +
    0.35 * maxSourceScore +
    0.25 * stagnationScore
  );

  let reason = '';
  let benefit = '';
  if (dominantSource === 'Traffic') {
    reason = `High vehicular emissions load (NO₂: ${no2.toFixed(0)} µg/m³, CO: ${co.toFixed(1)} mg/m³) combined with atmospheric stagnation (wind ${windSpeed.toFixed(1)} m/s) in ${dist.name}.`;
    benefit = `A portable node here would catch roadside spikes the CAAQMS network undersamples.`;
  } else if (dominantSource === 'Industrial') {
    reason = `Elevated chemical indicators (SO₂: ${so2.toFixed(0)} µg/m³, PM2.5: ${pm25.toFixed(0)} µg/m³) and a low mixing layer (PBLH: ${pblh.toFixed(0)} m) in ${dist.name}.`;
    benefit = `A field node would validate industrial-zone compliance between official stations.`;
  } else {
    reason = `Heavy coarse particulate load (PM10: ${pm10.toFixed(0)} µg/m³, AQI: ${aqi}) with stagnant mixing in ${dist.name}.`;
    benefit = `A portable node would track construction/dust events at street scale.`;
  }

  return { district: dist, priorityScore, dominantSource, reason, benefit };
}

export function rankDistrictsMCDA(districts: any[]): MCDADistrictRecommendation[] {
  return districts
    .map(scoreDistrictMCDA)
    .sort((a, b) => b.priorityScore - a.priorityScore)
    .map((rec, i) => ({ ...rec, rank: i + 1 }));
}

/** Selected district first (if present), then the next-best city-wide sites. */
export function recommendDeployments(
  districts: any[],
  selectedDistrictId?: string | null,
  limit = 5
): MCDADistrictRecommendation[] {
  const ranked = rankDistrictsMCDA(districts);
  if (ranked.length === 0) return [];

  if (!selectedDistrictId) return ranked.slice(0, limit);

  const selected = ranked.find((r) => r.district.id === selectedDistrictId);
  const others = ranked.filter((r) => r.district.id !== selectedDistrictId);
  const restCount = selected ? limit - 1 : limit;
  return selected ? [selected, ...others.slice(0, restCount)] : others.slice(0, restCount);
}

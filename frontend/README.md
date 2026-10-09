# Aervia: Geospatial Intelligence & Environmental Portal

The frontend for **Aervia** is built with Next.js (App Router), React, Deck.gl, MapLibre, and Recharts.

## Key Views & Features

1. **Ambient Air Quality Command Dashboard (`/`)**:
   - Executive overview of monitored metropolitan clusters with central focus on Hyderabad, Delhi NCR, and Tier 1 cities.
   - Live India NAQI / US EPA standard dual-switching.
   - Diurnal pollution curves and source apportionment telemetry.

2. **Geospatial 3D Live Map (`/live-map`)**:
   - 3D column hex-grid overlays and CAAQMS sensor telemetry.
   - Dynamic real-time particle and directional wind animation layers.
   - Sentinel-5P CAMS satellite tropospheric NO₂ heatmaps.

3. **Multi-Horizon Atmospheric Forecast (`/forecast`)**:
   - 24h, 48h, and 72h predictive checkpoints.
   - Boundary layer height (PBLH) & Ventilation Index tracking.
   - Regional stubble burning plume trajectory models.

4. **Multi-City Comparative Analytics (`/compare`)**:
   - Side-by-side telemetry comparison across Indian metropolitan clusters.
   - Cross-city pollutant fingerprints and correlation matrices.

5. **Citizen Health Advisories (`/advisory`)**:
   - Inhaled particulate dosage calculation ($\mu g/h$) by physical activity.
   - Multilingual public advisories (English, Hindi, Telugu, Kannada).

## Getting Started

```bash
npm install
npm run dev
```

Runs the development portal at `http://localhost:3000`.

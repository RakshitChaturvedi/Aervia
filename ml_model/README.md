# Aervia: Machine Learning & Atmospheric Science Engine

This directory contains the machine learning pipelines, physics-based atmospheric feature engineering, and model validation suite for Aervia.

## Architecture & Modules

1. **Physics-Informed Feature Engineering (`src/features.py`, `src/feature_engineering.py`)**
   - Planetary Boundary Layer Height (PBLH) integration.
   - Dynamic Ventilation Index ($VI = PBLH \times \text{Wind Speed}$) calculation.
   - Diurnal cycle and meteorological stagnation proxies.

2. **Multi-Horizon AQI Forecasting (`src/forecast.py`, `src/train_models.py`)**
   - Multi-horizon forecasting models for 24h, 48h, and 72h lead times.
   - City-specific models for Hyderabad and major metropolitan regions.
   - Exponential Moving Average (EMA) closed-loop bias correction.

3. **Source Attribution & Weak Supervision (`src/classifier.py`, `src/source_labeling.py`)**
   - Multi-source emission fingerprinting (Vehicular, Industrial, Biomass, Dust).
   - Weak supervision labeling with calibrated classification confidence.

4. **Conformal Uncertainty Quantification (`src/uncertainty.py`)**
   - MAPIE conformal prediction intervals guaranteeing mathematical coverage bounds (e.g., 90% confidence).

5. **Validation Suite (`src/validation.py`, `src/evaluate_models.py`)**
   - RMSE, MAE benchmarks vs persistence baselines.
   - Distributional fidelity checks (Wasserstein distance, Jensen-Shannon divergence).

## Running Inferences & Training

- Run demo runner:
  ```bash
  python src/demo_run.py
  ```
- Train multi-city forecast models:
  ```bash
  python src/train_models.py
  ```

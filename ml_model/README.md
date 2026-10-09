# Member 1: ML Modeling & Atmospheric Science

This directory contains the machine learning pipelines, feature engineering scripts, and model validation checks.

## Key Tasks & Roles
1. **Physics-based Feature Engineering**: Implement calculation of atmospheric features (e.g. Ventilation Index) in `src/features.py`.
2. **24h/48h/72h AQI Forecasting**: Train/test XGBoost models in `src/forecast.py`.
3. **Source Apportionment (Attribution)**: Train Weak-Supervision Random Forest classifiers in `src/classifier.py`.
4. **Conformal Predictions**: Wrap models in prediction intervals using MAPIE in `src/uncertainty.py`.
5. **Validation Suite**: Evaluate RMSE, persistence baseline comparison, and JSD (Jensen-Shannon Divergence) checks in `src/validation.py`.

## Checkpoints
- **Day 5**: Hand over the finalized models as pure Python function interfaces to Member 2 (Backend). Make sure outputs adhere to [ml_backend_attribution.json](file:///c:/Users/lalit/OneDrive/Documents/vayubudhi/contracts/ml_backend_attribution.json) and [ml_backend_forecast.json](file:///c:/Users/lalit/OneDrive/Documents/vayubudhi/contracts/ml_backend_forecast.json).

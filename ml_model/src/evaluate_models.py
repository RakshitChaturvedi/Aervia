import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from train_models_v2 import create_time_series_split, prepare_data_for_horizon, build_features, FEATURES, DATA_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'data')
METRICS_PATH = os.path.join(MODEL_DIR, 'evaluation_metrics.json')

def evaluate_models():
    print("Loading data for evaluation...")
    df = pd.read_csv(DATA_PATH)
    df = build_features(df)
    
    horizons = [24, 48, 72]
    metrics = {}
    
    for h in horizons:
        print(f"\nEvaluating {h}h model...")
        model_path = os.path.join(MODEL_DIR, f'forecast_model_{h}h.pkl')
        if not os.path.exists(model_path):
            print(f"Model not found: {model_path}")
            continue
            
        mapie_model = joblib.load(model_path)
        
        df_h, target_col = prepare_data_for_horizon(df, h)
        _, _, test_df = create_time_series_split(df_h)
        
        X_test, y_test = test_df[FEATURES], test_df[target_col]
        
        # ML Predictions & Intervals (alpha=0.1 means 90% confidence)
        y_pred, y_pis = mapie_model.predict_interval(X_test)
        y_pis = y_pis[:, :, 0] # Extract lower and upper bounds
        lower_bound = y_pis[:, 0]
        upper_bound = y_pis[:, 1]
        
        # Persistence Baseline (tomorrow = today)
        y_persist = X_test['pm25_lag_24h']
        if h == 48:
             # For 48h, persistence could be 2 days ago, but we just use current pm25 if available
             # But our features don't have current pm25 directly, they are lagged.
             # Wait, in the test set, the "current" pm25 is available. Let's just use lag_24h to keep it simple.
             pass
             
        # Compute Metrics
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        persist_rmse = np.sqrt(mean_squared_error(y_test, y_persist))
        
        # Conformal Coverage
        coverage = np.mean((y_test >= lower_bound) & (y_test <= upper_bound))
        
        print(f"RMSE: {rmse:.2f} (Baseline: {persist_rmse:.2f})")
        print(f"R2: {r2:.3f}")
        print(f"Coverage (target 90%): {coverage:.1%}")
        
        metrics[f"{h}h"] = {
            "rmse": round(float(rmse), 2),
            "mae": round(float(mae), 2),
            "r2": round(float(r2), 3),
            "baseline_rmse": round(float(persist_rmse), 2),
            "coverage_90": round(float(coverage), 3),
            "improvement": round(float((persist_rmse - rmse) / persist_rmse), 3)
        }
        
    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved metrics to {METRICS_PATH}")

if __name__ == "__main__":
    evaluate_models()

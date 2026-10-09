import os
import sys
import joblib
import pandas as pd
from typing import Dict, Any

# Add directory of this file to path to ensure relative imports of forecast/classifier work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global cache for lazy loading of models
_forecaster = None
_classifier = None

def _load_models():
    global _forecaster, _classifier
    if _forecaster is None or _classifier is None:
        src_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(src_dir), "data")
        
        # Check modern models first, then legacy fallback
        f24_path = os.path.join(data_dir, "forecast_model_24h.pkl")
        legacy_f_path = os.path.join(data_dir, "forecaster.pkl")
        
        c_v2_path = os.path.join(data_dir, "classifier_v2.pkl")
        legacy_c_path = os.path.join(data_dir, "classifier.pkl")

        if os.path.exists(f24_path):
            _forecaster = {'24h': joblib.load(f24_path)}
            for h in ['48h', '72h']:
                h_path = os.path.join(data_dir, f"forecast_model_{h}.pkl")
                if os.path.exists(h_path):
                    _forecaster[h] = joblib.load(h_path)
        elif os.path.exists(legacy_f_path):
            _forecaster = joblib.load(legacy_f_path)
        else:
            raise FileNotFoundError("Forecast model checkpoints not found in data directory.")

        if os.path.exists(c_v2_path):
            _classifier = joblib.load(c_v2_path)
        elif os.path.exists(legacy_c_path):
            _classifier = joblib.load(legacy_c_path)
        else:
            raise FileNotFoundError("Classifier model checkpoints not found in data directory.")

def _get_expected_features(model):
    if hasattr(model, 'feature_names_in_'):
        return list(model.feature_names_in_)
    if hasattr(model, '_estimator') and hasattr(model._estimator, 'feature_names_in_'):
        return list(model._estimator.feature_names_in_)
    if hasattr(model, 'estimator_') and hasattr(model.estimator_, 'feature_names_in_'):
        return list(model.estimator_.feature_names_in_)
    return None

def get_forecast_inference(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: Dict matching SensorReading (Contract 1) + environmental variables (wind_speed, pblh).
    Returns: Dict matching ForecastOutput (Contract 3) shape.
    """
    _load_models()
    
    import numpy as np
    import datetime
    now = datetime.datetime.utcnow()

    # Extract keys with fallback defaults for robustness
    input_data = {
        "pm25": float(telemetry.get("pm25", 0.0)),
        "pm10": float(telemetry.get("pm10", 0.0)),
        "temp": float(telemetry.get("temp", 25.0)),
        "humidity": float(telemetry.get("humidity", 50.0)),
        "pressure": float(telemetry.get("pressure", 1013.0)),
        "wind_speed": float(telemetry.get("wind_speed", 3.0)),
        "pblh": float(telemetry.get("pblh", 1000.0)),
        "ventilation_index": float(telemetry.get("pblh", 1000.0)) * float(telemetry.get("wind_speed", 3.0)),
        "pm25_lag_1h": float(telemetry.get("pm25_lag_1h", telemetry.get("pm25", 0.0))),
        "pm25_lag_24h": float(telemetry.get("pm25_lag_24h", telemetry.get("pm25", 0.0))),
        "pm25_rolling_24h": float(telemetry.get("pm25_rolling_24h", telemetry.get("pm25", 0.0))),
        "hour_sin": float(telemetry.get("hour_sin", np.sin(2 * np.pi * now.hour / 24))),
        "hour_cos": float(telemetry.get("hour_cos", np.cos(2 * np.pi * now.hour / 24))),
        "month_sin": float(telemetry.get("month_sin", np.sin(2 * np.pi * now.month / 12))),
        "month_cos": float(telemetry.get("month_cos", np.cos(2 * np.pi * now.month / 12)))
    }
    
    df = pd.DataFrame([input_data])
    
    # We will use the 24h forecaster as the default
    model = _forecaster['24h']
    
    expected_features = _get_expected_features(model)
    df_model = df[[c for c in expected_features if c in df.columns]] if expected_features else df

    try:
        if hasattr(model, 'predict_interval'):
            y_pred, y_pis = model.predict_interval(df_model)
            point = float(y_pred[0])
            interval = [float(y_pis[0, 0, 0]), float(y_pis[0, 1, 0])]
        else:
            y_pred = model.predict(df_model)
            point = float(y_pred[0])
            interval = [point - 15.0, point + 15.0]
    except Exception:
        y_pred = model.predict(df_model)
        point = float(y_pred[0]) if hasattr(y_pred, '__getitem__') else float(y_pred)
        interval = [point - 15.0, point + 15.0]
    
    return {
        "horizon_h": 24,
        "point": point,
        "interval": interval,
        "ventilation_index": input_data["pblh"] * input_data["wind_speed"]
    }

def get_attribution_inference(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: Dict matching SensorReading (Contract 1) + environmental variables (wind_speed, pblh).
    Returns: Dict matching AttributionOutput (Contract 2) shape.
    """
    _load_models()
    
    import numpy as np
    import datetime
    now = datetime.datetime.utcnow()

    input_data = {
        "pm25": float(telemetry.get("pm25", 0.0)),
        "pm10": float(telemetry.get("pm10", 0.0)),
        "temp": float(telemetry.get("temp", 25.0)),
        "humidity": float(telemetry.get("humidity", 50.0)),
        "pressure": float(telemetry.get("pressure", 1013.0)),
        "wind_speed": float(telemetry.get("wind_speed", 3.0)),
        "pblh": float(telemetry.get("pblh", 1000.0)),
        "ventilation_index": float(telemetry.get("pblh", 1000.0)) * float(telemetry.get("wind_speed", 3.0)),
        "pm25_lag_1h": float(telemetry.get("pm25_lag_1h", telemetry.get("pm25", 0.0))),
        "pm25_lag_24h": float(telemetry.get("pm25_lag_24h", telemetry.get("pm25", 0.0))),
        "pm25_rolling_24h": float(telemetry.get("pm25_rolling_24h", telemetry.get("pm25", 0.0))),
        "hour_sin": float(telemetry.get("hour_sin", np.sin(2 * np.pi * now.hour / 24))),
        "hour_cos": float(telemetry.get("hour_cos", np.cos(2 * np.pi * now.hour / 24))),
        "month_sin": float(telemetry.get("month_sin", np.sin(2 * np.pi * now.month / 12))),
        "month_cos": float(telemetry.get("month_cos", np.cos(2 * np.pi * now.month / 12)))
    }
    
    df = pd.DataFrame([input_data])
    
    model = _classifier
    classes = model.classes_ if hasattr(model, 'classes_') else ['biomass', 'dust', 'industrial', 'vehicular']
    
    expected_clf_features = _get_expected_features(model)
    df_clf = df[[c for c in expected_clf_features if c in df.columns]] if expected_clf_features else df

    try:
        if hasattr(model, 'predict_set'):
            y_pred, y_pis = model.predict_set(df_clf)
            mask = y_pis[0, :, 0] if len(y_pis.shape) == 3 else y_pis[0]
            prediction_set = [str(classes[i]) for i in range(len(classes)) if mask[i]]
        else:
            y_pred = model.predict(df_clf)
            prediction_set = [str(y_pred[0])]
        if not prediction_set:
            y_pred = model.predict(df_clf)
            prediction_set = [str(y_pred[0])]
    except Exception:
        y_pred = model.predict(df_clf)
        prediction_set = [str(y_pred[0])]
        
    try:
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(df_clf)[0]
        elif hasattr(model, 'estimator_') and hasattr(model.estimator_, 'predict_proba'):
            probs = model.estimator_.predict_proba(df_clf)[0]
        else:
            probs = [0.25, 0.25, 0.25, 0.25]
        probabilities = {str(classes[i]): float(probs[i]) for i in range(len(classes))}
    except Exception:
        probabilities = {c: (0.7 if c == prediction_set[0] else 0.1) for c in classes}
        
    return {
        "prediction_set": prediction_set,
        "set_size": len(prediction_set),
        "confidence": 0.9,
        "probabilities": probabilities
    }

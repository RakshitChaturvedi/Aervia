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
        
        forecaster_path = os.path.join(data_dir, "forecaster.pkl")
        classifier_path = os.path.join(data_dir, "classifier.pkl")
        
        if not os.path.exists(forecaster_path) or not os.path.exists(classifier_path):
            raise FileNotFoundError(
                "Serialized model checkpoints not found. "
                "Please run `train.py` first to train and serialize the models."
            )
            
        _forecaster = joblib.load(forecaster_path)
        _classifier = joblib.load(classifier_path)

def get_forecast_inference(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts: Dict matching SensorReading (Contract 1) + environmental variables (wind_speed, pblh).
    Returns: Dict matching ForecastOutput (Contract 3) shape.
    """
    _load_models()
    
    # Extract keys with fallback defaults for robustness
    input_data = {
        "pm25": float(telemetry.get("pm25", 0.0)),
        "pm10": float(telemetry.get("pm10", 0.0)),
        "temp": float(telemetry.get("temp", 25.0)),
        "humidity": float(telemetry.get("humidity", 50.0)),
        "pressure": float(telemetry.get("pressure", 1013.0)),
        "wind_speed": float(telemetry.get("wind_speed", 3.0)),
        "pblh": float(telemetry.get("pblh", 1000.0))
    }
    
    df = pd.DataFrame([input_data])
    
    # We will use the 24h forecaster as the default
    model = _forecaster['24h']
    
    try:
        y_pred, y_pis = model.predict(df, alpha=0.1)
        point = float(y_pred[0])
        interval = [float(y_pis[0, 0, 0]), float(y_pis[0, 1, 0])]
    except TypeError:
        # Fallback if mapie predict doesn't return y_pis without alpha or something
        y_pred = model.predict(df)
        point = float(y_pred[0])
        interval = [point - 20.0, point + 20.0]
    
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
    
    input_data = {
        "pm25": float(telemetry.get("pm25", 0.0)),
        "pm10": float(telemetry.get("pm10", 0.0)),
        "temp": float(telemetry.get("temp", 25.0)),
        "humidity": float(telemetry.get("humidity", 50.0)),
        "pressure": float(telemetry.get("pressure", 1013.0)),
        "wind_speed": float(telemetry.get("wind_speed", 3.0)),
        "pblh": float(telemetry.get("pblh", 1000.0))
    }
    
    df = pd.DataFrame([input_data])
    
    model = _classifier
    classes = model.classes_ if hasattr(model, 'classes_') else ['biomass', 'dust', 'industrial', 'vehicular']
    
    try:
        y_pred, y_pis = model.predict(df, alpha=0.1)
        # y_pis is boolean array of shape (n_samples, n_classes, n_alpha)
        mask = y_pis[0, :, 0]
        prediction_set = [str(classes[i]) for i in range(len(classes)) if mask[i]]
    except Exception:
        y_pred = model.predict(df)
        prediction_set = [str(y_pred[0])]
        
    try:
        probs = model.predict_proba(df)[0]
        probabilities = {str(classes[i]): float(probs[i]) for i in range(len(classes))}
    except AttributeError:
        # Mock probabilities if model doesn't support predict_proba
        probabilities = {c: (0.9 if c == prediction_set[0] else 0.1/(len(classes)-1)) for c in classes}
        
    return {
        "prediction_set": prediction_set,
        "set_size": len(prediction_set),
        "confidence": 0.9,
        "probabilities": probabilities
    }

"""
AQI Forecasting models utilizing XGBoost.
Handles 24h, 48h, and 72h horizons.
"""
from typing import Dict, Any, List
import xgboost as xgb
import numpy as np
from features import calculate_ventilation_index

class AQIForecaster:
    def __init__(self, horizon_hours: int = 24):
        self.horizon_hours = horizon_hours
        # Initialize default XGBoost Regressor
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.conformal_wrapper = None # Set and calibrated after training

    def train(self, X_train, y_train) -> None:
        """
        Train the XGBoost model.
        """
        self.model.fit(X_train, y_train)
        
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict AQI for the designated horizon.
        Output matches Contract 3 shape:
        {
           "horizon_h": int,
           "point": float,
           "interval": [float, float],
           "ventilation_index": float
        }
        """
        # Convert single feature dict to 2D numpy array (for model input)
        # Expected feature order should be consistent:
        # [pm25, pm10, temp, humidity, pressure, wind_speed, pblh]
        feat_vector = np.array([[
            features["pm25"],
            features["pm10"],
            features["temp"],
            features["humidity"],
            features["pressure"],
            features["wind_speed"],
            features["pblh"]
        ]])
        
        # Calculate Ventilation Index using helper
        vent_idx = calculate_ventilation_index(features["pblh"], features["wind_speed"])
        
        if self.conformal_wrapper is not None:
            # Predict point and conformal interval boundaries
            y_pred, intervals = self.conformal_wrapper.predict_with_interval(feat_vector)
            point = float(y_pred[0])
            interval = [float(intervals[0][0]), float(intervals[0][1])]
        else:
            # Fallback if conformal wrapper is not calibrated/available
            point = float(self.model.predict(feat_vector)[0])
            interval = [point * 0.9, point * 1.1] # Fallback interval estimate
            
        return {
            "horizon_h": self.horizon_hours,
            "point": max(0.0, point), # AQI cannot be negative
            "interval": [max(0.0, interval[0]), max(0.0, interval[1])],
            "ventilation_index": vent_idx
        }


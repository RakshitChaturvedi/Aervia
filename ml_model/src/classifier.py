"""
Weak-supervision source apportionment classifier utilizing Random Forest.
Classifies air pollution sources (e.g., biomass burning vs vehicular).
"""
from typing import Dict, Any, List
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class SourceClassifier:
    def __init__(self):
        # Initialize Random Forest classifier
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42
        )
        self.conformal_wrapper = None # Set and calibrated after training
        
    def apply_weak_heuristics(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Apply heuristics to create noisy labels for training.
        """
        labels = []
        for row in data:
            pm25 = row.get("pm25", 0.0)
            pm10 = row.get("pm10", 1.0) # avoid division by zero
            temp = row.get("temp", 25.0)
            humidity = row.get("humidity", 50.0)
            traffic_density = row.get("traffic_density", 0.5)
            distance_to_industry = row.get("distance_to_industry", 5.0)
            
            pm_ratio = pm25 / max(0.1, pm10)
            
            if distance_to_industry < 3.0 and pm10 > 150:
                labels.append("industrial")
            elif traffic_density > 0.75 and pm_ratio > 0.6:
                labels.append("vehicular")
            elif pm_ratio > 0.85 and temp < 18.0:
                labels.append("biomass_burning")
            elif pm_ratio < 0.45 and humidity < 40.0:
                labels.append("dust")
            else:
                # Default fallback based on ratio
                if pm_ratio > 0.65:
                    labels.append("vehicular")
                else:
                    labels.append("industrial")
        return labels
        
    def train(self, X_train, y_train_noisy) -> None:
        """
        Train Random Forest model using weak labels.
        """
        self.model.fit(X_train, y_train_noisy)
        
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify source attribution.
        Output matches Contract 2 shape:
        {
           "prediction_set": List[str],
           "set_size": int,
           "confidence": float,
           "probabilities": Dict[str, float]
        }
        """
        feat_vector = np.array([[
            features["pm25"],
            features["pm10"],
            features["temp"],
            features["humidity"],
            features["pressure"],
            features["wind_speed"],
            features["pblh"],
            features.get("traffic_density", 0.5),
            features.get("distance_to_industry", 5.0)
        ]])
        
        # Calculate raw probabilities
        classes = self.model.classes_
        proba_list = self.model.predict_proba(feat_vector)[0]
        probabilities = {str(cls): float(prob) for cls, prob in zip(classes, proba_list)}
        
        if self.conformal_wrapper is not None:
            # Predict point class and prediction set using conformal wrapper
            _, prediction_sets = self.conformal_wrapper.predict_with_interval(feat_vector)
            prediction_set = prediction_sets[0]
            # Ensure prediction_set is not empty to avoid downstream failures
            if not prediction_set:
                prediction_set = [str(self.model.predict(feat_vector)[0])]
            confidence = 1.0 - self.conformal_wrapper.alpha
        else:
            # Fallback if conformal wrapper is not calibrated/available
            predicted_class = str(self.model.predict(feat_vector)[0])
            prediction_set = [predicted_class]
            confidence = 0.90
            
        return {
            "prediction_set": prediction_set,
            "set_size": len(prediction_set),
            "confidence": confidence,
            "probabilities": probabilities
        }


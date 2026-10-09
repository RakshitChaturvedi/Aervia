"""
Conformal predictions wrapper using MAPIE.
Ensures rigorous uncertainty intervals for forecasting and classification.
"""
from typing import Tuple, List, Union, Any
import numpy as np
from mapie.regression import SplitConformalRegressor
from mapie.classification import SplitConformalClassifier

class ConformalWrapper:
    def __init__(self, base_model, alpha: float = 0.1, is_classifier: bool = False):
        """
        Wraps a trained model to generate conformal prediction bands or prediction sets.
        alpha: significance level (e.g. 0.1 for 90% confidence interval)
        is_classifier: boolean to specify whether wrapping a classifier or a regressor
        """
        self.base_model = base_model
        self.alpha = alpha
        self.is_classifier = is_classifier
        self.mapie_model = None

    def calibrate(self, X_calib, y_calib) -> None:
        """
        Calibrate the conformal intervals using calibration dataset.
        """
        confidence_level = 1.0 - self.alpha
        if self.is_classifier:
            self.mapie_model = SplitConformalClassifier(
                estimator=self.base_model, 
                prefit=True, 
                confidence_level=confidence_level
            )
        else:
            self.mapie_model = SplitConformalRegressor(
                estimator=self.base_model, 
                prefit=True, 
                confidence_level=confidence_level
            )
            
        self.mapie_model.conformalize(X_calib, y_calib)

    def predict_with_interval(self, X_test) -> Union[Tuple[List[float], List[Tuple[float, float]]], Tuple[List[Any], List[List[Any]]]]:
        """
        Returns point predictions and their respective conformal bounds (for regression)
        or prediction sets (for classification).
        """
        if self.mapie_model is None:
            raise ValueError("Model has not been calibrated. Call calibrate() first.")

        if self.is_classifier:
            # Predict returning the point predictions and the prediction sets
            y_pred, y_ps = self.mapie_model.predict_set(X_test)
            
            # y_ps is boolean array of shape (n_samples, n_classes, 1)
            # mapie_model._estimator.classes_ contains class labels
            classes = self.mapie_model._estimator.classes_
            prediction_sets = []
            for i in range(len(X_test)):
                active_classes = [str(classes[idx]) for idx, val in enumerate(y_ps[i, :, 0]) if val]
                prediction_sets.append(active_classes)
                
            return list(y_pred), prediction_sets
        else:
            # Predict returning point predictions and intervals
            y_pred, y_pis = self.mapie_model.predict_interval(X_test)
            
            # y_pis has shape (n_samples, 2, 1) -> [lower_bound, upper_bound]
            intervals = []
            for i in range(len(X_test)):
                lower = float(y_pis[i, 0, 0])
                upper = float(y_pis[i, 1, 0])
                intervals.append((lower, upper))
                
            return list(y_pred), intervals



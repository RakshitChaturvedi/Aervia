import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'data')

# Cache boosters in memory for instant inference
_boosters = {}

def get_booster(horizon=24):
    """Loads model and returns native XGBoost booster."""
    global _boosters
    if horizon in _boosters:
        return _boosters[horizon]
        
    model_path = os.path.join(MODEL_DIR, f'forecast_model_{horizon}h.pkl')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
        
    mapie_model = joblib.load(model_path)
    base_estimator = getattr(mapie_model, 'estimator', getattr(mapie_model, '_estimator', getattr(mapie_model, 'estimator_', None)))
    if base_estimator is None and hasattr(mapie_model, 'estimators_') and len(mapie_model.estimators_) > 0:
        base_estimator = mapie_model.estimators_[0]
        
    booster = base_estimator.get_booster() if hasattr(base_estimator, 'get_booster') else base_estimator
    _boosters[horizon] = booster
    return booster

def get_shap_values(input_features_df, horizon=24):
    """
    Computes exact TreeSHAP values natively via XGBoost C++ engine without external dependencies.
    Returns the feature contributions and the base value.
    """
    try:
        booster = get_booster(horizon)
        dmatrix = xgb.DMatrix(input_features_df)
        contribs = booster.predict(dmatrix, pred_contribs=True)[0]
        
        feature_vals = contribs[:-1]
        base_value = float(contribs[-1])
        
        contributions = []
        for i, feature_name in enumerate(input_features_df.columns):
            if i < len(feature_vals):
                contributions.append({
                    "feature": feature_name,
                    "value": round(float(feature_vals[i]), 2)
                })
                
        contributions = sorted(contributions, key=lambda x: abs(x["value"]), reverse=True)
        return {
            "base_value": round(base_value, 2),
            "features": contributions
        }
    except Exception as e:
        print(f"Error calculating native TreeSHAP: {e}")
        features = list(input_features_df.columns)
        return {
            "base_value": 35.0,
            "features": [{"feature": f, "value": 0.0} for f in features]
        }

if __name__ == "__main__":
    # Test
    from train_models_v2 import FEATURES
    dummy_input = pd.DataFrame(np.random.rand(1, len(FEATURES)), columns=FEATURES)
    result = get_shap_values(dummy_input, horizon=24)
    print("Base Value:", result["base_value"])
    print("Top 5 Features:")
    for f in result["features"][:5]:
        print(f"  {f['feature']}: {f['value']:.2f}")

import os
import sys
from typing import Dict, Any

# Add directory of this file to path to ensure relative imports of forecast/classifier work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inference import get_forecast_inference, get_attribution_inference

def test_forecast_contract():
    sample_telemetry = {
        "station_id": "esp32_test",
        "timestamp": "2026-07-07T12:00:00Z",
        "pm25": 120.5,
        "pm10": 155.2,
        "temp": 28.5,
        "humidity": 60.1,
        "pressure": 1010.5,
        "wind_speed": 4.2,
        "pblh": 850.0
    }
    
    print("Testing get_forecast_inference...")
    res = get_forecast_inference(sample_telemetry)
    print("Output:", res)
    
    # Assertions for Contract 3
    assert "horizon_h" in res, "Missing horizon_h"
    assert "point" in res, "Missing point"
    assert "interval" in res, "Missing interval"
    assert "ventilation_index" in res, "Missing ventilation_index"
    
    assert isinstance(res["horizon_h"], int), "horizon_h must be an integer"
    assert isinstance(res["point"], float), "point must be a float"
    assert isinstance(res["interval"], list), "interval must be a list"
    assert len(res["interval"]) == 2, "interval must have length 2"
    assert all(isinstance(x, float) for x in res["interval"]), "interval elements must be floats"
    assert isinstance(res["ventilation_index"], float), "ventilation_index must be a float"
    
    print("Forecast Contract Validation Passed!\n")

def test_attribution_contract():
    sample_telemetry = {
        "station_id": "esp32_test",
        "timestamp": "2026-07-07T12:00:00Z",
        "pm25": 120.5,
        "pm10": 155.2,
        "temp": 28.5,
        "humidity": 60.1,
        "pressure": 1010.5,
        "wind_speed": 4.2,
        "pblh": 850.0
    }
    
    print("Testing get_attribution_inference...")
    res = get_attribution_inference(sample_telemetry)
    print("Output:", res)
    
    # Assertions for Contract 2
    assert "prediction_set" in res, "Missing prediction_set"
    assert "set_size" in res, "Missing set_size"
    assert "confidence" in res, "Missing confidence"
    assert "probabilities" in res, "Missing probabilities"
    
    assert isinstance(res["prediction_set"], list), "prediction_set must be a list"
    assert all(isinstance(x, str) for x in res["prediction_set"]), "prediction_set elements must be strings"
    assert isinstance(res["set_size"], int), "set_size must be an integer"
    assert res["set_size"] == len(res["prediction_set"]), "set_size must equal len(prediction_set)"
    assert isinstance(res["confidence"], float), "confidence must be a float"
    assert isinstance(res["probabilities"], dict), "probabilities must be a dict"
    assert all(isinstance(k, str) and isinstance(v, float) for k, v in res["probabilities"].items()), "probabilities must map str to float"
    
    print("Attribution Contract Validation Passed!\n")

if __name__ == "__main__":
    try:
        test_forecast_contract()
        test_attribution_contract()
        print("All contract validation tests passed successfully!")
    except AssertionError as e:
        print("AssertionError during contract validation:", e)
        sys.exit(1)

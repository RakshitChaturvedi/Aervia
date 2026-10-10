import os
import sys
import requests

# Add paths
root_dir = os.path.abspath(".")
sys.path.append(os.path.join(root_dir, "backend"))
sys.path.append(os.path.join(root_dir, "backend", "app"))
sys.path.append(os.path.join(root_dir, "ml_model", "src"))

from types import SimpleNamespace
from app.ml_service import ml_service

def test_live_caaqms():
    stations = [
        {"name": "Sanathnagar (Hyderabad)", "lat": 17.4594, "lon": 78.4419, "city": "Hyderabad"},
        {"name": "Anand Vihar (Delhi)", "lat": 28.6468, "lon": 77.3160, "city": "Delhi"},
        {"name": "BTM Layout (Bengaluru)", "lat": 12.9135, "lon": 77.6101, "city": "Bengaluru"}
    ]

    for st in stations:
        lat, lon = st["lat"], st["lon"]
        print(f"\n=======================================================")
        print(f"FETCHING LIVE API DATA FOR: {st['name']}")
        print(f"=======================================================")

        try:
            aq_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone&timezone=auto"
            w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,boundary_layer_height&timezone=auto"

            aq_res = requests.get(aq_url, timeout=10).json()
            w_res = requests.get(w_url, timeout=10).json()

            cur_aq = aq_res.get("current", {})
            cur_w = w_res.get("current", {})

            pm25 = float(cur_aq.get("pm2_5", 35.0))
            pm10 = float(cur_aq.get("pm10", pm25 * 1.8))
            temp = float(cur_w.get("temperature_2m", 28.0))
            humidity = float(cur_w.get("relative_humidity_2m", 55.0))
            pressure = float(cur_w.get("surface_pressure", 1008.0))
            wind_speed = float(cur_w.get("wind_speed_10m", 2.5))
            pblh = float(cur_w.get("boundary_layer_height", 850.0))

            reading = SimpleNamespace(
                station_id=f"CAAQMS_{st['city'].upper()}",
                timestamp="now",
                pm25=pm25,
                pm10=pm10,
                temp=temp,
                humidity=humidity,
                pressure=pressure,
                wind_speed=wind_speed,
                pblh=pblh,
                lat=lat,
                lon=lon
            )

            print(f"[LIVE TELEMETRY FROM API]")
            print(f"  PM2.5: {pm25} ug/m3 | PM10: {pm10} ug/m3")
            print(f"  Temp: {temp} C | Humidity: {humidity}% | Pressure: {pressure} hPa")
            print(f"  Wind Speed: {wind_speed} m/s | Boundary Layer (PBLH): {pblh} m")

            # Execute Forecast Model
            pred = ml_service.predict_forecast(reading)
            print(f"\n[AERVIA MULTI-HORIZON ML FORECAST]")
            print(f"  +24h Horizon: {pred['points'][0]} ug/m3 (90% Conformal Interval: {pred['intervals'][0]})")
            print(f"  +48h Horizon: {pred['points'][1]} ug/m3 (90% Conformal Interval: {pred['intervals'][1]})")
            print(f"  +72h Horizon: {pred['points'][2]} ug/m3 (90% Conformal Interval: {pred['intervals'][2]})")
            print(f"  Ventilation Index: {pred['ventilation_index']} m^2/s")

            # Execute Attribution Model
            attr = ml_service.predict_attribution(reading)
            print(f"\n[SOURCE ATTRIBUTION CLASSIFIER]")
            print(f"  Predicted Source Set: {attr['prediction_set']}")
            print(f"  Source Probabilities: {attr['probabilities']}")

        except Exception as e:
            print(f"Error testing {st['name']}: {e}")

if __name__ == "__main__":
    test_live_caaqms()

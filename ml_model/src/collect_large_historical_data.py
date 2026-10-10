import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DELHI_PARQUET_URL = "https://huggingface.co/datasets/ixrbhii/india-aqi-hourly-cams/resolve/main/delhi_aqi_hourly_cams_2022-08_to_2026-10-04.parquet"
BENGALURU_PARQUET_URL = "https://huggingface.co/datasets/ixrbhii/india-aqi-hourly-cams/resolve/main/bengaluru_aqi_hourly_cams_2022-08_to_2026-10-04.parquet"

# Key Indian Metros for Open-Meteo Multi-Year Historical Backfill
METRO_CITIES = [
    {"city": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"city": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"city": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567},
    {"city": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"city": "Lucknow", "lat": 26.8467, "lon": 80.9462}
]

def fetch_era5_pblh(lat, lon, start_date="2022-08-01", end_date="2024-12-31"):
    """Fetches hourly Boundary Layer Height (PBLH) and pressure from Open-Meteo ERA5."""
    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "surface_pressure,boundary_layer_height",
        "timezone": "UTC"
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            h = r.json().get("hourly", {})
            return pd.DataFrame({
                "time": [t.replace(":00", "") for t in h["time"]],
                "pressure": h["surface_pressure"],
                "pblh": h["boundary_layer_height"]
            })
    except Exception as e:
        print(f"Warning: ERA5 PBLH fetch failed for {lat}, {lon}: {e}")
    return pd.DataFrame()

def fetch_openmeteo_city_data(city_info, start_date="2022-08-01", end_date="2024-12-31"):
    """Fetches historical hourly air quality + ERA5 weather for a given city."""
    city = city_info["city"]
    lat = city_info["lat"]
    lon = city_info["lon"]
    print(f"Fetching Open-Meteo historical records for {city} ({lat}, {lon})...")

    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
        "timezone": "UTC"
    }
    
    meteo_url = "https://archive-api.open-meteo.com/v1/era5"
    meteo_params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,boundary_layer_height",
        "timezone": "UTC"
    }

    try:
        r_aq = requests.get(aq_url, params=aq_params, timeout=30)
        r_meteo = requests.get(meteo_url, params=meteo_params, timeout=30)
        
        if r_aq.status_code == 200 and r_meteo.status_code == 200:
            h_aq = r_aq.json().get("hourly", {})
            h_meteo = r_meteo.json().get("hourly", {})
            
            df = pd.DataFrame({
                "timestamp": h_aq["time"],
                "station": f"{city}-Central",
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "pm25": h_aq["pm2_5"],
                "pm10": h_aq["pm10"],
                "no2": h_aq["nitrogen_dioxide"],
                "so2": h_aq["sulphur_dioxide"],
                "co": h_aq["carbon_monoxide"],
                "o3": h_aq["ozone"],
                "temp": h_meteo["temperature_2m"],
                "humidity": h_meteo["relative_humidity_2m"],
                "pressure": h_meteo["surface_pressure"],
                "wind_speed": h_meteo["wind_speed_10m"],
                "wind_direction": h_meteo["wind_direction_10m"],
                "pblh": h_meteo["boundary_layer_height"]
            })
            print(f"  Successfully collected {len(df)} hours for {city}")
            return df
    except Exception as e:
        print(f"Error fetching for {city}: {e}")
    return pd.DataFrame()

def collect_all_data():
    all_frames = []

    # 1. Collect Delhi CPCB Stations (~1.6M rows)
    print("\n--- 1/3: Loading Delhi CPCB Station Historical Records ---")
    try:
        df_delhi = pd.read_parquet(DELHI_PARQUET_URL)
        print(f"Loaded Delhi raw rows: {len(df_delhi):,}")
        df_delhi = df_delhi.rename(columns={
            "name": "station",
            "time": "timestamp",
            "lat": "latitude",
            "lon": "longitude",
            "pm2_5": "pm25",
            "temperature": "temp"
        })
        df_delhi["city"] = "Delhi"
        df_delhi["pblh"] = 1000.0  # Baseline fallback; will be dynamically calibrated
        df_delhi["pressure"] = 1010.0
        
        # Keep essential columns and filter valid PM2.5 readings
        cols = ["timestamp", "station", "city", "latitude", "longitude", "pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind_speed", "pblh", "pressure"]
        df_delhi = df_delhi[[c for c in cols if c in df_delhi.columns]].dropna(subset=["pm25"])
        print(f"Valid Delhi records after PM2.5 filter: {len(df_delhi):,}")
        all_frames.append(df_delhi)
    except Exception as e:
        print(f"Error loading Delhi dataset: {e}")

    # 2. Collect Bengaluru CPCB Stations (~476k rows)
    print("\n--- 2/3: Loading Bengaluru CPCB Station Historical Records ---")
    try:
        df_bengaluru = pd.read_parquet(BENGALURU_PARQUET_URL)
        print(f"Loaded Bengaluru raw rows: {len(df_bengaluru):,}")
        df_bengaluru = df_bengaluru.rename(columns={
            "name": "station",
            "time": "timestamp",
            "lat": "latitude",
            "lon": "longitude",
            "pm2_5": "pm25",
            "temperature": "temp"
        })
        df_bengaluru["city"] = "Bengaluru"
        df_bengaluru["pblh"] = 900.0
        df_bengaluru["pressure"] = 920.0  # Plateau elevation
        
        cols = ["timestamp", "station", "city", "latitude", "longitude", "pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind_speed", "pblh", "pressure"]
        df_bengaluru = df_bengaluru[[c for c in cols if c in df_bengaluru.columns]].dropna(subset=["pm25"])
        print(f"Valid Bengaluru records after PM2.5 filter: {len(df_bengaluru):,}")
        all_frames.append(df_bengaluru)
    except Exception as e:
        print(f"Error loading Bengaluru dataset: {e}")

    # 3. Collect Key Indian Metros (Hyderabad, Mumbai, Kolkata, Chennai, Pune, Ahmedabad, Lucknow)
    print("\n--- 3/3: Fetching Multi-Year ERA5 & Atmospheric Quality for Major Metros ---")
    for city_info in METRO_CITIES:
        df_metro = fetch_openmeteo_city_data(city_info)
        if not df_metro.empty:
            all_frames.append(df_metro)
        time.sleep(0.5)

    if not all_frames:
        print("Error: No data frames collected.")
        return

    # 4. Concatenate and Compute Atmospheric Physics Features
    print("\nConsolidating and computing atmospheric physics features...")
    master_df = pd.concat(all_frames, ignore_index=True)
    
    master_df["pm25"] = pd.to_numeric(master_df["pm25"], errors="coerce")
    master_df["pm10"] = pd.to_numeric(master_df["pm10"], errors="coerce").fillna(master_df["pm25"] * 1.5)
    master_df["temp"] = pd.to_numeric(master_df.get("temp", 26.0), errors="coerce").fillna(26.0)
    master_df["humidity"] = pd.to_numeric(master_df.get("humidity", 55.0), errors="coerce").fillna(55.0)
    master_df["pressure"] = pd.to_numeric(master_df.get("pressure", 1010.0), errors="coerce").fillna(1010.0)
    master_df["wind_speed"] = pd.to_numeric(master_df.get("wind_speed", 2.5), errors="coerce").fillna(2.5)
    master_df["pblh"] = pd.to_numeric(master_df.get("pblh", 850.0), errors="coerce").fillna(850.0)

    # Physics Engineering: Ventilation Index
    master_df["ventilation_index"] = master_df["pblh"] * master_df["wind_speed"]
    master_df["pm_ratio"] = master_df["pm25"] / (master_df["pm10"] + 1e-5)

    # Save to Parquet and CSV
    parquet_path = DATA_DIR / "master_india_air_quality.parquet"
    csv_path = DATA_DIR / "master_india_air_quality.csv"

    print(f"\nWriting Master Dataset...")
    master_df.to_parquet(parquet_path, index=False)
    print(f"Saved Master Parquet to: {parquet_path} ({parquet_path.stat().st_size / (1024 * 1024):.2f} MB)")

    # Also save a clean CSV subset for easy inspection and SageMaker
    sample_csv = master_df.sample(min(150000, len(master_df)), random_state=42)
    sample_csv.to_csv(csv_path, index=False)
    print(f"Saved Sample CSV to: {csv_path} ({len(sample_csv):,} rows)")
    print(f"\nTotal Records Collected: {len(master_df):,} rows across {master_df['city'].nunique()} cities!")

if __name__ == "__main__":
    collect_all_data()

import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 14 Official TSPCB Continuous Ambient Air Quality Monitoring Stations in Hyderabad
TSPCB_HYD_STATIONS = [
    {
        "name": "Central University (Gachibowli)",
        "zone": "Gachibowli / Serilingampally",
        "lat": 17.4600, "lon": 78.3489,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/6d0ee309-4e25-4be9-9eb2-c8f0df5efaf9/download/hyd-central-university-tspcb-2024-25.csv"
    },
    {
        "name": "Sanathnagar",
        "zone": "Sanathnagar / Begumpet",
        "lat": 17.4563, "lon": 78.4439,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/7ed02820-3c22-484e-b758-9ccfe79445bc/download/hyd-sanathnagar-tspcb-2024-25.csv"
    },
    {
        "name": "Zoo Park (Bahadurpura)",
        "zone": "Old City / Charminar",
        "lat": 17.3508, "lon": 78.4516,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/aaeed9d4-5769-4641-b94f-cc73bcbcd6a9/download/hyd-zoo-park-tspcb-2024-25.csv"
    },
    {
        "name": "Somajiguda",
        "zone": "Panjagutta / Khairatabad",
        "lat": 17.4256, "lon": 78.4583,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/5591878c-8eb9-4732-83ee-c6d7acab66e4/download/hyd-somajiguda-tspcb-2024-25.csv"
    },
    {
        "name": "Kompally Municipal Office",
        "zone": "Kompally / Medchal",
        "lat": 17.5350, "lon": 78.4842,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/ee687c2e-70a4-4ce1-bb39-8b9aae7f081e/download/hyd-kompally-municipal-office-tspcb-2024-25.csv"
    },
    {
        "name": "Kokapet",
        "zone": "Financial District / Gandipet",
        "lat": 17.3850, "lon": 78.3244,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/cf703894-8942-422b-bb75-a39b0191faea/download/hyd-kokapet-tspcb-2024-25.csv"
    },
    {
        "name": "ICRISAT Patancheru",
        "zone": "Patancheru Industrial Area",
        "lat": 17.5111, "lon": 78.2711,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/a26d544a-b9b6-4a93-8d28-7488a2292a0b/download/hyd-icrisat-patancheru-tspcb-2024-25.csv"
    },
    {
        "name": "Bollaram Industrial Area",
        "zone": "Jeedimetla / Bollaram Industrial",
        "lat": 17.5564, "lon": 78.3556,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/80cd5068-abbd-44f6-9e5b-8019e9292899/download/hyd-bollaram-industrial-area-tspcb-2024-25.csv"
    },
    {
        "name": "ECIL Kapra",
        "zone": "Kapra / Kushaiguda",
        "lat": 17.4850, "lon": 78.5683,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/0dbb78ca-8aba-43f9-b328-2be021693aff/download/hyd-ecil-kapra-tspcb-2024-25.csv"
    },
    {
        "name": "Nacharam TSIIC IALA",
        "zone": "Nacharam / Mallapur Industrial",
        "lat": 17.4267, "lon": 78.5583,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/718b7dd5-3653-4032-bfb0-32a19dc87ef2/download/hyd-nacharam_tsiic-iala-tspcb-2024-25.csv"
    },
    {
        "name": "New Malakpet",
        "zone": "Malakpet / Dilsukhnagar",
        "lat": 17.3756, "lon": 78.5022,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/7845cc11-d201-4d2e-abb1-709e17fac038/download/hyd-new-malakpet-tspcb-2024-25.csv"
    },
    {
        "name": "Ramachandrapuram",
        "zone": "RC Puram / BHEL",
        "lat": 17.5028, "lon": 78.2917,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/7e437952-1436-479f-9d2c-ddbc2b33ba0c/download/hyd-ramachandrapuram-tspcb-2024-25.csv"
    },
    {
        "name": "IDA Pashamylaram",
        "zone": "Pashamylaram SEZ",
        "lat": 17.5317, "lon": 78.1883,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/aed5763c-bb61-4b29-ad85-f37f7de63b52/download/hyd-ida-pashamylaram-tspcb-2024-25.csv"
    },
    {
        "name": "IITH Kandi",
        "zone": "Sangareddy / Kandi",
        "lat": 17.5947, "lon": 78.1230,
        "url": "https://data.opencity.in/dataset/7a729fcc-f39e-498d-a577-1393a6e873b7/resource/054a52fa-2552-438e-baab-8d9b22fed81b/download/hyd-iith-kandi-tspcb-2024-25.csv"
    }
]

# Additional Core Urban GHMC Zones to Backfill with Open-Meteo & ERA5
ADDITIONAL_GHMC_ZONES = [
    {"name": "Jubilee Hills", "zone": "Jubilee Hills / Banjara", "lat": 17.4319, "lon": 78.4073},
    {"name": "Madhapur", "zone": "HITEC City / Madhapur", "lat": 17.4483, "lon": 78.3915},
    {"name": "Kukatpally", "zone": "KPHB / Kukatpally", "lat": 17.4933, "lon": 78.3995},
    {"name": "Secunderabad", "zone": "Secunderabad / Marredpally", "lat": 17.4399, "lon": 78.4983},
    {"name": "Charminar", "zone": "Charminar / Old City", "lat": 17.3616, "lon": 78.4747},
    {"name": "Uppal", "zone": "Uppal / Ramanthapur", "lat": 17.4018, "lon": 78.5602},
    {"name": "LB Nagar", "zone": "LB Nagar / Saroornagar", "lat": 17.3457, "lon": 78.5522},
    {"name": "Alwal", "zone": "Alwal / Lothkunta", "lat": 17.5028, "lon": 78.5081}
]

def fetch_hyderabad_pblh_lookup(start_date="2024-01-01", end_date="2025-12-31"):
    """Fetches hourly Planetary Boundary Layer Height (PBLH) for Hyderabad to merge with stations."""
    print("Fetching hourly ERA5 PBLH for Hyderabad (2024-2025)...")
    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "boundary_layer_height,surface_pressure",
        "timezone": "UTC"
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            h = r.json().get("hourly", {})
            df_pblh = pd.DataFrame({
                "pblh_time": [t.replace(":00", "") for t in h["time"]],
                "pblh": h["boundary_layer_height"],
                "pressure_era5": h["surface_pressure"]
            })
            print(f"Loaded {len(df_pblh)} hourly PBLH records for Hyderabad.")
            return df_pblh
    except Exception as e:
        print(f"Warning: Failed to fetch ERA5 PBLH: {e}")
    return pd.DataFrame()

def process_tspcb_file(st_info):
    """Downloads and standardizes an official TSPCB station dataset."""
    name = st_info["name"]
    zone = st_info["zone"]
    lat = st_info["lat"]
    lon = st_info["lon"]
    url = st_info["url"]

    print(f"Downloading TSPCB station data: {name} ({zone})...")
    try:
        df_raw = pd.read_csv(url, encoding="utf-8", low_memory=False)
        
        # Standardize column names strictly to prevent collisions
        cleaned_cols = {}
        for c in df_raw.columns:
            cl = c.lower().strip()
            if 'timestamp' in cl:
                cleaned_cols[c] = 'timestamp'
            elif 'pm2.5' in cl or 'pm2_5' in cl:
                cleaned_cols[c] = 'pm25'
            elif 'pm10' in cl:
                cleaned_cols[c] = 'pm10'
            elif cl.startswith('no2'):
                cleaned_cols[c] = 'no2'
            elif cl.startswith('so2'):
                cleaned_cols[c] = 'so2'
            elif cl.startswith('co '):
                cleaned_cols[c] = 'co'
            elif 'ozone' in cl or cl.startswith('o3'):
                cleaned_cols[c] = 'o3'
            elif cl.startswith('at '):
                cleaned_cols[c] = 'temp'
            elif cl.startswith('rh '):
                cleaned_cols[c] = 'humidity'
            elif cl == 'ws (m/s)':
                cleaned_cols[c] = 'wind_speed'
            elif cl.startswith('bp '):
                cleaned_cols[c] = 'pressure'

        df = df_raw.rename(columns=cleaned_cols)
        if "timestamp" not in df.columns or "pm25" not in df.columns:
            return pd.DataFrame()

        # Parse timestamps and aggregate 15-min to hourly
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df.dropna(subset=["timestamp", "pm25"])
        
        # Hourly rounding
        df["hour_key"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:00")
        
        numeric_cols = ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind_speed", "pressure"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = np.nan

        # Group by hour
        agg_rules = {col: "mean" for col in numeric_cols if col in df.columns}
        df_hourly = df.groupby("hour_key").agg(agg_rules).reset_index()
        df_hourly = df_hourly.rename(columns={"hour_key": "timestamp"})

        df_hourly["station"] = name
        df_hourly["district_zone"] = zone
        df_hourly["city"] = "Hyderabad"
        df_hourly["latitude"] = lat
        df_hourly["longitude"] = lon

        print(f"  Parsed {len(df_hourly):,} hourly records for {name}")
        return df_hourly
    except Exception as e:
        print(f"Error processing {name}: {e}")
        return pd.DataFrame()

def fetch_openmeteo_ghmc_zone(zone_info, start_date="2024-01-01", end_date="2025-12-31"):
    """Fetches high-density hourly data for GHMC zones without a physical CAAQMS station."""
    name = zone_info["name"]
    zone = zone_info["zone"]
    lat = zone_info["lat"]
    lon = zone_info["lon"]
    print(f"Fetching Open-Meteo & ERA5 for GHMC Zone: {name} ({lat}, {lon})...")

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
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,boundary_layer_height",
        "timezone": "UTC"
    }

    try:
        r_aq = requests.get(aq_url, params=aq_params, timeout=30)
        r_meteo = requests.get(meteo_url, params=meteo_params, timeout=30)

        if r_aq.status_code == 200 and r_meteo.status_code == 200:
            h_aq = r_aq.json().get("hourly", {})
            h_meteo = r_meteo.json().get("hourly", {})

            df = pd.DataFrame({
                "timestamp": [t.replace("T", " ") for t in h_aq["time"]],
                "station": name,
                "district_zone": zone,
                "city": "Hyderabad",
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
                "pblh": h_meteo["boundary_layer_height"]
            })
            print(f"  Collected {len(df):,} hours for GHMC zone {name}")
            return df
    except Exception as e:
        print(f"Error for zone {name}: {e}")
    return pd.DataFrame()

def build_hyderabad_dataset():
    station_dfs = []

    # 1. Download & Process 14 Physical TSPCB Stations
    print("\n--- PHASE 1: Official TSPCB Continuous Monitoring Stations ---")
    for st in TSPCB_HYD_STATIONS:
        df_st = process_tspcb_file(st)
        if not df_st.empty:
            station_dfs.append(df_st)
        time.sleep(0.3)

    # 2. Backfill Core GHMC Urban Centers
    print("\n--- PHASE 2: Additional GHMC Urban Zones Backfill ---")
    for zone in ADDITIONAL_GHMC_ZONES:
        df_z = fetch_openmeteo_ghmc_zone(zone)
        if not df_z.empty:
            station_dfs.append(df_z)
        time.sleep(0.5)

    if not station_dfs:
        print("Error: No data frames collected.")
        return

    # 3. Combine All Hyderabad Stations & Districts
    print("\n--- PHASE 3: Merging & Atmospheric Physics Calculation ---")
    hyd_df = pd.concat(station_dfs, ignore_index=True)

    # Fetch Hyderabad PBLH lookup for TSPCB stations
    df_pblh = fetch_hyderabad_pblh_lookup()
    if not df_pblh.empty:
        hyd_df["timestamp_clean"] = hyd_df["timestamp"].astype(str).str.slice(0, 13).str.replace(" ", "T")
        df_pblh["pblh_clean"] = df_pblh["pblh_time"].astype(str).str.slice(0, 13)
        
        # Merge PBLH where missing
        merged = pd.merge(hyd_df, df_pblh, left_on="timestamp_clean", right_on="pblh_clean", how="left")
        if "pblh_x" in merged.columns and "pblh_y" in merged.columns:
            merged["pblh"] = merged["pblh_x"].fillna(merged["pblh_y"])
            hyd_df["pblh"] = merged["pblh"].fillna(850.0)
        elif "pblh" not in hyd_df.columns:
            hyd_df["pblh"] = merged["pblh"].fillna(850.0)

    # Clean numeric fields
    hyd_df["pm25"] = pd.to_numeric(hyd_df["pm25"], errors="coerce")
    hyd_df = hyd_df.dropna(subset=["pm25"])
    hyd_df["pm10"] = pd.to_numeric(hyd_df["pm10"], errors="coerce").fillna(hyd_df["pm25"] * 1.5)
    hyd_df["temp"] = pd.to_numeric(hyd_df.get("temp", 28.0), errors="coerce").fillna(28.0)
    hyd_df["humidity"] = pd.to_numeric(hyd_df.get("humidity", 55.0), errors="coerce").fillna(55.0)
    hyd_df["pressure"] = pd.to_numeric(hyd_df.get("pressure", 1008.0), errors="coerce").fillna(1008.0)
    hyd_df["wind_speed"] = pd.to_numeric(hyd_df.get("wind_speed", 2.5), errors="coerce").fillna(2.5)
    hyd_df["pblh"] = pd.to_numeric(hyd_df.get("pblh", 850.0), errors="coerce").fillna(850.0)

    # Physics Features:
    hyd_df["ventilation_index"] = hyd_df["pblh"] * hyd_df["wind_speed"]
    hyd_df["pm_ratio"] = hyd_df["pm25"] / (hyd_df["pm10"] + 1e-5)

    # Sort strictly by station and timestamp
    hyd_df = hyd_df.sort_values(by=["station", "timestamp"])

    # 4. Save to Disk
    parquet_path = DATA_DIR / "hyderabad_district_dataset.parquet"
    csv_path = DATA_DIR / "hyderabad_district_dataset.csv"
    active_dataset_csv = DATA_DIR / "dataset.csv"

    print(f"\nWriting Hyderabad District Datasets...")
    hyd_df.to_parquet(parquet_path, index=False)
    hyd_df.to_csv(csv_path, index=False)
    
    # Also update Aervia's active dataset.csv
    hyd_df.to_csv(active_dataset_csv, index=False)

    print(f"Saved Hyderabad Master Parquet to: {parquet_path} ({parquet_path.stat().st_size / (1024 * 1024):.2f} MB)")
    print(f"Saved Hyderabad Master CSV to: {csv_path}")
    print(f"Updated active Aervia dataset at: {active_dataset_csv}")
    print(f"\nSummary: {len(hyd_df):,} total hourly records across {hyd_df['station'].nunique()} unique Hyderabad stations/districts!")
    print("Unique Hyderabad Stations/Districts:")
    for st in hyd_df["station"].unique():
        count = len(hyd_df[hyd_df["station"] == st])
        print(f"  - {st}: {count:,} hourly records")

if __name__ == "__main__":
    build_hyderabad_dataset()

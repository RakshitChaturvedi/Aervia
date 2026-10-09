import requests
import pandas as pd
from datetime import datetime, timedelta
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_openaq_data(lat=28.6139, lon=77.2090, days_back=14):
    """
    Fetches real air quality data. 
    (Using Open-Meteo Air Quality API as OpenAQ v2 public endpoint is deprecated).
    """
    print(f"Fetching Air Quality data for coordinates {lat}, {lon} over the last {days_back} days...")
    
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
        "timezone": "UTC"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        hourly_data = data.get('hourly', {})
        if not hourly_data:
            print("No hourly data found.")
            return None
            
        df = pd.DataFrame({
            "timestamp": hourly_data['time'],
            "pm10": hourly_data['pm10'],
            "pm25": hourly_data['pm2_5'],
            "co": hourly_data['carbon_monoxide'],
            "no2": hourly_data['nitrogen_dioxide'],
            "so2": hourly_data['sulphur_dioxide'],
            "o3": hourly_data['ozone']
        })
        
        # Add mock location ID for compatibility
        df['station_id'] = "Delhi-Center"
        df['location'] = "Delhi"
        
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%dT%H:00:00+00:00')
        
        output_path = os.path.join(DATA_DIR, "openaq_sample.csv")
        df.to_csv(output_path, index=False)
        print(f"Saved Air Quality data to {output_path}")
        return df
        
    except Exception as e:
        print(f"Failed to fetch Air Quality data: {e}")
        return None

def fetch_openmeteo_data(lat=28.6139, lon=77.2090, days_back=7):
    """
    Fetches real weather data from Open-Meteo including boundary layer height (PBLH).
    Delhi coordinates: 28.6139, 77.2090
    """
    print(f"Fetching Open-Meteo data for coordinates {lat}, {lon}...")
    
    url = "https://archive-api.open-meteo.com/v1/era5"
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,boundary_layer_height",
        "timezone": "UTC"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        hourly_data = data.get('hourly', {})
        if not hourly_data:
            print("No hourly data found from Open-Meteo.")
            return None
            
        df = pd.DataFrame({
            "timestamp": hourly_data['time'],
            "temperature_2m": hourly_data['temperature_2m'],
            "relative_humidity_2m": hourly_data['relative_humidity_2m'],
            "wind_speed_10m": hourly_data['wind_speed_10m'],
            "wind_direction_10m": hourly_data['wind_direction_10m'],
            "boundary_layer_height": hourly_data['boundary_layer_height']
        })
        
        # Round time to hour to match OpenAQ if needed
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%dT%H:00:00+00:00')
        
        output_path = os.path.join(DATA_DIR, "openmeteo_sample.csv")
        df.to_csv(output_path, index=False)
        print(f"Saved Open-Meteo data to {output_path}")
        return df
        
    except Exception as e:
        print(f"Failed to fetch Open-Meteo data: {e}")
        return None

if __name__ == "__main__":
    print("--- Starting Data Fetch ---")
    openaq_df = fetch_openaq_data(days_back=14)
    meteo_df = fetch_openmeteo_data(days_back=14)
    print("--- Data Fetch Complete ---")

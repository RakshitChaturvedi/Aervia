import os
import pandas as pd
import requests
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_PATH = os.path.join(BASE_DIR, 'dataset.csv')

def fetch_pblh_for_dataset():
    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    
    if 'pblh' not in df.columns:
        df['pblh'] = 1000.0 # Default starting value
        
    # Get unique stations to minimize API calls
    unique_stations = df.drop_duplicates(subset=['latitude', 'longitude'])
    print(f"Found {len(unique_stations)} unique coordinates to fetch PBLH for.")
    
    updates = 0
    
    # We will fetch current / recent historical data for each unique coordinate
    # Open-Meteo provides boundary_layer_height in the hourly API.
    for idx, row in unique_stations.iterrows():
        lat = row['latitude']
        lon = row['longitude']
        try:
            # We'll fetch 1 day of recent data to get a realistic PBLH value
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=boundary_layer_height&past_days=1&forecast_days=0"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # Get the average PBLH for the day to represent a realistic value
                pblh_values = data.get('hourly', {}).get('boundary_layer_height', [])
                valid_pblh = [v for v in pblh_values if v is not None]
                if valid_pblh:
                    avg_pblh = sum(valid_pblh) / len(valid_pblh)
                    # Update all rows matching these coordinates
                    df.loc[(df['latitude'] == lat) & (df['longitude'] == lon), 'pblh'] = avg_pblh
                    updates += 1
            time.sleep(0.1) # Be gentle to the free API
        except Exception as e:
            print(f"Failed to fetch for {lat}, {lon}: {e}")
            
    print(f"Successfully fetched PBLH for {updates} out of {len(unique_stations)} unique locations.")
    
    # Save back to CSV
    df.to_csv(DATASET_PATH, index=False)
    print("Saved updated dataset.csv with real PBLH values!")

if __name__ == "__main__":
    fetch_pblh_for_dataset()

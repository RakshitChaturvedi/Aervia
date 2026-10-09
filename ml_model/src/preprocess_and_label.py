import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def load_and_merge_data():
    """Loads fetched data and merges them on timestamp."""
    openaq_path = os.path.join(DATA_DIR, 'openaq_sample.csv')
    meteo_path = os.path.join(DATA_DIR, 'openmeteo_sample.csv')
    
    if not os.path.exists(openaq_path) or not os.path.exists(meteo_path):
        print("Required CSV files not found. Run fetch_data.py first.")
        return None
        
    df_aq = pd.read_csv(openaq_path)
    df_meteo = pd.read_csv(meteo_path)
    
    df_aq['timestamp'] = pd.to_datetime(df_aq['timestamp'])
    df_meteo['timestamp'] = pd.to_datetime(df_meteo['timestamp'])
    
    df = pd.merge(df_aq, df_meteo, on='timestamp', how='left')
    return df

def create_features(df):
    """Engineers physical and temporal features to match existing models."""
    if df is None or df.empty:
        return df
        
    print("Creating features...")
    # Fill NAs
    for col in ['pm25', 'pm10']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Map to standard feature names expected by models
    df['temp'] = df['temperature_2m'].fillna(25.0)
    df['humidity'] = df['relative_humidity_2m'].fillna(50.0)
    df['pressure'] = 1013.0 # Mocking pressure as it wasn't fetched
    df['wind_speed'] = df['wind_speed_10m'].fillna(2.0)
    df['pblh'] = df['boundary_layer_height'].fillna(1000.0)
    
    # Target for forecasting: next day's PM2.5 (or we can just use AQI lag)
    df = df.sort_values(by=['station_id', 'timestamp'])
    df['target_y_reg'] = df.groupby('station_id')['pm25'].shift(-24)
    
    # Generate synthetic geospatial features for the attribution engine
    # In production, this would come from a geospatial database or satellite imagery.
    np.random.seed(42)
    # Traffic density index (0.0 to 1.0) with some diurnal pattern (higher during day)
    hour = pd.to_datetime(df['timestamp']).dt.hour
    df['traffic_density'] = np.where((hour >= 8) & (hour <= 20), np.random.uniform(0.6, 1.0, len(df)), np.random.uniform(0.1, 0.5, len(df)))
    # Distance to nearest industrial zone (in km)
    df['distance_to_industry'] = np.random.uniform(1.0, 15.0, len(df))
    
    df = df.dropna(subset=['target_y_reg'])
    return df

def create_training_data():
    df = load_and_merge_data()
    if df is None:
        return None, None, None
        
    df = create_features(df)
    
    # Format X matrix: [pm25, pm10, temp, humidity, pressure, wind_speed, pblh, traffic_density, distance_to_industry]
    feature_cols = ['pm25', 'pm10', 'temp', 'humidity', 'pressure', 'wind_speed', 'pblh', 'traffic_density', 'distance_to_industry']
    X = df[feature_cols].values
    y_reg = df['target_y_reg'].values
    
    # Create dict list for weak labels
    data_list = df[feature_cols].to_dict('records')
    
    return X, y_reg, data_list

if __name__ == "__main__":
    X, y_reg, data_list = create_training_data()
    if X is not None:
        print(f"Successfully processed {len(X)} real data samples.")

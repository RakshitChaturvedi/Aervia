import pandas as pd
import numpy as np

def add_temporal_lags(df):
    """Adds historical lag features for PM2.5 and AQI."""
    # Ensure dataframe is sorted by time
    df = df.sort_values(by=['district_id', 'timestamp'])
    
    # PM2.5 Lags
    df['pm25_lag_1h'] = df.groupby('district_id')['pm25'].shift(1)
    df['pm25_lag_3h'] = df.groupby('district_id')['pm25'].shift(3)
    df['pm25_lag_6h'] = df.groupby('district_id')['pm25'].shift(6)
    df['pm25_lag_12h'] = df.groupby('district_id')['pm25'].shift(12)
    df['pm25_lag_24h'] = df.groupby('district_id')['pm25'].shift(24)
    
    # Target Lags (useful if forecasting AQI directly)
    if 'aqi_in' in df.columns:
        df['aqi_lag_24h'] = df.groupby('district_id')['aqi_in'].shift(24)
        
    return df

def add_rolling_stats(df):
    """Adds rolling window statistics."""
    df = df.sort_values(by=['district_id', 'timestamp'])
    
    # 6-hour and 24-hour rolling means
    df['pm25_rolling_6h_mean'] = df.groupby('district_id')['pm25'].transform(lambda x: x.rolling(window=6, min_periods=1).mean())
    df['pm25_rolling_24h_mean'] = df.groupby('district_id')['pm25'].transform(lambda x: x.rolling(window=24, min_periods=1).mean())
    
    # 24-hour rolling standard deviation (volatility)
    df['pm25_rolling_24h_std'] = df.groupby('district_id')['pm25'].transform(lambda x: x.rolling(window=24, min_periods=1).std().fillna(0))
    
    # Momentum / Delta
    if 'pm25_lag_6h' in df.columns:
        df['pm25_delta_6h'] = df['pm25'] - df['pm25_lag_6h']
        
    return df

def add_cyclic_encodings(df):
    """Encodes time of day and time of year as cyclic sine/cosine features."""
    # Convert timestamp to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    # Hour of day (0-23)
    hours = df['timestamp'].dt.hour
    df['hour_sin'] = np.sin(2 * np.pi * hours / 24)
    df['hour_cos'] = np.cos(2 * np.pi * hours / 24)
    
    # Month of year (1-12)
    months = df['timestamp'].dt.month
    df['month_sin'] = np.sin(2 * np.pi * months / 12)
    df['month_cos'] = np.cos(2 * np.pi * months / 12)
    
    return df

def add_atmospheric_physics(df):
    """Derives physics-based features like Ventilation Index."""
    # Ventilation Index = Planetary Boundary Layer Height * Wind Speed
    # Higher VI = Better mixing/dispersion
    if 'pblh' in df.columns and 'wind_speed_ms' in df.columns:
        df['ventilation_index'] = df['pblh'] * df['wind_speed_ms']
        
        # Stagnation flag: VI < 2000 is generally considered poor dispersion
        df['stagnation_flag'] = (df['ventilation_index'] < 2000).astype(int)
        
    # PM Ratio
    if 'pm25' in df.columns and 'pm10' in df.columns:
        epsilon = 1e-5
        df['pm_ratio'] = df['pm25'] / (df['pm10'] + epsilon)
        
    return df

def add_pollutant_ratios(df):
    """Adds chemical ratios used for source fingerprinting."""
    epsilon = 1e-5
    
    if 'no2' in df.columns and 'so2' in df.columns:
        df['no2_so2_ratio'] = df['no2'] / (df['so2'] + epsilon)
        
    if 'co' in df.columns and 'no2' in df.columns:
        df['co_no2_ratio'] = df['co'] / (df['no2'] + epsilon)
        
    if 'o3' in df.columns and 'pm25' in df.columns:
        df['o3_pm25_ratio'] = df['o3'] / (df['pm25'] + epsilon)
        
    return df

def build_features(df):
    """Orchestrates the entire feature engineering pipeline."""
    print("Starting feature engineering...")
    
    # 1. Base physics & ratios
    df = add_atmospheric_physics(df)
    df = add_pollutant_ratios(df)
    
    # 2. Time encodings
    df = add_cyclic_encodings(df)
    
    # 3. Lags & Rolling (must be done per district, sorted by time)
    df = add_temporal_lags(df)
    df = add_rolling_stats(df)
    
    # 4. Drop initial rows that have NaN due to lags (e.g., first 24 hours per district)
    original_len = len(df)
    df = df.dropna(subset=['pm25_lag_24h'])
    new_len = len(df)
    print(f"Dropped {original_len - new_len} rows due to lag NaNs.")
    
    print(f"Feature engineering complete. Output shape: {df.shape}")
    return df

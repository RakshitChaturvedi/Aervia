import pandas as pd
import numpy as np

def assign_source_labels(df):
    """
    Improved weak-supervision labeling using a multi-signal heuristic engine.
    This creates the ground truth target column for the Source Attribution Classifier.
    
    Categories:
    - vehicular
    - industrial
    - dust (construction/road dust)
    - biomass_burning
    - secondary_photochemical
    """
    print("Assigning source labels...")
    
    # Ensure required derived features exist
    if 'pm_ratio' not in df.columns:
        df['pm_ratio'] = df['pm25'] / (df['pm10'] + 1e-5)
    
    # Initialize scores for each category
    scores = pd.DataFrame(index=df.index)
    scores['vehicular'] = 0.0
    scores['industrial'] = 0.0
    scores['dust'] = 0.0
    scores['biomass_burning'] = 0.0
    scores['secondary_photochemical'] = 0.0
    
    # --- VEHICULAR HEURISTICS ---
    # High PM2.5/PM10 ratio, elevated NO2, high CO, morning/evening peaks
    scores['vehicular'] += np.where(df['pm_ratio'] >= 0.65, 1.0, 0.0)
    scores['vehicular'] += np.where(df['no2'] > df['no2'].quantile(0.7), 1.0, 0.0)
    scores['vehicular'] += np.where(df['co'] > df['co'].quantile(0.7), 0.5, 0.0)
    
    hour = pd.to_datetime(df['timestamp']).dt.hour
    is_rush_hour = ((hour >= 7) & (hour <= 10)) | ((hour >= 17) & (hour <= 21))
    scores['vehicular'] += np.where(is_rush_hour, 0.5, 0.0)
    
    # --- INDUSTRIAL HEURISTICS ---
    # Elevated SO2, steady emission (not rush hour dependent), low PM ratio
    scores['industrial'] += np.where(df['so2'] > df['so2'].quantile(0.75), 1.5, 0.0)
    scores['industrial'] += np.where((df['pm_ratio'] >= 0.4) & (df['pm_ratio'] <= 0.65), 0.5, 0.0)
    scores['industrial'] += np.where(~is_rush_hour, 0.5, 0.0) # More prominent at night/off-peak when traffic dies down
    
    # --- DUST / CONSTRUCTION HEURISTICS ---
    # Low PM ratio (mostly coarse particles), high PM10, dry conditions
    scores['dust'] += np.where(df['pm_ratio'] < 0.45, 1.5, 0.0)
    scores['dust'] += np.where(df['humidity'] < 50, 0.5, 0.0)
    scores['dust'] += np.where(df['wind_speed_ms'] > df['wind_speed_ms'].quantile(0.8), 0.5, 0.0) # Wind kicks up dust
    
    # --- BIOMASS BURNING HEURISTICS ---
    # Very high PM ratio, high CO, low temp/high humidity (winter inversions), high AOD if available
    scores['biomass_burning'] += np.where(df['pm_ratio'] > 0.8, 1.0, 0.0)
    scores['biomass_burning'] += np.where(df['co'] > df['co'].quantile(0.8), 1.0, 0.0)
    scores['biomass_burning'] += np.where(df['temp_c'] < 20, 0.5, 0.0) # Common in winter mornings
    
    if 'aod' in df.columns:
        scores['biomass_burning'] += np.where(df['aod'] > 0.5, 1.0, 0.0)
        
    # --- SECONDARY PHOTOCHEMICAL HEURISTICS ---
    # High O3, high temperature, high UV (afternoon)
    scores['secondary_photochemical'] += np.where(df['o3'] > df['o3'].quantile(0.75), 1.5, 0.0)
    scores['secondary_photochemical'] += np.where(df['temp_c'] > 30, 0.5, 0.0)
    
    is_afternoon = (hour >= 12) & (hour <= 16)
    scores['secondary_photochemical'] += np.where(is_afternoon, 0.5, 0.0)
    
    # Add some random noise to break ties and prevent the ML model from just learning deterministic thresholds
    np.random.seed(42)
    noise = np.random.uniform(0, 0.1, size=scores.shape)
    scores = scores + noise
    
    # Assign primary source based on highest score
    df['primary_source'] = scores.idxmax(axis=1)
    
    # Quality check
    dist = df['primary_source'].value_counts(normalize=True) * 100
    print("Assigned Source Distribution:")
    for source, pct in dist.items():
        print(f"  - {source}: {pct:.1f}%")
        
    return df

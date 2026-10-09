import os
import sys
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestClassifier
from mapie.regression import SplitConformalRegressor
from mapie.classification import SplitConformalClassifier
from sklearn.model_selection import train_test_split

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ML_DATA_DIR = os.path.join(BASE_DIR, 'ml_model', 'data')
DATASET_PATH = os.path.join(BASE_DIR, 'dataset.csv')

os.makedirs(ML_DATA_DIR, exist_ok=True)

def load_and_prepare_data():
    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    
    # Extract needed columns based on what's available
    # Available in dataset: pm25, pm10, temp_c, humidity, pressure_mb, wind_kph
    df = df.rename(columns={
        'temp_c': 'temp',
        'pressure_mb': 'pressure'
    })
    
    # Calculate wind_speed in m/s from kph
    df['wind_speed'] = df['wind_kph'] / 3.6
    
    # Fill any NaNs
    for col in ['pm25', 'pm10', 'temp', 'humidity', 'pressure', 'wind_speed', 'aqi']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(df[col].median() if not df[col].isnull().all() else 0)

    # Ensure pblh exists (it should be populated by fetch_pblh.py)
    if 'pblh' not in df.columns:
        print("Warning: pblh column missing! Please run fetch_pblh.py first.")
        df['pblh'] = 1000.0
    
    # Ensure Date is parsed
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        df['Date'] = pd.to_datetime('today')
        
    # Sort chronologically to prepare for time-series shift
    df = df.sort_values(by=['station', 'Date'])
    
    # 1. Forecast Target: True 24h, 48h, 72h Future PM2.5 based on historical dataset trends
    df['target_pm25_24h'] = df.groupby('station')['pm25'].shift(-1)
    df['target_pm25_48h'] = df.groupby('station')['pm25'].shift(-2)
    df['target_pm25_72h'] = df.groupby('station')['pm25'].shift(-3)
    
    # Drop rows where we don't have all next 3 days
    df = df.dropna(subset=['target_pm25_24h', 'target_pm25_48h', 'target_pm25_72h'])

    
    # 2. Classification Target: Pollution Source
    # Let's create a heuristic so the model learns from the clean features
    sources = []
    for _, row in df.iterrows():
        ratio = row['pm25'] / (row['pm10'] + 1e-5)
        if ratio > 0.8:
            sources.append("vehicular")
        elif row['temp'] > 35 and row['humidity'] < 40:
            sources.append("dust")
        elif row.get('co', 0) > 300:
            sources.append("biomass")
        else:
            sources.append("industrial")
            
    df['target_source'] = sources
    
    # The required EXACT feature order
    features = ['pm25', 'pm10', 'temp', 'humidity', 'pressure', 'wind_speed', 'pblh']
    
    # Extract City from station string (e.g. "Soni Ni Chali, Ahmedabad, Gujarat, India")
    df['city'] = df['station'].apply(lambda x: [part.strip() for part in x.split(',')][1] if len(x.split(',')) > 1 else 'Unknown')
    
    return df, features


def train_models():
    df, features = load_and_prepare_data()
    
    cities_to_train = ['Delhi', 'Bangalore', 'Hyderabad']
    
    print("Training Random Forest Classifier with MAPIE...")
    # Train one global classifier
    X_clf = df[features]
    y_clf = df['target_source']
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_clf, y_clf, test_size=0.2, random_state=42)
    
    rfc = RandomForestClassifier(n_estimators=100, random_state=42)
    mapie_clf = SplitConformalClassifier(estimator=rfc)
    
    X_train_clf_sub, X_cal_clf, y_train_clf_sub, y_cal_clf = train_test_split(X_train_c, y_train_c, test_size=0.3, random_state=42)
    rfc.fit(X_train_clf_sub, y_train_clf_sub)
    mapie_clf.conformalize(X_cal_clf, y_cal_clf)
    joblib.dump(mapie_clf, os.path.join(ML_DATA_DIR, 'classifier_v2.pkl'))
    
    # Base model (using all data)
    print("Training Global Base XGBoost Forecasters...")
    for label, target_col in [('24h', 'target_pm25_24h'), ('48h', 'target_pm25_48h'), ('72h', 'target_pm25_72h')]:
        X_all = df[features]
        y_all = df[target_col]
        X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
        xgb = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
        mapie_reg = SplitConformalRegressor(estimator=xgb)
        
        X_train_reg_sub, X_cal_reg, y_train_reg_sub, y_cal_reg = train_test_split(X_train_r, y_train_r, test_size=0.3, random_state=42)
        xgb.fit(X_train_reg_sub, y_train_reg_sub)
        mapie_reg.conformalize(X_cal_reg, y_cal_reg)
        
        joblib.dump(mapie_reg, os.path.join(ML_DATA_DIR, f'forecast_model_{label}.pkl'))
    
    print("Training City-Specific XGBoost Forecasters...")
    for city in cities_to_train:
        city_df = df[df['city'] == city]
        if city_df.empty:
            print(f"Skipping {city}, no data.")
            continue
            
        # Standardize 'Bangalore' to 'Bengaluru' for the filename matching the backend expectation
        city_name = "Bengaluru" if city == "Bangalore" else city
        
        for label, target_col in [('24h', 'target_pm25_24h'), ('48h', 'target_pm25_48h'), ('72h', 'target_pm25_72h')]:
            X_city = city_df[features]
            y_city = city_df[target_col]
            X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_city, y_city, test_size=0.2, random_state=42)
            
            xgb = XGBRegressor(n_estimators=50, learning_rate=0.1, random_state=42)
            mapie_reg = SplitConformalRegressor(estimator=xgb)
            
            X_train_reg_sub, X_cal_reg, y_train_reg_sub, y_cal_reg = train_test_split(X_train_r, y_train_r, test_size=0.3, random_state=42)
            xgb.fit(X_train_reg_sub, y_train_reg_sub)
            mapie_reg.conformalize(X_cal_reg, y_cal_reg)
            
            model_path = os.path.join(ML_DATA_DIR, f'forecast_model_{city_name.lower()}_{label}.pkl')
            joblib.dump(mapie_reg, model_path)
            print(f"Saved {model_path}")
            
    print("Models successfully trained and saved!")

if __name__ == "__main__":
    train_models()

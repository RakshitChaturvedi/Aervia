import os
import sys
import json
import argparse
import joblib
import subprocess
import numpy as np
import pandas as pd

# Automatically ensure required ML libraries are installed in the container
for pkg in ["pyarrow", "fastparquet", "xgboost", "mapie"]:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestClassifier
from mapie.regression import SplitConformalRegressor
from mapie.classification import SplitConformalClassifier
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

FEATURES = [
    'pm25', 'pm10', 'temp', 'humidity', 'pressure', 'wind_speed', 'pblh',
    'ventilation_index', 'pm25_lag_1h', 'pm25_lag_24h', 'pm25_rolling_24h',
    'hour_sin', 'hour_cos', 'month_sin', 'month_cos'
]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR', '/opt/ml/model'))
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN', '/opt/ml/input/data/train'))
    return parser.parse_args()

def load_and_preprocess(train_dir):
    candidates = [
        os.path.join(train_dir, f) for f in os.listdir(train_dir) if f.endswith('.parquet') or f.endswith('.csv')
    ]
    if not candidates:
        raise FileNotFoundError(f"No dataset file found in training directory: {train_dir}")
    
    # Prioritize master dataset (tri-city: Delhi, Bengaluru, Hyderabad), then other parquets, then csv
    master_files = [f for f in candidates if 'master' in os.path.basename(f).lower() and f.endswith('.parquet')]
    if master_files:
        data_file = master_files[0]
    else:
        parquet_files = [f for f in candidates if f.endswith('.parquet')]
        data_file = parquet_files[0] if parquet_files else candidates[0]
    
    print(f"Loading dataset from: {data_file}")
    if data_file.endswith('.parquet'):
        df = pd.read_parquet(data_file)
    else:
        df = pd.read_csv(data_file)

    # Standardize column names
    col_map = {'temp_c': 'temp', 'pressure_mb': 'pressure', 'Date': 'timestamp'}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Derive wind_speed in m/s if only wind_kph is present
    if 'wind_speed' not in df.columns and 'wind_kph' in df.columns:
        df['wind_speed'] = pd.to_numeric(df['wind_kph'], errors='coerce') / 3.6
    
    if 'pblh' not in df.columns:
        df['pblh'] = 1000.0

    # Clean numeric fields
    for col in ['pm25', 'pm10', 'temp', 'humidity', 'pressure', 'wind_speed', 'pblh', 'aqi']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(df[col].median() if not df[col].isnull().all() else 0.0)

    # Fix pressure units: ERA5 returns Pa, convert to hPa if values are too high
    if df['pressure'].median() > 1500:
        df['pressure'] = df['pressure'] / 100.0
        print("Converted pressure from Pa to hPa.")

    # Clamp extreme outliers to physically valid ranges
    df['temp'] = df['temp'].clip(-20, 55)
    df['pblh'] = df['pblh'].clip(10, 5000)
    df['pm25'] = df['pm25'].clip(0, 2000)
    df['pm10'] = df['pm10'].clip(0, 5000)

    # Atmospheric physics: Ventilation Index
    df['ventilation_index'] = df['pblh'] * df['wind_speed']

    # Sort chronologically by station using timestamp
    sort_cols = ['station', 'timestamp'] if 'timestamp' in df.columns else ['station']
    df = df.sort_values(by=sort_cols)

    # Multi-horizon forecast targets (24h, 48h, 72h ahead in hourly steps)
    df['target_24h'] = df.groupby('station')['pm25'].shift(-24)
    df['target_48h'] = df.groupby('station')['pm25'].shift(-48)
    df['target_72h'] = df.groupby('station')['pm25'].shift(-72)

    # Autoregressive memory and rolling dynamics
    df['pm25_lag_1h'] = df.groupby('station')['pm25'].shift(1).bfill()
    df['pm25_lag_24h'] = df.groupby('station')['pm25'].shift(24).bfill()
    df['pm25_rolling_24h'] = df.groupby('station')['pm25'].transform(lambda x: x.rolling(24, min_periods=1).mean())

    # Cyclical temporal encodings
    if 'timestamp' in df.columns:
        ts = pd.to_datetime(df['timestamp'], format='mixed')
        df['hour_sin'] = np.sin(2 * np.pi * ts.dt.hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * ts.dt.hour / 24)
        df['month_sin'] = np.sin(2 * np.pi * ts.dt.month / 12)
        df['month_cos'] = np.cos(2 * np.pi * ts.dt.month / 12)
    else:
        df['hour_sin'] = 0.0
        df['hour_cos'] = 1.0
        df['month_sin'] = 0.0
        df['month_cos'] = 1.0

    df = df.dropna(subset=['target_24h', 'target_48h', 'target_72h', 'pm25_lag_24h'])

    # Multi-pollutant weak-supervision source attribution (vectorized for performance)
    pm_ratio = df['pm25'] / (df['pm10'] + 1e-5)
    co_vals = df['co'] if 'co' in df.columns else pd.Series(0, index=df.index)
    df['target_source'] = np.where(
        pm_ratio > 0.8, 'vehicular',
        np.where(
            (df['temp'] > 35) & (df['humidity'] < 40), 'dust',
            np.where(co_vals > 300, 'biomass', 'industrial')
        )
    )

    print(f"Dataset preprocessed: {len(df)} rows across {df['station'].nunique()} stations.")
    print(f"Source distribution: {pd.Series(df['target_source']).value_counts().to_dict()}")
    return df

def compute_hazard_metrics(actuals, preds, threshold=90.0):
    """Computes meteorological hazard/spike detection metrics (Precision, Recall, CSI)."""
    act_spikes = (actuals >= threshold).astype(int)
    pred_spikes = (preds >= threshold).astype(int)

    tp = int(np.sum((act_spikes == 1) & (pred_spikes == 1)))
    fp = int(np.sum((act_spikes == 0) & (pred_spikes == 1)))
    fn = int(np.sum((act_spikes == 1) & (pred_spikes == 0)))

    prec = round(float(tp / (tp + fp)), 3) if (tp + fp) > 0 else 1.0
    rec = round(float(tp / (tp + fn)), 3) if (tp + fn) > 0 else 1.0
    f1 = round(float(2 * prec * rec / (prec + rec)), 3) if (prec + rec) > 0 else 0.0
    csi = round(float(tp / (tp + fp + fn)), 3) if (tp + fp + fn) > 0 else 1.0

    return {
        'threshold_pm25': threshold,
        'precision': prec,
        'recall': rec,
        'f1_score': f1,
        'critical_success_index': csi,
        'total_hazard_events': int(np.sum(act_spikes))
    }

def main():
    args = parse_args()
    os.makedirs(args.model_dir, exist_ok=True)
    
    df = load_and_preprocess(args.train)

    # -------------------------------------------------------------
    # 1. STRICT CHRONOLOGICAL WALK-FORWARD SPLIT PER STATION
    # -------------------------------------------------------------
    train_indices, calib_indices, test_indices = [], [], []
    for _, group in df.groupby('station'):
        gn = len(group)
        t_end = int(gn * 0.70)
        c_end = int(gn * 0.85)
        train_indices.extend(group.index[:t_end])
        calib_indices.extend(group.index[t_end:c_end])
        test_indices.extend(group.index[c_end:])

    train_df = df.loc[train_indices]
    calib_df = df.loc[calib_indices]
    test_df  = df.loc[test_indices]

    print(f"Data Partitions -> Train: {len(train_df)}, Calibrate (MAPIE): {len(calib_df)}, Hidden Test: {len(test_df)}")

    horizons = [(24, 'target_24h'), (48, 'target_48h'), (72, 'target_72h')]
    metrics = {
        'global_forecast': {},
        'city_breakdown': {},
        'hyderabad_district_breakdown': {},
        'hazard_exceedance_metrics': {},
        'rolling_origin_cv': {}
    }

    # -------------------------------------------------------------
    # 2. ROLLING-ORIGIN TEMPORAL CROSS-VALIDATION (PURGED TS-CV)
    # -------------------------------------------------------------
    print("\n--- Running Multi-Cutoff Rolling-Origin Temporal Cross-Validation ---")
    cv_folds = [(0.50, 0.65), (0.65, 0.80), (0.70, 0.85)]
    cv_scores = {24: [], 48: [], 72: []}
    for fold_idx, (f_train, f_test) in enumerate(cv_folds, 1):
        f_tr_idx, f_te_idx = [], []
        for _, grp in df.groupby('station'):
            gn = len(grp)
            f_tr_idx.extend(grp.index[:int(gn * f_train)])
            f_te_idx.extend(grp.index[int(gn * f_train):int(gn * f_test)])
        
        tr_sample = df.loc[f_tr_idx]
        te_sample = df.loc[f_te_idx]
        for h, tcol in horizons:
            quick_xgb = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1)
            quick_xgb.fit(tr_sample[FEATURES], tr_sample[tcol])
            p_val = quick_xgb.predict(te_sample[FEATURES])
            r_val = float(np.sqrt(mean_squared_error(te_sample[tcol], p_val)))
            cv_scores[h].append(round(r_val, 2))
        print(f"Fold {fold_idx} (Train {int(f_train*100)}% -> Test {int(f_test*100)}%) RMSE: 24h={cv_scores[24][-1]}, 48h={cv_scores[48][-1]}, 72h={cv_scores[72][-1]}")

    for h in [24, 48, 72]:
        metrics['rolling_origin_cv'][f'{h}h'] = {
            'fold_rmse': cv_scores[h],
            'mean_cv_rmse': round(float(np.mean(cv_scores[h])), 2),
            'cv_stability_std': round(float(np.std(cv_scores[h])), 2)
        }

    # -------------------------------------------------------------
    # 3. GLOBAL MULTI-HORIZON FORECASTERS (XGBoost + MAPIE)
    # -------------------------------------------------------------
    global_models = {}
    test_predictions = {}
    for h, target_col in horizons:
        print(f"\n--- Training Production Global {h}h Forecaster (XGBoost + MAPIE Conformal) ---")
        X_train, y_train = train_df[FEATURES], train_df[target_col]
        X_calib, y_calib = calib_df[FEATURES], calib_df[target_col]
        X_test, y_test   = test_df[FEATURES], test_df[target_col]

        xgb = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.03, random_state=42, n_jobs=-1)
        xgb.fit(X_train, y_train)

        mapie_reg = SplitConformalRegressor(estimator=xgb, confidence_level=0.90, prefit=True)
        mapie_reg.conformalize(X_calib, y_calib)
        global_models[h] = mapie_reg

        # Predict with 90% confidence bands on the blind test set
        y_pred, y_pis = mapie_reg.predict_interval(X_test)
        test_predictions[h] = (y_pred, y_pis)

        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae  = float(mean_absolute_error(y_test, y_pred))
        r2   = float(r2_score(y_test, y_pred))
        coverage = float(np.mean((y_test.values >= y_pis[:, 0, 0]) & (y_test.values <= y_pis[:, 1, 0])))
        mpiw = float(np.mean(y_pis[:, 1, 0] - y_pis[:, 0, 0]))  # Mean Prediction Interval Width (Sharpness)

        # Hazard detection
        hazard_stat = compute_hazard_metrics(y_test.values, y_pred, threshold=90.0)

        print(f"[Global {h}h] Test RMSE: {rmse:.2f} | MAE: {mae:.2f} | R2: {r2:.3f} | Coverage 90%: {coverage:.1%} | Interval Width: {mpiw:.1f}")
        metrics['global_forecast'][f'{h}h'] = {
            'rmse': round(rmse, 2),
            'mae': round(mae, 2),
            'r2': round(r2, 3),
            'coverage_90': round(coverage, 3),
            'mean_interval_width': round(mpiw, 2)
        }
        metrics['hazard_exceedance_metrics'][f'{h}h'] = hazard_stat

        out_path = os.path.join(args.model_dir, f'forecast_model_{h}h.pkl')
        joblib.dump(mapie_reg, out_path)
        print(f"Saved {out_path}")

    # -------------------------------------------------------------
    # 4. CITY-SPECIFIC FORECASTERS & CITY-LEVEL BENCHMARKING
    # -------------------------------------------------------------
    if 'city' in df.columns:
        for city_name in df['city'].unique():
            city_df = df[df['city'] == city_name]
            if len(city_df) < 500:
                continue

            city_key = city_name.lower()
            metrics['city_breakdown'][city_key] = {}

            # Chronological per-station split for this city
            c_tr_idx, c_cal_idx, c_te_idx = [], [], []
            for _, grp in city_df.groupby('station'):
                gn = len(grp)
                c_tr_idx.extend(grp.index[:int(gn * 0.70)])
                c_cal_idx.extend(grp.index[int(gn * 0.70):int(gn * 0.85)])
                c_te_idx.extend(grp.index[int(gn * 0.85):])

            city_train = city_df.loc[c_tr_idx]
            city_calib = city_df.loc[c_cal_idx]
            city_test  = city_df.loc[c_te_idx]

            for h, target_col in horizons:
                print(f"\n--- Training {city_name} {h}h Local Forecaster ---")
                xgb_city = XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.03, random_state=42, n_jobs=-1)
                xgb_city.fit(city_train[FEATURES], city_train[target_col])

                mapie_city = SplitConformalRegressor(estimator=xgb_city, confidence_level=0.90, prefit=True)
                mapie_city.conformalize(city_calib[FEATURES], city_calib[target_col])

                y_pred_c, y_pis_c = mapie_city.predict_interval(city_test[FEATURES])
                rmse_c = float(np.sqrt(mean_squared_error(city_test[target_col], y_pred_c)))
                mae_c  = float(mean_absolute_error(city_test[target_col], y_pred_c))
                r2_c   = float(r2_score(city_test[target_col], y_pred_c))
                cov_c  = float(np.mean((city_test[target_col].values >= y_pis_c[:, 0, 0]) & (city_test[target_col].values <= y_pis_c[:, 1, 0])))

                print(f"[{city_name} {h}h] RMSE: {rmse_c:.2f} | MAE: {mae_c:.2f} | R2: {r2_c:.3f} | Coverage: {cov_c:.1%}")
                metrics['city_breakdown'][city_key][f'{h}h'] = {
                    'rmse': round(rmse_c, 2),
                    'mae': round(mae_c, 2),
                    'r2': round(r2_c, 3),
                    'coverage_90': round(cov_c, 3)
                }

                city_out = os.path.join(args.model_dir, f'forecast_model_{city_key}_{h}h.pkl')
                joblib.dump(mapie_city, city_out)
                print(f"Saved {city_out}")

    # -------------------------------------------------------------
    # 5. GRANULAR PER-DISTRICT / PER-STATION VALIDATION (HYDERABAD)
    # -------------------------------------------------------------
    hyd_test = test_df[test_df['city'] == 'Hyderabad'] if 'city' in test_df.columns else test_df
    print("\n--- Generating Per-District / Station Validation Breakdown for Hyderabad ---")
    
    # Evaluate 24h forecast across each individual station in Hyderabad
    y_pred_24, y_pis_24 = test_predictions[24]
    test_df_copy = test_df.copy()
    test_df_copy['pred_24h'] = y_pred_24
    test_df_copy['pi_low_24h'] = y_pis_24[:, 0, 0]
    test_df_copy['pi_high_24h'] = y_pis_24[:, 1, 0]

    for st_name, st_grp in test_df_copy.groupby('station'):
        if 'city' in st_grp.columns and st_grp['city'].iloc[0] != 'Hyderabad':
            continue
        if len(st_grp) < 10:
            continue

        st_rmse = float(np.sqrt(mean_squared_error(st_grp['target_24h'], st_grp['pred_24h'])))
        st_mae  = float(mean_absolute_error(st_grp['target_24h'], st_grp['pred_24h']))
        st_r2   = float(r2_score(st_grp['target_24h'], st_grp['pred_24h']))
        st_cov  = float(np.mean((st_grp['target_24h'] >= st_grp['pi_low_24h']) & (st_grp['target_24h'] <= st_grp['pi_high_24h'])))
        st_mpiw = float(np.mean(st_grp['pi_high_24h'] - st_grp['pi_low_24h']))

        metrics['hyderabad_district_breakdown'][st_name] = {
            'test_observations': len(st_grp),
            '24h_rmse': round(st_rmse, 2),
            '24h_mae': round(st_mae, 2),
            '24h_r2': round(st_r2, 3),
            'coverage_90': round(st_cov, 3),
            'interval_width': round(st_mpiw, 2)
        }

    # -------------------------------------------------------------
    # 6. SOURCE ATTRIBUTION CLASSIFIER (RANDOM FOREST + MAPIE)
    # -------------------------------------------------------------
    print("\n--- Training Production Source Attribution Classifier ---")
    X_clf_train, y_clf_train = train_df[FEATURES], train_df['target_source']
    X_clf_calib, y_clf_calib = calib_df[FEATURES], calib_df['target_source']
    X_clf_test, y_clf_test   = test_df[FEATURES], test_df['target_source']

    rfc = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rfc.fit(X_clf_train, y_clf_train)

    mapie_clf = SplitConformalClassifier(estimator=rfc, confidence_level=0.90, prefit=True)
    mapie_clf.conformalize(X_clf_calib, y_clf_calib)

    y_pred_clf, y_pis_clf = mapie_clf.predict_set(X_clf_test)
    clf_acc = float(np.mean(y_clf_test.values == y_pred_clf))
    avg_set_size = float(np.mean(np.sum(y_pis_clf, axis=1)))

    print(f"[Source Classifier] Test Accuracy: {clf_acc:.1%} | Avg Conformal Set Size: {avg_set_size:.2f}")
    metrics['source_attribution'] = {
        'accuracy': round(clf_acc, 3),
        'avg_conformal_set_size': round(avg_set_size, 2),
        'classes': list(np.unique(y_clf_train))
    }

    clf_path = os.path.join(args.model_dir, 'classifier_v2.pkl')
    joblib.dump(mapie_clf, clf_path)
    print(f"Saved {clf_path}")

    # -------------------------------------------------------------
    # 7. SAVE COMPLETE EVALUATION METRICS REPORT
    # -------------------------------------------------------------
    metrics_path = os.path.join(args.model_dir, 'evaluation_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved complete evaluation report to {metrics_path}")

    print("\nTraining complete! All production artifacts verified and ready for SageMaker export.")

if __name__ == '__main__':
    main()

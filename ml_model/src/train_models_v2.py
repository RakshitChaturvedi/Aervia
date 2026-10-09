import os
import sys
import subprocess

if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.abspath(__file__))
    train_script = os.path.join(src_dir, "train_models.py")
    subprocess.run([sys.executable, train_script], check=True)


def create_time_series_split(df, train_frac=0.7, calib_frac=0.15):
    """Splits data strictly chronologically to prevent leakage."""
    # Ensure sorted by time
    df = df.sort_values(by='timestamp')
    
    n = len(df)
    train_end = int(n * train_frac)
    calib_end = int(n * (train_frac + calib_frac))
    
    train_df = df.iloc[:train_end]
    calib_df = df.iloc[train_end:calib_end]
    test_df = df.iloc[calib_end:]
    
    print(f"Split sizes -> Train: {len(train_df)}, Calib: {len(calib_df)}, Test: {len(test_df)}")
    return train_df, calib_df, test_df

def prepare_data_for_horizon(df, horizon_h):
    """Creates the target variable shifted by horizon_h hours."""
    # Shift backwards to get future values as target
    df = df.sort_values(by=['district_id', 'timestamp'])
    
    target_col = f'target_{horizon_h}h'
    df[target_col] = df.groupby('district_id')['pm25'].shift(-horizon_h)
    
    # Drop rows where target is NaN (end of time series)
    df_clean = df.dropna(subset=[target_col] + FEATURES)
    return df_clean, target_col

def train_forecast_models():
    print("\n--- Training Forecast Models ---")
    df = pd.read_csv(DATA_PATH)
    df = build_features(df)
    
    horizons = [24, 48, 72]
    
    for h in horizons:
        print(f"\nTraining models for {h}h horizon...")
        df_h, target_col = prepare_data_for_horizon(df, h)
        
        train_df, calib_df, test_df = create_time_series_split(df_h)
        
        X_train, y_train = train_df[FEATURES], train_df[target_col]
        X_calib, y_calib = calib_df[FEATURES], calib_df[target_col]
        X_test, y_test = test_df[FEATURES], test_df[target_col]
        
        # 1. XGBoost
        xgb_model = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.03, random_state=42)
        xgb_model.fit(X_train, y_train)
        xgb_preds = xgb_model.predict(X_test)
        xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_preds))
        print(f"XGBoost RMSE: {xgb_rmse:.2f}")
        
        # 2. LightGBM
        lgb_model = lgb.LGBMRegressor(n_estimators=300, num_leaves=31, learning_rate=0.03, random_state=42)
        lgb_model.fit(X_train, y_train)
        lgb_preds = lgb_model.predict(X_test)
        lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_preds))
        print(f"LightGBM RMSE: {lgb_rmse:.2f}")
        
        # 3. CatBoost
        cb_model = CatBoostRegressor(iterations=300, depth=6, learning_rate=0.03, verbose=0, random_seed=42)
        cb_model.fit(X_train, y_train)
        cb_preds = cb_model.predict(X_test)
        cb_rmse = np.sqrt(mean_squared_error(y_test, cb_preds))
        print(f"CatBoost RMSE: {cb_rmse:.2f}")
        
        # Select best model
        models = {'xgboost': (xgb_model, xgb_rmse), 'lightgbm': (lgb_model, lgb_rmse), 'catboost': (cb_model, cb_rmse)}
        best_name, (best_model, best_rmse) = min(models.items(), key=lambda x: x[1][1])
        print(f"Best model for {h}h: {best_name} (RMSE: {best_rmse:.2f})")
        
        # Wrap in MAPIE for conformal prediction
        mapie_model = SplitConformalRegressor(estimator=best_model)
        mapie_model.conformalize(X_calib, y_calib)
        
        # Save model
        model_path = os.path.join(MODEL_DIR, f'forecast_model_{h}h.pkl')
        joblib.dump(mapie_model, model_path)
        print(f"Saved {h}h model to {model_path}")

def train_attribution_model():
    print("\n--- Training Source Attribution Classifier ---")
    df = pd.read_csv(DATA_PATH)
    df = build_features(df)
    df = assign_source_labels(df)
    
    # Drop rows with NaN features
    df = df.dropna(subset=FEATURES)
    
    train_df, calib_df, test_df = create_time_series_split(df)
    
    X_train, y_train = train_df[FEATURES], train_df['primary_source']
    X_calib, y_calib = calib_df[FEATURES], calib_df['primary_source']
    X_test, y_test = test_df[FEATURES], test_df['primary_source']
    
    # Train CatBoost Classifier on GPU for maximum accuracy
    from catboost import CatBoostClassifier
    rf_model = CatBoostClassifier(iterations=1000, depth=8, task_type='GPU', random_seed=42, verbose=50)
    rf_model.fit(X_train, y_train, eval_set=(X_calib, y_calib), early_stopping_rounds=50)
    
    preds = rf_model.predict(X_test)
    # CatBoost returns a 2D array for predictions sometimes e.g., [['vehicular'], ['dust']], flatten it:
    preds = [p[0] if isinstance(p, (list, np.ndarray)) else p for p in preds]
    acc = accuracy_score(y_test, preds)
    print(f"CatBoost GPU Accuracy: {acc:.2%}")
    
    # Wrap in MAPIE
    mapie_clf = SplitConformalClassifier(estimator=rf_model)
    mapie_clf.conformalize(X_calib, y_calib)
    
    model_path = os.path.join(MODEL_DIR, 'classifier_v2.pkl')
    joblib.dump(mapie_clf, model_path)
    print(f"Saved classifier to {model_path}")

if __name__ == "__main__":
    train_forecast_models()
    # train_attribution_model()

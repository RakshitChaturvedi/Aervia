import os
import sys
import pickle
import numpy as np

# Add src to python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from forecast import AQIForecaster
from classifier import SourceClassifier
from uncertainty import ConformalWrapper
from validation import (
    calculate_rmse,
    compare_persistence_baseline,
    calculate_js_divergence,
    calculate_wasserstein_distance
)
from preprocess_and_label import create_training_data

def main():
    print("Loading and preprocessing real data from APIs...")
    X, y_reg, data_list = create_training_data()
    
    if X is None or len(X) < 100:
        print("Not enough real data found! Make sure to run fetch_data.py and get enough samples.")
        print("We need at least 100 samples to train and calibrate. Exiting.")
        return
        
    print(f"Loaded {len(X)} samples of real data.")
    
    # Split into Train (80%), Calib (10%), Test (10%)
    n = len(X)
    train_idx = int(0.8 * n)
    calib_idx = int(0.9 * n)
    
    X_train, y_train_reg, data_train = X[:train_idx], y_reg[:train_idx], data_list[:train_idx]
    X_calib, y_calib_reg, data_calib = X[train_idx:calib_idx], y_reg[train_idx:calib_idx], data_list[train_idx:calib_idx]
    X_test, y_test_reg, data_test = X[calib_idx:], y_reg[calib_idx:], data_list[calib_idx:]
    
    # 1. FORECASTING
    print("\n--- Training Forecast Model (XGBoost) ---")
    forecaster = AQIForecaster(horizon_hours=24)
    forecaster.train(X_train, y_train_reg)
    
    print("Calibrating forecast model conformal intervals with MAPIE...")
    forecaster.conformal_wrapper = ConformalWrapper(forecaster.model, alpha=0.1, is_classifier=False)
    forecaster.conformal_wrapper.calibrate(X_calib, y_calib_reg)
    
    # 2. SOURCE APPORTIONMENT
    print("\n--- Training Source Apportionment Classifier (Random Forest) ---")
    classifier = SourceClassifier()
    # Label source attribution noisy labels using weak heuristics
    y_train_noisy = classifier.apply_weak_heuristics(data_train)
    y_train_noisy_arr = np.array(y_train_noisy)
    classifier.train(X_train, y_train_noisy_arr)
    
    print("Calibrating classifier conformal prediction sets with MAPIE...")
    classifier.conformal_wrapper = ConformalWrapper(classifier.model, alpha=0.1, is_classifier=True)
    y_calib_noisy = classifier.apply_weak_heuristics(data_calib)
    classifier.conformal_wrapper.calibrate(X_calib, np.array(y_calib_noisy))
    
    # 3. OFFLINE VALIDATION
    print("\n--- Running Offline Validation ---")
    y_pred_reg, intervals = forecaster.conformal_wrapper.predict_with_interval(X_test)
    
    # RMSE calculation
    rmse = calculate_rmse(y_pred_reg, y_test_reg)
    # Persistence baseline (predict target is current PM2.5 level)
    baseline_rmse = calculate_rmse(X_test[:, 0].tolist(), y_test_reg.tolist())
    comparison = compare_persistence_baseline(rmse, baseline_rmse)
    
    print(f"XGBoost Model RMSE: {rmse:.4f}")
    print(f"Persistence Baseline RMSE: {baseline_rmse:.4f}")
    print(f"Improvement over Baseline: {comparison['improvement_pct']:.2f}%")
    print(f"Validation Status: {comparison['status'].upper()}")
    
    # Conformal Coverage Verification
    coverage_count = 0
    for val, (low, high) in zip(y_test_reg, intervals):
        if low <= val <= high:
            coverage_count += 1
    coverage = coverage_count / len(y_test_reg)
    print(f"Empirical Conformal Coverage (Target 90%): {coverage*100:.2f}%")
    
    # Statistical distances on classification distribution
    classes = classifier.model.classes_
    y_test_noisy = classifier.apply_weak_heuristics(data_test)
    
    # Let's build target distributions (one-hot) vs predicted probability distributions
    jsd_list = []
    wasserstein_list = []
    
    class_map = {cls: idx for idx, cls in enumerate(classes)}
    for i in range(len(X_test)):
        # One-hot true label
        true_dist = np.zeros(len(classes))
        true_label = y_test_noisy[i]
        true_dist[class_map[true_label]] = 1.0
        
        # Predicted probability
        pred_dict = classifier.predict(data_test[i])
        pred_dist = np.array([pred_dict["probabilities"][cls] for cls in classes])
        
        # Calculate JSD and Wasserstein
        jsd = calculate_js_divergence(pred_dist.tolist(), true_dist.tolist())
        wd = calculate_wasserstein_distance(pred_dist.tolist(), true_dist.tolist())
        jsd_list.append(jsd)
        wasserstein_list.append(wd)
        
    print(f"Average JS-Divergence vs Weak Labels: {np.mean(jsd_list):.4f}")
    print(f"Average Wasserstein Distance vs Weak Labels: {np.mean(wasserstein_list):.4f}")
    
    # 4. SERIALIZATION
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    forecaster_path = os.path.join(data_dir, "forecaster.pkl")
    classifier_path = os.path.join(data_dir, "classifier.pkl")
    
    print(f"\nSaving model checkpoints to {data_dir}...")
    with open(forecaster_path, "wb") as f:
        pickle.dump(forecaster, f)
    with open(classifier_path, "wb") as f:
        pickle.dump(classifier, f)
        
    print("Success! Models trained, calibrated, validated, and serialized.")

if __name__ == "__main__":
    main()

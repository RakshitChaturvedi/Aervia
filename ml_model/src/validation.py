"""
Validation suite for VayuBudhi ML models.
Includes RMSE benchmarks, JSD (Jensen-Shannon Divergence), and Wasserstein checks.
"""
from typing import Dict, Any, List
import numpy as np
from scipy.stats import entropy, wasserstein_distance

def calculate_rmse(predictions: List[float], ground_truth: List[float]) -> float:
    """
    Computes Root Mean Squared Error.
    """
    preds = np.array(predictions, dtype=float)
    targets = np.array(ground_truth, dtype=float)
    return float(np.sqrt(np.mean((preds - targets) ** 2)))

def compare_persistence_baseline(model_rmse: float, baseline_rmse: float) -> Dict[str, Any]:
    """
    Compares the model's RMSE against a persistence baseline.
    """
    improvement = baseline_rmse - model_rmse
    improvement_pct = (improvement / baseline_rmse) * 100 if baseline_rmse > 0 else 0.0
    
    return {
        "model_rmse": float(model_rmse),
        "baseline_rmse": float(baseline_rmse),
        "improvement_pct": float(improvement_pct),
        "status": "improving" if model_rmse < baseline_rmse else "underperforming"
    }

def calculate_js_divergence(p_prob: List[float], q_prob: List[float]) -> float:
    """
    Computes Jensen-Shannon Divergence between two probability distributions.
    """
    p = np.array(p_prob, dtype=float)
    q = np.array(q_prob, dtype=float)
    
    # Ensure they sum to 1 to form valid probability distributions
    p = p / np.sum(p) if np.sum(p) > 0 else p
    q = q / np.sum(q) if np.sum(q) > 0 else q
    
    m = 0.5 * (p + q)
    
    # Calculate KL divergence components using scipy stats entropy
    kl_pm = entropy(p, m)
    kl_qm = entropy(q, m)
    
    return float(0.5 * kl_pm + 0.5 * kl_qm)

def calculate_wasserstein_distance(p_dist: List[float], q_dist: List[float]) -> float:
    """
    Computes Wasserstein (Earth Mover's) Distance.
    """
    p = np.array(p_dist, dtype=float)
    q = np.array(q_dist, dtype=float)
    return float(wasserstein_distance(p, q))


from __future__ import annotations
import pandas as pd
from .schemas import AnalysisResult, AnalysisStatus, Coverage, Provenance, fingerprint_dataframe

ALGORITHM_VERSION = "0.2.0"

def normalize_features(features, required):
    missing = sorted(set(required) - set(features.columns))
    if missing: return None, f"Missing required columns: {missing}"
    df = features.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if df["timestamp"].isna().any(): return None, "Invalid or missing timestamps."
    if df["timestamp"].duplicated().any(): return None, "Duplicate timestamps."
    return df.sort_values("timestamp").reset_index(drop=True), None

def eligible_mask(df, col):
    mask = df["analysis_ok"].fillna(False).astype(bool) if "analysis_ok" in df else pd.Series(False, index=df.index)
    return mask & pd.to_numeric(df[col], errors="coerce").notna()

def as_bool(s):
    if s.dtype == bool: return s.fillna(False)
    return s.astype(str).str.lower().isin({"true", "1", "yes"})

def make_result(module, status, df, dataset_id, config, results, units, limitations,
                eligible=None, exclusions=None, valid_outputs=None):
    if df.empty: start = end = None
    else:
        ts = pd.to_datetime(df["timestamp"], utc=True)
        start, end = ts.min().isoformat(), ts.max().isoformat()
    if df.empty:
        coverage = Coverage(notes=["No observations in requested window."])
    else:
        expected = max(1., (pd.to_datetime(df["timestamp"], utc=True).max() -
                            pd.to_datetime(df["timestamp"], utc=True).min()).total_seconds()/60 + 1)
        observed = float(len(df))
        elig = float(eligible.sum()) if eligible is not None else observed
        coverage = Coverage(expected, observed, elig, min(1., elig/expected), [
            "Coverage uses elapsed minute-grid duration; missing grid minutes reduce coverage."
        ])
    prov = Provenance(dataset_id, config, ALGORITHM_VERSION, start, end, len(df), len(results),
                     exclusions or [], fingerprint_dataframe(df) if len(df) else None)
    return AnalysisResult(module, status, units, {"start_utc": start, "end_utc": end},
                          coverage, prov, results, limitations, valid_outputs or [])
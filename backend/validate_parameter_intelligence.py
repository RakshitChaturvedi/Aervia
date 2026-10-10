#!/usr/bin/env python3
"""Numerical validation for Aervia Layer 3A output."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES = Path("data/parameter_intelligence/ft1_final_v2/features.csv")
MANIFEST = Path("data/parameter_intelligence/ft1_final_v2/manifest.json")

def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return bool(ok)

def main():
    if not FEATURES.exists():
        raise SystemExit(f"Cannot find {FEATURES}. Run from backend/ or edit FEATURES.")
    df = pd.read_csv(FEATURES)
    failures = 0
    print(f"Rows: {len(df)} | Columns: {len(df.columns)}")
    print()

    # Output / provenance
    failures += not check("99 expected minute rows", len(df) == 99, f"found {len(df)}")
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text())
            expected = manifest.get("output_rows", manifest.get("input_minute_rows"))
            failures += not check("manifest row count agrees", expected is None or expected == len(df),
                                  f"manifest={expected}, CSV={len(df)}")
        except Exception as exc:
            failures += not check("manifest readable", False, str(exc))
    else:
        print("[WARN] manifest.json not found; skipping manifest check")

    # Baseline/excess relationship
    needed = {"pm2_5", "baseline_pm2_5", "pm2_5_excess"}
    if needed <= set(df.columns):
        valid = df[list(needed)].notna().all(axis=1)
        err = (df.loc[valid, "pm2_5_excess"] -
               (df.loc[valid, "pm2_5"] - df.loc[valid, "baseline_pm2_5"])).abs()
        failures += not check("PM2.5 excess equals PM2.5 minus baseline",
                              bool((err <= 1e-5).all()),
                              f"checked {int(valid.sum())} rows; max abs error={err.max() if len(err) else 'n/a'}")
        missing_baseline = df["baseline_pm2_5"].isna()
        excess_missing = df.loc[missing_baseline, "pm2_5_excess"].isna()
        failures += not check("excess remains missing without baseline",
                              bool(excess_missing.all()),
                              f"{int(missing_baseline.sum())} rows without baseline")
    else:
        failures += not check("baseline/excess source columns present", False,
                              f"missing {sorted(needed - set(df.columns))}")

    # Particle mass-band arithmetic (only verify arithmetic, not physical sensor semantics)
    bands = [
        ("pm1", "pm2_5", "pm1_to_pm2_5_band"),
        ("pm2_5", "pm4", "pm2_5_to_pm4_band"),
        ("pm4", "pm10", "pm4_to_pm10_band"),
    ]
    for lower, upper, band in bands:
        if {lower, upper, band} <= set(df.columns):
            valid = df[[lower, upper, band]].notna().all(axis=1)
            err = (df.loc[valid, band] -
                   (df.loc[valid, upper] - df.loc[valid, lower])).abs()
            failures += not check(f"{band} arithmetic",
                                  bool((err <= 1e-5).all()),
                                  f"checked {int(valid.sum())} rows; max abs error={err.max() if len(err) else 'n/a'}")
            negative = int((df.loc[valid, band] < -1e-5).sum())
            failures += not check(f"{band} non-negative where calculated",
                                  negative == 0, f"negative rows={negative}")
        else:
            failures += not check(f"{band} source columns present", False,
                                  f"missing {[x for x in (lower, upper, band) if x not in df.columns]}")

    # Status and readiness invariants
    if "gas_health_warning_eligible" in df.columns:
        eligible = int(df["gas_health_warning_eligible"].fillna(False).astype(bool).sum())
        failures += not check("gas health warnings withheld when gas is not ready",
                              eligible == 0, f"eligible rows={eligible}")
    if "particle_distribution_status" in df.columns:
        statuses = df["particle_distribution_status"].value_counts(dropna=False).to_dict()
        print(f"[INFO] particle_distribution_status: {statuses}")
        if any("UNVERIFIED" in str(s) for s in statuses):
            print("[PASS] particle-count semantics remain explicitly unverified")
        else:
            print("[WARN] Confirm how particle-count semantics are represented in this output")
    if "analysis_ok" in df.columns and "baseline_mature" in df.columns:
        bad = df["analysis_ok"].fillna(False).astype(bool) & ~df["baseline_mature"].fillna(False).astype(bool)
        failures += not check("analysis_ok does not bypass baseline maturity",
                              int(bad.sum()) == 0, f"violating rows={int(bad.sum())}")
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        failures += not check("timestamps parse and are ordered",
                              bool(ts.notna().all() and ts.is_monotonic_increasing),
                              f"unparseable={int(ts.isna().sum())}, ordered={ts.is_monotonic_increasing}")

    print()
    if failures:
        print(f"RESULT: {failures} check(s) failed. Investigate before sign-off.")
        raise SystemExit(1)
    print("RESULT: all implemented checks passed. This is numerical validation, not full scientific validation.")

if __name__ == "__main__":
    main()
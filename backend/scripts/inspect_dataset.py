"""Inspect live CSV/TSV exports or JSONL stream directories without changing them."""
from __future__ import annotations
import argparse, json, math
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.ingestion.loaders import load_tabular
STREAMS = ("sensor", "activity", "weather", "reference")

def inspect_rows(rows, label="dataset"):
    print(f"{label}: {len(rows)} rows")
    if not rows: return
    tskey = next((k for k in ("timestamp_ist", "timestamp", "recorded_at") if any(r.get(k) for r in rows)), None)
    times=[]
    if tskey:
        for r in rows:
            value=r.get(tskey)
            if value:
                try: times.append(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
                except ValueError: pass
        print(f"timestamps: {len(times)}/{len(rows)} parseable")
        if times: print(f"range: {min(times).isoformat()} -> {max(times).isoformat()}")
    for key in ("quality_flag", "sps30_state", "sgp41_state", "clock_source", "boot_id", "device_id"):
        vals=Counter(str(r.get(key)) for r in rows if r.get(key) not in (None, ""))
        if vals: print(f"{key}: {dict(vals.most_common(12))}")
    qf=Counter()
    for r in rows:
        value=r.get("quality_flags")
        if value in (None, "", "[]"): continue
        try:
            parsed=json.loads(value) if isinstance(value,str) else value
            if isinstance(parsed,list): qf.update(map(str,parsed))
            else: qf.update([str(parsed)])
        except (ValueError, TypeError): qf.update([str(value)])
    if qf: print(f"quality_flags: {dict(qf)}")
    for key in ("pm2_5_ug_m3", "pm25", "pm10_ug_m3", "temp_c", "humidity_rh_pct", "voc_index", "nox_index"):
        vals=[]
        for r in rows:
            try:
                x=float(r.get(key));
                if math.isfinite(x): vals.append(x)
            except (TypeError, ValueError): pass
        if vals:
            vals.sort(); n=len(vals)
            print(f"{key}: n={n}, min={vals[0]:.3f}, median={vals[n//2]:.3f}, max={vals[-1]:.3f}")

def main():
    p=argparse.ArgumentParser(); p.add_argument("input"); a=p.parse_args(); path=Path(a.input)
    if path.is_file(): inspect_rows(load_tabular(path), path.name); return
    for stream in STREAMS:
        f=path/f"{stream}.jsonl"
        if not f.exists(): f=path/stream/f"{stream}.jsonl"
        if f.exists():
            rows=[json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
            inspect_rows(rows, stream)
        else: print(f"{stream}: missing")
if __name__ == "__main__": main()
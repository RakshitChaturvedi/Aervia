import os
import sys
from pathlib import Path
from config import get_s3_client, S3_BUCKET, S3_RAW_DATA_KEY, AERVIA_ROOT

def upload_dataset(local_path=None):
    if local_path is None:
        # Default to the tri-city master dataset (most comprehensive), fallback to Hyderabad
        master_parquet = AERVIA_ROOT / "ml_model" / "data" / "real_station_dataset_master.parquet"
        hyd_parquet = AERVIA_ROOT / "ml_model" / "data" / "hyderabad_district_dataset.parquet"
        local_path = master_parquet if master_parquet.exists() else (hyd_parquet if hyd_parquet.exists() else (AERVIA_ROOT / "ml_model" / "data" / "dataset.csv"))
    
    local_path = Path(local_path)
    if not local_path.exists():
        print(f"Error: Dataset file not found at {local_path}")
        sys.exit(1)

    s3 = get_s3_client()
    file_size_mb = local_path.stat().st_size / (1024 * 1024)
    target_key = f"ml/raw/{local_path.name}"
    print(f"Uploading {local_path.name} ({file_size_mb:.2f} MB) to s3://{S3_BUCKET}/{target_key}...")

    s3.upload_file(str(local_path), S3_BUCKET, target_key)
    print(f"Upload completed successfully! Target: s3://{S3_BUCKET}/{target_key}")

def upload_all_datasets():
    """Uploads all relevant training datasets to S3."""
    s3 = get_s3_client()
    data_dir = AERVIA_ROOT / "ml_model" / "data"
    
    datasets = [
        data_dir / "real_station_dataset_master.parquet",
        data_dir / "hyderabad_district_dataset.parquet",
    ]
    
    for ds in datasets:
        if ds.exists():
            file_size_mb = ds.stat().st_size / (1024 * 1024)
            target_key = f"ml/raw/{ds.name}"
            print(f"Uploading {ds.name} ({file_size_mb:.2f} MB)...")
            s3.upload_file(str(ds), S3_BUCKET, target_key)
            print(f"  -> s3://{S3_BUCKET}/{target_key}")
        else:
            print(f"Skipping {ds.name}: not found")
    
    print("\nAll dataset uploads complete!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        upload_all_datasets()
    else:
        custom_path = sys.argv[1] if len(sys.argv) > 1 else None
        upload_dataset(custom_path)

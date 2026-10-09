import os
import tarfile
import tempfile
from pathlib import Path
from config import get_s3_client, S3_BUCKET, AERVIA_ROOT

LOCAL_DATA_DIR = AERVIA_ROOT / "ml_model" / "data"

def download_and_extract_latest_models():
    s3 = get_s3_client()
    prefix = "ml/models/"

    print(f"Checking for trained models in s3://{S3_BUCKET}/{prefix}...")
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

    candidates = [
        obj for obj in response.get("Contents", [])
        if obj["Key"].endswith("model.tar.gz")
    ]

    if not candidates:
        print("No completed model.tar.gz found yet. Ensure the SageMaker training job has finished.")
        return False

    # Pick the most recently created model artifact
    latest_model = sorted(candidates, key=lambda x: x["LastModified"])[-1]
    model_key = latest_model["Key"]
    print(f"Found latest model artifact: {model_key} (Modified: {latest_model['LastModified']})")

    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
        tmp_tar_path = tmp_file.name

    print(f"Downloading artifact to temporary file...")
    s3.download_file(S3_BUCKET, model_key, tmp_tar_path)

    print(f"Extracting .pkl models directly into {LOCAL_DATA_DIR}...")
    with tarfile.open(tmp_tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            print(f"  - Extracting: {member.name}")
            tar.extract(member, path=str(LOCAL_DATA_DIR))

    os.remove(tmp_tar_path)
    print("\nAll models downloaded and extracted successfully into Aervia/ml_model/data/!")
    return True

if __name__ == "__main__":
    download_and_extract_latest_models()

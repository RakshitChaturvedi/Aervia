import os
import sys
import time
import json
import tarfile
import tempfile
from pathlib import Path
from config import (
    get_s3_client,
    get_sagemaker_client,
    S3_BUCKET,
    S3_RAW_DATA_KEY,
    S3_OUTPUT_PATH,
    SAGEMAKER_ROLE_ARN,
    AWS_DEFAULT_REGION,
    AERVIA_ROOT
)
from download_models import download_and_extract_latest_models

# AWS Scikit-Learn container image for ap-south-1 (Mumbai)
IMAGE_URI = "720646828776.dkr.ecr.ap-south-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"

def package_and_upload_source(s3_client):
    """Packs sagemaker_train_entry.py into sourcedir.tar.gz and uploads to S3."""
    current_dir = Path(__file__).resolve().parent
    entry_script = current_dir / "sagemaker_train_entry.py"

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_tar:
        tar_path = tmp_tar.name

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(entry_script, arcname="sagemaker_train_entry.py")

    s3_source_key = "ml/code/sourcedir.tar.gz"
    print(f"Uploading source code to s3://{S3_BUCKET}/{s3_source_key}...")
    s3_client.upload_file(tar_path, S3_BUCKET, s3_source_key)
    try:
        os.remove(tar_path)
    except OSError:
        pass
    return f"s3://{S3_BUCKET}/{s3_source_key}"

def monitor_training_job(sm_client, job_name):
    """Polls training status until completion."""
    print(f"\n=== Monitoring SageMaker Training Job: {job_name} ===")
    start_time = time.time()
    last_status = None
    
    while True:
        elapsed_min = (time.time() - start_time) / 60.0
        response = sm_client.describe_training_job(TrainingJobName=job_name)
        status = response["TrainingJobStatus"]
        secondary = response.get("SecondaryStatus", "")
        
        status_tuple = (status, secondary)
        if status_tuple != last_status:
            print(f"[{elapsed_min:.1f}m elapsed] Status: {status} | Step: {secondary}")
            last_status = status_tuple
            
        if status in ["Completed", "Failed", "Stopped"]:
            break
            
        time.sleep(30)
        
    if status == "Completed":
        print(f"\nTraining Job {job_name} COMPLETED successfully in {elapsed_min:.1f} minutes!")
        return True
    else:
        failure = response.get("FailureReason", "Unknown error")
        print(f"\nTraining Job {job_name} {status}: {failure}")
        return False

def start_training(wait=True):
    s3 = get_s3_client()
    sm = get_sagemaker_client()

    source_s3_uri = package_and_upload_source(s3)
    job_name = f"aervia-train-{int(time.time())}"

    print(f"\nLaunching SageMaker Training Job: {job_name}...")
    print(f"Role ARN: {SAGEMAKER_ROLE_ARN}")
    print(f"Region: {AWS_DEFAULT_REGION}")
    print(f"Instance: ml.m5.large (2 vCPU, 8 GB RAM)")

    response = sm.create_training_job(
        TrainingJobName=job_name,
        HyperParameters={
            "sagemaker_program": "sagemaker_train_entry.py",
            "sagemaker_submit_directory": source_s3_uri
        },
        AlgorithmSpecification={
            "TrainingImage": IMAGE_URI,
            "TrainingInputMode": "File"
        },
        RoleArn=SAGEMAKER_ROLE_ARN,
        InputDataConfig=[
            {
                "ChannelName": "train",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{S3_BUCKET}/ml/raw/",
                        "S3DataDistributionType": "FullyReplicated"
                    }
                }
            }
        ],
        OutputDataConfig={
            "S3OutputPath": S3_OUTPUT_PATH
        },
        ResourceConfig={
            "InstanceType": "ml.m5.large",
            "InstanceCount": 1,
            "VolumeSizeInGB": 10
        },
        StoppingCondition={
            "MaxRuntimeInSeconds": 3600
        },
        EnableNetworkIsolation=False
    )

    print(f"Successfully started training job! Job ARN: {response['TrainingJobArn']}")

    if wait:
        success = monitor_training_job(sm, job_name)
        if success:
            print("\nDownloading and extracting trained models from S3...")
            download_and_extract_latest_models()
            
            metrics_file = AERVIA_ROOT / "ml_model" / "data" / "evaluation_metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    metrics_data = json.load(f)
                print("\n================ FINAL EVALUATION METRICS ================")
                print(json.dumps(metrics_data, indent=2))
                print("==========================================================")
        else:
            sys.exit(1)
            
    return job_name

if __name__ == "__main__":
    wait_flag = "--no-wait" not in sys.argv
    start_training(wait=wait_flag)

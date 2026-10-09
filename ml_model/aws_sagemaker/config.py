import os
import boto3
from pathlib import Path

# Base Paths
AERVIA_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = AERVIA_ROOT / ".env"

# Load .env if present
if DOTENV_PATH.exists():
    with open(DOTENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")

# AWS Resource Configuration for Aervia
S3_BUCKET = "aervia-sensor-telemetry-410133709556"
S3_RAW_DATA_KEY = "ml/raw/air_quality_dataset.csv"
S3_OUTPUT_PATH = f"s3://{S3_BUCKET}/ml/models/"
SAGEMAKER_ROLE_ARN = "arn:aws:iam::410133709556:role/AerviaSageMakerExecutionRole"  # Note: Double-colon is correct AWS IAM ARN format

def get_boto3_session():
    """Returns an authenticated boto3 session."""
    return boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )

def get_s3_client():
    return get_boto3_session().client('s3')

def get_sagemaker_client():
    return get_boto3_session().client('sagemaker')

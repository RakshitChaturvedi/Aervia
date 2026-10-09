import os
import sys
import time
import json
import boto3
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(env_path)

access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region = os.getenv('AWS_DEFAULT_REGION', 'ap-south-1')

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=region
)

sts = session.client('sts')
account_id = sts.get_caller_identity()['Account']
print(f"[1/5] Verified AWS Identity. Account ID: {account_id}, Region: {region}")

# 1. Create DynamoDB Table for Real-time Hot Path
dynamodb = session.client('dynamodb')
table_name = "Aervia_Sensor_Telemetry"

try:
    existing_tables = dynamodb.list_tables()['TableNames']
    if table_name in existing_tables:
        print(f"[2/5] DynamoDB table '{table_name}' already exists.")
    else:
        print(f"[2/5] Creating DynamoDB table '{table_name}' (On-Demand billing)...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'device_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'device_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Waiting for DynamoDB table to become ACTIVE...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"DynamoDB table '{table_name}' is ACTIVE.")
except Exception as e:
    print(f"Error checking/creating DynamoDB table: {e}")
    sys.exit(1)

# 2. Create S3 Bucket for ML Training Cold Path
s3 = session.client('s3')
bucket_name = f"aervia-sensor-telemetry-{account_id}"

try:
    buckets = [b['Name'] for b in s3.list_buckets().get('Buckets', [])]
    if bucket_name in buckets:
        print(f"[3/5] S3 Data Lake bucket '{bucket_name}' already exists.")
    else:
        print(f"[3/5] Creating S3 Data Lake bucket '{bucket_name}' in {region}...")
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"S3 bucket '{bucket_name}' created successfully.")
except Exception as e:
    print(f"Error checking/creating S3 bucket: {e}")
    sys.exit(1)

# 3. Create IAM Role for AWS IoT Core to write to DynamoDB and S3
iam = session.client('iam')
role_name = "Aervia_IoTRule_StorageRole"

trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "iot.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

permissions_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}

try:
    try:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"[4/5] Found existing IAM Role '{role_name}'.")
    except iam.exceptions.NoSuchEntityException:
        print(f"[4/5] Creating IAM Role '{role_name}' for AWS IoT...")
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role allowing AWS IoT Core topic rule to write to DynamoDB and S3"
        )
        role_arn = role['Role']['Arn']
        print(f"Created role: {role_arn}")

    # Attach/Update inline policy
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="AerviaStorageWritePolicy",
        PolicyDocument=json.dumps(permissions_policy)
    )
    print("Permissions policy attached to role. Waiting 10s for IAM propagation across AWS regions...")
    time.sleep(10)
except Exception as e:
    print(f"Error setting up IAM role: {e}")
    sys.exit(1)

# 4. Create or Replace AWS IoT Topic Rule
iot = session.client('iot')
rule_name = "Aervia_Store_Sensor_Telemetry"

rule_payload = {
    "sql": "SELECT * FROM 'aervia/+/telemetry'",
    "description": "Routes real-time sensor telemetry to DynamoDB (hot path) and S3 (cold path ML data lake)",
    "ruleDisabled": False,
    "awsIotSqlVersion": "2016-03-23",
    "actions": [
        {
            "dynamoDBv2": {
                "roleArn": role_arn,
                "putItem": {
                    "tableName": table_name
                }
            }
        },
        {
            "s3": {
                "roleArn": role_arn,
                "bucketName": bucket_name,
                "key": "raw/${device_id}/${timestamp()}.json"
            }
        }
    ]
}

try:
    print(f"[5/5] Creating/Updating AWS IoT Topic Rule '{rule_name}'...")
    iot.create_topic_rule(
        ruleName=rule_name,
        topicRulePayload=rule_payload
    )
    print(f"Successfully configured IoT Topic Rule '{rule_name}'!")
except iot.exceptions.ResourceAlreadyExistsException:
    print(f"Rule already exists, replacing rule '{rule_name}'...")
    iot.replace_topic_rule(
        ruleName=rule_name,
        topicRulePayload=rule_payload
    )
    print(f"Successfully updated IoT Topic Rule '{rule_name}'!")
except Exception as e:
    print(f"Error configuring IoT topic rule: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("PIPELINE FULLY OPERATIONAL!")
print(f"  • DynamoDB Table : {table_name} (Primary Key: device_id, Sort Key: timestamp)")
print(f"  • S3 Data Lake   : s3://{bucket_name}/raw/")
print(f"  • IoT Topic Rule : {rule_name} listening on 'aervia/+/telemetry'")
print("="*70 + "\n")

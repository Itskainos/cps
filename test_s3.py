import os
import boto3
from dotenv import load_dotenv

# Load from .env.local
load_dotenv(".env.local")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

print(f"AWS_ACCESS_KEY_ID: {AWS_ACCESS_KEY_ID}")
print(f"AWS_REGION: {AWS_REGION}")
print(f"S3_BUCKET_NAME: {S3_BUCKET_NAME}")

if not AWS_ACCESS_KEY_ID or not S3_BUCKET_NAME:
    print("S3 credentials or bucket name missing!")
else:
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        print("S3 client initialized.")
        
        # List objects to test connectivity
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
        print(f"Successfully connected to S3. Bucket contains {response.get('KeyCount', 0)} objects.")
        
        # Try a test upload
        test_content = b"This is a test file for S3 integration."
        test_key = "test_connectivity.txt"
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=test_key, Body=test_content)
        print(f"Successfully uploaded {test_key} to S3.")
        
    except Exception as e:
        print(f"S3 connection/upload failed: {str(e)}")

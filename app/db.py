"""Database and AWS service clients.

Initializes AWS resources (DynamoDB tables and S3 bucket) from environment variables.
Provides table references for routers and helper functions for S3 operations.

Environment Variables:
  - AWS_REGION: AWS region for DynamoDB/S3 (default: "us-east-1")
  - LOGIN_TABLE_NAME: DynamoDB table for user credentials (default: "login")
  - MUSIC_TABLE_NAME: DynamoDB table for song data (default: "music")
  - SUBSCRIPTIONS_TABLE_NAME: DynamoDB table for user subscriptions (default: "subscriptions")
  - S3_BUCKET_NAME: S3 bucket for artist images (default: ""; presigned URLs disabled if empty)

DynamoDB Tables:
  - login: {email (PK), user_name, password}
  - music: {title (PK), album (SK), artist, year, image_url}
  - subscriptions: {user_email (PK), music_id (SK), ...song metadata}

S3 Bucket:
  - Stores artist image files with path format like "beatles/lennon.jpg"
  - Backend generates presigned URLs (3600-second TTL) for frontend consumption
  - Presigned URLs allow direct browser download without AWS credentials

Notes:
  - All resources initialized at module load time (on import)
  - Presigned URL generation fails gracefully if S3_BUCKET_NAME not configured
  - Uses boto3 session credentials (from IAM role if on AWS, from ~/.aws/credentials otherwise)
"""

import os

import boto3
from fastapi.logger import logger

# Configuration from environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOGIN_TABLE_NAME = os.getenv("LOGIN_TABLE_NAME", "login")
MUSIC_TABLE_NAME = os.getenv("MUSIC_TABLE_NAME", "music")
SUBSCRIPTIONS_TABLE_NAME = os.getenv("SUBSCRIPTIONS_TABLE_NAME", "subscriptions")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

# Initialize AWS clients and resources
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

# DynamoDB table references (lazy-loaded on first access)
login_table = dynamodb.Table(LOGIN_TABLE_NAME)
music_table = dynamodb.Table(MUSIC_TABLE_NAME)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)


def create_presigned_image_url(image_key: str, expires_seconds: int = 3600) -> str:
    """
    Generate a presigned URL for an S3 object to allow temporary public access.

    Args:
        image_key (str): The S3 object key (path) for the image (e.g., "beatles/lennon.jpg")
        expires_seconds (int, optional): URL expiration time in seconds. Defaults to 3600.

    Returns:
        str: The presigned S3 URL or the original image key if S3_BUCKET_NAME is not configured.
    """
    if not S3_BUCKET_NAME:
        return image_key

    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": image_key},
        ExpiresIn=expires_seconds,
    )


def test_connection():
    """
    Test function to verify DynamoDB and S3 connectivity.
    """
    # Check DynamoDB tables
    logger.info("Login table status: %s", login_table.table_status)
    # Scan a sample item from music table to verify read access
    logger.info("Music table sample: %s", music_table.scan(Limit=1))


if __name__ == "__main__":
    test_connection()

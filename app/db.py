import boto3
import os
from fastapi.logger import logger

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOGIN_TABLE_NAME = os.getenv("LOGIN_TABLE_NAME", "login")
MUSIC_TABLE_NAME = os.getenv("MUSIC_TABLE_NAME", "music")
SUBSCRIPTIONS_TABLE_NAME = os.getenv("SUBSCRIPTIONS_TABLE_NAME", "subscriptions")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

login_table = dynamodb.Table(LOGIN_TABLE_NAME)
music_table = dynamodb.Table(MUSIC_TABLE_NAME)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)


def create_presigned_image_url(image_key: str, expires_seconds: int = 3600) -> str:
    if not S3_BUCKET_NAME:
        return image_key

    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": image_key},
        ExpiresIn=expires_seconds,
    )


# test connection
def test_connection():
    logger.info("Login table status: %s", login_table.table_status)
    logger.info("Music table sample: %s", music_table.scan(Limit=1))


if __name__ == "__main__":
    test_connection()

import boto3
from fastapi.logger import logger

AWS_REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
subscriptions_table = dynamodb.Table("subscriptions")


# test connection
def test_connection():
    logger.info("Login table status: %s", login_table.table_status)
    logger.info("Music table sample: %s", music_table.scan(Limit=1))


if __name__ == "__main__":
    test_connection()

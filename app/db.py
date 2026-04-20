import boto3

AWS_REGION = "us-east-1"

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

login_table = dynamodb.Table("login")
music_table = dynamodb.Table("music")
subscriptions_table = dynamodb.Table("subscriptions")


# test connection
def test_connection():
    print("Login table status:", login_table.table_status)
    print("Music table sample:", music_table.scan(Limit=1))


if __name__ == "__main__":
    test_connection()

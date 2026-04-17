import boto3

AWS_REGION = "us-east-1"   # change if needed

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

table_name = "subscriptions"

def create_table():
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": "user_email",
                    "KeyType": "HASH"   # Partition key
                },
                {
                    "AttributeName": "music_id",
                    "KeyType": "RANGE"  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "user_email",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "music_id",
                    "AttributeType": "S"
                }
            ],
            BillingMode="PAY_PER_REQUEST"  # no need to manage capacity
        )

        print("Creating table... please wait")

        # Wait until table exists
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

        print(f"Table '{table_name}' created successfully!")

    except Exception as e:
        print("Error creating table:", e)


if __name__ == "__main__":
    create_table()
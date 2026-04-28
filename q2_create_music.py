import logging

import boto3

logging.basicConfig(level=logging.INFO)


def create_music_table() -> None:
    """
    This function creates a DynamoDB table named "music"
    """
    # Connect to AWS using the credentials you configured
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    try:
        table = dynamodb.create_table(
            TableName="music",
            KeySchema=[
                {"AttributeName": "title", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "album", "KeyType": "RANGE"},  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "title", "AttributeType": "S"},
                {"AttributeName": "album", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        logging.info("Creating table... please wait.")
        table.meta.client.get_waiter("table_exists").wait(TableName="music")
        logging.info("Table 'music' created successfully!")
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    create_music_table()

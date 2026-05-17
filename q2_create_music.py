import logging
from typing import TYPE_CHECKING

import boto3

logging.basicConfig(level=logging.INFO)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource


def create_music_table() -> None:
    """
    This function creates a DynamoDB table named "music"

    The table has the following schema:
    - Primary Key: title (Partition Key), album (Sort Key)
    - LSI TitleYearIndex: supports title + year queries (e.g. a song released
      across multiple years); same partition as base table so no extra cost per read.
    - GSI TitlePrefixIndex: serves the majority access pattern — title prefix search.
      PK=first_char (first lowercase letter) + SK=title_lower enables
      begins_with queries that read only ~5-10 items per letter partition (~1 RCU)
      instead of a full table scan (~9 RCU).
    - GSI ArtistYearIndex: serves the graded demo queries (artist + year filter,
      e.g. "Jimmy Buffett in 1974"). Exact artist match is efficient via Query.
    """
    # Connect to AWS using the credentials you configured
    dynamodb: "DynamoDBServiceResource" = boto3.resource("dynamodb", region_name="us-east-1")  # type: ignore

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
                {"AttributeName": "artist", "AttributeType": "S"},
                {"AttributeName": "year", "AttributeType": "S"},
                {
                    "AttributeName": "first_char",
                    "AttributeType": "S",
                },  # TitlePrefixIndex PK
                {
                    "AttributeName": "title_lower",
                    "AttributeType": "S",
                },  # TitlePrefixIndex SK
            ],
            LocalSecondaryIndexes=[
                {
                    "IndexName": "TitleYearIndex",
                    "KeySchema": [
                        {"AttributeName": "title", "KeyType": "HASH"},
                        {"AttributeName": "year", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "TitlePrefixIndex",
                    "KeySchema": [
                        {"AttributeName": "first_char", "KeyType": "HASH"},
                        {"AttributeName": "title_lower", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "ArtistYearIndex",
                    "KeySchema": [
                        {"AttributeName": "artist", "KeyType": "HASH"},
                        {"AttributeName": "year", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                BillingMode="PAY_PER_REQUEST",
            ],
        )
        logging.info("Creating table... please wait.")
        table.meta.client.get_waiter("table_exists").wait(TableName="music")
        logging.info("Table 'music' created successfully!")
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    create_music_table()

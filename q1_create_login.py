import logging
from typing import TYPE_CHECKING

import boto3
from tqdm.auto import tqdm

# --- UPDATE YOUR DETAILS HERE ---
STUDENT_ID: str = "s4139673"  # Replace with your actual RMIT ID
YOUR_NAME: str = "KaushikNarumanchi"  # Replace with your name (FirstnameLastname)
# --------------------------------

logging.basicConfig(
    level=logging.INFO,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


def create_and_populate_login() -> None:
    """
    This function creates a DynamoDB table named 'login' with 'email' as the primary key.
    It then populates the table with 10 entities following the specified pattern for email, user_name, and password.
    """
    dynamodb: "DynamoDBServiceResource" = boto3.resource("dynamodb", region_name="us-east-1")

    # 1. Create Table (Using 'email' as the primary key)
    try:
        table: "Table" = dynamodb.create_table(
            TableName="login",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        logging.info("Creating 'login' table...")
        table.meta.client.get_waiter("table_exists").wait(TableName="login")
        logging.info("Table 'login' created successfully!")
    except Exception as e:
        logging.error(f"Checking table: {e}")
        table = dynamodb.Table("login")

    # 2. Generate 10 entities based on the image pattern
    logging.info("Populating 10 entities...")
    with table.batch_writer() as batch:
        for i in tqdm(range(10), leave=False, desc="Populating login table"):
            # Password pattern: 012345, 123456... 901234
            # We use string formatting to handle the leading zero for '012345'
            password_base = "012345678901234"
            current_password = password_base[i : i + 6]

            item = {
                "email": f"{STUDENT_ID}{i}@student.rmit.edu.au",
                "user_name": f"{YOUR_NAME}{i}",
                "password": current_password,
            }
            batch.put_item(Item=item)

    logging.info("Login table population complete!")


if __name__ == "__main__":
    create_and_populate_login()

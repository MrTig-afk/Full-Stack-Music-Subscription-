import boto3

# --- UPDATE YOUR DETAILS HERE ---
STUDENT_ID = "s4139673"  # Replace with your actual RMIT ID
YOUR_NAME = "KaushikNarumanchi"  # Replace with your name (FirstnameLastname)
# --------------------------------


def create_and_populate_login():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # 1. Create Table (Using 'email' as the primary key)
    try:
        table = dynamodb.create_table(
            TableName="login",
            KeySchema=[{"AttributeName": "email", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        print("Creating 'login' table...")
        table.meta.client.get_waiter("table_exists").wait(TableName="login")
        print("Table 'login' created successfully!")
    except Exception as e:
        print(f"Checking table: {e}")
        table = dynamodb.Table("login")

    # 2. Generate 10 entities based on the image pattern
    print("Populating 10 entities...")
    with table.batch_writer() as batch:
        for i in range(10):
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

    print("Login table population complete!")


if __name__ == "__main__":
    create_and_populate_login()

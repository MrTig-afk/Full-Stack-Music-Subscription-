import json

import boto3


def load_music_data():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("music")

    # Load the JSON file
    with open("2026a2_songs.json", "r") as file:
        data = json.load(file)

    print("Uploading songs to DynamoDB...")
    with table.batch_writer() as batch:
        for song in data["songs"]:
            batch.put_item(Item=song)
    print(f"Successfully loaded {len(data['songs'])} songs!")


if __name__ == "__main__":
    load_music_data()

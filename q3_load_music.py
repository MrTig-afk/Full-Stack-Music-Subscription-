import json
import logging
from pathlib import Path

import boto3
from tqdm.auto import tqdm

MUSIC_DATAFILE = Path("2026a2_songs.json")

logging.basicConfig(level=logging.INFO)


def build_music_id(title: str, album: str) -> str:
    # Keep deterministic ID compatible with subscription key strategy.
    return f"{title}#{album}"


def load_music_data():
    """
    This function loads music data from a JSON file into the DynamoDB "music" table.
    - It uses batch writing for efficient uploads.
    - It checks for duplicates based on the primary key (title + album) before uploading.
    - It logs the number of songs uploaded and skipped due to duplicates.
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("music")

    # Load the JSON file
    with open(MUSIC_DATAFILE, "r") as file:
        data = json.load(file)

    logging.info("Uploading songs to DynamoDB...")
    uploaded = 0
    skipped = 0
    invalid = 0

    # Adapted from boto3 DynamoDB batch_writer usage patterns.
    with table.batch_writer() as batch:
        for song in tqdm(data["songs"], leave=False, desc="Uploading songs"):
            # Use the table's primary key (title + album) to check for duplicates
            key = {"title": song.get("title"), "album": song.get("album")}
            if key["title"] is None or key["album"] is None:
                invalid += 1
                logging.warning("Skipping invalid row without title/album: %s", song)
                continue

            song["music_id"] = build_music_id(str(key["title"]), str(key["album"]))
            song["year"] = str(song.get("year", "")).strip()

            # Query DynamoDB for existing item with same key
            try:
                resp = table.get_item(Key=key)
            except Exception as e:
                # If the read fails for any reason, fall back to writing the item
                logging.warning(f"Error occurred while fetching item: {e}")
                batch.put_item(Item=song)
                uploaded += 1
                continue

            if "Item" in resp:
                skipped += 1
            else:
                batch.put_item(Item=song)
                uploaded += 1

    total = len(data.get("songs", []))
    logging.info("Upload complete.")
    logging.info(
        "uploaded=%s skipped=%s invalid=%s total=%s",
        uploaded,
        skipped,
        invalid,
        total,
    )


if __name__ == "__main__":
    load_music_data()

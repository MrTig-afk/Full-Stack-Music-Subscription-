import json
import logging
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

import boto3
from tqdm.auto import tqdm

MUSIC_DATAFILE: Path = Path("2026a2_songs.json")

logging.basicConfig(level=logging.INFO)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


def build_music_id(title: str, album: str) -> str:
    # Keep deterministic ID compatible with subscription key strategy.
    return f"{title}#{album}"


def load_music_data() -> None:
    """
    This function loads music data from a JSON file into the DynamoDB "music" table.
    - It uses batch writing for efficient uploads.
    - It checks for duplicates based on the primary key (title + album) before uploading.
    - It logs the number of songs uploaded and skipped due to duplicates.
    """
    dynamodb: "DynamoDBServiceResource" = boto3.resource(
        "dynamodb", region_name="us-east-1"
    )
    table: "Table" = dynamodb.Table("music")

    # Load the JSON file
    with open(MUSIC_DATAFILE, "r") as file:
        data: Dict[str, Any] = json.load(file)

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

            # Computed lowercase attributes for case-insensitive DynamoDB filtering
            # and for the TitlePrefixIndex GSI (first_char PK, title_lower SK).
            title_val = str(song.get("title", ""))
            artist_val = str(song.get("artist", ""))
            album_val = str(song.get("album", ""))
            song["title_lower"] = title_val.lower()
            song["artist_lower"] = artist_val.lower()
            song["album_lower"] = album_val.lower()
            song["first_char"] = (
                title_val[0].lower() if title_val and title_val[0].isalpha() else "#"
            )

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

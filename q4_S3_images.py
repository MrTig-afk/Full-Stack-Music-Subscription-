import io
import json
import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import boto3
import requests
from tqdm.auto import tqdm

# UPDATE THIS: S3 bucket names must be globally unique!
BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "rmit-music-images-unique-91725")

logging.basicConfig(level=logging.INFO)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from requests import Response


def run_s3_pipeline() -> None:
    s3: "S3Client" = boto3.client("s3", region_name="us-east-1")

    # 1. Create the Bucket
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        logging.info(f"Bucket '{BUCKET_NAME}' created.")
    except Exception as e:
        print(f"Bucket check: {e}")

    # 2. Process JSON Data
    with open("2026a2_songs.json", "r") as f:
        data = json.load(f)

    # Use a set to avoid downloading the same image twice (Efficiency!)
    processed_urls = set()

    logging.info("Starting image transfer to S3...")
    for song in tqdm(data["songs"], leave=False, desc="S3 upload"):
        img_url = song.get("img_url")
        if img_url and img_url not in processed_urls:
            filename = os.path.basename(urlparse(img_url).path)

            # Download image into memory
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                # Upload directly to S3 without saving locally
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=filename,
                    Body=response.content,
                    ContentType=response.headers.get(
                        "Content-Type", "application/octet-stream"
                    ),
                )
                processed_urls.add(img_url)
                logging.info(f"Uploaded: {filename}")

    logging.info(f"\nFinished! All images are now in S3 bucket: {BUCKET_NAME}")


if __name__ == "__main__":
    run_s3_pipeline()

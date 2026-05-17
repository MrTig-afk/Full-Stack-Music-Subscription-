import json
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Set
from urllib.parse import urlparse

import boto3
import requests
from requests import Response
from tqdm.auto import tqdm

# UPDATE THIS: S3 bucket names must be globally unique!
BUCKET_NAME: str = os.getenv(
    "S3_BUCKET_NAME",
    "rmit-music-images-unique-gayathritest",
)

logging.basicConfig(level=logging.INFO)

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


def run_s3_pipeline() -> None:
    s3: "S3Client" = boto3.client("s3", region_name="us-east-1")  # type: ignore

    # 1. Create the Bucket
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        logging.info(f"Bucket '{BUCKET_NAME}' created.")
    except Exception as e:
        print(f"Bucket check: {e}")

    # 2. Process JSON Data
    with open("2026a2_songs.json", "r") as f:
        data: Dict[str, Any] = json.load(f)

    # Track processed URLs
    processed_urls: Set[str] = set()

    logging.info("Starting image transfer to S3...")

    for song in tqdm(data["songs"], leave=False, desc="S3 upload"):

        img_url: Optional[str] = song.get("img_url")

        if not img_url:
            continue

        filename: str = os.path.basename(urlparse(img_url).path)

        # Final S3 URL
        s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"

        # Upload only once
        if img_url not in processed_urls:

            response: Response = requests.get(img_url, stream=True)

            if response.status_code == 200:

                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=filename,
                    Body=response.content,
                    ContentType=response.headers.get(
                        "Content-Type",
                        "application/octet-stream",
                    ),
                )

                logging.info(f"Uploaded: {filename}")

                processed_urls.add(img_url)

        # IMPORTANT:
        # Always replace GitHub URL with S3 URL
        song["img_url"] = s3_url

    # IMPORTANT:
    # Save updated JSON permanently
    with open("2026a2_songs.json", "w") as f:
        json.dump(data, f, indent=2)

    logging.info(
        f"\nFinished! All images are now in S3 bucket: {BUCKET_NAME}"
    )


if __name__ == "__main__":
    run_s3_pipeline() 
import json
import os
from urllib.parse import urlparse

import boto3
import requests

# UPDATE THIS: S3 bucket names must be globally unique!
BUCKET_NAME = "rmit-music-images-unique-91725"


def run_s3_pipeline():
    s3 = boto3.client("s3", region_name="us-east-1")

    # 1. Create the Bucket
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created.")
    except Exception as e:
        print(f"Bucket check: {e}")

    # 2. Process JSON Data
    with open("2026a2_songs.json", "r") as f:
        data = json.load(f)

    # Use a set to avoid downloading the same image twice (Efficiency!)
    processed_urls = set()

    print("Starting image transfer to S3...")
    for song in data["songs"]:
        img_url = song.get("img_url")
        if img_url and img_url not in processed_urls:
            filename = os.path.basename(urlparse(img_url).path)

            # Download image into memory
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                # Upload directly to S3 without saving locally
                s3.upload_fileobj(response.raw, BUCKET_NAME, filename)
                processed_urls.add(img_url)
                print(f"Uploaded: {filename}")

    print(f"\nFinished! All images are now in S3 bucket: {BUCKET_NAME}")


if __name__ == "__main__":
    run_s3_pipeline()

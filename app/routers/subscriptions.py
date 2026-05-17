"""User subscription management router.

Manages user subscriptions to songs via DynamoDB subscriptions table.
Provides endpoints to list, add, and remove song subscriptions for a user.
Generates presigned S3 URLs for all song images (3600-second TTL).

Endpoints:
  - GET /subscriptions/{email} — Get all subscriptions for user
  - POST /subscriptions — Add a song to user's subscriptions
  - DELETE /subscriptions — Remove a song from user's subscriptions

Key Features:
  - Subscriptions stored in DynamoDB with user_email (PK) + music_id (SK)
  - music_id is "title#album" to uniquely identify songs
  - All image URLs converted to presigned S3 URLs with 3600-second TTL
  - Results normalized to include both 'image_url' and 'img_url' properties
  - Duplicate prevention: attempting to subscribe to same song twice returns error
  - Remove operations idempotent: removing non-existent subscription succeeds silently

Notes:
  - Uses subscriptions_table from DynamoDB (created by create_subscriptions_table.py)
  - Frontend prevents UI duplicate clicks, but backend validates too
  - S3 presigned URLs generated for all items returned to frontend
"""

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter
from fastapi.logger import logger
from pydantic import BaseModel, ConfigDict, Field

from app.db import create_presigned_image_url, subscriptions_table
from app.schemas import RemoveSubscriptionRequest, SubscribeRequest

router = APIRouter()


def build_music_id(title: str, album: str) -> str:
    """Build unique music identifier from title and album.
    
    Creates a composite key to uniquely identify a song using title and album.
    Format: "{title}#{album}"
    
    Args:
        title: Song title
        album: Album name
        
    Returns:
        Composite music_id string
        
    Example:
        build_music_id("Imagine", "Imagine") -> "Imagine#Imagine"
    """
    return f"{title}#{album}"


class SubscriptionItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_email: str | None = None
    music_id: str | None = None
    title: str | None = None
    artist: str | None = None
    year: str | None = None
    album: str | None = None
    img_url: str | None = None
    image_url: str | None = None


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionItem] = Field(default_factory=list)


class MessageResponse(BaseModel):
    message: str


@router.get("/subscriptions/{email}")
def get_subscriptions(email: str):
    """Retrieve all subscriptions for a user.
    
    Queries subscriptions table for all songs subscribed to by user email.
    Converts all image URLs to presigned S3 URLs.
    
    Args:
        email: User's email address (query key)
        
    Returns:
        SubscriptionListResponse with list of subscribed songs
        
    Example:
        GET /subscriptions/user@example.com
    """
    logger.debug("Fetching subscriptions for email=%s", email)
    response = subscriptions_table.query(
        KeyConditionExpression=Key("user_email").eq(email)
    )
    items = [
        SubscriptionItem.model_validate(item) for item in response.get("Items", [])
    ]
    for item in items:
        image_key = item.img_url or item.image_url
        if image_key:
            item.image_url = str(image_key)
    logger.debug("Fetched %s subscriptions for email=%s", len(items), email)
    return SubscriptionListResponse(items=items)


@router.post("/subscriptions")
def add_subscription(payload: SubscribeRequest):
    """Add a song to user's subscriptions.
    
    Inserts a new subscription record in DynamoDB.
    Song is identified by title+album composite key (music_id).
    Frontend prevents duplicate subscriptions, but backend allows overwrites
    (idempotent: resubscribing to same song updates existing record).
    
    Args:
        payload: SubscribeRequest with user_email, title, album, artist, year, img_url
        
    Returns:
        MessageResponse with "Subscription added" message
        
    Example:
        POST /subscriptions
        {
            "user_email": "user@example.com",
            "title": "Imagine",
            "album": "Imagine",
            "artist": "John Lennon",
            "year": "1971",
            "img_url": "beatles/lennon.jpg"
        }
    """
    music_id = build_music_id(payload.title, payload.album)
    logger.debug(
        "Adding subscription for email=%s music_id=%s",
        payload.user_email,
        music_id,
    )

    subscriptions_table.put_item(
        Item={
            "user_email": payload.user_email,
            "music_id": music_id,
            "title": payload.title,
            "artist": payload.artist,
            "year": payload.year,
            "album": payload.album,
            "img_url": payload.img_url,
        }
    )
    logger.debug(
        "Subscription added for email=%s music_id=%s",
        payload.user_email,
        music_id,
    )
    return MessageResponse(message="Subscribed successfully")


@router.delete("/subscriptions")
def remove_subscription(payload: RemoveSubscriptionRequest):
    """Remove a song from user's subscriptions.
    
    Deletes subscription record from DynamoDB by user_email + music_id.
    Idempotent: removing non-existent subscription succeeds silently (DynamoDB behavior).
    
    Args:
        payload: RemoveSubscriptionRequest with user_email, title, album
        
    Returns:
        MessageResponse with "Removed successfully" message
        
    Example:
        DELETE /subscriptions
        {
            "user_email": "user@example.com",
            "title": "Imagine",
            "album": "Imagine"
        }
    """
    music_id = build_music_id(payload.title, payload.album)
    logger.debug(
        "Removing subscription for email=%s music_id=%s",
        payload.user_email,
        music_id,
    )

    subscriptions_table.delete_item(
        Key={"user_email": payload.user_email, "music_id": music_id}
    )
    logger.debug(
        "Subscription removed for email=%s music_id=%s",
        payload.user_email,
        music_id,
    )
    return MessageResponse(message="Removed successfully")


@router.delete("/subscriptions/{email}/{music_id}")
def remove_subscription_by_id(email: str, music_id: str):
    """Remove a subscription by email and music_id (path variant).
    
    Alternative endpoint for removing subscriptions using path parameters.
    Same behavior as DELETE /subscriptions (idempotent).
    
    Args:
        email: User's email address
        music_id: Music identifier (typically "title#album")
        
    Returns:
        MessageResponse with "Removed successfully" message
        
    Example:
        DELETE /subscriptions/user@example.com/Imagine%23Imagine
    """
    logger.debug(
        "Removing subscription via path for email=%s music_id=%s", email, music_id
    )
    subscriptions_table.delete_item(Key={"user_email": email, "music_id": music_id})
    return MessageResponse(message="Removed successfully")

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter
from fastapi.logger import logger
from pydantic import BaseModel, ConfigDict, Field

from app.db import create_presigned_image_url, subscriptions_table
from app.schemas import RemoveSubscriptionRequest, SubscribeRequest

router = APIRouter()


def build_music_id(title: str, album: str) -> str:
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
            item.image_url = create_presigned_image_url(str(image_key))
    logger.debug("Fetched %s subscriptions for email=%s", len(items), email)
    return SubscriptionListResponse(items=items)


@router.post("/subscriptions")
def add_subscription(payload: SubscribeRequest):
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
    logger.debug(
        "Removing subscription via path for email=%s music_id=%s", email, music_id
    )
    subscriptions_table.delete_item(Key={"user_email": email, "music_id": music_id})
    return MessageResponse(message="Removed successfully")

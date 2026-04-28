from boto3.dynamodb.conditions import Key
from fastapi import APIRouter
from fastapi.logger import logger

from app.db import subscriptions_table
from app.schemas import RemoveSubscriptionRequest, SubscribeRequest

router = APIRouter()


def build_music_id(title: str, album: str) -> str:
    return f"{title}#{album}"


@router.get("/subscriptions/{email}")
def get_subscriptions(email: str):
    logger.debug("Fetching subscriptions for email=%s", email)
    response = subscriptions_table.query(
        KeyConditionExpression=Key("user_email").eq(email)
    )
    items = response.get("Items", [])
    logger.debug("Fetched %s subscriptions for email=%s", len(items), email)
    return {"items": items}


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
    return {"message": "Subscribed successfully"}


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
    return {"message": "Removed successfully"}

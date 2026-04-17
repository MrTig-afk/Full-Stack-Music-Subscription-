from fastapi import APIRouter
from boto3.dynamodb.conditions import Key
from app.db import subscriptions_table
from app.schemas import SubscribeRequest, RemoveSubscriptionRequest

router = APIRouter()

def build_music_id(title: str, album: str) -> str:
    return f"{title}#{album}"

@router.get("/subscriptions/{email}")
def get_subscriptions(email: str):
    response = subscriptions_table.query(
        KeyConditionExpression=Key("user_email").eq(email)
    )
    return {"items": response.get("Items", [])}

@router.post("/subscriptions")
def add_subscription(payload: SubscribeRequest):
    music_id = build_music_id(payload.title, payload.album)

    subscriptions_table.put_item(
        Item={
            "user_email": payload.user_email,
            "music_id": music_id,
            "title": payload.title,
            "artist": payload.artist,
            "year": payload.year,
            "album": payload.album,
            "img_url": payload.img_url
        }
    )
    return {"message": "Subscribed successfully"}

@router.delete("/subscriptions")
def remove_subscription(payload: RemoveSubscriptionRequest):
    music_id = build_music_id(payload.title, payload.album)

    subscriptions_table.delete_item(
        Key={
            "user_email": payload.user_email,
            "music_id": music_id
        }
    )
    return {"message": "Removed successfully"}
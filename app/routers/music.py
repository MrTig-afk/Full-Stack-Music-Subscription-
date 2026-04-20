from boto3.dynamodb.conditions import Attr, ConditionBase
from fastapi import APIRouter, HTTPException

from app.db import music_table
from app.schemas import SearchRequest

router = APIRouter()


@router.post("/songs/search")
def search_songs(payload: SearchRequest):
    conditions: list[ConditionBase] = []

    if payload.title and payload.title.strip():
        conditions.append(Attr("title").eq(payload.title.strip()))

    if payload.artist and payload.artist.strip():
        conditions.append(Attr("artist").eq(payload.artist.strip()))

    if payload.album and payload.album.strip():
        conditions.append(Attr("album").eq(payload.album.strip()))

    if payload.year is not None:
        conditions.append(Attr("year").eq(str(payload.year)))

    if not conditions:
        raise HTTPException(
            status_code=400, detail="At least one field must be completed"
        )

    filter_expression = conditions[0]
    for expr in conditions[1:]:
        filter_expression = filter_expression & expr

    response = music_table.scan(FilterExpression=filter_expression)
    items = response.get("Items", [])

    if not items:
        return {"message": "No result is retrieved. Please query again", "items": []}

    return {"items": items}

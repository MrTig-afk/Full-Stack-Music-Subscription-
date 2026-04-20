from boto3.dynamodb.conditions import Attr
from fastapi import APIRouter, HTTPException

from app.db import music_table
from app.schemas import SearchRequest

router = APIRouter()


@router.post("/songs/search")
def search_songs(payload: SearchRequest):
    if not any([payload.title, payload.year, payload.artist, payload.album]):
        raise HTTPException(
            status_code=400, detail="At least one field must be completed"
        )

    filter_expression = None

    if payload.title:
        expr = Attr("title").eq(payload.title.strip())
        filter_expression = (
            expr if filter_expression is None else filter_expression & expr
        )

    if payload.artist:
        expr = Attr("artist").eq(payload.artist.strip())
        filter_expression = (
            expr if filter_expression is None else filter_expression & expr
        )

    if payload.album:
        expr = Attr("album").eq(payload.album.strip())
        filter_expression = (
            expr if filter_expression is None else filter_expression & expr
        )

    if payload.year is not None:
        expr = Attr("year").eq(str(payload.year))  # important fix
        filter_expression = (
            expr if filter_expression is None else filter_expression & expr
        )

    response = music_table.scan(FilterExpression=filter_expression)
    items = response.get("Items", [])

    if not items:
        return {"message": "No result is retrieved. Please query again", "items": []}

    return {"items": items}

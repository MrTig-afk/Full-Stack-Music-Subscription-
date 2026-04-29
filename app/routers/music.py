from boto3.dynamodb.conditions import Attr, ConditionBase
from fastapi import APIRouter, HTTPException
from fastapi.logger import logger

from app.db import create_presigned_image_url
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
        logger.debug("Song search rejected because no filters were provided")
        raise HTTPException(
            status_code=400, detail="At least one field must be completed"
        )

    filter_expression = conditions[0]
    for expr in conditions[1:]:
        filter_expression = filter_expression & expr

    logger.debug(
        "Song search filters built: title=%s artist=%s album=%s year=%s",
        payload.title,
        payload.artist,
        payload.album,
        payload.year,
    )
    response = music_table.scan(FilterExpression=filter_expression)
    items = response.get("Items", [])

    for item in items:
        image_key = item.get("img_url") or item.get("image_url")
        if image_key:
            item["image_url"] = create_presigned_image_url(str(image_key))

    if not items:
        logger.debug("Song search returned no results")
        return {"message": "No result is retrieved. Please query again", "items": []}

    logger.debug("Song search returned %s items", len(items))
    return {"items": items}


@router.get("/songs/search")
def search_songs_get(
    title: str | None = None,
    year: int | None = None,
    artist: str | None = None,
    album: str | None = None,
):
    payload = SearchRequest(title=title, year=year, artist=artist, album=album)
    return search_songs(payload)

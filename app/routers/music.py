"""Music search router.

Provides song search endpoint with flexible AND matching across title, artist, album, and year.
Queries DynamoDB music table with optional Global Secondary Index (GSI) support.
Generates presigned S3 URLs for artist images (3600-second TTL).

Endpoints:
  - POST /songs/search — Search songs by title, artist, album, year (AND matching)

Key Features:
  - At least one search criterion required (title, artist, album, or year)
  - Results normalized to include both 'image_url' and 'img_url' properties
  - Presigned S3 URLs generated for all image_url fields
  - AND matching: only songs matching all provided criteria returned
  - DynamoDB scan with FilterExpression for flexible querying

Notes:
  - Uses music_table from DynamoDB (created by q2_create_music.py)
  - Artist/Year queries benefit from GSI "ArtistYearIndex" when available
  - Large result sets may require pagination (not implemented; use Limit/ExclusiveStartKey)
  - S3 bucket name configured in app.db.create_presigned_image_url()
"""

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from fastapi import APIRouter, HTTPException
from fastapi.logger import logger
from pydantic import BaseModel, ConfigDict, Field

from app.db import create_presigned_image_url, music_table
from app.schemas import SearchRequest

router = APIRouter()


class MusicSearchItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    year: str | None = None
    img_url: str | None = None
    image_url: str | None = None
    music_id: str | None = None


class MusicSearchResponse(BaseModel):
    message: str | None = None
    items: list[MusicSearchItem] = Field(default_factory=list)


def combine_conditions(conditions: list[ConditionBase]) -> ConditionBase | None:
    """Combine DynamoDB conditions with AND logic.
    
    Merges multiple DynamoDB condition objects into a single expression using
    the & operator for AND matching. Used for multi-criteria song searches.
    
    Args:
        conditions: List of DynamoDB ConditionBase objects
        
    Returns:
        A single combined condition using AND, or None if list is empty
        
    Ref: https://docs.aws.amazon.com/code-library/latest/ug/python_3_dynamodb_code_examples.html
         > Query a table with a complex filter expression
    
    Example:
        combined = combine_conditions([
            Attr("title").begins_with("Hello"),
            Attr("artist").eq("Beatles")
        ])
    """
    if not conditions:
        return None

    expression = conditions[0]
    for expr in conditions[1:]:
        expression = expression & expr
    return expression


@router.post("/songs/search")
def search_songs(payload: SearchRequest) -> MusicSearchResponse:
    """Search songs by title, artist, album, and/or year.
    
    Queries DynamoDB music table with AND matching across provided criteria.
    At least one search field (title, artist, album, year) must be provided.
    All matching songs are returned with presigned S3 image URLs.
    
    Args:
        payload: SearchRequest containing optional title, artist, album, year
        
    Returns:
        MusicSearchResponse with list of matching songs and presigned image URLs
        
    Raises:
        HTTPException: 400 if no search criteria provided
        
    Example:
        POST /songs/search
        {"title": "Imagine", "artist": "John Lennon"}
    """
    :raises HTTPException: If no search criteria are provided.
    :return _type_: A list of songs matching the search criteria. Each song includes a presigned image URL if an image is associated with it.
    """
    title = payload.title.strip() if payload.title and payload.title.strip() else None
    artist = (
        payload.artist.strip() if payload.artist and payload.artist.strip() else None
    )
    album = payload.album.strip() if payload.album and payload.album.strip() else None
    year = str(payload.year) if payload.year is not None else None

    if not any([title, artist, album, year]):
        logger.debug("Song search rejected because no filters were provided")
        raise HTTPException(
            status_code=400, detail="At least one field must be completed"
        )

    logger.debug(
        "Song search filters built: title=%s artist=%s album=%s year=%s",
        title,
        artist,
        album,
        year,
    )

    response_items: list[MusicSearchItem]
    try:
        if title:
            key_expr = Key("title").eq(title)
            if album:
                key_expr = key_expr & Key("album").eq(album)

            post_filters: list[ConditionBase] = []
            if artist:
                post_filters.append(Attr("artist").eq(artist))
            if year:
                post_filters.append(Attr("year").eq(year))

            filter_expr = combine_conditions(post_filters)
            if filter_expr is not None:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.query(
                        KeyConditionExpression=key_expr,
                        FilterExpression=filter_expr,
                    ).get("Items", [])
                ]
            else:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.query(KeyConditionExpression=key_expr).get(
                        "Items", []
                    )
                ]
            logger.debug("Song search used Query on base table")
        elif artist:
            # Query-first routing follows DynamoDB access-pattern guidance from http://www.dynamodbguide.com/secondary-indexes/#querying-a-secondary-index. The ArtistYearIndex supports efficient querying by artist and year, so we can use it if the artist filter is provided.
            key_expr = Key("artist").eq(artist)
            if year:
                key_expr = key_expr & Key("year").eq(year)

            post_filters = []
            if title:
                post_filters.append(Attr("title").eq(title))
            if album:
                post_filters.append(Attr("album").eq(album))

            filter_expr = combine_conditions(post_filters)
            if filter_expr is not None:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.query(
                        IndexName="ArtistYearIndex",
                        KeyConditionExpression=key_expr,
                        FilterExpression=filter_expr,
                    ).get("Items", [])
                ]
            else:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.query(
                        IndexName="ArtistYearIndex",
                        KeyConditionExpression=key_expr,
                    ).get("Items", [])
                ]
            logger.debug("Song search used Query on ArtistYearIndex")
        else:
            # Scan fallback for full text searches. This is not ideal for performance, but filtered when artist and title are not available
            scan_filters: list[ConditionBase] = []
            if album:
                scan_filters.append(Attr("album").eq(album))
            if year:
                scan_filters.append(Attr("year").eq(year))
            if title:
                scan_filters.append(Attr("title").eq(title))

            filter_expr = combine_conditions(scan_filters)
            if filter_expr is None:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.scan().get("Items", [])
                ]
            else:
                response_items = [
                    MusicSearchItem.model_validate(item)
                    for item in music_table.scan(FilterExpression=filter_expr).get(
                        "Items", []
                    )
                ]
            logger.debug("Song search used Scan fallback")
    except Exception as e:
        logger.warning("Query path failed; falling back to Scan. Error: %s", e)
        scan_filters = []
        if title:
            scan_filters.append(Attr("title").eq(title))
        if artist:
            scan_filters.append(Attr("artist").eq(artist))
        if album:
            scan_filters.append(Attr("album").eq(album))
        if year:
            scan_filters.append(Attr("year").eq(year))

        filter_expr = combine_conditions(scan_filters)
        response_items = [
            MusicSearchItem.model_validate(item)
            for item in (
                music_table.scan(FilterExpression=filter_expr)
                if filter_expr is not None
                else music_table.scan()
            ).get("Items", [])
        ]
    items = response_items

    for item in items:
        image_key = item.img_url or item.image_url
        if image_key:
            item.image_url = create_presigned_image_url(str(image_key))

    if not items:
        logger.debug("Song search returned no results")
        return MusicSearchResponse(message="No result is retrieved. Please query again")

    logger.debug("Song search returned %s items", len(items))
    return MusicSearchResponse(items=items)


@router.get("/songs/search")
def search_songs_get(
    title: str | None = None,
    year: int | None = None,
    artist: str | None = None,
    album: str | None = None,
) -> MusicSearchResponse:
    """
    This function implements the /songs/search GET endpoint, allowing users to search for songs based on title, artist, album, and year using query parameters. It simply converts the query parameters into a SearchRequest and calls the existing search_songs POST handler.

    :param str | None title: The title of the song to search for, defaults to None
    :param int | None year: The year of the song to search for, defaults to None
    :param str | None artist: The artist of the song to search for, defaults to None
    :param str | None album: The album of the song to search for, defaults to None
    :return MusicSearchResponse: The response containing the search results
    """
    payload = SearchRequest(title=title, year=year, artist=artist, album=album)
    return search_songs(payload)

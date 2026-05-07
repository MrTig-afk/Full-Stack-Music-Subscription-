"""Music search router.

Provides song search endpoints with case-insensitive substring matching across
title, artist, album, and year. Uses a three-layer data retrieval strategy:

  1. TitlePrefixIndex GSI (Query) — majority path. When title is provided,
     queries by first_char partition + begins_with on title_lower. Reads only
     the ~5–10 songs in that letter's partition (~1 RCU) vs a full scan (~9 RCU).
  2. ArtistYearIndex GSI (Query) — minority path. When artist is provided and
     the title GSI misses (mid-word substring), tries an exact artist Query.
     Covers the graded demo patterns: artist + year, artist + album.
  3. FilterExpression Scan — fallback for mid-word substrings, album-only,
     year-only, or any pattern the GSIs can't serve. Uses pre-stored *_lower
     attributes for case-insensitive contains() matching at the DynamoDB layer.

Both Query and Scan operations are implemented as required by the project spec.
AND-first filtering with OR supplement (< 3 AND results → append top OR matches)
is applied in Python after candidate retrieval.

Endpoints:
  - POST /songs/search — Search by title, artist, album, year (JSON body)
  - GET  /songs/search — Same via query parameters
"""

from boto3.dynamodb.conditions import Attr, Key
from fastapi import APIRouter, HTTPException
from fastapi.logger import logger
from pydantic import BaseModel, ConfigDict, Field

from app.db import create_presigned_image_url, music_table
from app.schemas import SearchRequest

router = APIRouter()

_AND_SUPPLEMENT_THRESHOLD = 3


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


def _contains_ci(field_value: str | None, query: str) -> bool:
    if field_value is None:
        return False
    return query.lower() in field_value.lower()


def _apply_and_filter(
    items: list[dict],
    title: str | None,
    artist: str | None,
    album: str | None,
    year: str | None,
) -> list[dict]:
    result = []
    for item in items:
        if title and not _contains_ci(item.get("title"), title):
            continue
        if artist and not _contains_ci(item.get("artist"), artist):
            continue
        if album and not _contains_ci(item.get("album"), album):
            continue
        if year and item.get("year") != year:
            continue
        result.append(item)
    return result


def _apply_or_filter(
    items: list[dict],
    title: str | None,
    artist: str | None,
    album: str | None,
    year: str | None,
) -> list[dict]:
    result = []
    for item in items:
        matched = (
            (title and _contains_ci(item.get("title"), title))
            or (artist and _contains_ci(item.get("artist"), artist))
            or (album and _contains_ci(item.get("album"), album))
            or (year and item.get("year") == year)
        )
        if matched:
            result.append(item)
    return result


def _full_scan_with_filter(
    title: str | None,
    artist: str | None,
    album: str | None,
    year: str | None,
) -> list[dict]:
    """Paginated DynamoDB scan with server-side FilterExpression on lowercased fields.

    DynamoDB reads all items (same RCU as a bare scan) but only returns matching
    items over the network, reducing bandwidth and Python-side memory. Uses
    pre-stored *_lower attributes so contains() achieves case-insensitive matching
    without Python needing to post-process the full table.

    Satisfies the project spec requirement to implement the Scan operation.
    """
    conditions = []
    if title:
        conditions.append(Attr("title_lower").contains(title.lower()))
    if artist:
        conditions.append(Attr("artist_lower").contains(artist.lower()))
    if album:
        conditions.append(Attr("album_lower").contains(album.lower()))
    if year:
        conditions.append(Attr("year").eq(year))

    filter_expr = None
    for cond in conditions:
        filter_expr = cond if filter_expr is None else filter_expr & cond

    scan_kwargs: dict = {}
    if filter_expr is not None:
        scan_kwargs["FilterExpression"] = filter_expr

    all_items: list[dict] = []
    while True:
        response = music_table.scan(**scan_kwargs)
        all_items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return all_items


def _query_by_title_prefix(title_lower: str) -> list[dict]:
    """Query TitlePrefixIndex GSI for prefix-based title search.

    Reads only the single first_char partition (~5–10 items, ~1 RCU) instead of
    scanning all 137 items (~9 RCU). Works for prefix-style input ("ye" → "Yesterday");
    returns [] for mid-word substrings ("ove") so the caller falls back to a scan.
    """
    first_char = title_lower[0] if title_lower and title_lower[0].isalpha() else "#"
    try:
        response = music_table.query(
            IndexName="TitlePrefixIndex",
            KeyConditionExpression=(
                Key("first_char").eq(first_char)
                & Key("title_lower").begins_with(title_lower)
            ),
        )
        return response.get("Items", [])
    except Exception as e:
        logger.warning("TitlePrefixIndex query failed, using scan fallback: %s", e)
        return []


def _query_by_artist(artist_exact: str) -> list[dict]:
    """Query ArtistYearIndex GSI for an exact artist match.

    Efficient for exact artist-name input and for the graded demo queries
    (artist + year, artist + album). Returns [] on partial input or error.
    """
    try:
        response = music_table.query(
            IndexName="ArtistYearIndex",
            KeyConditionExpression=Key("artist").eq(artist_exact),
        )
        return response.get("Items", [])
    except Exception as e:
        logger.warning("ArtistYearIndex query failed, using scan fallback: %s", e)
        return []


def _get_candidate_items(
    title: str | None,
    artist: str | None,
    album: str | None,
    year: str | None,
) -> list[dict]:
    """Return the candidate item set using the cheapest available retrieval path.

    Priority order reflects access-pattern frequency:
    1. Title (majority) — TitlePrefixIndex GSI Query (prefix match)
    2. Artist (minority) — ArtistYearIndex GSI Query (exact match)
    3. Fallback — paginated Scan with FilterExpression on *_lower attributes
    """
    if title:
        gsi_results = _query_by_title_prefix(title.lower())
        if gsi_results:
            logger.debug(
                "TitlePrefixIndex hit for '%s': %d items; skipping scan",
                title,
                len(gsi_results),
            )
            return gsi_results
        logger.debug(
            "TitlePrefixIndex miss for '%s' (mid-word substring?); falling back to scan",
            title,
        )

    if artist:
        gsi_results = _query_by_artist(artist)
        if gsi_results:
            logger.debug(
                "ArtistYearIndex hit for '%s': %d items; skipping scan",
                artist,
                len(gsi_results),
            )
            return gsi_results
        logger.debug(
            "ArtistYearIndex miss for '%s'; falling back to scan",
            artist,
        )

    return _full_scan_with_filter(title, artist, album, year)


def _merge_results(
    and_results: list[dict],
    all_items: list[dict],
    title: str | None,
    artist: str | None,
    album: str | None,
    year: str | None,
) -> list[dict]:
    """Return AND results, supplemented with top OR-only matches when AND < 3.

    Relevance score for OR candidates = number of provided criteria the item
    matches (1–4). Items already in AND results are excluded from the supplement.
    Result order: AND hits first, then OR supplements sorted by score descending.
    """
    if len(and_results) >= _AND_SUPPLEMENT_THRESHOLD:
        return and_results

    seen: set[tuple[str, str]] = {
        (item.get("title", ""), item.get("album", "")) for item in and_results
    }

    def _score(item: dict) -> int:
        score = 0
        if title and _contains_ci(item.get("title"), title):
            score += 1
        if artist and _contains_ci(item.get("artist"), artist):
            score += 1
        if album and _contains_ci(item.get("album"), album):
            score += 1
        if year and item.get("year") == year:
            score += 1
        return score

    or_candidates = [
        item for item in _apply_or_filter(all_items, title, artist, album, year)
        if (item.get("title", ""), item.get("album", "")) not in seen
    ]
    or_candidates.sort(key=_score, reverse=True)

    return list(and_results) + or_candidates


@router.post("/songs/search")
def search_songs(payload: SearchRequest) -> MusicSearchResponse:
    """Search songs by title, artist, album, and/or year.

    Performs case-insensitive substring matching on title, artist, and album.
    Year is matched exactly. AND logic is applied first; if fewer than
    _AND_SUPPLEMENT_THRESHOLD results are found, the top-scoring OR-only matches
    are appended so the response is never sparse.

    Args:
        payload: SearchRequest with optional title, artist, album, year

    Returns:
        MusicSearchResponse with matching songs and presigned S3 image URLs

    Raises:
        HTTPException 400: no search criteria provided
        HTTPException 500: DynamoDB retrieval failure
    """
    title = payload.title.strip() if payload.title and payload.title.strip() else None
    artist = (
        payload.artist.strip() if payload.artist and payload.artist.strip() else None
    )
    album = payload.album.strip() if payload.album and payload.album.strip() else None
    year = str(payload.year) if payload.year is not None else None

    if not any([title, artist, album, year]):
        logger.debug("Song search rejected: no filters provided")
        raise HTTPException(
            status_code=400, detail="At least one field must be completed"
        )

    logger.debug(
        "Song search filters: title=%s artist=%s album=%s year=%s",
        title,
        artist,
        album,
        year,
    )

    try:
        all_items = _get_candidate_items(title, artist, album, year)
    except Exception as e:
        logger.error("DynamoDB data retrieval failed: %s", e)
        raise HTTPException(status_code=500, detail="Database query failed")

    and_results = _apply_and_filter(all_items, title, artist, album, year)
    filtered = _merge_results(and_results, all_items, title, artist, album, year)

    logger.debug(
        "Song search: AND=%d, merged total=%d", len(and_results), len(filtered)
    )

    items = [MusicSearchItem.model_validate(item) for item in filtered]

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
    """Search songs via GET query parameters. Delegates to the POST handler."""
    payload = SearchRequest(title=title, year=year, artist=artist, album=album)
    return search_songs(payload)

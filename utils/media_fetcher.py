"""Fetch public artwork and audio previews for Spotify catalog tracks."""

from __future__ import annotations

import html
import json
import logging
import re
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 4
MEDIA_CACHE_TTL = 300
SPOTIFY_TRACK_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")
JAPANESE_TEXT_PATTERN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


class TrackMedia(TypedDict):
    cover_url: str
    preview_url: str | None
    fallback_preview_url: str | None


def primary_artist(artists: str) -> str:
    """Return the first artist when names are stored as a delimited string."""
    return re.split(r"[;,]", artists, maxsplit=1)[0].strip()


def deduplicate_recommendations(tracks: pd.DataFrame) -> pd.DataFrame:
    """Keep the first row for each case-insensitive title and primary artist."""
    required = {"track_name", "artists"}
    missing = required.difference(tracks.columns)
    if missing:
        raise ValueError(f"Kolom rekomendasi tidak tersedia: {', '.join(sorted(missing))}")
    if tracks.empty:
        return tracks.copy()

    keys = pd.DataFrame(
        {
            "title": tracks["track_name"].fillna("").astype(str).str.strip().str.casefold(),
            "artist": tracks["artists"].fillna("").astype(str).map(primary_artist).str.casefold(),
        },
        index=tracks.index,
    )
    empty_keys = keys["title"].eq("") & keys["artist"].eq("")
    if empty_keys.any():
        keys.loc[empty_keys, "title"] = [
            f"__unknown_row_{position}"
            for position in range(len(tracks))
            if empty_keys.iloc[position]
        ]

    result = tracks.loc[~keys.duplicated(keep="first")].copy().reset_index(drop=True)
    result.attrs = tracks.attrs.copy()
    return result


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def clean_track_title(title: str) -> str:
    """Remove common release annotations that make public music searches less precise."""
    cleaned = re.sub(
        r"\s*[\[(]\s*(?:feat(?:uring)?\.?|with)\b[^\])]*[\])]",
        "",
        title,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*-\s*(?:\d{4}\s*)?remaster(?:ed)?\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*[\[(]\s*(?:explicit|clean|radio edit)\b[^\])]*[\])]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip()


def _spotify_track_id(value: object) -> str:
    candidate = _text(value)
    if SPOTIFY_TRACK_ID_PATTERN.fullmatch(candidate):
        return candidate
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return ""
    if parsed.scheme != "https" or parsed.hostname not in {
        "open.spotify.com",
        "www.open.spotify.com",
    }:
        return ""
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "track":
        return ""
    track_id = parts[1]
    return track_id if SPOTIFY_TRACK_ID_PATTERN.fullmatch(track_id) else ""


def _has_japanese(text: str) -> bool:
    return bool(JAPANESE_TEXT_PATTERN.search(text))


def _normalize_name(text: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold(), flags=re.UNICODE).split())


def _valid_https_url(value: object, allowed_domains: tuple[str, ...]) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        host = parsed.hostname.lower() if parsed.hostname else ""
    except ValueError as exc:
        LOGGER.warning("Ignoring malformed media URL: %s", exc)
        return None
    if parsed.scheme != "https" or not any(
        host == domain or host.endswith(f".{domain}")
        for domain in allowed_domains
    ):
        return None
    return value


def _request_json(url: str, provider: str) -> dict[str, object] | None:
    for attempt in range(2):
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "TuneCluster/1.0"},
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if attempt == 0 and exc.code in {403, 429}:
                exc.close()
                time.sleep(0.2)
                continue
            LOGGER.warning("%s metadata request failed: %s", provider, exc)
            return None
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            if attempt == 0:
                time.sleep(0.2)
                continue
            LOGGER.warning("%s metadata request failed: %s", provider, exc)
            return None
        if not isinstance(payload, dict):
            LOGGER.warning("%s metadata response was not a JSON object", provider)
            return None
        return {str(key): value for key, value in payload.items()}
    return None


def _search_variants(title: str, artist: str) -> list[tuple[str, str | None]]:
    combined = " ".join(part for part in (title, artist) if part)
    variants = [(combined, None), (title, None)] if combined else []
    if title and _has_japanese(title):
        variants.append((title, "JP"))
    return list(dict.fromkeys(variant for variant in variants if variant[0]))


def _title_matches(requested: str, result: str) -> bool:
    target = _normalize_name(requested)
    candidate = _normalize_name(result)
    if not target or not candidate:
        return False
    return (
        target == candidate
        or target in candidate
        or candidate.startswith(f"{target} ")
        or target.startswith(f"{candidate} ")
    )


def _rank_records(
    records: list[dict[str, object]],
    title: str,
    artist: str,
    *,
    provider: str,
) -> list[dict[str, object]]:
    def record_title(record: dict[str, object]) -> str:
        return _text(record.get("trackName" if provider == "itunes" else "title"))

    def record_artist(record: dict[str, object]) -> str:
        raw_artist = record.get("artistName") if provider == "itunes" else record.get("artist")
        if isinstance(raw_artist, dict):
            raw_artist = raw_artist.get("name")
        return _text(raw_artist)

    relevant = [
        record
        for record in records
        if _title_matches(title, record_title(record))
    ]
    return sorted(
        relevant,
        key=lambda record: (
            _normalize_name(primary_artist(record_artist(record)))
            == _normalize_name(artist),
            bool(_itunes_artwork(record) or _deezer_artwork(record))
            and bool(_itunes_preview(record) or _deezer_preview(record)),
        ),
        reverse=True,
    )


def _itunes_artwork(record: dict[str, object]) -> str | None:
    artwork = _valid_https_url(record.get("artworkUrl100"), ("mzstatic.com",))
    if artwork is None:
        return None
    return re.sub(
        r"/\d+x\d+bb(?=\.jpg(?:[?#]|$))",
        "/600x600bb",
        artwork,
        flags=re.IGNORECASE,
    )


def _itunes_preview(record: dict[str, object]) -> str | None:
    return _valid_https_url(record.get("previewUrl"), ("itunes.apple.com",))


def _deezer_artwork(record: dict[str, object]) -> str | None:
    album = record.get("album")
    if not isinstance(album, dict):
        return None
    return _valid_https_url(
        album.get("cover_xl") or album.get("cover_big"),
        ("dzcdn.net",),
    )


def _deezer_preview(record: dict[str, object]) -> str | None:
    return _valid_https_url(record.get("preview"), ("dzcdn.net",))


@st.cache_data(ttl=MEDIA_CACHE_TTL, show_spinner=False)
def get_spotify_cover_url(track_id: str) -> str | None:
    """Look up a cover from Spotify oEmbed after validating the Spotify track ID."""
    clean_id = _spotify_track_id(track_id)
    if not SPOTIFY_TRACK_ID_PATTERN.fullmatch(clean_id):
        return None
    track_url = f"https://open.spotify.com/track/{clean_id}"
    oembed_url = "https://open.spotify.com/oembed?" + urlencode({"url": track_url})
    metadata = _request_json(oembed_url, "Spotify oEmbed")
    if metadata is None:
        return None
    return _valid_https_url(
        metadata.get("thumbnail_url"),
        ("i.scdn.co", "image-cdn-ak.spotifycdn.com"),
    )


def placeholder_cover_data_uri(track_name: str) -> str:
    """Build a compact dark SVG cover with initials for tracks without artwork."""
    words = re.findall(r"[^\W_]+", track_name.strip(), flags=re.UNICODE)
    initials = "".join(word[0] for word in words[:2]).upper() or "?"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">'
        '<rect width="600" height="600" fill="#121212"/>'
        '<circle cx="300" cy="300" r="220" fill="#1DB954" opacity=".12"/>'
        '<text x="300" y="338" text-anchor="middle" fill="#1DB954" '
        'font-family="system-ui, sans-serif" font-size="150" font-weight="700">'
        f"{html.escape(initials)}"
        "</text></svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


@st.cache_data(ttl=MEDIA_CACHE_TTL, show_spinner=False)
def fetch_track_media(
    track_name: str,
    artists: str,
    track_id: str | None = None,
) -> TrackMedia:
    """Prefer Spotify artwork, then fill missing media from iTunes and Deezer."""
    title = clean_track_title(_text(track_name))
    artist = primary_artist(_text(artists))
    spotify_id = _spotify_track_id(track_id)
    cover_url = get_spotify_cover_url(spotify_id) if spotify_id else None
    preview_url: str | None = None
    fallback_preview_url: str | None = None
    preview_source: str | None = None
    variants = _search_variants(title, artist)

    for term, country in variants:
        if cover_url and preview_url:
            break
        params: dict[str, str] = {"term": term, "entity": "song", "limit": "5"}
        if country:
            params["country"] = country
        payload = _request_json(
            "https://itunes.apple.com/search?" + urlencode(params),
            "iTunes",
        )
        raw_results = payload.get("results") if payload else None
        records = [row for row in raw_results if isinstance(row, dict)] if isinstance(raw_results, list) else []
        for record in _rank_records(records, title, artist, provider="itunes"):
            cover_url = cover_url or _itunes_artwork(record)
            itunes_preview = _itunes_preview(record)
            if preview_url is None and itunes_preview:
                preview_url = itunes_preview
                preview_source = "itunes"
            if cover_url and preview_url:
                break
        if cover_url and preview_url:
            break

    deezer_terms = list(dict.fromkeys(term for term, _ in variants))
    for term in deezer_terms:
        if cover_url and preview_url and (
            preview_source == "deezer" or fallback_preview_url
        ):
            break
        payload = _request_json(
            "https://api.deezer.com/search?" + urlencode({"q": term, "limit": "5"}),
            "Deezer",
        )
        raw_results = payload.get("data") if payload else None
        records = [row for row in raw_results if isinstance(row, dict)] if isinstance(raw_results, list) else []
        for record in _rank_records(records, title, artist, provider="deezer"):
            cover_url = cover_url or _deezer_artwork(record)
            deezer_preview = _deezer_preview(record)
            if preview_url is None and deezer_preview:
                preview_url = deezer_preview
                preview_source = "deezer"
            elif (
                preview_source == "itunes"
                and fallback_preview_url is None
                and deezer_preview != preview_url
            ):
                fallback_preview_url = deezer_preview
            if cover_url and preview_url and (
                preview_source == "deezer" or fallback_preview_url
            ):
                break

    if cover_url is None:
        LOGGER.warning("No remote cover found for %r by %r; using initials placeholder", title, artist)
        cover_url = placeholder_cover_data_uri(title)

    return {
        "cover_url": cover_url,
        "preview_url": preview_url,
        "fallback_preview_url": fallback_preview_url,
    }


def _fetch_track_row(track: Mapping[str, object]) -> TrackMedia:
    track_name = _text(track.get("track_name"))
    artists = _text(track.get("artists"))
    track_id = next(
        (
            candidate
            for candidate in (
                _text(track.get("track_id")),
                _text(track.get("spotify_id")),
                _text(track.get("spotify_url")),
            )
            if _spotify_track_id(candidate)
        ),
        None,
    )
    return fetch_track_media(track_name, artists, track_id)


def fetch_recommendation_media(
    tracks: Sequence[Mapping[str, object]],
) -> list[TrackMedia]:
    """Fetch media for recommendation rows concurrently, preserving row order."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(_fetch_track_row, tracks))

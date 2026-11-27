import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pandas as pd

from utils.media_fetcher import (
    deduplicate_recommendations,
    fetch_track_media,
    get_spotify_cover_url,
    primary_artist,
)


def _mock_json_response(payload: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return response


def _itunes_result(
    title: str = "Comedy",
    artist: str = "Gen Hoshino",
) -> dict[str, object]:
    return {
        "trackName": title,
        "artistName": artist,
        "artworkUrl100": "https://is1-ssl.mzstatic.com/image/100x100bb.jpg",
        "previewUrl": "https://audio-ssl.itunes.apple.com/preview.m4a",
    }


def test_primary_artist_uses_first_semicolon_or_comma_delimited_name() -> None:
    assert primary_artist("Rustage;Shwabadi;PESO PETE") == "Rustage"
    assert primary_artist("Artist One, Artist Two") == "Artist One"


def test_deduplicate_recommendations_preserves_first_row_and_attrs() -> None:
    tracks = pd.DataFrame(
        [
            {"track_name": "Go Big or Go Home", "artists": "ENHYPEN", "track_id": "first"},
            {"track_name": "go big or go home", "artists": "ENHYPEN", "track_id": "duplicate"},
            {"track_name": "Yonko", "artists": "Rustage;Shwabadi;PESO PETE", "track_id": "third"},
            {"track_name": "YONKO", "artists": "Rustage", "track_id": "duplicate-artist"},
        ]
    )
    tracks.attrs["target_cluster"] = 2

    result = deduplicate_recommendations(tracks)

    assert result["track_id"].tolist() == ["first", "third"]
    assert result.attrs["target_cluster"] == 2


def test_itunes_result_upgrades_artwork_and_returns_preview() -> None:
    fetch_track_media.clear()
    response = _mock_json_response({"results": [_itunes_result()]})

    with patch("utils.media_fetcher.urlopen", return_value=response) as urlopen:
        media = fetch_track_media("Comedy", "Gen Hoshino", None)

    assert media == {
        "cover_url": "https://is1-ssl.mzstatic.com/image/600x600bb.jpg",
        "preview_url": "https://audio-ssl.itunes.apple.com/preview.m4a",
    }
    query = parse_qs(urlparse(urlopen.call_args.args[0].full_url).query)
    assert query["term"] == ["Comedy Gen Hoshino"]
    assert urlopen.call_args.kwargs["timeout"] == 4


def test_japanese_query_is_utf8_encoded_and_retries_with_japan_store() -> None:
    fetch_track_media.clear()
    empty = _mock_json_response({"results": []})
    japanese_result = _mock_json_response(
        {"results": [_itunes_result("白金ディスコ", "物語シリーズ")]}
    )

    with patch(
        "utils.media_fetcher.urlopen",
        side_effect=[empty, japanese_result],
    ) as urlopen:
        media = fetch_track_media("白金ディスコ", "物語シリーズ", None)

    assert media["cover_url"].endswith("/600x600bb.jpg")
    assert media["preview_url"].endswith(".m4a")
    first_url = urlopen.call_args_list[0].args[0].full_url
    second_url = urlopen.call_args_list[1].args[0].full_url
    assert "%E7%99%BD%E9%87%91%E3%83%87%E3%82%A3%E3%82%B9%E3%82%B3" in first_url
    assert parse_qs(urlparse(second_url).query)["country"] == ["JP"]


def test_deezer_fills_metadata_after_itunes_misses_and_uses_primary_artist() -> None:
    fetch_track_media.clear()
    empty = _mock_json_response({"results": []})
    deezer_result = _mock_json_response(
        {
            "data": [
                {
                    "title": "Yonko (feat. Shwabadi)",
                    "artist": {"name": "Rustage"},
                    "album": {"cover_xl": "https://cdn-images.dzcdn.net/images/cover.jpg"},
                    "preview": "https://cdn-preview-4.dzcdn.net/preview.mp3",
                }
            ]
        }
    )

    with patch(
        "utils.media_fetcher.urlopen",
        side_effect=[empty, empty, deezer_result],
    ) as urlopen:
        media = fetch_track_media(
            "Yonko",
            "Rustage;Shwabadi;PESO PETE;Lex Bratcher",
            None,
        )

    assert media["cover_url"] == "https://cdn-images.dzcdn.net/images/cover.jpg"
    assert media["preview_url"] == "https://cdn-preview-4.dzcdn.net/preview.mp3"
    deezer_query = parse_qs(urlparse(urlopen.call_args_list[2].args[0].full_url).query)
    assert deezer_query["q"] == ["Yonko Rustage"]


def test_missing_remote_artwork_uses_dark_initials_svg() -> None:
    fetch_track_media.clear()
    empty = _mock_json_response({"results": []})
    deezer_empty = _mock_json_response({"data": []})

    with patch(
        "utils.media_fetcher.urlopen",
        side_effect=[empty, empty, deezer_empty, deezer_empty],
    ):
        media = fetch_track_media("Blue Bird", "Ikimono-gakari", None)

    assert media["cover_url"].startswith("data:image/svg+xml;charset=utf-8,")
    assert "BB" in media["cover_url"]
    assert media["preview_url"] is None


def test_spotify_oembed_is_used_when_music_search_has_no_cover() -> None:
    fetch_track_media.clear()
    get_spotify_cover_url.clear()
    empty_itunes = _mock_json_response({"results": []})
    empty_deezer = _mock_json_response({"data": []})
    spotify_response = _mock_json_response(
        {"thumbnail_url": "https://image-cdn-ak.spotifycdn.com/image/spotify-cover"}
    )

    with patch(
        "utils.media_fetcher.urlopen",
        side_effect=[
            empty_itunes,
            empty_itunes,
            empty_deezer,
            empty_deezer,
            spotify_response,
        ],
    ):
        media = fetch_track_media("Unknown Track", "Unknown Artist", "e" * 22)

    assert media["cover_url"] == "https://image-cdn-ak.spotifycdn.com/image/spotify-cover"
    assert media["preview_url"] is None

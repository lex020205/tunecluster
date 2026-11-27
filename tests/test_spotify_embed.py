import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from utils.media_fetcher import get_spotify_cover_url


def _mock_oembed_response(payload: dict[str, str]) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
    return response


def test_spotify_cover_url_uses_public_oembed_endpoint() -> None:
    get_spotify_cover_url.clear()
    response = _mock_oembed_response(
        {"thumbnail_url": "https://i.scdn.co/image/test-cover"}
    )

    with patch("utils.media_fetcher.urlopen", return_value=response) as urlopen:
        result = get_spotify_cover_url("a" * 22)

    assert result == "https://i.scdn.co/image/test-cover"
    assert urlopen.call_args.kwargs["timeout"] == 4


def test_spotify_cover_url_falls_back_when_oembed_fails() -> None:
    get_spotify_cover_url.clear()

    with patch("utils.media_fetcher.urlopen", side_effect=URLError("timeout")):
        assert get_spotify_cover_url("b" * 22) is None


def test_spotify_cover_url_rejects_non_spotify_thumbnail_hosts() -> None:
    get_spotify_cover_url.clear()
    response = _mock_oembed_response(
        {"thumbnail_url": "https://example.com/not-a-cover"}
    )

    with patch("utils.media_fetcher.urlopen", return_value=response):
        assert get_spotify_cover_url("c" * 22) is None


def test_spotify_cover_url_accepts_current_spotify_cdn_host() -> None:
    get_spotify_cover_url.clear()
    response = _mock_oembed_response(
        {"thumbnail_url": "https://image-cdn-ak.spotifycdn.com/image/test-cover"}
    )

    with patch("utils.media_fetcher.urlopen", return_value=response):
        assert get_spotify_cover_url("d" * 22) == (
            "https://image-cdn-ak.spotifycdn.com/image/test-cover"
        )

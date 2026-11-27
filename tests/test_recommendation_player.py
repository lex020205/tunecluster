import json

from utils.recommendation_player import serialize_player_tracks


def test_player_track_payload_is_script_safe_and_preserves_track_data() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "</script><script>alert(1)</script>",
        "artists": "Artist",
        "cover_url": "https://example.com/cover.jpg",
        "preview_url": None,
        "spotify_url": "https://open.spotify.com/search/track",
    }

    serialized = serialize_player_tracks([track])

    assert "</script>" not in serialized.lower()
    assert json.loads(serialized) == [
        {
            "track_id": "track-1",
            "track_name": "</script><script>alert(1)</script>",
            "artists": "Artist",
            "cover_url": "https://example.com/cover.jpg",
            "preview_url": None,
            "spotify_url": "https://open.spotify.com/search/track",
        }
    ]

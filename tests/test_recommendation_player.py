import json

from utils.recommendation_player import PLAYER_COMPONENT_HTML, serialize_player_tracks


def test_player_track_payload_is_script_safe_and_preserves_track_data() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "</script><script>alert(1)</script>",
        "artists": "Artist",
        "cover_url": "https://example.com/cover.jpg",
        "preview_url": None,
        "spotify_url": "https://open.spotify.com/search/track",
        "card_keys": ["track-1"],
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
            "card_keys": ["track-1"],
        }
    ]


def test_player_uses_one_shared_audio_element_and_real_volume_controls() -> None:
    assert 'doc.createElement("audio")' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("timeupdate"' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("loadedmetadata"' in PLAYER_COMPONENT_HTML
    assert 'data-player-volume aria-label="Volume"' in PLAYER_COMPONENT_HTML
    assert 'refs.volume.addEventListener("input"' in PLAYER_COMPONENT_HTML
    assert 'refs.volume.addEventListener("change"' in PLAYER_COMPONENT_HTML
    assert 'localStorage.setItem("tc_volume"' in PLAYER_COMPONENT_HTML
    assert "Math.min(1, Math.max(0, parsedVolume))" in PLAYER_COMPONENT_HTML

import json
from unittest.mock import patch

from utils.recommendation_player import (
    PLAYER_COMPONENT_HTML,
    render_recommendation_player,
    serialize_player_tracks,
)


def test_player_track_payload_is_script_safe_and_preserves_track_data() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "</script><script>alert(1)</script>",
        "artists": "Artist",
        "cover_url": "https://example.com/cover.jpg",
        "preview_url": "https://audio-ssl.itunes.apple.com/preview.m4a",
        "fallback_preview_url": "https://cdn-preview-4.dzcdn.net/preview.mp3",
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
            "preview_url": "https://audio-ssl.itunes.apple.com/preview.m4a",
            "fallback_preview_url": "https://cdn-preview-4.dzcdn.net/preview.mp3",
            "spotify_url": "https://open.spotify.com/search/track",
            "card_keys": ["track-1"],
        }
    ]


def test_player_uses_one_shared_audio_element_and_real_volume_controls() -> None:
    assert 'doc.createElement("audio")' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("timeupdate"' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("loadedmetadata"' in PLAYER_COMPONENT_HTML
    assert 'data-player-volume aria-label="Volume"' in PLAYER_COMPONENT_HTML
    assert 'doc.addEventListener("input", handlePlayerInput, true)' in PLAYER_COMPONENT_HTML
    assert 'doc.addEventListener("change", handlePlayerChange, true)' in PLAYER_COMPONENT_HTML
    assert 'localStorage.setItem("tc_volume"' in PLAYER_COMPONENT_HTML
    assert "Math.min(1, Math.max(0, parsedVolume))" in PLAYER_COMPONENT_HTML
    assert "bar.hidden = !active" in PLAYER_COMPONENT_HTML
    assert "tracks[0]" in PLAYER_COMPONENT_HTML
    assert "Preview audio tidak tersedia untuk lagu ini" in PLAYER_COMPONENT_HTML
    assert "[TuneCluster player] play requested" in PLAYER_COMPONENT_HTML
    assert "audio.src = previewUrl" in PLAYER_COMPONENT_HTML
    assert "function primaryPreviewUrl(track)" in PLAYER_COMPONENT_HTML
    assert "retrying with fallback preview" in PLAYER_COMPONENT_HTML
    assert 'doc.addEventListener("click", handleDocumentClick, true)' in PLAYER_COMPONENT_HTML
    assert "player.version > playerVersion" in PLAYER_COMPONENT_HTML
    assert "player.version !== playerVersion" in PLAYER_COMPONENT_HTML
    assert "audio.error.code === 1" in PLAYER_COMPONENT_HTML
    assert "body:not(:has(.tc-rec-scope-marker)) #tc-recommendation-player" in PLAYER_COMPONENT_HTML
    assert "host.setInterval(reconcilePage, 500)" in PLAYER_COMPONENT_HTML
    assert "player.update(incomingTracks, incomingDefaultTrackId)" in PLAYER_COMPONENT_HTML


def test_player_renders_selected_default_track_into_component() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "Track",
        "artists": "Artist",
        "preview_url": "https://audio.example/preview.m4a",
        "fallback_preview_url": "https://cdn-preview.dzcdn.net/preview.mp3",
    }

    with patch("utils.recommendation_player.st.components.v1.html") as component:
        render_recommendation_player([track], default_track_id="track-1")

    component_html = component.call_args.args[0]
    assert 'const incomingDefaultTrackId = "track-1";' in component_html
    assert '"fallback_preview_url":"https://cdn-preview.dzcdn.net/preview.mp3"' in component_html
    assert "__TRACKS_JSON__" not in component_html

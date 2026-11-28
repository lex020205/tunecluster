import json
from unittest.mock import MagicMock, patch

from utils.recommendation_player import (
    PLAYER_COMPONENT_HTML,
    PLAYER_FRAME_HEIGHT,
    render_recommendation_player,
    request_track_play,
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


def test_player_is_self_contained_and_uses_svg_controls() -> None:
    assert "window.parent" not in PLAYER_COMPONENT_HTML
    assert "const audio = new Audio()" in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("timeupdate"' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("loadedmetadata"' in PLAYER_COMPONENT_HTML
    assert 'audio.addEventListener("error"' in PLAYER_COMPONENT_HTML
    assert 'data-player-action="prev"' in PLAYER_COMPONENT_HTML
    assert 'data-player-action="toggle"' in PLAYER_COMPONENT_HTML
    assert 'data-player-action="next"' in PLAYER_COMPONENT_HTML
    assert '<svg viewBox="0 0 24 24">' in PLAYER_COMPONENT_HTML
    assert 'aria-label="Lagu sebelumnya"' in PLAYER_COMPONENT_HTML
    assert 'aria-label="Lagu berikutnya"' in PLAYER_COMPONENT_HTML
    assert 'min="0" max="1" step="0.01"' in PLAYER_COMPONENT_HTML
    assert "flex: 0 0 96px" in PLAYER_COMPONENT_HTML
    assert 'refs.volume.addEventListener("input"' in PLAYER_COMPONENT_HTML
    assert 'refs.volume.addEventListener("change"' in PLAYER_COMPONENT_HTML
    assert 'refs.mute.addEventListener("click", toggleMute)' in PLAYER_COMPONENT_HTML
    assert 'window.localStorage.setItem("tc_volume"' in PLAYER_COMPONENT_HTML
    assert 'storedVolumeValue === null' in PLAYER_COMPONENT_HTML
    assert "audio.volume > 0 && !audio.muted" in PLAYER_COMPONENT_HTML
    assert "audio.muted = volume === 0" in PLAYER_COMPONENT_HTML


def test_card_play_requests_autoplay_with_a_unique_request_id() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "Track",
        "preview_url": "https://audio.example/preview.m4a",
    }
    session_state: dict[str, object] = {}

    with patch("utils.recommendation_player.st.session_state", session_state):
        request_track_play(track)
        first_request_id = session_state["_player_play_request_id"]
        request_track_play(track)

    assert first_request_id == 1
    assert session_state["_player_play_request_id"] == 2
    assert session_state["_player_autoplay"] is True
    assert session_state["_player_selected_track_id"] == "track-1"
    selected_track = session_state["_player_selected_track"]
    assert isinstance(selected_track, dict)
    assert selected_track.get("preview_url") == track["preview_url"]


def test_player_autoplays_only_when_a_card_request_is_rendered() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "Track",
        "preview_url": "https://audio.example/preview.m4a",
    }
    container_context = MagicMock()

    with (
        patch("utils.recommendation_player.st.components.v1.html") as component,
        patch(
            "utils.recommendation_player.st.container",
            return_value=container_context,
        ),
    ):
        render_recommendation_player(
            [track],
            default_track_id="track-1",
            autoplay=True,
            play_request_id=42,
        )

    component_html = component.call_args.args[0]
    assert "const autoplay = true;" in component_html
    assert "const autoplayRequestId = 42;" in component_html
    assert "audio.preload = \"auto\";" in component_html
    assert "playTrack(currentTrack, autoplayRequestId);" in component_html
    assert "playRequest.catch((error) =>" in component_html
    assert "__AUTOPLAY__" not in component_html
    assert "__PLAY_REQUEST_ID__" not in component_html


def test_missing_or_failed_preview_triggers_fresh_itunes_lookup() -> None:
    assert "fetchFreshITunesPreview(track)" in PLAYER_COMPONENT_HTML
    assert "encodeURIComponent(" in PLAYER_COMPONENT_HTML
    assert "https://itunes.apple.com/search?term=${query}&entity=song&limit=3" in PLAYER_COMPONENT_HTML
    assert 'cache: "no-store"' in PLAYER_COMPONENT_HTML
    assert "recoverPreview(currentTrack, playRequestId, audio.src)" in PLAYER_COMPONENT_HTML
    assert "Preview tidak tersedia" in PLAYER_COMPONENT_HTML


def test_player_renders_in_a_fixed_parent_container() -> None:
    track = {
        "track_id": "track-1",
        "track_name": "Track",
        "artists": "Artist",
        "preview_url": "https://audio.example/preview.m4a",
        "fallback_preview_url": "https://cdn-preview.dzcdn.net/preview.mp3",
    }
    container_context = MagicMock()

    with (
        patch("utils.recommendation_player.st.components.v1.html") as component,
        patch(
            "utils.recommendation_player.st.container",
            return_value=container_context,
        ) as container,
    ):
        render_recommendation_player([track], default_track_id="track-1")

    container.assert_called_once_with(key="tc-recommendation-player-host")
    component_html = component.call_args.args[0]
    assert 'const defaultTrackId = "track-1";' in component_html
    assert '"fallback_preview_url":"https://cdn-preview.dzcdn.net/preview.mp3"' in component_html
    assert "__TRACKS_JSON__" not in component_html
    assert component.call_args.kwargs == {
        "height": PLAYER_FRAME_HEIGHT,
        "scrolling": False,
    }


def test_empty_player_does_not_render_an_empty_fixed_iframe() -> None:
    with (
        patch("utils.recommendation_player.st.components.v1.html") as component,
        patch("utils.recommendation_player.st.container") as container,
    ):
        render_recommendation_player([])

    component.assert_not_called()
    container.assert_not_called()

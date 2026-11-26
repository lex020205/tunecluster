"""
spotify_embed.py — Helper untuk menampilkan Spotify embed player dan kartu lagu di Streamlit.
"""

from __future__ import annotations

import html
import json
import logging
import re
from textwrap import dedent
from urllib.error import URLError
from urllib.parse import quote_plus, urlencode, urlparse
from urllib.request import Request, urlopen

import streamlit as st

SPOTIFY_TRACK_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")
LOGGER = logging.getLogger(__name__)


def is_valid_spotify_track_id(track_id: str | None) -> bool:
    """Periksa apakah `track_id` berformat valid Spotify Base62 (22 karakter alfanumerik)."""
    if not isinstance(track_id, str):
        return False
    return bool(SPOTIFY_TRACK_ID_PATTERN.fullmatch(track_id.strip()))


def get_spotify_embed_url(track_id: str) -> str:
    """Bangun URL iframe Spotify untuk `track_id` yang valid."""
    clean_id = str(track_id).strip() if track_id is not None else ""
    if not is_valid_spotify_track_id(clean_id):
        raise ValueError(f"Track ID Spotify tidak valid untuk embed: '{track_id}'")
    return f"https://open.spotify.com/embed/track/{clean_id}?utm_source=generator&theme=0"


def get_spotify_search_url(track_name: str, artists: str) -> str:
    """Bangun URL pencarian Spotify untuk lagu dan artis yang diberikan."""
    q_track = quote_plus(str(track_name or "").strip())
    q_artist = quote_plus(str(artists or "").strip())
    query = f"{q_track}+{q_artist}" if q_track and q_artist else (q_track or q_artist)
    return f"https://open.spotify.com/search/{query}"


@st.cache_data(ttl=86400, show_spinner=False)
def get_spotify_cover_url(track_id: str) -> str | None:
    """Fetch and cache an official album thumbnail from Spotify's public oEmbed endpoint."""
    clean_id = str(track_id).strip() if track_id is not None else ""
    if not is_valid_spotify_track_id(clean_id):
        return None

    track_url = f"https://open.spotify.com/track/{clean_id}"
    oembed_url = f"https://open.spotify.com/oembed?{urlencode({'url': track_url})}"
    request = Request(
        oembed_url,
        headers={"Accept": "application/json", "User-Agent": "TuneCluster/1.0"},
    )
    try:
        with urlopen(request, timeout=3) as response:
            metadata = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        LOGGER.warning("Spotify oEmbed cover lookup failed for track %s: %s", clean_id, exc)
        return None

    thumbnail_url = metadata.get("thumbnail_url") if isinstance(metadata, dict) else None
    parsed_url = urlparse(thumbnail_url) if isinstance(thumbnail_url, str) else None
    if (
        parsed_url is None
        or parsed_url.scheme != "https"
        or parsed_url.hostname != "i.scdn.co"
    ):
        LOGGER.warning("Spotify oEmbed returned no valid cover URL for track %s", clean_id)
        return None
    return thumbnail_url


def get_spotify_embed(track_id: str, height: int = 80) -> str:
    """
    Kembalikan HTML iframe Spotify embed player (dark theme) untuk `track_id`.

    Parameters
    ----------
    track_id : str
        ID track Spotify (22 karakter alfanumerik).
    height : int, default=80
        Tinggi iframe player dalam piksel (80 untuk compact, 152 untuk full).
    """
    safe_height = max(80, int(height))
    return (
        f'<iframe style="border-radius:12px" '
        f'src="{get_spotify_embed_url(track_id)}" '
        f'width="100%" height="{safe_height}" frameBorder="0" allowfullscreen="" '
        f'allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
        f'loading="lazy"></iframe>'
    )


def get_spotify_embed_compact(track_id: str) -> str:
    """Kembalikan HTML iframe Spotify embed versi compact/mini player (height=80)."""
    return get_spotify_embed(track_id, height=80)


def get_spotify_embed_full(track_id: str) -> str:
    """Kembalikan HTML iframe Spotify embed versi full player (height=152)."""
    return get_spotify_embed(track_id, height=152)


# Alias untuk kompatibilitas mundur
get_embed_html = get_spotify_embed


def _render_spotify_fallback_buttons(
    track_name: str,
    artists: str,
    track_id: str | None = None,
    pesan: str = "Player tidak dapat dimuat atau preview diblokir?",
) -> None:
    """Tampilkan tombol tautan fallback untuk membuka atau mencari lagu di Spotify."""
    search_url = html.escape(get_spotify_search_url(track_name, artists), quote=True)
    buttons_html = ""

    if is_valid_spotify_track_id(track_id):
        clean_id = str(track_id).strip()
        track_url = f"https://open.spotify.com/track/{clean_id}"
        buttons_html += (
            f'<a href="{track_url}" target="_blank" rel="noopener noreferrer" '
            f'class="tc-link-button tc-link-button-primary">Buka di Spotify</a>'
        )

    buttons_html += (
        f'<a href="{search_url}" target="_blank" rel="noopener noreferrer" '
        f'class="tc-link-button">Cari di Spotify</a>'
    )

    st.markdown(
        f'<div class="tc-fallback"><span class="tc-muted">{html.escape(pesan)}</span>'
        f'{buttons_html}</div>',
        unsafe_allow_html=True,
    )


def render_track_card(
    track_name: str,
    artists: str,
    genre: str,
    similarity_score: float,
    track_id: str | None = None,
    *,
    rank: int | None = None,
    show_player: bool = True,
    show_full_player: bool = True,
    jarak: float | None = None,
) -> None:
    """
    Render kartu sampul album, metadata lagu, similarity score, dan pemutar opsional.

    Parameters
    ----------
    track_name : str
        Judul lagu.
    artists : str
        Nama artis.
    genre : str
        String daftar genre (dipisah `|` atau `,`).
    similarity_score : float
        Skor kemiripan dalam persen (0–100).
    track_id : str | None, optional
        ID track Spotify. Jika tidak valid, tampilkan tombol Cari di Spotify.
    rank : int | None, optional
        Nomor urut lagu pada playlist.
    show_player : bool, default=True
        Apakah compact player langsung ditampilkan di kartu lagu.
    show_full_player : bool, default=True
        Apakah full player dan tautan Spotify ditampilkan dalam expander.
    jarak : float | None, optional
        Jarak Euclidean fitur audio (opsional untuk info tambahan).
    """
    safe_title = html.escape(str(track_name or "Tanpa Judul"))
    safe_artists = html.escape(str(artists or "Artis Tidak Diketahui"))
    cover_url = get_spotify_cover_url(str(track_id)) if is_valid_spotify_track_id(track_id) else None

    score_pct = min(100.0, max(0.0, float(similarity_score)))
    raw_genres = [
        g.strip()
        for g in re.split(r"\s*\|\s*|\s*,\s*", str(genre or ""))
        if g.strip()
    ]
    if not raw_genres:
        raw_genres = ["tidak dikategorikan"]

    genres_label = html.escape(" · ".join(raw_genres[:2]))
    cover_html = (
        f'<img src="{html.escape(cover_url, quote=True)}" '
        f'alt="Sampul {safe_title}" loading="lazy" decoding="async">'
        if cover_url
        else '<div class="tc-album-cover-placeholder">Sampul tidak tersedia</div>'
    )

    jarak_html = (
        f'<span class="tc-muted"> · Jarak {jarak:.4f}</span>'
        if jarak is not None
        else ""
    )

    with st.container(border=True):
        st.markdown(
            dedent(f"""
            <div class="tc-album-card">
                <div class="tc-album-cover">{cover_html}</div>
                <div class="tc-track-title">{safe_title}</div>
                <div class="tc-track-meta">{safe_artists}</div>
                <div class="tc-track-meta tc-track-genre">{genres_label}</div>
                <div class="tc-track-score">
                    Kemiripan {score_pct:.1f}%{jarak_html}
                    <div class="tc-score-track">
                        <div class="tc-score-fill" style="width:{score_pct:.1f}%;"></div>
                    </div>
                </div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )

        if is_valid_spotify_track_id(track_id):
            clean_id = str(track_id).strip()
            if show_player:
                try:
                    st.iframe(get_spotify_embed_url(clean_id), width="stretch", height=90)
                except Exception:
                    _render_spotify_fallback_buttons(
                        track_name,
                        artists,
                        clean_id,
                        pesan="Gagal memuat mini player.",
                    )

            if show_full_player:
                with st.expander("Pemutar dan tautan Spotify"):
                    try:
                        st.iframe(get_spotify_embed_url(clean_id), width="stretch", height=162)
                    except Exception:
                        st.warning("Full player gagal dimuat di browser ini.")
                    _render_spotify_fallback_buttons(
                        track_name,
                        artists,
                        clean_id,
                        pesan="Jika embed tidak dapat diputar:",
                    )
        else:
            st.caption("Embed Spotify tidak tersedia untuk format track ID lagu ini.")
            _render_spotify_fallback_buttons(
                track_name,
                artists,
                None,
                pesan="Putar langsung di Spotify:",
            )


def render_now_playing(track_name: str, artists: str, track_id: str | None) -> None:
    """Render a prominent Spotify player for the selected track."""
    st.subheader("Sedang diputar")
    with st.container(border=True):
        st.markdown(f"**{html.escape(str(track_name or 'Tanpa Judul'))}**")
        st.caption(str(artists or "Artis Tidak Diketahui"))
        if is_valid_spotify_track_id(track_id):
            st.iframe(get_spotify_embed_url(str(track_id).strip()), width="stretch", height=162)
        else:
            st.warning("Pemutar Spotify tidak tersedia untuk lagu ini.")
            _render_spotify_fallback_buttons(track_name, artists, track_id)

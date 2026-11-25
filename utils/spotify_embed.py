"""
spotify_embed.py — Helper untuk menampilkan Spotify embed player dan kartu lagu di Streamlit.
"""

from __future__ import annotations

import html
import re
from urllib.parse import quote_plus

import streamlit as st

SPOTIFY_TRACK_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


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
            f'style="display:inline-block; background-color:#1DB954; color:#000000; '
            f'font-weight:700; font-size:0.82rem; text-decoration:none; '
            f'padding:0.38rem 0.85rem; border-radius:999px; margin-right:0.5rem;">'
            f'🎧 Buka di Spotify</a>'
        )

    buttons_html += (
        f'<a href="{search_url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block; background-color:#282828; color:#FFFFFF; '
        f'border:1px solid #404040; font-weight:600; font-size:0.82rem; '
        f'text-decoration:none; padding:0.38rem 0.85rem; border-radius:999px;">'
        f'🔍 Cari di Spotify</a>'
    )

    st.markdown(
        f'<div style="margin-top:0.35rem; display:flex; align-items:center; flex-wrap:wrap; gap:0.4rem;">'
        f'<span style="font-size:0.78rem; color:#9E9E9E; margin-right:0.35rem;">{html.escape(pesan)}</span>'
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
    jarak: float | None = None,
) -> None:
    """
    Render kartu lagu lengkap dengan judul, artis, tag genre, similarity score bar,
    pemutar Spotify (compact + expander full player), atau tombol fallback Cari di Spotify.

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
    jarak : float | None, optional
        Jarak Euclidean fitur audio (opsional untuk info tambahan).
    """
    safe_title = html.escape(str(track_name or "Tanpa Judul"))
    safe_artists = html.escape(str(artists or "Artis Tidak Diketahui"))
    prefix = f"{rank}. " if rank is not None else ""

    score_pct = min(100.0, max(0.0, float(similarity_score)))
    raw_genres = [
        g.strip()
        for g in re.split(r"\s*\|\s*|\s*,\s*", str(genre or ""))
        if g.strip()
    ]
    if not raw_genres:
        raw_genres = ["tidak dikategorikan"]

    tags_html = "".join(
        f'<span style="display:inline-block; background-color:#262626; color:#D9D9D9; '
        f'border:1px solid #383838; border-radius:999px; padding:0.15rem 0.6rem; '
        f'margin:0.15rem 0.25rem 0.15rem 0; font-size:0.76rem;">{html.escape(g)}</span>'
        for g in raw_genres
    )

    jarak_html = (
        f'<span style="font-size:0.74rem; color:#9E9E9E; margin-left:0.5rem;">'
        f'(Jarak: {jarak:.4f})</span>'
        if jarak is not None
        else ""
    )

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.75rem;">
                <div style="flex:1 1 65%; min-width:220px;">
                    <div style="font-size:1.05rem; font-weight:700; color:#FFFFFF; margin-bottom:0.2rem;">
                        {prefix}🎵 {safe_title}
                        <span style="font-weight:500; color:#B3B3B3;"> — {safe_artists}</span>
                    </div>
                    <div style="margin-top:0.25rem;">{tags_html}</div>
                </div>
                <div style="flex:0 1 220px; min-width:180px; text-align:right;">
                    <div style="font-size:0.85rem; font-weight:700; color:#1ED760; margin-bottom:0.25rem;">
                        Kemiripan {score_pct:.1f}%{jarak_html}
                    </div>
                    <div style="width:100%; height:8px; background-color:#2A2A2A; border-radius:999px; overflow:hidden;">
                        <div style="width:{score_pct:.1f}%; height:100%; background:linear-gradient(90deg, #1DB954, #1ED760); border-radius:999px;"></div>
                    </div>
                </div>
            </div>
            """,
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

            with st.expander("🎧 Full Player & Tautan Spotify"):
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
            st.caption("Preview embed Spotify tidak tersedia untuk format Track ID lagu ini.")
            _render_spotify_fallback_buttons(
                track_name,
                artists,
                None,
                pesan="Putar langsung di Spotify:",
            )

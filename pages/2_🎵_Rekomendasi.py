"""
2__Rekomendasi.py — Halaman utama mesin rekomendasi playlist TuneCluster.
"""

from __future__ import annotations

import html
import json
import math
from collections.abc import Mapping, Sequence
from textwrap import dedent
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from utils.auth import (
    get_current_user,
    init_session_state,
    render_footer,
    render_genre_badges,
    render_sidebar,
)
from utils.database import (
    get_saved_tracks,
    remove_saved_track,
    save_history,
    save_track,
)
from utils.media_fetcher import (
    deduplicate_recommendations,
    fetch_recommendation_media,
    primary_artist,
)
from utils.playlist_export import playlist_to_csv, playlist_to_text
from utils.recommendation_player import render_recommendation_player
from utils.recommender import get_recommender, normalisasi_genre
from utils.spotify_embed import get_spotify_search_url, render_track_card

st.set_page_config(
    page_title="Rekomendasi · TuneCluster",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

AKTIVITAS_OPTIONS = {
    "Olahraga": "Olahraga",
    "Belajar": "Belajar",
    "Santai": "Santai",
    "Perjalanan": "Perjalanan",
}

MOOD_OPTIONS = {
    "Senang/Happy": "Senang/Happy",
    "Sedih/Sad": "Sedih/Sad",
    "Energik": "Energik",
    "Tenang/Calm": "Tenang/Calm",
    "Fokus": "Fokus",
}

ALGORITMA_OPTIONS = {
    "K-Means (Direkomendasikan)": "kmeans",
    "BIRCH": "birch",
}

FITUR_LABELS = {
    "danceability": "Danceability",
    "energy": "Energy",
    "valence": "Valence",
    "acousticness": "Acousticness",
    "instrumentalness": "Instrumentalness",
}

RECOMMENDATION_PAGE_CSS = """
<style>
body:has(.tc-rec-scope-marker) [data-testid="stAppViewContainer"],
body:has(.tc-rec-scope-marker) [data-testid="stMain"],
body:has(.tc-rec-scope-marker) [data-testid="stMainBlockContainer"] {
    background: #000000 !important;
}

body:has(.tc-rec-scope-marker) [data-testid="stMainBlockContainer"] {
    max-width: 1440px;
    padding-top: 1.25rem;
    padding-bottom: 110px;
}

body:has(.tc-rec-scope-marker) section[data-testid="stSidebar"] {
    background: #070707 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

body:has(.tc-rec-scope-marker) section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    border-radius: 8px;
    min-height: 44px;
    transition: background-color 120ms ease, color 120ms ease;
}

body:has(.tc-rec-scope-marker) section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
    background: rgba(255, 255, 255, 0.07);
}

body:has(.tc-rec-scope-marker) section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    font-weight: 600;
}

body:has(.tc-rec-scope-marker) section[data-testid="stSidebar"] [data-testid="stButton"] button {
    min-height: 44px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    background: #101010;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header {
    margin: 0.5rem 0 1rem;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stHorizontalBlock"] {
    align-items: center;
    gap: 0.8rem;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stColumn"] {
    min-width: 0;
}

body:has(.tc-rec-scope-marker) .tc-rec-results-title {
    margin: 0;
    color: #ffffff;
    font-size: clamp(1.35rem, 2.2vw, 1.7rem);
    font-weight: 700;
    letter-spacing: -0.035em;
    line-height: 1.2;
}

body:has(.tc-rec-scope-marker) .tc-rec-results-caption {
    margin-top: 0.3rem;
    color: #888888;
    font-size: 0.82rem;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] button {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: max-content !important;
    max-width: 100%;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 999px;
    background: #111111;
    color: #ffffff;
    font-size: 0.82rem;
    font-weight: 600;
    line-height: 1 !important;
    white-space: nowrap;
    box-sizing: border-box;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] button p,
body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] button div {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] {
    display: flex;
    justify-content: flex-end;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] button:hover {
    border-color: rgba(255, 255, 255, 0.36);
    background: #1b1b1b;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1.35rem 1.1rem;
}

body:has(.tc-rec-scope-marker) .st-key-tc-search-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"],
body:has(.tc-rec-scope-marker) .st-key-tc-similar-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

body:has(.tc-rec-scope-marker) .st-key-tc-search-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
body:has(.tc-rec-scope-marker) .st-key-tc-similar-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: auto !important;
    min-width: 0 !important;
    flex: initial !important;
}

body:has(.tc-rec-scope-marker) div[data-testid="stVerticalBlock"][class*="st-key-tc-media-card-"] {
    width: 100%;
    max-width: 240px;
    margin-inline: auto;
}

body:has(.tc-rec-scope-marker) .st-key-tc-rec-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: auto !important;
    min-width: 0 !important;
    flex: initial !important;
}

body:has(.tc-rec-scope-marker) div[data-testid="stVerticalBlock"][class*="st-key-tc-rec-card-"] {
    gap: 0 !important;
}

body:has(.tc-rec-scope-marker) .tc-rec-artwork {
    aspect-ratio: 1 / 1;
    width: 100%;
    max-width: 240px;
    margin-inline: auto;
    overflow: hidden;
    border-radius: 10px;
    background: #070707;
}

body:has(.tc-rec-scope-marker) .tc-rec-artwork img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 180ms ease-out;
}

body:has(.tc-rec-scope-marker) .tc-rec-artwork:hover img {
    transform: scale(1.025);
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stHorizontalBlock"] {
    position: relative;
    z-index: 2;
    height: 44px;
    margin: -54px 0 32px;
    padding: 0 10px;
    gap: 8px;
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stColumn"] {
    min-width: 0;
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stButton"] button {
    display: grid;
    place-items: center;
    width: 44px !important;
    min-width: 44px;
    height: 44px;
    min-height: 44px;
    margin: 0 auto;
    padding: 0;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.76);
    color: #ffffff;
    backdrop-filter: blur(12px);
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stButton"] button [data-testid="stMarkdownContainer"] p {
    margin: 0;
    font-size: 0;
    line-height: 0;
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stButton"] button [data-testid="stIconMaterial"] {
    font-size: 20px;
}

body:has(.tc-rec-scope-marker) div[class*="st-key-tc-rec-card-"] [data-testid="stButton"] button:hover {
    border-color: rgba(255, 255, 255, 0.42);
    background: #1b1b1b;
}

body:has(.tc-rec-scope-marker) .tc-rec-card-details {
    min-width: 0;
    padding: 0 1px;
}

body:has(.tc-rec-scope-marker) .tc-rec-track-title {
    overflow: hidden;
    color: #f5f5f5;
    font-size: 0.96rem;
    font-weight: 650;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
}

body:has(.tc-rec-scope-marker) .tc-rec-track-meta {
    overflow: hidden;
    margin-top: 0.18rem;
    color: #858585;
    font-size: 0.78rem;
    line-height: 1.35;
    text-overflow: ellipsis;
    white-space: nowrap;
}

body:has(.tc-rec-scope-marker) .tc-rec-score-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-top: 0.62rem;
}

body:has(.tc-rec-scope-marker) .tc-rec-score-track {
    flex: 1;
    height: 2px;
    overflow: hidden;
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.14);
}

body:has(.tc-rec-scope-marker) .tc-rec-score-fill {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: #1db954;
}

body:has(.tc-rec-scope-marker) .tc-rec-score-label {
    flex: none;
    color: #858585;
    font-size: 0.68rem;
    line-height: 1;
    white-space: nowrap;
}

@media (max-width: 1050px) {
    body:has(.tc-rec-scope-marker) .st-key-tc-rec-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.2rem 0.9rem;
    }

}

@media (max-width: 760px) {
    body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 0.65rem;
    }

    body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {
        grid-column: 1 / -1;
    }

    body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: auto !important;
        min-width: 0 !important;
        flex: initial !important;
    }

    body:has(.tc-rec-scope-marker) .st-key-tc-rec-grid > div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1.1rem 0.8rem;
    }

    body:has(.tc-rec-scope-marker) .st-key-tc-rec-results-header [data-testid="stDownloadButton"] button {
        max-width: 100%;
    }
}

@media (prefers-reduced-motion: reduce) {
    body:has(.tc-rec-scope-marker) .tc-rec-artwork img {
        transition: none;
    }
}
</style>
"""

def _render_genre_badges(genres: list[str]) -> None:
    """Tampilkan daftar genre user dalam bentuk badge monokrom."""
    render_genre_badges(
        genres,
        empty_message="Belum ada genre favorit. Tambahkan genre melalui halaman Profil.",
    )


def _buat_radar_chart(
    profil_cluster_row: dict[str, float],
    target_vektor: dict[str, float],
    nama_cluster: str,
) -> go.Figure:
    """Buat radar chart Plotly yang membandingkan profil rata-rata cluster vs target audio."""
    fitur_keys = list(FITUR_LABELS.keys())
    kategori = [FITUR_LABELS[k] for k in fitur_keys]
    nilai_cluster = [float(profil_cluster_row.get(k, 0.0)) for k in fitur_keys]
    nilai_target = [float(target_vektor.get(k, 0.0)) for k in fitur_keys]

    # Tutup poligon radar chart
    kategori_closed = kategori + [kategori[0]]
    cluster_closed = nilai_cluster + [nilai_cluster[0]]
    target_closed = nilai_target + [nilai_target[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=cluster_closed,
            theta=kategori_closed,
            fill="toself",
            name=f"Rata-rata {nama_cluster}",
            line=dict(color="#A7A7A7", width=2),
            fillcolor="rgba(167, 167, 167, 0.16)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=target_closed,
            theta=kategori_closed,
            fill="toself",
            name="Target Aktivitas & Mood",
            line=dict(color="#1DB954", width=2.5),
            fillcolor="rgba(29, 185, 84, 0.28)",
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor="#181818",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(color="#A0A0A0", size=10),
                gridcolor="#2E2E2E",
                linecolor="#2E2E2E",
            ),
            angularaxis=dict(
                tickfont=dict(color="#FFFFFF", size=11),
                gridcolor="#2E2E2E",
                linecolor="#2E2E2E",
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="center",
            x=0.5,
            font=dict(color="#FFFFFF", size=11),
        ),
        margin=dict(l=45, r=45, t=25, b=55),
        height=320,
    )
    return fig


def _render_copy_playlist_button(playlist_text: str) -> None:
    """Render a clipboard button with a visible success or failure state."""
    serialized_text = (
        json.dumps(playlist_text, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    component_html = f"""
        <button id="copy-playlist" type="button">Salin playlist</button>
        <script>
            const playlistText = {serialized_text};
            const button = document.getElementById("copy-playlist");
            button.addEventListener("click", async () => {{
                let copied = false;
                try {{
                    if (navigator.clipboard && window.isSecureContext) {{
                        await navigator.clipboard.writeText(playlistText);
                        copied = true;
                    }}
                }} catch (error) {{
                    copied = false;
                }}
                if (!copied) {{
                    const textarea = document.createElement("textarea");
                    textarea.value = playlistText;
                    textarea.style.position = "fixed";
                    textarea.style.opacity = "0";
                    document.body.appendChild(textarea);
                    textarea.select();
                    try {{
                        copied = document.execCommand("copy");
                    }} catch (error) {{
                        copied = false;
                    }}
                    textarea.remove();
                }}
                button.textContent = copied ? "Playlist tersalin" : "Gagal menyalin";
                window.setTimeout(() => {{
                    button.textContent = "Salin playlist";
                }}, 2200);
            }});
        </script>
        <style>
            body {{ margin: 0; }}
            button {{
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: max-content;
                max-width: 100%;
                height: 40px !important;
                min-height: 40px !important;
                padding: 0 20px !important;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 999px;
                background: #111111;
                color: #FFFFFF;
                font-weight: 600;
                font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                font-size: 0.82rem;
                line-height: 1 !important;
                cursor: pointer;
                white-space: nowrap;
                box-sizing: border-box;
            }}
            button:hover {{
                background: #1B1B1B;
                border-color: rgba(255, 255, 255, 0.36);
            }}
        </style>
    """
    st.components.v1.html(component_html, height=44, scrolling=False)


def _render_result_genre_filter() -> list[str]:
    """Render a compact genre filter above the current recommendation list."""
    last_df = st.session_state.get("last_rekomendasi")
    if last_df is None or last_df.empty:
        return []

    genre_hasil = sorted(
        {
            normalisasi_genre(genre)
            for value in last_df["genre_gabungan"].fillna("")
            for genre in str(value).split(" | ")
            if normalisasi_genre(genre)
        }
    )
    if st.session_state.pop("_reset_filter_genre", False):
        st.session_state["filter_genre_hasil"] = []
    return st.multiselect(
        "Filter genre",
        options=genre_hasil,
        placeholder="Semua genre",
        key="filter_genre_hasil",
    )


def _register_player_tracks(
    rows: Sequence[Mapping[str, Any]],
    media_rows: Sequence[Mapping[str, object]],
    card_keys: list[str],
    player_tracks: dict[str, dict[str, Any]],
) -> None:
    """Merge each rendered card into the single browser-side player playlist."""
    for row, media, card_key in zip(rows, media_rows, card_keys):
        track_id = str(row.get("track_id") or row.get("spotify_id") or "")
        if not track_id:
            continue
        track_name = str(row.get("track_name") or "Tanpa Judul")
        artists = primary_artist(str(row.get("artists") or ""))
        track = player_tracks.get(track_id)
        if track is None:
            track = {
                "track_id": track_id,
                "track_name": track_name,
                "artists": artists,
                "cover_url": str(media["cover_url"]),
                "preview_url": media["preview_url"],
                "spotify_url": get_spotify_search_url(track_name, artists),
                "card_keys": [],
            }
            player_tracks[track_id] = track
        if card_key not in track["card_keys"]:
            track["card_keys"].append(card_key)


# 1. Sidebar utama + cek login
render_sidebar()
st.markdown(
    '<div class="tc-rec-scope-marker" aria-hidden="true"></div>',
    unsafe_allow_html=True,
)
st.markdown(RECOMMENDATION_PAGE_CSS, unsafe_allow_html=True)
user = get_current_user(refresh_from_db=True)

if user is None:
    st.title("Rekomendasi playlist")
    st.warning("Anda harus login terlebih dahulu untuk menggunakan fitur rekomendasi personal.")
    try:
        st.page_link("app.py", label="Kembali ke Halaman Utama untuk Login / Daftar")
    except Exception:
        st.info("Silakan kembali ke halaman utama **app** di sidebar untuk Login atau Daftar.")
    if st.button("Pergi ke halaman utama", type="primary"):
        st.switch_page("app.py")
    st.stop()

recommender = get_recommender()
has_popularity = (
    "popularity" in recommender.katalog.columns
    and recommender.katalog["popularity"].notna().any()
)

# Refresh referensi user jika diubah dari sidebar
user = get_current_user() or user
nama_user = html.escape(str(user.get("nama_lengkap") or user.get("username", "Teman Musik")))
user_genres = list(user.get("genres", []))

# 2. Header Personal
st.title(f"Rekomendasi untuk {nama_user}")
st.markdown("##### Genre favorit")
_render_genre_badges(user_genres)
st.divider()
player_tracks_by_id: dict[str, dict[str, Any]] = {}

with st.expander(
    "Cari lagu di katalog",
    expanded=st.session_state.get("hasil_cari_lagu") is not None,
):
    with st.form("form_cari_lagu"):
        col_search, col_search_button = st.columns([4, 1], vertical_alignment="bottom")
        with col_search:
            query_lagu = st.text_input(
                "Nama lagu atau artis",
                placeholder="Contoh: Bad Habits atau Ed Sheeran",
                key="query_cari_lagu",
            )
        with col_search_button:
            cari_lagu_submit = st.form_submit_button(
                "Cari Lagu",
                type="primary",
                width="stretch",
            )

    if cari_lagu_submit:
        query_bersih = query_lagu.strip()
        st.session_state["hasil_cari_lagu"] = (
            recommender.cari_lagu(query_bersih, limit=10)
            if query_bersih
            else recommender.cari_lagu("")
        )
        st.session_state["query_hasil_cari_lagu"] = query_bersih
        st.session_state.pop("lagu_pencarian_serupa", None)

    hasil_cari_lagu = st.session_state.get("hasil_cari_lagu")
    if hasil_cari_lagu is not None:
        query_hasil = st.session_state.get("query_hasil_cari_lagu", "")
        st.markdown(f"#### Hasil pencarian: {html.escape(query_hasil) or '—'}")
        if not query_hasil:
            st.info("Masukkan nama lagu atau artis untuk memulai pencarian.")
        elif hasil_cari_lagu.empty:
            st.info("Tidak ada lagu yang cocok. Coba kata kunci lain.")
        else:
            search_rows = hasil_cari_lagu.to_dict(orient="records")
            search_media = fetch_recommendation_media(search_rows)
            search_card_keys = [
                f"search_{idx}_{row.get('track_id', '')}"
                for idx, row in enumerate(search_rows)
            ]
            _register_player_tracks(
                search_rows,
                search_media,
                search_card_keys,
                player_tracks_by_id,
            )
            with st.container(key="tc-search-grid"):
                search_columns = st.columns(2, gap="medium")
                for idx, (row, media, card_key) in enumerate(
                    zip(search_rows, search_media, search_card_keys)
                ):
                    track_id = str(row["track_id"])
                    with search_columns[idx % len(search_columns)]:
                        st.caption(
                            f"Cluster K-Means {int(row['cluster_kmeans'])} · {row['nama_cluster']} "
                            f"│ Cluster BIRCH {int(row['cluster_birch'])} · {row['nama_cluster_birch']}"
                        )
                        render_track_card(
                            track_name=str(row["track_name"]),
                            artists=str(row["artists"]),
                            genre=str(row["genre_gabungan"]),
                            similarity_score=100.0,
                            track_id=track_id,
                            rank=idx + 1,
                            show_player=True,
                            show_full_player=False,
                            cover_url=media["cover_url"],
                            preview_url=media["preview_url"],
                            shared_player=True,
                            player_key=card_key,
                        )
                        if st.button(
                            "Cari yang mirip",
                            key=f"cari_mirip_{track_id}",
                            width="stretch",
                        ):
                            st.session_state["lagu_pencarian_serupa"] = track_id
                            st.rerun()

    lagu_pencarian_serupa = st.session_state.get("lagu_pencarian_serupa")
    if lagu_pencarian_serupa:
        lagu_sumber = recommender.katalog.loc[
            recommender.katalog["track_id"].astype(str) == lagu_pencarian_serupa
        ].iloc[0]
        st.markdown(
            "#### Lagu yang mirip dengan "
            f"**{html.escape(str(lagu_sumber['track_name']))}** — "
            f"{html.escape(str(lagu_sumber['artists']))}"
        )
        hasil_serupa = recommender.cari_lagu_serupa(lagu_pencarian_serupa, n=10)
        if hasil_serupa.empty:
            st.info("Tidak ada lagu lain di katalog untuk dibandingkan.")
        else:
            max_jarak = max(float(hasil_serupa["jarak"].max()) * 1.1, 1e-12)
            similar_rows = hasil_serupa.to_dict(orient="records")
            similar_media = fetch_recommendation_media(similar_rows)
            similar_card_keys = [
                f"similar_{idx}_{row.get('track_id', '')}"
                for idx, row in enumerate(similar_rows)
            ]
            _register_player_tracks(
                similar_rows,
                similar_media,
                similar_card_keys,
                player_tracks_by_id,
            )
            with st.container(key="tc-similar-grid"):
                similar_columns = st.columns(2, gap="medium")
                for idx, (row, media, card_key) in enumerate(
                    zip(similar_rows, similar_media, similar_card_keys)
                ):
                    with similar_columns[idx % len(similar_columns)]:
                        st.caption(
                            f"Cluster K-Means {int(row['cluster_kmeans'])} · {row['nama_cluster']} "
                            f"│ Cluster BIRCH {int(row['cluster_birch'])} · {row['nama_cluster_birch']}"
                        )
                        render_track_card(
                            track_name=str(row["track_name"]),
                            artists=str(row["artists"]),
                            genre=str(row["genre_gabungan"]),
                            similarity_score=max(
                                0.0,
                                (1.0 - float(row["jarak"]) / max_jarak) * 100.0,
                            ),
                            track_id=str(row["track_id"]),
                            rank=idx + 1,
                            show_player=True,
                            show_full_player=False,
                            jarak=float(row["jarak"]),
                            cover_url=media["cover_url"],
                            preview_url=media["preview_url"],
                            shared_player=True,
                            player_key=card_key,
                        )


# 3. Filter rekomendasi
with st.form("form_rekomendasi_playlist"):
    with st.container(border=True):
        st.subheader("Buat playlist")
        st.caption("Genre pilihan Anda")
        _render_genre_badges(user_genres)

        col_activity, col_mood = st.columns(2)
        with col_activity:
            aktivitas_label = st.radio(
                "Aktivitas",
                options=list(AKTIVITAS_OPTIONS.keys()),
                horizontal=True,
                key="input_aktivitas",
            )
        with col_mood:
            mood_label = st.radio(
                "Suasana",
                options=list(MOOD_OPTIONS.keys()),
                horizontal=True,
                key="input_mood",
            )

        col_count, col_popular = st.columns([1, 1.4], vertical_alignment="center")
        with col_count:
            jumlah_lagu = st.slider(
                "Jumlah lagu",
                min_value=5,
                max_value=20,
                value=10,
                step=1,
                key="input_jumlah_lagu",
            )
        with col_popular:
            mode_populer = st.toggle(
                "Utamakan lagu populer / familiar",
                value=False,
                key="input_mode_populer",
                disabled=not has_popularity,
                help="Mengurutkan kandidat berdasarkan popularitas Spotify yang tersedia.",
            )
            mode_rekomendasi = (
                "Populer / Familiar" if mode_populer else "Kecocokan Audio"
            )

        with st.expander("Pengaturan lanjutan"):
            algoritma_label = st.radio(
                "Algoritma clustering",
                options=list(ALGORITMA_OPTIONS.keys()),
                index=0,
                horizontal=True,
                key="input_algoritma",
                help="K-Means direkomendasikan karena lebih seimbang dan stabil (ARI 0.9853 vs BIRCH 0.2381).",
            )

        submit_btn = st.form_submit_button(
            "Dapatkan playlist",
            type="primary",
            width="stretch",
        )

if submit_btn:
    aktivitas_val = AKTIVITAS_OPTIONS[aktivitas_label]
    mood_val = MOOD_OPTIONS[mood_label]
    algo_val = ALGORITMA_OPTIONS[algoritma_label]

    with st.spinner("Sedang menganalisis karakteristik audio dan menyusun playlist terbaik..."):
        df_rekom = recommender.rekomendasi(
            genre_user=user_genres,
            aktivitas=aktivitas_val,
            mood=mood_val,
            n=int(jumlah_lagu),
            algoritma=algo_val,
            prioritaskan_populer=(mode_rekomendasi == "Populer / Familiar"),
        )
        df_rekom = deduplicate_recommendations(df_rekom)

        # Hitung skor kemiripan: (1 - normalized distance) dalam persen
        max_dist_ref = max(4.0, float(df_rekom["jarak"].max()) * 1.1) if not df_rekom.empty else 4.0
        df_rekom = df_rekom.copy()
        df_rekom["skor_kemiripan"] = (
            (1.0 - (df_rekom["jarak"] / max_dist_ref)).clip(0.0, 1.0) * 100.0
        )

        meta: dict[str, Any] = {
            "algoritma": algo_val,
            "algoritma_label": algoritma_label,
            "aktivitas": aktivitas_val,
            "mood": mood_val,
            "target_cluster": df_rekom.attrs.get("target_cluster", 0),
            "nama_cluster": df_rekom.attrs.get("nama_cluster", "-"),
            "target_vektor": df_rekom.attrs.get("target_vektor", {}),
            "genre_cocok": df_rekom.attrs.get("genre_cocok", []),
            "genre_tidak_tersedia": df_rekom.attrs.get("genre_tidak_tersedia", []),
            "fallback_audio": df_rekom.attrs.get("fallback_audio", False),
            "jumlah_kandidat": df_rekom.attrs.get("jumlah_kandidat", len(df_rekom)),
            "prioritaskan_populer": df_rekom.attrs.get("prioritaskan_populer", False),
        }

        st.session_state["last_rekomendasi"] = df_rekom
        st.session_state["last_rekomendasi_meta"] = meta
        st.session_state["_reset_filter_genre"] = True

        # Simpan otomatis ke database user_history
        if not df_rekom.empty:
            save_history(
                user_id=user["user_id"],
                aktivitas=aktivitas_val,
                mood=mood_val,
                rekomendasi_track_ids=df_rekom["track_id"].tolist(),
            )

    st.rerun()

# 4. Tampilkan Hasil Rekomendasi
filter_genres_hasil = _render_result_genre_filter()
df_hasil = st.session_state.get("last_rekomendasi")
meta_hasil = st.session_state.get("last_rekomendasi_meta")

if df_hasil is not None and meta_hasil is not None:
    st.divider()
    st.subheader("Hasil rekomendasi")

    algo_used = meta_hasil["algoritma"]
    target_cluster = int(meta_hasil["target_cluster"])
    nama_cluster = str(meta_hasil["nama_cluster"])
    profil_df = recommender.get_profil_cluster(algo_used)
    profil_cluster_row = (
        profil_df.loc[target_cluster].to_dict()
        if target_cluster in profil_df.index
        else profil_df.iloc[0].to_dict()
    )

    with st.expander("Rincian kecocokan audio", expanded=False):
        # 4a. Info Cluster & Radar Chart
        col_info, col_radar = st.columns([1.15, 1], vertical_alignment="center")
        with col_info:
            genre_cocok_txt = (
                ", ".join(meta_hasil["genre_cocok"]) if meta_hasil["genre_cocok"] else "Tidak ada (menggunakan fallback audio)"
            )
            fallback_notice = (
                "<br><span class='tc-muted'>Preferensi genre belum tersedia di cluster target, "
                "sistem menggunakan seluruh lagu di cluster ini berdasarkan kemiripan audio.</span>"
                if meta_hasil["fallback_audio"]
                else ""
            )
            st.markdown(
                dedent(f"""
                <div class="cluster-box">
                    <div style="font-size:0.82rem; color:#B3B3B3;">Cluster Target ({algo_used.upper()})</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#1DB954; margin-bottom:0.4rem;">
                        Cluster {target_cluster} · {html.escape(nama_cluster)}
                    </div>
                    <div style="font-size:0.9rem; color:#E0E0E0; line-height:1.55;">
                        <b>Aktivitas & Mood:</b> {html.escape(meta_hasil['aktivitas'])} · {html.escape(meta_hasil['mood'])}<br>
                        <b>Kandidat di Cluster:</b> {meta_hasil['jumlah_kandidat']:,} lagu<br>
                        <b>Genre Cocok:</b> {html.escape(genre_cocok_txt)}
                        {fallback_notice}
                    </div>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )

        with col_radar:
            fig_radar = _buat_radar_chart(
                profil_cluster_row=profil_cluster_row,
                target_vektor=meta_hasil["target_vektor"],
                nama_cluster=nama_cluster,
            )
            st.plotly_chart(fig_radar, width="stretch")

        metric_columns = st.columns(5, gap="small")
        for col_m, fitur_key in zip(metric_columns, FITUR_LABELS):
            val_c = float(profil_cluster_row.get(fitur_key, 0.0))
            val_t = float(meta_hasil["target_vektor"].get(fitur_key, 0.0))
            col_m.metric(
                label=FITUR_LABELS[fitur_key],
                value=f"{val_t:.2f}",
                delta=f"{val_t - val_c:+.2f} vs cluster",
            )

    # Terapkan filter genre bila aktif
    df_tampil = df_hasil.copy()
    if filter_genres_hasil:
        filter_set = set(filter_genres_hasil)
        mask_f = df_tampil["genre_gabungan"].fillna("").apply(
            lambda s: bool(
                {normalisasi_genre(g) for g in str(s).split(" | ") if normalisasi_genre(g)} & filter_set
            )
        )
        df_tampil = df_tampil[mask_f].reset_index(drop=True)

    media_by_track_id = {}
    if not df_tampil.empty:
        track_ids = [str(track_id) for track_id in df_tampil["track_id"]]
        fetched_media = fetch_recommendation_media(df_tampil.to_dict(orient="records"))
        media_by_track_id = dict(zip(track_ids, fetched_media))

    if df_tampil.empty:
        with st.container(key="tc-rec-results-header"):
            st.markdown(
                '<h2 class="tc-rec-results-title">Hasil rekomendasi</h2>',
                unsafe_allow_html=True,
            )
        st.info("Tidak ada lagu yang cocok dengan filter di atas. Kosongkan filter untuk melihat semua lagu.")
    else:
        saved_track_ids = {
            str(saved["track_id"])
            for saved in get_saved_tracks(int(user["user_id"]))
        }
        df_export = df_tampil.copy()
        df_export["spotify_search_url"] = [
            get_spotify_search_url(str(row["track_name"]), str(row["artists"]))
            for _, row in df_export.iterrows()
        ]
        export_rows = df_export.to_dict(orient="records")
        export_track_ids = [str(row["track_id"]) for row in export_rows]
        _register_player_tracks(
            export_rows,
            [media_by_track_id[track_id] for track_id in export_track_ids],
            export_track_ids,
            player_tracks_by_id,
        )

        with st.container(key="tc-rec-results-header"):
            col_title, col_copy, col_csv = st.columns(
                [5, 1.4, 1.4],
                vertical_alignment="center",
            )
            with col_title:
                st.markdown(
                    f"""
                    <div>
                        <h2 class="tc-rec-results-title">Hasil rekomendasi</h2>
                        <div class="tc-rec-results-caption">{len(df_tampil)} lagu untuk playlist Anda</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_copy:
                _render_copy_playlist_button(playlist_to_text(df_export))
            with col_csv:
                st.download_button(
                    "Unduh CSV",
                    data=playlist_to_csv(df_export),
                    file_name="tunecluster_playlist.csv",
                    mime="text/csv; charset=utf-8",
                    key="btn_download_playlist_csv",
                    width="stretch",
                )

        col_shuffle, _ = st.columns([1, 3])
        with col_shuffle:
            if st.button(
                "Acak playlist",
                key="btn_shuffle_playlist",
                width="stretch",
                disabled=df_hasil.empty,
            ):
                st.session_state["last_rekomendasi"] = df_hasil.sample(frac=1).reset_index(drop=True)
                st.rerun()

        with st.container(key="tc-rec-grid"):
            track_columns = st.columns(4, gap="medium")
            for position, (_, row) in enumerate(df_tampil.iterrows()):
                track_id = str(row["track_id"])
                track_name = str(row["track_name"])
                artists = str(row["artists"])
                genre = str(row["genre_gabungan"])
                primary = primary_artist(artists)
                score = min(100.0, max(0.0, float(row["skor_kemiripan"])))
                distance = float(row["jarak"])
                cover_url = media_by_track_id[track_id]["cover_url"]
                title_attr = html.escape(track_name, quote=True)
                safe_title = html.escape(track_name)
                safe_artist_genre = html.escape(f"{primary} · {genre}", quote=True)
                safe_cover_url = html.escape(cover_url, quote=True)
                popularity_html = ""
                if meta_hasil.get("prioritaskan_populer", False):
                    popularity = float(row["popularity"])
                    if math.isfinite(popularity):
                        popularity_html = (
                            '<div class="tc-rec-track-meta">'
                            f"Popularitas Spotify {popularity:.0f}/100</div>"
                        )

                with track_columns[position % len(track_columns)]:
                    with st.container(key=f"tc-rec-card-{track_id}"):
                        st.markdown(
                            f"""
                            <div class="tc-rec-artwork">
                                <img src="{safe_cover_url}" alt="Sampul {safe_title}"
                                     loading="lazy" decoding="async">
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        play_col, save_col = st.columns([1, 1], gap="small")
                        with play_col:
                            st.button(
                                "Putar",
                                key=f"play_recommended_track_{track_id}",
                                icon=":material/play_arrow:",
                                width="stretch",
                                help=f"Putar {track_name}",
                            )
                        with save_col:
                            if track_id in saved_track_ids:
                                if st.button(
                                    "Tersimpan",
                                    key=f"remove_saved_track_{track_id}",
                                    icon=":material/bookmark_added:",
                                    width="stretch",
                                    help="Hapus dari lagu tersimpan",
                                ):
                                    if remove_saved_track(int(user["user_id"]), track_id):
                                        st.toast("Lagu dihapus dari daftar tersimpan.")
                                        st.rerun()
                                    else:
                                        st.error("Lagu tersimpan tidak dapat dihapus.")
                            elif st.button(
                                "Simpan",
                                key=f"save_track_{track_id}",
                                icon=":material/bookmark_add:",
                                width="stretch",
                                help="Simpan ke Profil Anda",
                            ):
                                if save_track(
                                    user_id=int(user["user_id"]),
                                    track_id=track_id,
                                    aktivitas=str(meta_hasil["aktivitas"]),
                                    mood=str(meta_hasil["mood"]),
                                ):
                                    st.toast("Lagu tersimpan di Profil Anda.")
                                    st.rerun()
                                else:
                                    st.info("Lagu ini sudah tersimpan.")

                        st.markdown(
                            f"""
                            <div class="tc-rec-card-details">
                                <div class="tc-rec-track-title" title="{title_attr}">{safe_title}</div>
                                <div class="tc-rec-track-meta" title="{safe_artist_genre}">
                                    {safe_artist_genre}
                                </div>
                                <div class="tc-rec-score-row">
                                    <div class="tc-rec-score-track" role="progressbar"
                                         aria-label="Kemiripan" aria-valuemin="0"
                                         aria-valuemax="100" aria-valuenow="{score:.1f}">
                                        <span class="tc-rec-score-fill" style="width:{score:.1f}%"></span>
                                    </div>
                                    <span class="tc-rec-score-label">{score:.0f}% · {distance:.2f}</span>
                                </div>
                                {popularity_html}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

render_recommendation_player(list(player_tracks_by_id.values()))
render_footer()

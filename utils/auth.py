"""
auth.py — Fungsi autentikasi, sidebar, dan styling global Dark Spotify untuk TuneCluster.
"""

from __future__ import annotations

import hashlib
import html
from typing import Any

import streamlit as st

from utils.database import get_user_profile, init_db

APP_VERSION = "v1.0.0"

# Warna teks pastel + tint background gelap untuk tag/badge genre
PASTEL_GENRE_PALETTE: list[tuple[str, str, str]] = [
    ("#A7F3D0", "rgba(29, 185, 84, 0.16)", "rgba(167, 243, 208, 0.45)"),
    ("#BFDBFE", "rgba(59, 130, 246, 0.16)", "rgba(191, 219, 254, 0.45)"),
    ("#DDD6FE", "rgba(139, 92, 246, 0.16)", "rgba(221, 214, 254, 0.45)"),
    ("#FBCFE8", "rgba(236, 72, 153, 0.16)", "rgba(251, 207, 232, 0.45)"),
    ("#FDE68A", "rgba(245, 158, 11, 0.16)", "rgba(253, 230, 138, 0.45)"),
    ("#FED7AA", "rgba(249, 115, 22, 0.16)", "rgba(254, 215, 170, 0.45)"),
]

GLOBAL_SPOTIFY_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

@keyframes tuneFadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 1. Background Gradien Gelap & 5. Typography */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #121212 0%, #191414 100%) !important;
    color: #F5F5F5 !important;
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    color: #FFFFFF !important;
}

p, li, span, label {
    font-weight: 400;
}

/* 9. Animasi fade-in halus */
[data-testid="stMainBlockContainer"] {
    animation: tuneFadeIn 0.35s ease-out;
}

/* 6. Sidebar lebih gelap */
section[data-testid="stSidebar"] {
    background-color: #0D0D0D !important;
    border-right: 1px solid #222222 !important;
}

/* 2. Card / Container & Expander */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] {
    background-color: #1E1E1E !important;
    border: 1px solid #2B2B2B !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
    animation: tuneFadeIn 0.3s ease-out;
}

[data-testid="stMetric"] {
    background-color: #1E1E1E;
    border: 1px solid #2A2A2A;
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.25);
}

/* 3. Tombol Hijau Spotify */
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
.stFormSubmitButton button[kind="primary"] {
    background-color: #1DB954 !important;
    border-color: #1DB954 !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border-radius: 999px !important;
    transition: background-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
}

button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
.stFormSubmitButton button[kind="primary"]:hover {
    background-color: #1ED760 !important;
    border-color: #1ED760 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(29, 185, 84, 0.35) !important;
}

button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
    background-color: #262626 !important;
    border: 1px solid #3A3A3A !important;
    color: #FFFFFF !important;
    border-radius: 10px !important;
    transition: border-color 0.2s ease, background-color 0.2s ease !important;
}

button[kind="secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover {
    border-color: #1DB954 !important;
    background-color: #2E2E2E !important;
}

/* 4. Genre Tags / Badges (Pill-shaped pastel di background gelap) */
.genre-badge {
    display: inline-block;
    padding: 0.34rem 0.85rem;
    margin: 0.22rem 0.35rem 0.22rem 0;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.15px;
    transition: transform 0.15s ease;
}

.genre-badge:hover {
    transform: translateY(-1px);
}

/* 7. Input fields */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
textarea {
    background-color: #2A2A2A !important;
    border: 1px solid #333333 !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="base-input"]:focus-within,
textarea:focus {
    border-color: #1DB954 !important;
    box-shadow: 0 0 0 1px #1DB954 !important;
}

/* 8. Slim Dark Scrollbar */
::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}
::-webkit-scrollbar-track {
    background: #121212;
}
::-webkit-scrollbar-thumb {
    background: #3E3E3E;
    border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover {
    background: #555555;
}

/* 10. Footer */
.tunecluster-footer {
    margin-top: 2.5rem;
    padding: 1.1rem 0 0.6rem 0;
    border-top: 1px solid #2A2A2A;
    text-align: center;
    font-size: 0.85rem;
    color: #9E9E9E;
}

/* Responsive mobile adjustments */
@media (max-width: 768px) {
    .hero-card {
        padding: 1.15rem 1.2rem !important;
    }
    .hero-title {
        font-size: 1.85rem !important;
    }
    .genre-badge {
        font-size: 0.78rem !important;
        padding: 0.26rem 0.68rem !important;
    }
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
}
</style>
"""


def inject_global_styles() -> None:
    """Suntikkan stylesheet global tema Dark Spotify ke halaman Streamlit aktif."""
    st.markdown(GLOBAL_SPOTIFY_CSS, unsafe_allow_html=True)


def render_genre_badges(genres: list[str], empty_message: str | None = None) -> None:
    """Tampilkan daftar genre sebagai pill-shaped pastel badges di atas background gelap."""
    if not genres:
        if empty_message:
            st.info(empty_message)
        return

    badge_parts: list[str] = []
    for idx, genre in enumerate(genres):
        text_color, bg_color, border_color = PASTEL_GENRE_PALETTE[idx % len(PASTEL_GENRE_PALETTE)]
        safe_genre = html.escape(str(genre))
        badge_parts.append(
            f'<span class="genre-badge" style="background-color:{bg_color}; '
            f'color:{text_color}; border:1px solid {border_color};">🎧 {safe_genre}</span>'
        )
    st.markdown("".join(badge_parts), unsafe_allow_html=True)


def render_footer(author_name: str = "Tim TuneCluster") -> None:
    """Tampilkan footer standar TuneCluster di bagian bawah halaman."""
    safe_author = html.escape(author_name)
    st.markdown(
        f'<div class="tunecluster-footer">Dibuat dengan 💚 oleh <b>{safe_author}</b> — TuneCluster © 2026</div>',
        unsafe_allow_html=True,
    )


def hash_password(password: str) -> str:
    """Hash password menggunakan SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verifikasi password terhadap hash yang tersimpan."""
    return hash_password(password) == password_hash


def init_session_state() -> None:
    """Inisialisasi state autentikasi dan database aplikasi."""
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True
    if "user" not in st.session_state:
        st.session_state["user"] = None


def get_current_user(refresh_from_db: bool = False) -> dict[str, Any] | None:
    """Ambil dict pengguna yang sedang login dari `st.session_state`."""
    init_session_state()
    user = st.session_state.get("user")
    if user is None:
        return None
    if refresh_from_db and "user_id" in user:
        fresh = get_user_profile(user["user_id"])
        if fresh is not None:
            st.session_state["user"] = fresh
            return fresh
    return user


def logout_user() -> None:
    """Hapus seluruh status sesi login pengguna."""
    keys_to_clear = [
        "user",
        "last_rekomendasi",
        "last_rekomendasi_meta",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state["user"] = None


def render_sidebar() -> None:
    """Terapkan styling global dan tampilkan komponen sidebar TuneCluster di semua halaman."""
    init_session_state()
    inject_global_styles()
    user = st.session_state.get("user")

    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.4rem 0 0.8rem 0;">
                <span style="font-size: 1.35rem; font-weight: 800; color: #1DB954;">
                    🎵 TuneCluster
                </span><br>
                <span style="font-size: 0.8rem; color: #B3B3B3;">
                    Spotify Clustering Recommender
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        if user:
            nama = html.escape(str(user.get("nama_lengkap") or user.get("username", "Pengguna")))
            username = html.escape(str(user.get("username", "-")))
            jumlah_genre = len(user.get("genres", []))
            st.markdown(
                f"""
                <div style="
                    background-color: #181818;
                    border: 1px solid #2A2A2A;
                    border-left: 4px solid #1DB954;
                    border-radius: 12px;
                    padding: 0.75rem 0.9rem;
                    margin-bottom: 0.75rem;
                ">
                    <div style="font-size: 0.75rem; color: #B3B3B3;">Masuk sebagai</div>
                    <div style="font-size: 1rem; font-weight: 700; color: #FFFFFF;">{nama}</div>
                    <div style="font-size: 0.8rem; color: #1DB954;">@{username} · {jumlah_genre} genre</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚪 Logout", key="sidebar_logout_btn", width="stretch"):
                logout_user()
                st.rerun()
        else:
            st.info("Anda belum login. Masuk atau daftar melalui halaman utama.")

        st.divider()
        st.caption(f"**TuneCluster {APP_VERSION}**")
        st.caption("K-Means & BIRCH Clustering · 89.741 Lagu Spotify")
        st.caption("© 2026 Tim TuneCluster · Streamlit")

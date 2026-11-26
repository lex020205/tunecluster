"""Fungsi autentikasi dan navigasi TuneCluster."""

from __future__ import annotations

import hashlib
import html
from textwrap import dedent
from typing import Any

import streamlit as st

from utils.database import get_user_profile, init_db
from utils.styles import inject_global_styles

def render_genre_badges(genres: list[str], empty_message: str | None = None) -> None:
    """Tampilkan daftar genre sebagai badge monokrom."""
    if not genres:
        if empty_message:
            st.info(empty_message)
        return

    badge_parts: list[str] = []
    for genre in genres:
        safe_genre = html.escape(str(genre))
        badge_parts.append(f'<span class="genre-badge">{safe_genre}</span>')
    st.markdown("".join(badge_parts), unsafe_allow_html=True)


def render_footer(author_name: str = "Tim TuneCluster") -> None:
    """Tampilkan footer standar TuneCluster di bagian bawah halaman."""
    safe_author = html.escape(author_name)
    st.markdown(
        f'<div class="tunecluster-footer">Dibuat oleh <b>{safe_author}</b> — TuneCluster © 2026</div>',
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
    """Terapkan styling global dan tampilkan navigasi TuneCluster."""
    init_session_state()
    inject_global_styles()
    user = st.session_state.get("user")

    with st.sidebar:
        st.markdown(
            '<div class="tc-brand">Tune<span class="tc-brand-accent">Cluster</span></div>',
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="Beranda")
        st.page_link("pages/2_🎵_Rekomendasi.py", label="Rekomendasi")
        st.page_link("pages/4_⚙️_Profil.py", label="Profil")
        st.page_link("pages/3_📊_Analisis.py", label="Analisis")

        st.divider()
        if user:
            nama = html.escape(str(user.get("nama_lengkap") or user.get("username", "Pengguna")))
            username = html.escape(str(user.get("username", "-")))
            jumlah_genre = len(user.get("genres", []))
            st.markdown(
                dedent(f"""
                <div class="tc-account">
                    <div class="tc-account-secondary" style="font-size:0.75rem;">Masuk sebagai</div>
                    <div style="font-size:0.95rem;font-weight:600;">{nama}</div>
                    <div class="tc-account-secondary" style="font-size:0.8rem;">@{username} · {jumlah_genre} genre</div>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )
            if st.button("Keluar", key="sidebar_logout_btn", width="stretch"):
                logout_user()
                st.rerun()
        else:
            st.markdown(
                '<div class="tc-account tc-account-secondary">Masuk untuk menyimpan preferensi dan lagu.</div>',
                unsafe_allow_html=True,
            )

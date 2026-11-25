"""
app.py — Entry point dan halaman utama TuneCluster.
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from utils.auth import (
    get_current_user,
    init_session_state,
    inject_global_styles,
    render_footer,
    render_genre_badges,
    render_sidebar,
)
from utils.database import get_history, init_db, login_user, register_user
from utils.recommender import TuneClusterRecommender

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"

st.set_page_config(
    page_title="TuneCluster · Temukan Playlist Sempurna",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Pastikan DB, session state, global CSS, dan sidebar siap saat app pertama kali dijalankan
init_db()
init_session_state()
inject_global_styles()
render_sidebar()

st.markdown(
    """
    <style>
    .hero-card {
        background: linear-gradient(135deg, #1E1E1E 0%, #14281B 100%);
        border: 1px solid #2A2A2A;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    .hero-accent {
        color: #1DB954;
    }
    .hero-tagline {
        font-size: 1.15rem;
        font-weight: 600;
        color: #1DB954;
        margin-top: 0.3rem;
        margin-bottom: 0.8rem;
    }
    .hero-desc {
        color: #D1D1D1;
        font-size: 0.98rem;
        line-height: 1.6;
        margin-bottom: 0;
    }
    .history-card {
        background-color: #1E1E1E;
        border: 1px solid #2C2C2C;
        border-left: 4px solid #1DB954;
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
        padding: 1rem 1.25rem;
        margin-bottom: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def _load_recommender() -> TuneClusterRecommender:
    """Muat instance TuneClusterRecommender sekali dan cache lintas rerun."""
    return TuneClusterRecommender()


recommender = _load_recommender()


def _render_hero() -> None:
    """Tampilkan logo, judul, tagline, dan deskripsi singkat TuneCluster."""
    col_logo, col_text = st.columns([1, 6], vertical_alignment="center")
    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=115)
    with col_text:
        st.markdown(
            """
            <div class="hero-card">
                <h1 class="hero-title">Tune<span class="hero-accent">Cluster</span></h1>
                <div class="hero-tagline">🎵 Temukan Playlist Sempurna untuk Aktivitasmu</div>
                <p class="hero-desc">
                    <strong>TuneCluster</strong> adalah aplikasi rekomendasi musik cerdas berbasis
                    <em>unsupervised machine learning</em> yang mengelompokkan <strong>89.741 lagu Spotify</strong>
                    ke dalam cluster karakteristik audio menggunakan algoritma <strong>K-Means</strong> dan <strong>BIRCH</strong>
                    pada lima fitur utama (<em>danceability, energy, valence, acousticness, instrumentalness</em>).
                </p>
                <p class="hero-desc" style="margin-top: 0.55rem;">
                    Cukup pilih genre favorit, aktivitas yang sedang Anda jalani (<em>Olahraga, Belajar, Santai, Perjalanan</em>),
                    serta mood saat ini — sistem akan mencarikan lagu dengan profil audio terdekat dan menampilkannya
                    lengkap dengan pemutar Spotify.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_auth_forms() -> None:
    """Tampilkan form Login dan Register berbasis tab jika user belum login."""
    st.subheader("🔐 Masuk atau Daftar Akun")
    st.caption("Masuk untuk mendapatkan rekomendasi playlist yang dipersonalisasi dan menyimpan riwayat mendengarkan Anda.")

    tab_login, tab_register = st.tabs(["🔑 Masuk (Login)", "📝 Daftar Akun (Register)"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            login_username = st.text_input(
                "Username",
                placeholder="Masukkan username Anda",
                key="login_username_input",
            )
            login_password = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan password Anda",
                key="login_password_input",
            )
            submit_login = st.form_submit_button(
                "Masuk",
                type="primary",
                width="stretch",
            )

        if submit_login:
            if not login_username.strip() or not login_password:
                st.error("Username dan password harus diisi.")
            else:
                user_info = login_user(login_username.strip(), login_password)
                if user_info is None:
                    st.error("Login gagal! Periksa kembali username atau password Anda.")
                else:
                    st.session_state["user"] = user_info
                    st.success("Login berhasil! Memuat beranda Anda...")
                    st.rerun()

    with tab_register:
        daftar_genre = recommender.get_daftar_genre()
        with st.form("register_form", clear_on_submit=False):
            col_a, col_b = st.columns(2)
            with col_a:
                reg_username = st.text_input(
                    "Username",
                    placeholder="Minimal 3 karakter, tanpa spasi",
                    key="reg_username_input",
                )
                reg_nama = st.text_input(
                    "Nama Lengkap",
                    placeholder="Masukkan nama lengkap Anda",
                    key="reg_nama_input",
                )
                reg_umur = st.number_input(
                    "Umur",
                    min_value=10,
                    max_value=80,
                    value=21,
                    step=1,
                    key="reg_umur_input",
                )
            with col_b:
                reg_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Minimal 6 karakter",
                    key="reg_password_input",
                )
                reg_confirm = st.text_input(
                    "Konfirmasi Password",
                    type="password",
                    placeholder="Ulangi password Anda",
                    key="reg_confirm_input",
                )
                reg_genres = st.multiselect(
                    "Pilih Genre Favorit (minimal 1, maksimal 10 genre)",
                    options=daftar_genre,
                    max_selections=10,
                    placeholder="Cari dan pilih genre favorit Anda...",
                    key="reg_genres_input",
                )

            submit_register = st.form_submit_button(
                "Daftar",
                type="primary",
                width="stretch",
            )

        if submit_register:
            username_clean = reg_username.strip()
            nama_clean = reg_nama.strip()
            errors: list[str] = []

            if len(username_clean) < 3:
                errors.append("Username minimal 3 karakter.")
            if " " in username_clean:
                errors.append("Username tidak boleh mengandung spasi.")
            if not nama_clean:
                errors.append("Nama lengkap tidak boleh kosong.")
            if len(reg_password) < 6:
                errors.append("Password minimal 6 karakter.")
            if reg_password != reg_confirm:
                errors.append("Password dan konfirmasi password harus cocok.")
            if len(reg_genres) < 1 or len(reg_genres) > 10:
                errors.append("Pilih minimal 1 dan maksimal 10 genre favorit.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                ok, msg = register_user(
                    username=username_clean,
                    nama_lengkap=nama_clean,
                    umur=int(reg_umur),
                    password=reg_password,
                    genre_list=reg_genres,
                )
                if not ok:
                    st.error(msg)
                else:
                    user_info = login_user(username_clean, reg_password)
                    if user_info is not None:
                        st.session_state["user"] = user_info
                    st.success("Pendaftaran berhasil! Selamat datang di TuneCluster.")
                    st.rerun()


def _render_genre_badges(genres: list[str]) -> None:
    """Tampilkan daftar genre favorit sebagai badge pastel berwarna."""
    render_genre_badges(
        genres,
        empty_message="Belum ada genre favorit tersimpan. Anda dapat menambahkannya di halaman Profil.",
    )


def _render_dashboard(user: dict) -> None:
    """Tampilkan halaman beranda personalisasi jika user sudah login."""
    nama = user.get("nama_lengkap") or user.get("username", "Teman Musik")
    genres = user.get("genres", [])

    st.markdown(f"## Halo, {html.escape(str(nama))}! 👋")
    st.caption(
        f"Username: **@{user.get('username', '-')}** · Umur: **{user.get('umur', '-')} tahun** · "
        f"Total genre favorit: **{len(genres)}**"
    )

    # Ringkasan profil & genre favorit berwarna
    st.markdown("#### 🎶 Genre Favorit Anda")
    _render_genre_badges(genres)

    st.write("")

    # Quick action buttons
    st.markdown("#### ⚡ Aksi Cepat")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button(
            "🎵 Dapatkan Rekomendasi",
            type="primary",
            width="stretch",
            key="quick_btn_rekomendasi",
        ):
            st.switch_page("pages/2_🎵_Rekomendasi.py")
    with col_act2:
        if st.button(
            "📊 Lihat Analisis",
            width="stretch",
            key="quick_btn_analisis",
        ):
            st.switch_page("pages/3_📊_Analisis.py")

    st.divider()

    # Riwayat 3 rekomendasi terakhir
    st.markdown("#### 🕒 Riwayat 3 Rekomendasi Terakhir")
    riwayat = get_history(user["user_id"], limit=3)

    if not riwayat:
        st.info(
            "Anda belum memiliki riwayat rekomendasi. Klik **🎵 Dapatkan Rekomendasi** di atas "
            "untuk membuat playlist pertama Anda!"
        )
        return

    katalog_lookup = recommender.katalog.set_index("track_id")[["track_name", "artists"]]

    for item in riwayat:
        track_ids = item.get("rekomendasi_track_ids", [])
        aktivitas = html.escape(str(item.get("aktivitas", "-")))
        mood = html.escape(str(item.get("mood", "-")))
        waktu = html.escape(str(item.get("timestamp", "-")))

        lagu_preview: list[str] = []
        for tid in track_ids[:3]:
            if tid in katalog_lookup.index:
                row = katalog_lookup.loc[tid]
                if isinstance(row, type(katalog_lookup)):
                    row = row.iloc[0]
                lagu_preview.append(
                    f"{html.escape(str(row['track_name']))} — {html.escape(str(row['artists']))}"
                )
            else:
                lagu_preview.append(html.escape(str(tid)))

        sisa = len(track_ids) - len(lagu_preview)
        preview_html = "<br>".join(f"• {txt}" for txt in lagu_preview) if lagu_preview else "• Tidak ada detail lagu"
        if sisa > 0:
            preview_html += f"<br><span style='color:#9E9E9E;'>… dan {sisa} lagu lainnya</span>"

        st.markdown(
            f"""
            <div class="history-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <span style="font-weight:700; font-size:1.02rem; color:#FFFFFF;">
                        🎯 {aktivitas} &nbsp;·&nbsp; <span style="color:#1DB954;">{mood}</span>
                    </span>
                    <span style="font-size:0.8rem; color:#B3B3B3;">🗓️ {waktu} · {len(track_ids)} lagu</span>
                </div>
                <div style="font-size:0.88rem; color:#D5D5D5; line-height:1.5;">
                    {preview_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


_render_hero()
st.divider()

current_user = get_current_user(refresh_from_db=True)
if current_user is None:
    _render_auth_forms()
else:
    _render_dashboard(current_user)

render_footer()

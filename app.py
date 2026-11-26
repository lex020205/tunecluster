"""
app.py — Entry point dan halaman utama TuneCluster.
"""

from __future__ import annotations

import html

import streamlit as st

from utils.auth import (
    get_current_user,
    init_session_state,
    render_footer,
    render_genre_badges,
    render_sidebar,
)
from utils.database import get_history, init_db, login_user, register_user
from utils.recommender import TuneClusterRecommender

st.set_page_config(
    page_title="TuneCluster · Temukan Playlist Sempurna",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Pastikan DB, session state, global CSS, dan sidebar siap saat app pertama kali dijalankan
init_db()
init_session_state()
render_sidebar()

@st.cache_resource(show_spinner=False)
def _load_recommender() -> TuneClusterRecommender:
    """Muat instance TuneClusterRecommender sekali dan cache lintas rerun."""
    return TuneClusterRecommender()


recommender = _load_recommender()


def _render_hero() -> None:
    """Tampilkan pengenalan singkat TuneCluster."""
    st.markdown(
        """
        <div class="hero-card">
            <h1 class="hero-title">Tune<span class="hero-accent">Cluster</span></h1>
            <div class="hero-tagline">Rekomendasi musik untuk aktivitas Anda</div>
            <p class="hero-desc">
                TuneCluster mengelompokkan 89.741 lagu Spotify berdasarkan karakteristik
                audio, lalu menyusun rekomendasi dengan K-Means atau BIRCH.
            </p>
            <p class="hero-desc">
                Pilih genre favorit, aktivitas, dan suasana. Setiap playlist disertai
                pemutar Spotify dan dapat disimpan ke profil Anda.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_auth_forms() -> None:
    """Tampilkan form Login dan Register berbasis tab jika user belum login."""
    st.subheader("Masuk atau daftar")
    st.caption("Masuk untuk mendapatkan rekomendasi playlist yang dipersonalisasi dan menyimpan riwayat mendengarkan Anda.")

    tab_login, tab_register = st.tabs(["Masuk", "Buat akun"])

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
    """Tampilkan daftar genre favorit sebagai badge monokrom."""
    render_genre_badges(
        genres,
        empty_message="Belum ada genre favorit tersimpan. Anda dapat menambahkannya di halaman Profil.",
    )


def _render_dashboard(user: dict) -> None:
    """Tampilkan halaman beranda personalisasi jika user sudah login."""
    nama = user.get("nama_lengkap") or user.get("username", "Teman Musik")
    genres = user.get("genres", [])

    st.markdown(f"## Halo, {html.escape(str(nama))}! ")
    st.caption(
        f"Username: **@{user.get('username', '-')}** · Umur: **{user.get('umur', '-')} tahun** · "
        f"Total genre favorit: **{len(genres)}**"
    )

    # Ringkasan profil & genre favorit berwarna
    st.markdown("#### Genre favorit")
    _render_genre_badges(genres)

    st.write("")

    # Quick action buttons
    st.markdown("#### Aksi cepat")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button(
            "Rekomendasi",
            type="primary",
            width="stretch",
            key="quick_btn_rekomendasi",
        ):
            st.switch_page("pages/2_🎵_Rekomendasi.py")
    with col_act2:
        if st.button(
            "Analisis",
            width="stretch",
            key="quick_btn_analisis",
        ):
            st.switch_page("pages/3_📊_Analisis.py")

    st.divider()

    # Riwayat 3 rekomendasi terakhir
    st.markdown("#### Riwayat rekomendasi terbaru")
    riwayat = get_history(user["user_id"], limit=3)

    if not riwayat:
        st.info(
            "Anda belum memiliki riwayat rekomendasi. Pilih **Rekomendasi** untuk membuat playlist pertama Anda."
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
                <div class="tc-track-title">{aktivitas} · {mood}</div>
                <div class="tc-track-meta">{waktu} · {len(track_ids)} lagu</div>
                <div class="tc-track-meta" style="margin-top:0.45rem;">
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

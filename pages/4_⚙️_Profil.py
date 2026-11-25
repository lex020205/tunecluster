"""
4_⚙️_Profil.py — Halaman manajemen profil pengguna, genre favorit, riwayat, & statistik personal.
"""

from __future__ import annotations

import html
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth import (
    PASTEL_GENRE_PALETTE,
    get_current_user,
    init_session_state,
    render_footer,
    render_sidebar,
)
from utils.database import (
    add_genre,
    get_history,
    get_user_stats,
    remove_genre,
    update_profile,
)
from utils.recommender import get_recommender
from utils.spotify_embed import render_track_card

st.set_page_config(
    page_title="Profil · TuneCluster",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
render_sidebar()

user = get_current_user(refresh_from_db=True)
if user is None:
    st.title("⚙️ Profil & Pengaturan Akun")
    st.warning("Anda harus login terlebih dahulu untuk mengakses dan mengelola profil Anda.")
    try:
        st.page_link("app.py", label="Kembali ke Halaman Utama untuk Login / Daftar", icon="🏠")
    except Exception:
        st.info("Silakan kembali ke halaman utama **app** di sidebar untuk Login atau Daftar.")
    if st.button("🏠 Pergi ke Halaman Utama", type="primary"):
        st.switch_page("app.py")
    render_footer()
    st.stop()

recommender = get_recommender()
user_id = int(user["user_id"])
user_genres = list(user.get("genres", []))

st.title(f"⚙️ Profil · {html.escape(str(user.get('nama_lengkap') or user.get('username')))}")
st.caption("Kelola informasi akun, preferensi genre favorit, riwayat playlist, serta statistik musik pribadi Anda.")

# =============================================================================
# SECTION 1: INFO PROFIL & FORM EDIT
# =============================================================================
st.subheader("👤 Info Profil")

col_info, col_edit = st.columns([1, 1.2], gap="large")

with col_info:
    with st.container(border=True):
        st.markdown("##### 📄 Detail Akun")
        st.markdown(
            f"""
            <div style="line-height:1.9; font-size:0.95rem;">
                <div><span style="color:#9E9E9E;">Username:</span> <b style="color:#1DB954;">@{html.escape(str(user.get('username', '-')))}</b></div>
                <div><span style="color:#9E9E9E;">Nama Lengkap:</span> <b>{html.escape(str(user.get('nama_lengkap', '-')))}</b></div>
                <div><span style="color:#9E9E9E;">Umur:</span> <b>{int(user.get('umur', 0))} tahun</b></div>
                <div><span style="color:#9E9E9E;">Tanggal Bergabung:</span> <b>{html.escape(str(user.get('created_at', '-')))}</b></div>
                <div><span style="color:#9E9E9E;">Login Terakhir:</span> <b>{html.escape(str(user.get('last_login') or '-'))}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with col_edit:
    with st.form("form_edit_profil"):
        st.markdown("##### ✏️ Edit Profil")
        edit_nama = st.text_input(
            "Nama Lengkap",
            value=str(user.get("nama_lengkap", "")),
            key="profil_edit_nama",
        )
        edit_umur = st.number_input(
            "Umur",
            min_value=10,
            max_value=80,
            value=min(80, max(10, int(user.get("umur", 21)))),
            step=1,
            key="profil_edit_umur",
        )
        simpan_profil = st.form_submit_button(
            "💾 Simpan Perubahan",
            type="primary",
            width="stretch",
        )

    if simpan_profil:
        nama_clean = edit_nama.strip()
        if not nama_clean:
            st.error("Nama lengkap tidak boleh kosong.")
        else:
            try:
                ok = update_profile(user_id, nama_lengkap=nama_clean, umur=int(edit_umur))
                if ok:
                    st.session_state["user"] = get_current_user(refresh_from_db=True)
                    st.success("Profil berhasil diperbarui!")
                    st.rerun()
                else:
                    st.error("Gagal memperbarui profil. Akun tidak ditemukan.")
            except ValueError as err:
                st.error(str(err))

st.divider()

# =============================================================================
# SECTION 2: GENRE FAVORIT
# =============================================================================
st.subheader(f"🎧 Genre Favorit ({len(user_genres)}/10)")
st.caption("Pilih minimal 1 dan maksimal 10 genre favorit untuk personalisasi playlist Anda.")

if not user_genres:
    st.warning("Anda belum memiliki genre favorit. Silakan tambahkan minimal 1 genre di bawah.")
else:
    n_cols = 3
    for start in range(0, len(user_genres), n_cols):
        row_genres = user_genres[start : start + n_cols]
        cols_g = st.columns(n_cols)
        for offset, (col_g, genre_item) in enumerate(zip(cols_g, row_genres)):
            idx_pal = (start + offset) % len(PASTEL_GENRE_PALETTE)
            text_c, bg_c, border_c = PASTEL_GENRE_PALETTE[idx_pal]
            safe_g = html.escape(str(genre_item))
            with col_g:
                c_tag, c_btn = st.columns([3.4, 1], vertical_alignment="center")
                with c_tag:
                    st.markdown(
                        f'<span class="genre-badge" style="display:block; text-align:center; '
                        f'background-color:{bg_c}; color:{text_c}; border:1px solid {border_c}; '
                        f'margin:0;">🎧 {safe_g}</span>',
                        unsafe_allow_html=True,
                    )
                with c_btn:
                    if st.button(
                        "❌",
                        key=f"remove_genre_btn_{start + offset}_{genre_item}",
                        help=f"Hapus genre '{genre_item}'",
                        width="stretch",
                    ):
                        if len(user_genres) <= 1:
                            st.warning("Minimal 1 genre favorit harus dipertahankan.")
                        else:
                            if remove_genre(user_id, genre_item):
                                st.session_state["user"] = get_current_user(refresh_from_db=True)
                                st.toast(f"Genre '{genre_item}' dihapus.", icon="🗑️")
                                st.rerun()

# Tambah genre baru
semua_genre = recommender.get_daftar_genre()
existing_lower = {g.lower() for g in user_genres}
genre_belum_dipilih = [g for g in semua_genre if g.lower() not in existing_lower]
sisa_slot = max(0, 10 - len(user_genres))

with st.container(border=True):
    if sisa_slot == 0:
        st.info("Maksimal 10 genre favorit telah tercapai. Hapus salah satu genre jika ingin mengganti.")
    else:
        col_add_sel, col_add_btn = st.columns([3, 1], vertical_alignment="bottom")
        with col_add_sel:
            genre_tambah = st.multiselect(
                f"Tambah genre baru (tersisa {sisa_slot} slot)",
                options=genre_belum_dipilih,
                max_selections=sisa_slot,
                placeholder="Pilih satu atau beberapa genre...",
                key="profil_add_genres_multiselect",
            )
        with col_add_btn:
            klik_tambah = st.button(
                "➕ Tambah Genre",
                type="primary",
                key="profil_add_genres_btn",
                width="stretch",
            )

        if klik_tambah:
            if not genre_tambah:
                st.warning("Pilih minimal 1 genre terlebih dahulu.")
            elif len(user_genres) + len(genre_tambah) > 10:
                st.error("Total genre favorit tidak boleh lebih dari 10.")
            else:
                berhasil = 0
                for g in genre_tambah:
                    if add_genre(user_id, g):
                        berhasil += 1
                if berhasil > 0:
                    st.session_state["user"] = get_current_user(refresh_from_db=True)
                    st.toast(f"{berhasil} genre berhasil ditambahkan!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Genre yang dipilih sudah ada di daftar favorit Anda.")

st.divider()

# =============================================================================
# SECTION 3: RIWAYAT REKOMENDASI (20 TERAKHIR)
# =============================================================================
st.subheader("🕒 Riwayat 20 Rekomendasi Terakhir")

riwayat_20 = get_history(user_id, limit=20)
katalog_lookup = recommender.katalog.set_index("track_id")

if not riwayat_20:
    st.info("Belum ada riwayat rekomendasi. Buat playlist pertama Anda di halaman Rekomendasi!")
    if st.button("🎵 Pergi ke Halaman Rekomendasi", type="primary"):
        st.switch_page("pages/2_🎵_Rekomendasi.py")
else:
    tabel_riwayat = pd.DataFrame(
        [
            {
                "ID": r["id"],
                "Tanggal & Waktu": r["timestamp"],
                "Aktivitas": r["aktivitas"],
                "Mood": r["mood"],
                "Jumlah Lagu": len(r["rekomendasi_track_ids"]),
            }
            for r in riwayat_20
        ]
    )
    st.dataframe(tabel_riwayat, width="stretch", hide_index=True)

    # Pilih riwayat untuk melihat detail playlist
    opsi_riwayat = {
        f"#{r['id']} · {r['timestamp']} — {r['aktivitas']} ({r['mood']}, {len(r['rekomendasi_track_ids'])} lagu)": r
        for r in riwayat_20
    }
    pilihan_label = st.selectbox(
        "Pilih riwayat untuk melihat detail playlist",
        options=list(opsi_riwayat.keys()),
        key="profil_select_riwayat_detail",
    )
    riwayat_terpilih = opsi_riwayat[pilihan_label]
    track_ids_sel = riwayat_terpilih.get("rekomendasi_track_ids", [])

    with st.expander(
        f"🎶 Detail Playlist: {riwayat_terpilih['aktivitas']} · {riwayat_terpilih['mood']} ({len(track_ids_sel)} lagu)",
        expanded=True,
    ):
        lagu_ditemukan = []
        for idx_t, tid in enumerate(track_ids_sel, start=1):
            if tid in katalog_lookup.index:
                row_k = katalog_lookup.loc[tid]
                if isinstance(row_k, pd.DataFrame):
                    row_k = row_k.iloc[0]
                lagu_ditemukan.append(
                    {
                        "No": idx_t,
                        "track_id": tid,
                        "Judul Lagu": str(row_k["track_name"]),
                        "Artis": str(row_k["artists"]),
                        "Genre": str(row_k["genre_gabungan"]),
                        "Cluster": str(row_k["nama_cluster"]),
                    }
                )
            else:
                lagu_ditemukan.append(
                    {
                        "No": idx_t,
                        "track_id": tid,
                        "Judul Lagu": f"Track {tid}",
                        "Artis": "-",
                        "Genre": "-",
                        "Cluster": "-",
                    }
                )

        df_detail = pd.DataFrame(lagu_ditemukan)
        st.dataframe(
            df_detail[["No", "Judul Lagu", "Artis", "Genre", "Cluster"]],
            width="stretch",
            hide_index=True,
        )

        tampilkan_player_riwayat = st.toggle(
            "🎧 Tampilkan Kartu & Pemutar Spotify untuk Riwayat Ini",
            value=False,
            key="profil_toggle_history_player",
        )
        if tampilkan_player_riwayat:
            for item_lagu in lagu_ditemukan:
                render_track_card(
                    track_name=item_lagu["Judul Lagu"],
                    artists=item_lagu["Artis"],
                    genre=item_lagu["Genre"],
                    similarity_score=100.0,
                    track_id=item_lagu["track_id"],
                    rank=item_lagu["No"],
                    show_player=True,
                )

st.divider()

# =============================================================================
# SECTION 4: STATISTIK PERSONAL
# =============================================================================
st.subheader("📊 Statistik Personal")

stats = get_user_stats(user_id)
riwayat_semua = get_history(user_id, limit=500)

genre_rekom_counter: Counter[str] = Counter()
for r in riwayat_semua:
    for tid in r.get("rekomendasi_track_ids", []):
        if tid in katalog_lookup.index:
            row_k = katalog_lookup.loc[tid]
            if isinstance(row_k, pd.DataFrame):
                row_k = row_k.iloc[0]
            for g in str(row_k["genre_gabungan"]).split(" | "):
                g_clean = g.strip()
                if g_clean:
                    genre_rekom_counter[g_clean] += 1

genre_tersering_rekom = (
    f"{genre_rekom_counter.most_common(1)[0][0]} ({genre_rekom_counter.most_common(1)[0][1]}×)"
    if genre_rekom_counter
    else "-"
)

c_s1, c_s2, c_s3, c_s4 = st.columns(4)
c_s1.metric(
    "Total Rekomendasi",
    f"{stats['total_rekomendasi']}",
    delta=f"{stats['total_lagu_direkomendasikan']} lagu",
)
c_s2.metric("Aktivitas Paling Sering", stats["aktivitas_terfavorit"] or "-")
c_s3.metric("Mood Paling Sering", stats["mood_terfavorit"] or "-")
c_s4.metric("Genre Tersering di Rekomendasi", genre_tersering_rekom)

if riwayat_semua:
    col_ch1, col_ch2 = st.columns(2)
    with col_ch1:
        dist_akt = stats.get("distribusi_aktivitas", {})
        if dist_akt:
            df_akt = pd.DataFrame(
                [{"Aktivitas": k, "Jumlah Sesi": v} for k, v in dist_akt.items()]
            ).sort_values("Jumlah Sesi", ascending=True)
            fig_akt = px.bar(
                df_akt,
                x="Jumlah Sesi",
                y="Aktivitas",
                orientation="h",
                color_discrete_sequence=["#1DB954"],
                title="Frekuensi Aktivitas Rekomendasi Anda",
            )
            fig_akt.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#181818",
                font=dict(color="#FFFFFF"),
                xaxis=dict(dtick=1, gridcolor="#2A2A2A"),
                height=300,
            )
            st.plotly_chart(fig_akt, width="stretch")

    with col_ch2:
        if genre_rekom_counter:
            top_g = genre_rekom_counter.most_common(8)
            df_top_g = pd.DataFrame(
                [{"Genre": g, "Kemunculan": c} for g, c in reversed(top_g)]
            )
            fig_g = px.bar(
                df_top_g,
                x="Kemunculan",
                y="Genre",
                orientation="h",
                color_discrete_sequence=["#4EA8DE"],
                title="Top Genre pada Lagu Rekomendasi Anda",
            )
            fig_g.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#181818",
                font=dict(color="#FFFFFF"),
                xaxis=dict(gridcolor="#2A2A2A"),
                height=300,
            )
            st.plotly_chart(fig_g, width="stretch")

render_footer()

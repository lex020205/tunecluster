"""
2_🎵_Rekomendasi.py — Halaman utama mesin rekomendasi playlist TuneCluster.
"""

from __future__ import annotations

import html
import math
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
    add_genre,
    get_saved_tracks,
    remove_genre,
    remove_saved_track,
    save_history,
    save_track,
)
from utils.recommender import get_recommender, normalisasi_genre
from utils.spotify_embed import render_track_card

st.set_page_config(
    page_title="Rekomendasi · TuneCluster",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

GENRE_BADGE_PALETTE = [
    ("#1DB954", "#0B2E16"),
    ("#1ED760", "#0E351B"),
    ("#2E77D0", "#11243D"),
    ("#AF2896", "#330D2C"),
    ("#E8115B", "#3D081A"),
    ("#F59B23", "#3D2608"),
]

AKTIVITAS_OPTIONS = {
    "🏃 Olahraga": "Olahraga",
    "📚 Belajar": "Belajar",
    "☕ Santai": "Santai",
    "🚗 Perjalanan": "Perjalanan",
}

MOOD_OPTIONS = {
    "😊 Senang/Happy": "Senang/Happy",
    "😢 Sedih/Sad": "Sedih/Sad",
    "⚡ Energik": "Energik",
    "😌 Tenang/Calm": "Tenang/Calm",
    "🎯 Fokus": "Fokus",
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

st.markdown(
    """
    <style>
    .genre-badge {
        display: inline-block;
        padding: 0.3rem 0.78rem;
        margin: 0.2rem 0.3rem 0.2rem 0;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 600;
    }
    .cluster-box {
        background: linear-gradient(135deg, #1E1E1E 0%, #14281B 100%);
        border: 1px solid #2A2A2A;
        border-left: 4px solid #1DB954;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _render_genre_badges(genres: list[str]) -> None:
    """Tampilkan daftar genre user dalam bentuk badge pastel berwarna."""
    render_genre_badges(
        genres,
        empty_message="Belum ada genre favorit tersimpan. Tambahkan melalui Quick Edit di sidebar atau halaman Profil.",
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
            line=dict(color="#4EA8DE", width=2),
            fillcolor="rgba(78, 168, 222, 0.22)",
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


def _render_sidebar_tambahan(user: dict[str, Any], recommender: Any) -> list[str]:
    """Tampilkan kontrol Quick Edit Genre dan Filter Hasil Rekomendasi di sidebar."""
    user_genres: list[str] = list(user.get("genres", []))
    semua_genre: list[str] = recommender.get_daftar_genre()

    with st.sidebar:
        st.divider()
        st.markdown("### 🎛️ Quick Edit Genre")

        # Tambah genre
        genre_tersedia_tambah = [
            g for g in semua_genre if g.lower() not in {ug.lower() for ug in user_genres}
        ]
        if len(user_genres) >= 10:
            st.caption("Maksimal 10 genre favorit tercapai. Hapus salah satu untuk menambah genre baru.")
        elif genre_tersedia_tambah:
            genre_baru = st.selectbox(
                "Tambah genre favorit",
                options=genre_tersedia_tambah,
                index=None,
                placeholder="Pilih genre untuk ditambah...",
                key="quick_add_genre_select",
            )
            if st.button("➕ Tambah Genre", key="quick_add_genre_btn", width="stretch"):
                if genre_baru:
                    if add_genre(user["user_id"], genre_baru):
                        st.session_state["user"] = get_current_user(refresh_from_db=True)
                        st.toast(f"Genre '{genre_baru}' ditambahkan!", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Genre gagal ditambahkan atau sudah ada.")

        # Hapus genre
        if user_genres:
            genre_hapus = st.selectbox(
                "Hapus genre favorit",
                options=user_genres,
                index=None,
                placeholder="Pilih genre untuk dihapus...",
                key="quick_remove_genre_select",
            )
            if st.button("🗑️ Hapus Genre", key="quick_remove_genre_btn", width="stretch"):
                if genre_hapus:
                    if remove_genre(user["user_id"], genre_hapus):
                        st.session_state["user"] = get_current_user(refresh_from_db=True)
                        st.toast(f"Genre '{genre_hapus}' dihapus!", icon="🗑️")
                        st.rerun()
        else:
            st.caption("Belum ada genre favorit.")

        # Filter genre dari hasil rekomendasi yang sedang tampil
        selected_filter_genres: list[str] = []
        last_df = st.session_state.get("last_rekomendasi")
        if last_df is not None and not last_df.empty:
            st.divider()
            st.markdown("### 🔍 Filter Hasil Playlist")
            genre_hasil = sorted(
                {
                    normalisasi_genre(g)
                    for row_g in last_df["genre_gabungan"].fillna("")
                    for g in str(row_g).split(" | ")
                    if normalisasi_genre(g)
                }
            )
            if st.session_state.pop("_reset_filter_genre", False):
                st.session_state["filter_genre_hasil"] = []
            selected_filter_genres = st.multiselect(
                "Filter genre lagu",
                options=genre_hasil,
                placeholder="Semua genre di hasil",
                key="filter_genre_hasil",
            )

    return selected_filter_genres


# 1. Sidebar utama + cek login
render_sidebar()
user = get_current_user(refresh_from_db=True)

if user is None:
    st.title("🎵 Rekomendasi Playlist")
    st.warning("Anda harus login terlebih dahulu untuk menggunakan fitur rekomendasi personal.")
    try:
        st.page_link("app.py", label="Kembali ke Halaman Utama untuk Login / Daftar", icon="🏠")
    except Exception:
        st.info("Silakan kembali ke halaman utama **app** di sidebar untuk Login atau Daftar.")
    if st.button("🏠 Pergi ke Halaman Utama", type="primary"):
        st.switch_page("app.py")
    st.stop()

recommender = get_recommender()
filter_genres_hasil = _render_sidebar_tambahan(user, recommender)
has_popularity = (
    "popularity" in recommender.katalog.columns
    and recommender.katalog["popularity"].notna().any()
)

# Refresh referensi user jika diubah dari sidebar
user = get_current_user() or user
nama_user = html.escape(str(user.get("nama_lengkap") or user.get("username", "Teman Musik")))
user_genres = list(user.get("genres", []))

# 2. Header Personal
st.title(f"🎵 Rekomendasi untuk {nama_user}")
st.markdown("##### 🎧 Genre Favorit Anda")
_render_genre_badges(user_genres)
st.divider()

# 3. Input Section (Form)
with st.form("form_rekomendasi_playlist"):
    st.subheader("🎯 Atur Suasana & Aktivitas Anda")

    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        aktivitas_label = st.radio(
            "a. Pilih Aktivitas Hari Ini",
            options=list(AKTIVITAS_OPTIONS.keys()),
            horizontal=True,
            key="input_aktivitas",
        )
    with col_inp2:
        mood_label = st.radio(
            "b. Pilih Mood Saat Ini",
            options=list(MOOD_OPTIONS.keys()),
            horizontal=True,
            key="input_mood",
        )

    jumlah_lagu = st.slider(
        "Jumlah Lagu dalam Playlist",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        key="input_jumlah_lagu",
    )

    mode_rekomendasi = st.radio(
        "Urutan rekomendasi",
        options=(
            ["Kecocokan Audio", "Populer / Familiar"]
            if has_popularity
            else ["Kecocokan Audio"]
        ),
        horizontal=True,
        key="input_mode_rekomendasi",
        help="Mode populer memakai popularity Spotify (0–100), bukan riwayat pribadi Anda.",
    )

    with st.expander("⚙️ Pengaturan Lanjutan"):
        algoritma_label = st.radio(
            "Pilih Algoritma Clustering",
            options=list(ALGORITMA_OPTIONS.keys()),
            index=0,
            horizontal=True,
            key="input_algoritma",
            help="K-Means direkomendasikan karena lebih seimbang dan stabil (ARI 0.9853 vs BIRCH 0.2381).",
        )

    submit_btn = st.form_submit_button(
        "🎵 Dapatkan Playlist!",
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
df_hasil = st.session_state.get("last_rekomendasi")
meta_hasil = st.session_state.get("last_rekomendasi_meta")

if df_hasil is not None and meta_hasil is not None:
    st.divider()
    st.subheader("🎧 Hasil Rekomendasi Playlist")

    algo_used = meta_hasil["algoritma"]
    target_cluster = int(meta_hasil["target_cluster"])
    nama_cluster = str(meta_hasil["nama_cluster"])
    profil_df = recommender.get_profil_cluster(algo_used)
    profil_cluster_row = (
        profil_df.loc[target_cluster].to_dict()
        if target_cluster in profil_df.index
        else profil_df.iloc[0].to_dict()
    )

    # 4a. Info Cluster & Radar Chart
    col_info, col_radar = st.columns([1.15, 1], vertical_alignment="center")
    with col_info:
        genre_cocok_txt = (
            ", ".join(meta_hasil["genre_cocok"]) if meta_hasil["genre_cocok"] else "Tidak ada (menggunakan fallback audio)"
        )
        fallback_notice = (
            "<br><span style='color:#F59B23;'>⚠️ Preferensi genre belum tersedia di cluster target, "
            "sistem menggunakan seluruh lagu di cluster ini berdasarkan kemiripan audio.</span>"
            if meta_hasil["fallback_audio"]
            else ""
        )
        st.markdown(
            f"""
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
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        m1, m2, m3, m4, m5 = st.columns(5)
        for col_m, fitur_key in zip([m1, m2, m3, m4, m5], FITUR_LABELS.keys()):
            val_c = float(profil_cluster_row.get(fitur_key, 0.0))
            val_t = float(meta_hasil["target_vektor"].get(fitur_key, 0.0))
            col_m.metric(
                label=FITUR_LABELS[fitur_key],
                value=f"{val_t:.2f}",
                delta=f"{val_t - val_c:+.2f} vs cluster",
            )

    with col_radar:
        fig_radar = _buat_radar_chart(
            profil_cluster_row=profil_cluster_row,
            target_vektor=meta_hasil["target_vektor"],
            nama_cluster=nama_cluster,
        )
        st.plotly_chart(fig_radar, width="stretch")

    # Terapkan filter genre sidebar bila aktif
    df_tampil = df_hasil.copy()
    if filter_genres_hasil:
        filter_set = set(filter_genres_hasil)
        mask_f = df_tampil["genre_gabungan"].fillna("").apply(
            lambda s: bool(
                {normalisasi_genre(g) for g in str(s).split(" | ") if normalisasi_genre(g)} & filter_set
            )
        )
        df_tampil = df_tampil[mask_f].reset_index(drop=True)

    col_hdr, col_toggle, col_shuffle = st.columns([2.4, 1.3, 1.3], vertical_alignment="center")
    with col_hdr:
        st.markdown(f"#### 🎶 Daftar Lagu Rekomendasi ({len(df_tampil)} lagu)")
    with col_toggle:
        tampilkan_player = st.toggle(
            "🎧 Tampilkan Player",
            value=True,
            key="toggle_tampilkan_player",
        )
    with col_shuffle:
        if st.button(
            "🔀 Shuffle Playlist",
            key="btn_shuffle_playlist",
            width="stretch",
            disabled=df_hasil.empty,
        ):
            st.session_state["last_rekomendasi"] = df_hasil.sample(frac=1).reset_index(drop=True)
            st.rerun()

    if df_tampil.empty:
        st.info("Tidak ada lagu yang cocok dengan filter genre di sidebar. Kosongkan filter untuk melihat semua lagu.")
    else:
        saved_track_ids = {
            str(saved["track_id"])
            for saved in get_saved_tracks(int(user["user_id"]))
        }
        for idx, row in df_tampil.iterrows():
            render_track_card(
                track_name=str(row["track_name"]),
                artists=str(row["artists"]),
                genre=str(row["genre_gabungan"]),
                similarity_score=float(row["skor_kemiripan"]),
                track_id=str(row["track_id"]),
                rank=idx + 1,
                show_player=tampilkan_player,
                jarak=float(row["jarak"]),
            )
            if meta_hasil.get("prioritaskan_populer", False):
                popularity = float(row["popularity"])
                if math.isfinite(popularity):
                    st.caption(f"Popularitas Spotify: {popularity:.0f}/100")
            track_id = str(row["track_id"])
            if track_id in saved_track_ids:
                if st.button(
                    "✅ Tersimpan · Hapus",
                    key=f"remove_saved_track_{track_id}",
                    width="stretch",
                ):
                    if remove_saved_track(int(user["user_id"]), track_id):
                        st.toast("Lagu dihapus dari daftar tersimpan.", icon="🗑️")
                        st.rerun()
                    else:
                        st.error("Lagu tersimpan tidak dapat dihapus.")
            elif st.button(
                "💾 Simpan Lagu",
                key=f"save_track_{track_id}",
                width="stretch",
            ):
                if save_track(
                    user_id=int(user["user_id"]),
                    track_id=track_id,
                    aktivitas=str(meta_hasil["aktivitas"]),
                    mood=str(meta_hasil["mood"]),
                ):
                    st.toast("Lagu tersimpan di Profil Anda.", icon="💾")
                    st.rerun()
                else:
                    st.info("Lagu ini sudah tersimpan.")

render_footer()

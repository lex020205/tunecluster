"""
2__Rekomendasi.py — Halaman utama mesin rekomendasi playlist TuneCluster.
"""

from __future__ import annotations

import html
import json
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
    get_saved_tracks,
    remove_saved_track,
    save_history,
    save_track,
)
from utils.playlist_export import playlist_to_csv, playlist_to_text
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
                width: 100%;
                min-height: 40px;
                border: 0;
                border-radius: 8px;
                background: #FFFFFF;
                color: #121212;
                font-weight: 600;
                cursor: pointer;
            }}
        </style>
    """
    st.components.v1.html(component_html, height=42, scrolling=False)


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


# 1. Sidebar utama + cek login
render_sidebar()
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
            for idx, row in hasil_cari_lagu.iterrows():
                st.caption(
                    f"Cluster K-Means {int(row['cluster_kmeans'])} · {row['nama_cluster']} "
                    f"│ Cluster BIRCH {int(row['cluster_birch'])} · {row['nama_cluster_birch']}"
                )
                render_track_card(
                    track_name=str(row["track_name"]),
                    artists=str(row["artists"]),
                    genre=str(row["genre_gabungan"]),
                    similarity_score=100.0,
                    track_id=str(row["track_id"]),
                    rank=idx + 1,
                    show_player=True,
                    show_full_player=False,
                )
                if st.button(
                    "Cari yang mirip",
                    key=f"cari_mirip_{row['track_id']}",
                    width="stretch",
                ):
                    st.session_state["lagu_pencarian_serupa"] = str(row["track_id"])
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
            for idx, row in hasil_serupa.iterrows():
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

    if not df_tampil.empty:
        st.markdown("### Pilihan utama")
        top_picks = df_tampil.head(3)
        pick_columns = st.columns(len(top_picks))
        for pick_rank, (_, pick) in enumerate(top_picks.iterrows(), start=1):
            with pick_columns[pick_rank - 1]:
                render_track_card(
                    track_name=str(pick["track_name"]),
                    artists=str(pick["artists"]),
                    genre=str(pick["genre_gabungan"]),
                    similarity_score=float(pick["skor_kemiripan"]),
                    track_id=str(pick["track_id"]),
                    rank=pick_rank,
                    show_player=False,
                    show_full_player=False,
                    jarak=float(pick["jarak"]),
                )

    col_hdr, col_toggle, col_shuffle = st.columns([2.4, 1.3, 1.3], vertical_alignment="center")
    with col_hdr:
        st.markdown(f"#### Daftar lagu ({len(df_tampil)})")
    with col_toggle:
        tampilkan_player = st.toggle(
            "Tampilkan pemutar",
            value=True,
            key="toggle_tampilkan_player",
        )
    with col_shuffle:
        if st.button(
            "Acak playlist",
            key="btn_shuffle_playlist",
            width="stretch",
            disabled=df_hasil.empty,
        ):
            st.session_state["last_rekomendasi"] = df_hasil.sample(frac=1).reset_index(drop=True)
            st.rerun()

    if df_tampil.empty:
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
        col_copy, col_csv = st.columns(2)
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
                    "Tersimpan · Hapus",
                    key=f"remove_saved_track_{track_id}",
                    width="stretch",
                ):
                    if remove_saved_track(int(user["user_id"]), track_id):
                        st.toast("Lagu dihapus dari daftar tersimpan.")
                        st.rerun()
                    else:
                        st.error("Lagu tersimpan tidak dapat dihapus.")
            elif st.button(
                "Simpan",
                key=f"save_track_{track_id}",
                width="stretch",
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
            st.link_button(
                "Spotify",
                url=get_spotify_search_url(str(row["track_name"]), str(row["artists"])),
                key=f"btn_spotify_playlist_{idx}_{row['track_id']}",
            )

render_footer()

"""
3__Analisis.py — Halaman analisis data science perbandingan K-Means vs BIRCH (publik).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sklearn.decomposition import PCA

from utils.auth import init_session_state, render_footer, render_sidebar
from utils.recommender import get_recommender

st.set_page_config(
    page_title="Analisis Data Science · TuneCluster",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
render_sidebar()

BASE_DIR = Path(__file__).resolve().parent.parent

FITUR_LABELS = {
    "danceability": "Danceability",
    "energy": "Energy",
    "valence": "Valence",
    "acousticness": "Acousticness",
    "instrumentalness": "Instrumentalness",
}

FITUR_DESKRIPSI = {
    "danceability": "Seberapa cocok lagu untuk menari berdasarkan tempo, stabilitas ritme, dan kekuatan ketukan (0–1).",
    "energy": "Ukuran intensitas dan aktivitas perseptual lagu; lagu cepat dan keras bernilai mendekati 1 (0–1).",
    "valence": "Positivitas musikal lagu; nilai tinggi terdengar lebih ceria/bahagia, rendah lebih murung/sedih (0–1).",
    "acousticness": "Tingkat kepercayaan bahwa lagu bersifat akustik tanpa banyak instrumen elektronik (0–1).",
    "instrumentalness": "Prediksi apakah lagu tidak memiliki vokal; nilai mendekati 1 berarti dominan instrumental (0–1).",
}

CLUSTER_COLORS = {
    "0": "#1DB954",
    "1": "#A7A7A7",
}

@st.cache_data(show_spinner=False)
def _muat_data_analisis(base_dir_str: str) -> dict[str, Any]:
    """Muat file evaluasi CSV dan konfigurasi model untuk halaman analisis."""
    root = Path(base_dir_str)
    eval_csv_path = root / "data" / "evaluasi_perbandingan.csv"
    config_path = root / "models" / "model_config.json"

    df_eval_k = (
        pd.read_csv(eval_csv_path, encoding="utf-8")
        if eval_csv_path.exists()
        else pd.DataFrame()
    )
    with open(config_path, "r", encoding="utf-8") as f:
        model_config = json.load(f)

    return {
        "df_eval_k": df_eval_k,
        "model_config": model_config,
    }


@st.cache_data(show_spinner="Menghitung proyeksi PCA 2D...")
def _hitung_pca_sample(
    _katalog: pd.DataFrame,
    _scaler: Any,
    _kmeans_model: Any,
    fitur_final: list[str],
    nama_cluster_km: dict[int, str],
    nama_cluster_bi: dict[int, str],
    sample_size: int,
) -> tuple[pd.DataFrame, list[float], pd.DataFrame]:
    """Proyeksikan sampel katalog lagu dan centroid K-Means ke ruang PCA 2D."""
    n_ambil = min(sample_size, len(_katalog))
    sampel = _katalog.sample(n=n_ambil, random_state=42).reset_index(drop=True)
    x_scaled = _scaler.transform(sampel[fitur_final])

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(x_scaled)
    var_ratio = [float(v * 100.0) for v in pca.explained_variance_ratio_]

    df_pca = pd.DataFrame(
        {
            "PCA 1": coords[:, 0],
            "PCA 2": coords[:, 1],
            "track_name": sampel["track_name"].astype(str),
            "artists": sampel["artists"].astype(str),
            "genre_gabungan": sampel["genre_gabungan"].astype(str),
            "cluster_kmeans": sampel["cluster_kmeans"].astype(str),
            "label_kmeans": sampel["cluster_kmeans"].map(
                lambda c: f"Cluster {c} · {nama_cluster_km.get(int(c), '')}"
            ),
            "cluster_birch": sampel["cluster_birch"].astype(str),
            "label_birch": sampel["cluster_birch"].map(
                lambda c: f"Cluster {c} · {nama_cluster_bi.get(int(c), '')}"
            ),
        }
    )

    centroid_coords = pca.transform(_kmeans_model.cluster_centers_)
    df_centroid = pd.DataFrame(
        {
            "PCA 1": centroid_coords[:, 0],
            "PCA 2": centroid_coords[:, 1],
            "cluster": [f"Centroid {i}" for i in range(len(centroid_coords))],
        }
    )
    return df_pca, var_ratio, df_centroid


@st.cache_data(show_spinner=False)
def _hitung_statistik_distribusi(_katalog: pd.DataFrame, fitur_final: list[str]) -> dict[str, Any]:
    """Hitung korelasi penuh dan bin histogram seluruh katalog + sampel box plot."""
    corr_matrix = _katalog[fitur_final].corr().round(3)

    hist_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for f in fitur_final:
        counts, bin_edges = np.histogram(_katalog[f].dropna().to_numpy(), bins=25, range=(0.0, 1.0))
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        hist_data[f] = (bin_centers, counts)

    sampel_box = _katalog.sample(n=min(10000, len(_katalog)), random_state=42).copy()
    return {
        "corr": corr_matrix,
        "hist": hist_data,
        "sampel_box": sampel_box,
    }


recommender = get_recommender()
artefak_analisis = _muat_data_analisis(str(BASE_DIR))
model_config = artefak_analisis["model_config"]
df_eval_k = artefak_analisis["df_eval_k"]
evaluasi = recommender.get_evaluasi()

katalog = recommender.katalog
fitur_final = recommender.fitur_final
profil_km = recommender.get_profil_cluster("kmeans")
profil_bi = recommender.get_profil_cluster("birch")

# =============================================================================
# SECTION 1: OVERVIEW PENELITIAN
# =============================================================================
st.title("Analisis")
st.caption(
    "Halaman publik hasil penelitian Data Science TuneCluster — mengevaluasi pengelompokan "
    "89.741 lagu Spotify berdasarkan karakteristik audio menggunakan K-Means dan BIRCH."
)

col_m1, col_m2 = st.columns(2)
col_m1.metric(
    "Total lagu unik",
    f"{len(katalog):,}",
    help="Hasil deduplikasi track_id dari 114.000 baris",
)
col_m2.metric(
    "Sampel pelatihan",
    f"{model_config.get('sample_size_train', 15000):,}",
    help="Sampel tetap (seed=42)",
)
col_m3, col_m4 = st.columns(2)
col_m3.metric("Genre unik", f"{len(recommender.get_daftar_genre())}")
col_m4.metric("Fitur / K", f"{len(fitur_final)} / {evaluasi['k_final']}")

with st.container(border=True):
    st.markdown("#### Metodologi CRISP-DM")
    tahap_crisp = [
        ("1. Business Understanding", "Merumuskan masalah eksplorasi playlist berbasis audio, genre, aktivitas, dan mood."),
        ("2. Data Understanding", "Mengaudit 114.000 baris dataset Spotify (89.741 lagu unik, 114 genre) & sebaran fitur."),
        ("3. Data Preparation", "Deduplikasi track_id, penggabungan multi-genre, pembersihan nilai kosong, & StandardScaler."),
        ("4. Modeling", "Membandingkan K-Means vs BIRCH pada variasi K (2–8), scaler (Standard vs MinMax), & fitur (9 vs 5)."),
        ("5. Evaluation", "Mengukur kualitas internal (Silhouette, DBI, CH), waktu training, serta stabilitas antar-seed (ARI)."),
        ("6. Deployment", "Mengekspor model K-Means final & katalog terklaster ke aplikasi web Streamlit interaktif."),
    ]
    cols_crisp = st.columns(2)
    for i, (judul_t, desk_t) in enumerate(tahap_crisp):
        with cols_crisp[i % len(cols_crisp)]:
            st.markdown(
                dedent(f"""
                <div class="crisp-card" style="margin-bottom:0.65rem;">
                    <div style="font-weight:700; color:#1DB954; font-size:0.92rem;">{judul_t}</div>
                    <div style="font-size:0.82rem; color:#D5D5D5; margin-top:0.25rem;">{desk_t}</div>
                </div>
                """).strip(),
                unsafe_allow_html=True,
            )

with st.expander("5 fitur audio yang digunakan model final", expanded=False):
    df_fitur_info = pd.DataFrame(
        [
            {"Fitur": f, "Label": FITUR_LABELS[f], "Rentang": "0.0 – 1.0", "Deskripsi": FITUR_DESKRIPSI[f]}
            for f in fitur_final
        ]
    )
    st.dataframe(df_fitur_info, width="stretch", hide_index=True)

st.divider()

# =============================================================================
# SECTION 2: PERBANDINGAN METRIK EVALUASI
# =============================================================================
st.subheader("Perbandingan metrik evaluasi K-Means vs BIRCH")

km_eval = evaluasi["kmeans"]
bi_eval = evaluasi["birch"]

df_tabel_eval = pd.DataFrame(
    [
        {
            "Algoritma": "K-Means",
            "Silhouette Score (↑)": round(float(km_eval["silhouette"]), 4),
            "Davies-Bouldin Index (↓)": round(float(km_eval["davies_bouldin"]), 4),
            "Calinski-Harabasz Index (↑)": round(float(km_eval["calinski_harabasz"]), 2),
            "ARI Stabilitas (↑)": round(float(km_eval["ari_mean"]), 4),
            "Waktu Training (detik, ↓)": round(float(km_eval["waktu_training_detik"]), 4),
        },
        {
            "Algoritma": "BIRCH",
            "Silhouette Score (↑)": round(float(bi_eval["silhouette"]), 4),
            "Davies-Bouldin Index (↓)": round(float(bi_eval["davies_bouldin"]), 4),
            "Calinski-Harabasz Index (↑)": round(float(bi_eval["calinski_harabasz"]), 2),
            "ARI Stabilitas (↑)": round(float(bi_eval["ari_mean"]), 4),
            "Waktu Training (detik, ↓)": round(float(bi_eval["waktu_training_detik"]), 4),
        },
    ]
)

st.markdown(f"##### Tabel perbandingan model final (K = {evaluasi['k_final']}, 5 fitur audio, StandardScaler)")
st.dataframe(df_tabel_eval, width="stretch", hide_index=True)

# Bar Chart Side-by-Side untuk setiap metrik (subplot agar skala proporsional per metrik)
metrik_specs = [
    ("Silhouette Score (↑)", "silhouette", ".4f"),
    ("Davies-Bouldin Index (↓)", "davies_bouldin", ".4f"),
    ("Calinski-Harabasz Index (↑)", "calinski_harabasz", ".1f"),
    ("ARI Stabilitas (↑)", "ari_mean", ".4f"),
    ("Waktu Training (detik ↓)", "waktu_training_detik", ".4f"),
]

fig_bars = make_subplots(
    rows=1,
    cols=5,
    subplot_titles=[m[0] for m in metrik_specs],
    horizontal_spacing=0.06,
)
for col_idx, (judul_m, key_m, fmt_m) in enumerate(metrik_specs, start=1):
    val_km = float(km_eval[key_m])
    val_bi = float(bi_eval[key_m])
    fig_bars.add_trace(
        go.Bar(
            x=["K-Means", "BIRCH"],
            y=[val_km, val_bi],
            marker_color=["#1DB954", "#A7A7A7"],
            text=[format(val_km, fmt_m), format(val_bi, fmt_m)],
            textposition="outside",
            showlegend=False,
            hovertemplate="%{x}: %{y:" + fmt_m + "}<extra>" + judul_m + "</extra>",
        ),
        row=1,
        col=col_idx,
    )
    ymax = max(val_km, val_bi) * 1.25 if max(val_km, val_bi) > 0 else 1.0
    fig_bars.update_yaxes(range=[0, ymax], row=1, col=col_idx, gridcolor="#2A2A2A")

fig_bars.update_layout(
    title="Perbandingan Side-by-Side Metrik Evaluasi (K-Means vs BIRCH, K=2, 5 Fitur)",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#181818",
    font=dict(color="#FFFFFF"),
    height=360,
    margin=dict(l=20, r=20, t=65, b=25),
)
st.plotly_chart(fig_bars, width="stretch")

# Interpretasi otomatis berdasarkan angka aktual
sil_km, sil_bi = float(km_eval["silhouette"]), float(bi_eval["silhouette"])
dbi_km, dbi_bi = float(km_eval["davies_bouldin"]), float(bi_eval["davies_bouldin"])
ch_km, ch_bi = float(km_eval["calinski_harabasz"]), float(bi_eval["calinski_harabasz"])
ari_km, ari_bi = float(km_eval["ari_mean"]), float(bi_eval["ari_mean"])
t_km, t_bi = float(km_eval["waktu_training_detik"]), float(bi_eval["waktu_training_detik"])

interp_lines: list[str] = []
if sil_km >= sil_bi:
    interp_lines.append(
        f"- **Silhouette Score**: K-Means unggul (**{sil_km:.4f}** vs **{sil_bi:.4f}**), menandakan cluster rata-rata lebih kohesif."
    )
else:
    interp_lines.append(
        f"- **Silhouette Score**: BIRCH lebih tinggi (**{sil_bi:.4f}** vs **{sil_km:.4f}**), karena BIRCH memisahkan sebagian kecil lagu sangat akustik/instrumental ke cluster tersendiri ({profil_bi.loc[1, 'persentase']:.1f}% katalog)."
    )

if dbi_km <= dbi_bi:
    interp_lines.append(
        f"- **Davies-Bouldin Index (DBI)**: K-Means lebih rendah/baik (**{dbi_km:.4f}** vs **{dbi_bi:.4f}**), menunjukkan tumpang-tindih antar-cluster lebih kecil."
    )
else:
    interp_lines.append(
        f"- **Davies-Bouldin Index (DBI)**: BIRCH lebih rendah/baik (**{dbi_bi:.4f}** vs **{dbi_km:.4f}**), dipengaruhi ukuran cluster minoritas BIRCH yang padat."
    )

if ch_km >= ch_bi:
    interp_lines.append(
        f"- **Calinski-Harabasz Index (CH)**: K-Means jauh lebih tinggi (**{ch_km:.2f}** vs **{ch_bi:.2f}**), menunjukkan rasio pemisahan antar-cluster terhadap keragaman dalam-cluster lebih optimal."
    )
else:
    interp_lines.append(
        f"- **Calinski-Harabasz Index (CH)**: BIRCH lebih tinggi (**{ch_bi:.2f}** vs **{ch_km:.2f}**)."
    )

if ari_km >= ari_bi:
    interp_lines.append(
        f"- **Stabilitas Antar-Seed (ARI)**: K-Means sangat konsisten (**{ari_km:.4f}** vs **{ari_bi:.4f}**), sehingga pengelompokan hampir tidak berubah meski sampel latih diacak ulang."
    )
else:
    interp_lines.append(
        f"- **Stabilitas Antar-Seed (ARI)**: BIRCH lebih stabil (**{ari_bi:.4f}** vs **{ari_km:.4f}**)."
    )

if t_km <= t_bi:
    interp_lines.append(
        f"- **Waktu Training**: K-Means lebih cepat (**{t_km:.4f} detik** vs **{t_bi:.4f} detik**) pada 15.000 sampel latih."
    )
else:
    interp_lines.append(
        f"- **Waktu Training**: BIRCH lebih cepat (**{t_bi:.4f} detik** vs **{t_km:.4f} detik**)."
    )

st.markdown("#####  Interpretasi Otomatis & Kesimpulan")
interp_html = "<br>".join(
    re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line) for line in interp_lines
)
st.markdown(f"<div class='insight-box'>{interp_html}</div>", unsafe_allow_html=True)
st.success(
    f"**Kesimpulan Keseluruhan:** **K-Means (K={evaluasi['k_final']}, 5 fitur)** dipilih sebagai model utama "
    f"TuneCluster. Meskipun BIRCH memperoleh Silhouette lebih tinggi pada 5 fitur ({sil_bi:.4f}), partisi BIRCH "
    f"tidak stabil antar-seed (ARI hanya {ari_bi:.4f}) dan sangat timpang ({profil_bi.loc[0, 'persentase']:.1f}% vs {profil_bi.loc[1, 'persentase']:.1f}%). "
    f"Sebaliknya, K-Means sangat stabil (ARI {ari_km:.4f}), lebih cepat ({t_km:.4f} s), memiliki CH tertinggi ({ch_km:.2f}), "
    f"dan membagi katalog secara seimbang ({profil_km.loc[0, 'persentase']:.1f}% vs {profil_km.loc[1, 'persentase']:.1f}%)."
)

# Tambahan: Tren variasi K=2..8 dan eksperimen scaler/fitur
if not df_eval_k.empty:
    with st.expander("Eksperimen variasi K, scaler, dan fitur (notebook)", expanded=False):
        tab_k, tab_sf = st.tabs(["Tren metrik K = 2..8", "Perbandingan scaler dan fitur"])
        with tab_k:
            metrik_pilih = st.selectbox(
                "Pilih metrik untuk grafik K=2..8",
                options=["Silhouette", "DBI", "CH", "ARI", "Waktu Training (s)"],
                key="analisis_k_metric",
            )
            fig_k = px.line(
                df_eval_k,
                x="K",
                y=metrik_pilih,
                color="Algoritma",
                markers=True,
                color_discrete_map={"K-Means": "#1DB954", "BIRCH": "#A7A7A7"},
                title=f"Perbandingan {metrik_pilih} untuk K = 2 sampai 8",
            )
            fig_k.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#181818",
                font=dict(color="#FFFFFF"),
                xaxis=dict(dtick=1, gridcolor="#2A2A2A"),
                yaxis=dict(gridcolor="#2A2A2A"),
                height=340,
            )
            st.plotly_chart(fig_k, width="stretch")
            st.dataframe(df_eval_k.round(4), width="stretch", hide_index=True)

        with tab_sf:
            eksp = evaluasi.get("eksperimen_tambahan", {})
            c_sc, c_ft = st.columns(2)
            with c_sc:
                st.markdown("**StandardScaler vs MinMaxScaler (K=2, 9 Fitur)**")
                df_sc = pd.DataFrame(eksp.get("perbandingan_scaler", []))
                if not df_sc.empty:
                    st.dataframe(df_sc.round(4), width="stretch", hide_index=True)
            with c_ft:
                st.markdown("**9 Fitur vs 5 Fitur (K=2, StandardScaler)**")
                df_ft = pd.DataFrame(eksp.get("perbandingan_fitur", []))
                if not df_ft.empty:
                    st.dataframe(df_ft.round(4), width="stretch", hide_index=True)

st.divider()

# =============================================================================
# SECTION 3: VISUALISASI CLUSTER (PCA 2D INTERAKTIF)
# =============================================================================
st.subheader("Visualisasi cluster dengan PCA 2D")

col_pca_opt1, col_pca_opt2 = st.columns([1.2, 1])
with col_pca_opt1:
    algo_pca = st.radio(
        "Pilih hasil clustering yang ditampilkan",
        options=["K-Means", "BIRCH"],
        horizontal=True,
        key="pca_algo_toggle",
    )
with col_pca_opt2:
    n_sampel_pca = st.slider(
        "Jumlah sampel lagu pada scatter plot",
        min_value=1000,
        max_value=5000,
        value=3000,
        step=500,
        key="pca_sample_slider",
    )

df_pca, var_pca, df_centroid = _hitung_pca_sample(
    katalog,
    recommender.scaler,
    recommender.kmeans_model,
    fitur_final,
    recommender.nama_cluster_map["kmeans"],
    recommender.nama_cluster_map["birch"],
    n_sampel_pca,
)

kolom_label_pca = "label_kmeans" if algo_pca == "K-Means" else "label_birch"
palette_pca = {}
for lbl in sorted(df_pca[kolom_label_pca].unique()):
    palette_pca[lbl] = "#1DB954" if lbl.startswith("Cluster 0") else "#A7A7A7"

fig_pca = px.scatter(
    df_pca,
    x="PCA 1",
    y="PCA 2",
    color=kolom_label_pca,
    color_discrete_map=palette_pca,
    hover_name="track_name",
    hover_data={
        "artists": True,
        "genre_gabungan": True,
        "PCA 1": ":.2f",
        "PCA 2": ":.2f",
        kolom_label_pca: False,
    },
    labels={
        "PCA 1": f"PCA 1 ({var_pca[0]:.1f}% variansi)",
        "PCA 2": f"PCA 2 ({var_pca[1]:.1f}% variansi)",
        kolom_label_pca: "Cluster",
        "artists": "Artis",
        "genre_gabungan": "Genre",
    },
    title=f"Proyeksi PCA 2D ({n_sampel_pca:,} Sampel Lagu · {algo_pca})",
    opacity=0.72,
)
fig_pca.update_traces(marker=dict(size=6))

if algo_pca == "K-Means":
    fig_pca.add_trace(
        go.Scatter(
            x=df_centroid["PCA 1"],
            y=df_centroid["PCA 2"],
            mode="markers+text",
            text=df_centroid["cluster"],
            textposition="top center",
            textfont=dict(color="#FFFFFF", size=12),
            marker=dict(
                symbol="x",
                size=14,
                color="#FFFFFF",
                line=dict(width=2, color="#121212"),
            ),
            name="Centroid K-Means",
        )
    )

fig_pca.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#181818",
    font=dict(color="#FFFFFF"),
    xaxis=dict(gridcolor="#2A2A2A", zerolinecolor="#3A3A3A"),
    yaxis=dict(gridcolor="#2A2A2A", zerolinecolor="#3A3A3A"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=480,
)
st.plotly_chart(fig_pca, width="stretch")

st.divider()

# =============================================================================
# SECTION 4: PROFIL CLUSTER (RADAR CHART & HEATMAP)
# =============================================================================
st.subheader("Profil audio setiap cluster")

algo_profil_pilihan = st.radio(
    "Tampilkan profil cluster untuk algoritma",
    options=["K-Means", "BIRCH"],
    horizontal=True,
    key="profil_algo_radio",
)
profil_aktif = profil_km if algo_profil_pilihan == "K-Means" else profil_bi

col_rad, col_heat = st.columns(2)

with col_rad:
    fig_radar_profil = go.Figure()
    kategori = [FITUR_LABELS[f] for f in fitur_final]
    kategori_closed = kategori + [kategori[0]]
    warna_cluster_list = [("#1DB954", "rgba(29, 185, 84, 0.25)"), ("#A7A7A7", "rgba(167, 167, 167, 0.16)")]

    for idx_c, row_c in profil_aktif.iterrows():
        vals = [float(row_c[f]) for f in fitur_final]
        vals_closed = vals + [vals[0]]
        line_c, fill_c = warna_cluster_list[int(idx_c) % len(warna_cluster_list)]
        fig_radar_profil.add_trace(
            go.Scatterpolar(
                r=vals_closed,
                theta=kategori_closed,
                fill="toself",
                name=f"Cluster {idx_c} · {row_c['nama_cluster']}",
                line=dict(color=line_c, width=2.5),
                fillcolor=fill_c,
            )
        )

    fig_radar_profil.update_layout(
        title=f"Radar Chart Profil Audio ({algo_profil_pilihan})",
        polar=dict(
            bgcolor="#181818",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#2E2E2E", tickfont=dict(color="#A0A0A0")),
            angularaxis=dict(gridcolor="#2E2E2E", tickfont=dict(color="#FFFFFF")),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        height=400,
    )
    st.plotly_chart(fig_radar_profil, width="stretch")

with col_heat:
    z_vals = profil_aktif[fitur_final].to_numpy()
    y_labels = [f"Cluster {idx_c} ({row_c['nama_cluster']})" for idx_c, row_c in profil_aktif.iterrows()]
    x_labels = [FITUR_LABELS[f] for f in fitur_final]

    fig_heat_profil = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=x_labels,
            y=y_labels,
            colorscale=[[0.0, "#2A2A2A"], [0.5, "#666666"], [1.0, "#1DB954"]],
            zmin=0.0,
            zmax=1.0,
            text=np.round(z_vals, 3),
            texttemplate="%{text:.3f}",
            textfont=dict(color="#FFFFFF", size=13),
            hovertemplate="Cluster: %{y}<br>Fitur: %{x}<br>Rata-rata: %{z:.3f}<extra></extra>",
        )
    )
    fig_heat_profil.update_layout(
        title=f"Heatmap Rata-Rata 5 Fitur Audio ({algo_profil_pilihan})",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#181818",
        font=dict(color="#FFFFFF"),
        height=400,
    )
    st.plotly_chart(fig_heat_profil, width="stretch")

# Interpretasi karakter setiap cluster
st.markdown("##### Interpretasi karakter cluster")
cols_interp = st.columns(len(profil_aktif))
for col_i, (idx_c, row_c) in zip(cols_interp, profil_aktif.iterrows()):
    fitur_tinggi = [
        f"{FITUR_LABELS[f]} ({row_c[f]:.3f})"
        for f in fitur_final
        if float(row_c[f]) >= 0.50
    ]
    fitur_rendah = [
        f"{FITUR_LABELS[f]} ({row_c[f]:.3f})"
        for f in fitur_final
        if float(row_c[f]) < 0.35
    ]
    ringkas_tinggi = ", ".join(fitur_tinggi) if fitur_tinggi else "nilai seimbang di semua fitur"
    ringkas_rendah = ", ".join(fitur_rendah) if fitur_rendah else "-"
    with col_i:
        st.markdown(
            dedent(f"""
            <div class="insight-box">
                <div style="font-size:1.05rem; font-weight:700; color:#1DB954;">
                    Cluster {idx_c} — {row_c['nama_cluster']}
                </div>
                <div style="font-size:0.86rem; color:#B3B3B3; margin:0.2rem 0 0.5rem 0;">
                    {int(row_c['jumlah_lagu']):,} lagu ({row_c['persentase']:.2f}% katalog)
                </div>
                <div style="font-size:0.88rem; color:#E0E0E0; line-height:1.5;">
                    <b>Ciri dominan (≥ 0.50):</b> {ringkas_tinggi}<br>
                    <b>Fitur bernilai rendah (&lt; 0.35):</b> {ringkas_rendah}
                </div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )

st.divider()

# =============================================================================
# SECTION 5: DISTRIBUSI DATA
# =============================================================================
st.subheader("Distribusi fitur audio dan korelasi")

stats_dist = _hitung_statistik_distribusi(katalog, fitur_final)

tab_hist, tab_corr, tab_box = st.tabs(
    ["Histogram fitur audio", "Matriks korelasi", "Box plot per cluster"]
)

with tab_hist:
    fig_hist = make_subplots(
        rows=2,
        cols=3,
        subplot_titles=[FITUR_LABELS[f] for f in fitur_final] + [""],
        vertical_spacing=0.16,
        horizontal_spacing=0.07,
    )
    for i, f in enumerate(fitur_final):
        r = (i // 3) + 1
        c = (i % 3) + 1
        centers, counts = stats_dist["hist"][f]
        fig_hist.add_trace(
            go.Bar(
                x=centers,
                y=counts,
                marker_color="#1DB954",
                name=FITUR_LABELS[f],
                showlegend=False,
                hovertemplate=f"{FITUR_LABELS[f]}: %{{x:.2f}}<br>Jumlah Lagu: %{{y:,}}<extra></extra>",
            ),
            row=r,
            col=c,
        )
        fig_hist.update_xaxes(range=[0, 1], gridcolor="#2A2A2A", row=r, col=c)
        fig_hist.update_yaxes(gridcolor="#2A2A2A", row=r, col=c)

    fig_hist.update_layout(
        title=f"Distribusi 5 Fitur Audio pada Seluruh {len(katalog):,} Lagu Unik",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#181818",
        font=dict(color="#FFFFFF"),
        height=520,
    )
    st.plotly_chart(fig_hist, width="stretch")

with tab_corr:
    corr_df = stats_dist["corr"]
    labels_corr = [FITUR_LABELS[f] for f in fitur_final]
    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corr_df.to_numpy(),
            x=labels_corr,
            y=labels_corr,
            colorscale=[
                [0.0, "#2A2A2A"],
                [0.5, "#A7A7A7"],
                [1.0, "#1DB954"],
            ],
            zmid=0.0,
            zmin=-1.0,
            zmax=1.0,
            text=corr_df.to_numpy(),
            texttemplate="%{text:.2f}",
            textfont=dict(size=13),
            hovertemplate="%{y} × %{x}<br>Korelasi: %{z:.3f}<extra></extra>",
        )
    )
    fig_corr.update_layout(
        title="Matriks Korelasi Pearson Antar Fitur Audio",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#181818",
        font=dict(color="#FFFFFF"),
        height=460,
    )
    st.plotly_chart(fig_corr, width="stretch")

with tab_box:
    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        algo_box = st.radio(
            "Algoritma untuk Box Plot",
            options=["K-Means", "BIRCH"],
            horizontal=True,
            key="box_algo_radio",
        )
    with col_b2:
        fitur_box = st.selectbox(
            "Pilih fitur audio (atau lihat semua)",
            options=["Semua 5 Fitur"] + fitur_final,
            key="box_fitur_select",
        )

    sampel_box = stats_dist["sampel_box"]
    col_c_box = "cluster_kmeans" if algo_box == "K-Means" else "cluster_birch"
    nama_map_box = recommender.nama_cluster_map["kmeans" if algo_box == "K-Means" else "birch"]

    if fitur_box == "Semua 5 Fitur":
        df_melt = sampel_box.melt(
            id_vars=[col_c_box],
            value_vars=fitur_final,
            var_name="Fitur",
            value_name="Nilai",
        )
        df_melt["Fitur"] = df_melt["Fitur"].map(FITUR_LABELS)
        df_melt["Cluster"] = df_melt[col_c_box].map(lambda c: f"Cluster {c} · {nama_map_box.get(int(c), '')}")
        fig_box = px.box(
            df_melt,
            x="Fitur",
            y="Nilai",
            color="Cluster",
            color_discrete_sequence=["#1DB954", "#A7A7A7"],
            title=f"Perbandingan Sebaran Fitur Audio per Cluster ({algo_box}, Sampel 10.000 Lagu)",
        )
    else:
        df_sub = sampel_box[[col_c_box, fitur_box]].copy()
        df_sub["Cluster"] = df_sub[col_c_box].map(lambda c: f"Cluster {c} · {nama_map_box.get(int(c), '')}")
        fig_box = px.box(
            df_sub,
            x="Cluster",
            y=fitur_box,
            color="Cluster",
            color_discrete_sequence=["#1DB954", "#A7A7A7"],
            title=f"Distribusi {FITUR_LABELS[fitur_box]} per Cluster ({algo_box}, Sampel 10.000 Lagu)",
        )

    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#181818",
        font=dict(color="#FFFFFF"),
        yaxis=dict(range=[0, 1], gridcolor="#2A2A2A"),
        xaxis=dict(gridcolor="#2A2A2A"),
        height=440,
    )
    st.plotly_chart(fig_box, width="stretch")

st.divider()

# =============================================================================
# SECTION 6: PENJELASAN ALGORITMA & METRIK EVALUASI
# =============================================================================
st.subheader("Penjelasan algoritma dan metrik evaluasi")

with st.expander("Bagaimana cara kerja K-Means?", expanded=False):
    st.markdown(
        """
        **K-Means** adalah algoritma *partition-based clustering* yang membagi dataset menjadi **K** kelompok
        dengan meminimalkan jarak kuadrat tiap titik data terhadap pusat cluster (*centroid*).

        **Alur iteratif K-Means:**
        1. **Inisialisasi:** Memilih `K` titik pusat awal (*centroid*), pada proyek ini menggunakan `k-means++` dengan `n_init=10` dan `random_state=42`.
        2. **Assignment:** Setiap lagu ditetapkan ke *centroid* terdekat berdasarkan jarak Euclidean pada ruang fitur terstandarisasi.
        3. **Update Centroid:** Posisi setiap *centroid* dihitung ulang sebagai rata-rata (*mean*) seluruh lagu di cluster tersebut.
        4. **Konvergensi:** Langkah 2–3 diulang hingga keanggotaan cluster tidak berubah atau batas toleransi tercapai.
        """
    )
    # Ilustrasi sederhana konvergensi K-Means (2 cluster sintetis)
    fig_ilustrasi = go.Figure()
    fig_ilustrasi.add_trace(
        go.Scatter(
            x=[0.75, 0.82, 0.68, 0.79, 0.85],
            y=[0.72, 0.88, 0.77, 0.65, 0.80],
            mode="markers",
            name="Cluster 0 (Energik)",
            marker=dict(size=11, color="#1DB954"),
        )
    )
    fig_ilustrasi.add_trace(
        go.Scatter(
            x=[0.22, 0.30, 0.18, 0.25, 0.35],
            y=[0.28, 0.22, 0.34, 0.19, 0.30],
            mode="markers",
            name="Cluster 1 (Tenang/Akustik)",
            marker=dict(size=11, color="#A7A7A7"),
        )
    )
    fig_ilustrasi.add_trace(
        go.Scatter(
            x=[0.778, 0.260],
            y=[0.764, 0.266],
            mode="markers+text",
            text=["Centroid 0", "Centroid 1"],
            textposition="top center",
            name="Centroid",
            marker=dict(symbol="star", size=16, color="#FFFFFF"),
        )
    )
    fig_ilustrasi.update_layout(
        title="Ilustrasi Sederhana Pemisahan Cluster & Centroid K-Means",
        xaxis_title="Energy",
        yaxis_title="Danceability",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#181818",
        font=dict(color="#FFFFFF"),
        xaxis=dict(range=[0, 1], gridcolor="#2A2A2A"),
        yaxis=dict(range=[0, 1], gridcolor="#2A2A2A"),
        height=300,
    )
    st.plotly_chart(fig_ilustrasi, width="stretch")

with st.expander("Bagaimana cara kerja BIRCH dan CF-Tree?", expanded=False):
    st.markdown(
        f"""
        **BIRCH (*Balanced Iterative Reducing and Clustering using Hierarchies*)** dirancang untuk dataset besar
        dengan meringkas titik data menjadi simpul padat bernama **Clustering Feature (CF)** di dalam struktur **CF-Tree**.

        - **Clustering Feature (`CF = (N, LS, SS)`):** menyimpan jumlah titik (`N`), jumlah vektor linear (`LS`), dan jumlah kuadrat (`SS`) sehingga jarak dan radius subcluster dapat dihitung cepat tanpa menyimpan semua titik mentah.
        - **Parameter Utama:**
          - `threshold` (**{model_config.get('threshold_birch', 1.1368):.4f}** pada 5 fitur): radius maksimum subcluster dalam sebuah *leaf node*. Jika jarak titik baru melebihi ambang batas ini, dibuat subcluster baru.
          - `branching_factor` (**{model_config.get('branching_factor_birch', 50)}**): jumlah maksimum anak tiap node dalam CF-Tree.
        - **Tahap Akhir:** Subcluster pada daun CF-Tree kemudian digabungkan menjadi `K` cluster final menggunakan pengelompokan global (*agglomerative clustering*).
        - **Catatan Penelitian:** Karena bergantung pada ambang jarak `threshold` dan urutan pemadatan CF-Tree, BIRCH cenderung lebih sensitif terhadap sampel latih (`ARI = {bi_eval['ari_mean']:.4f}`) dan dapat membentuk cluster yang kurang seimbang pada data musik ini.
        """
    )

with st.expander("Penjelasan metrik evaluasi (Silhouette, DBI, CH, ARI)", expanded=False):
    st.markdown(
        """
        - **Silhouette Score (`-1` hingga `1`, lebih tinggi lebih baik):** Mengukur seberapa mirip suatu lagu dengan clusternya sendiri (*cohesion*) dibanding cluster terdekat lainnya (*separation*).
        - **Davies–Bouldin Index / DBI (`≥ 0`, lebih rendah lebih baik):** Mengukur rasio antara sebaran internal tiap cluster dengan jarak antar-centroid cluster. Nilai mendekati `0` berarti cluster padat dan terpisah tegas.
        - **Calinski–Harabasz Index / CH (`≥ 0`, lebih tinggi lebih baik):** Rasio variansi antar-cluster terhadap variansi di dalam cluster. Nilai besar menandakan cluster terdefinisi dengan baik.
        - **Adjusted Rand Index / ARI (`-1` hingga `1`, lebih tinggi lebih baik):** Mengukur kesepakatan/konsistensi hasil pengelompokan pada data uji yang sama saat model dilatih dengan sampel/seed berbeda (`11`, `42`, `99`), meski label nomor cluster tertukar. Nilai mendekati `1.0` menandakan model sangat stabil.
        """
    )

render_footer()

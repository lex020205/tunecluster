"""
export_models.py — Ekstraksi model clustering, scaler, konfigurasi, dan dataset katalog
dari logika inti notebook TuneCluster_TAS_SPOTIFY_Upgrade.ipynb (tanpa plotting).

Menghasilkan:
- models/kmeans_model.joblib
- models/birch_model.joblib
- models/scaler.joblib
- models/model_config.json
- data/katalog_lagu.csv
- data/genre_index.csv
- data/target_aktivitas.json
- data/evaluasi_perbandingan.csv
- data/profil_cluster.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import combinations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import Birch, KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Konstanta sesuai notebook TuneCluster_TAS_SPOTIFY_Upgrade.ipynb
SEED = 42
SAMPLE_SIZE = 15000
STABILITY_SEEDS = [11, 42, 99]
TEST_SAMPLE_SIZE = 1500
TEST_SEED = 2026

FITUR_9 = [
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
    "loudness",
    "tempo",
]

FITUR_FINAL = [
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
]

ALIAS_GENRE = {"r&b": "r-n-b"}

TARGET_AKTIVITAS = {
    "Olahraga": {
        "danceability": 0.78,
        "energy": 0.85,
        "valence": 0.65,
        "acousticness": 0.15,
        "instrumentalness": 0.12,
    },
    "Belajar": {
        "danceability": 0.42,
        "energy": 0.25,
        "valence": 0.42,
        "acousticness": 0.65,
        "instrumentalness": 0.70,
    },
    "Santai": {
        "danceability": 0.52,
        "energy": 0.35,
        "valence": 0.48,
        "acousticness": 0.70,
        "instrumentalness": 0.35,
    },
    "Perjalanan": {
        "danceability": 0.70,
        "energy": 0.67,
        "valence": 0.64,
        "acousticness": 0.30,
        "instrumentalness": 0.12,
    },
}

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"


def normalisasi_genre(nama: str) -> str:
    """Normalisasi ejaan genre ringan + alias eksplisit sesuai notebook."""
    standar = str(nama).strip().lower()
    return ALIAS_GENRE.get(standar, standar)


def cari_dataset(custom_path: str | None = None) -> Path:
    """Cari file spotify-tracks-dataset.csv atau .xlsx di lokasi umum."""
    if custom_path:
        p = Path(custom_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"File dataset tidak ditemukan di path: {p}")

    kandidat = [
        BASE_DIR / "spotify-tracks-dataset.csv",
        BASE_DIR / "spotify_tracks_dataset.csv",
        BASE_DIR / "spotify-tracks-dataset.xlsx",
        BASE_DIR / "spotify_tracks_dataset.xlsx",
        DATA_DIR / "spotify-tracks-dataset.csv",
        DATA_DIR / "spotify_tracks_dataset.csv",
        DATA_DIR / "spotify-tracks-dataset.xlsx",
        DATA_DIR / "spotify_tracks_dataset.xlsx",
        Path.home() / "Downloads" / "spotify-tracks-dataset.csv",
        Path.home() / "Downloads" / "spotify-tracks-dataset.xlsx",
    ]
    ditemukan = next((p for p in kandidat if p.exists()), None)
    if ditemukan is None:
        pesan = (
            "Dataset Spotify ('spotify-tracks-dataset.csv' atau '.xlsx') tidak ditemukan.\n"
            "Silakan unduh dari Kaggle:\n"
            "  https://www.kaggle.com/datasets/yashdev01/spotify-tracks-dataset\n"
            f"Lalu letakkan file di folder:\n  {BASE_DIR / 'spotify-tracks-dataset.csv'}\n"
            f"atau:\n  {DATA_DIR / 'spotify-tracks-dataset.csv'}"
        )
        raise FileNotFoundError(pesan)
    return ditemukan


def muat_dan_bersihkan_data(file_path: Path) -> pd.DataFrame:
    """Baca dataset Spotify dan terapkan preprocessing persis sesuai Cell 7 notebook."""
    print(f"[1/6] Membaca dataset: {file_path}")
    if file_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, encoding="utf-8")

    print(f"      Ukuran mentah: {df.shape[0]:,} baris x {df.shape[1]} kolom")

    kolom_wajib = set(FITUR_9 + ["track_id", "track_genre", "popularity"])
    hilang = kolom_wajib - set(df.columns)
    if hilang:
        raise ValueError(f"Kolom wajib hilang dari dataset: {sorted(hilang)}")

    # Hapus kolom indeks yang tidak diperlukan (Unnamed: 0.1, Unnamed: 0)
    kolom_drop = [c for c in ["Unnamed: 0.1", "Unnamed: 0"] if c in df.columns]
    data = df.drop(columns=kolom_drop).copy()

    # Simpan seluruh genre untuk setiap lagu
    genre_gabungan = data.groupby("track_id")["track_genre"].agg(
        lambda x: " | ".join(sorted(set(x.dropna().astype(str))))
    )

    # Ringkas popularity untuk ID lagu yang sama
    popularitas_median = data.groupby("track_id")["popularity"].median()

    # Ambil satu baris untuk setiap lagu
    data_bersih = data.drop_duplicates(subset="track_id", keep="first").copy()

    # Masukkan kembali genre gabungan dan popularity
    data_bersih["genre_gabungan"] = data_bersih["track_id"].map(genre_gabungan)
    data_bersih["popularity"] = data_bersih["track_id"].map(popularitas_median)

    # Tangani nama lagu atau artis yang kosong
    for kolom in ["track_name", "artists", "album_name"]:
        if kolom in data_bersih.columns:
            data_bersih[kolom] = data_bersih[kolom].fillna("Tidak diketahui")

    # Pastikan fitur audio tersedia
    data_bersih = data_bersih.dropna(subset=FITUR_9).reset_index(drop=True)
    print(f"      Sesudah cleaning (lagu unik): {len(data_bersih):,} baris")
    return data_bersih


def hitung_threshold_birch(X_scaled: np.ndarray, seed: int = SEED) -> float:
    """Hitung threshold BIRCH = 0.4 * median jarak Euclidean antar 2000 pasangan acak."""
    rng = np.random.default_rng(seed)
    a = rng.integers(0, len(X_scaled), 2000)
    b = rng.integers(0, len(X_scaled), 2000)
    median_jarak = float(np.median(np.linalg.norm(X_scaled[a] - X_scaled[b], axis=1)))
    return 0.4 * median_jarak


def evaluasi_clustering(X: np.ndarray, labels: np.ndarray, seed: int = SEED) -> dict:
    """Hitung Silhouette (sampel tetap max 1800), DBI, dan Calinski-Harabasz."""
    jumlah_cluster = len(np.unique(labels))
    if jumlah_cluster < 2:
        return {
            "silhouette": np.nan,
            "davies_bouldin": np.nan,
            "calinski_harabasz": np.nan,
        }

    rng = np.random.default_rng(seed)
    indeks = rng.choice(len(X), size=min(1800, len(X)), replace=False)
    X_eval = X[indeks]
    label_eval = labels[indeks]

    if len(np.unique(label_eval)) < 2:
        silhouette = np.nan
    else:
        silhouette = float(silhouette_score(X_eval, label_eval))

    return {
        "silhouette": silhouette,
        "davies_bouldin": float(davies_bouldin_score(X, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
    }


def uji_stabilitas_ari(
    data_bersih: pd.DataFrame,
    fitur: list[str],
    n_clusters: int,
    seeds: list[int] = STABILITY_SEEDS,
) -> dict:
    """Hitung rata-rata ARI stabilitas antar seed pada data uji tetap (Cell 32)."""
    data_uji = data_bersih.sample(
        n=min(TEST_SAMPLE_SIZE, len(data_bersih)),
        random_state=TEST_SEED,
    )
    data_pool = data_bersih.drop(data_uji.index)
    n_latih = min(SAMPLE_SIZE, len(data_pool))

    prediksi_map: dict[str, list[np.ndarray]] = {"K-Means": [], "BIRCH": []}
    silhouette_test_map: dict[str, list[float]] = {"K-Means": [], "BIRCH": []}

    for s in seeds:
        latih = data_pool.sample(n=n_latih, random_state=s)
        scaler_uji = StandardScaler()
        X_train = scaler_uji.fit_transform(latih[fitur])
        X_test = scaler_uji.transform(data_uji[fitur])
        thresh = hitung_threshold_birch(X_train, seed=s)

        model_km = KMeans(n_clusters=n_clusters, n_init=10, random_state=s)
        model_bi = Birch(n_clusters=n_clusters, threshold=thresh, branching_factor=50)
        model_km.fit(X_train)
        model_bi.fit(X_train)

        for nama, model in [("K-Means", model_km), ("BIRCH", model_bi)]:
            labels_test = model.predict(X_test)
            prediksi_map[nama].append(labels_test)
            if len(np.unique(labels_test)) >= 2:
                sil = float(silhouette_score(X_test, labels_test))
            else:
                sil = np.nan
            silhouette_test_map[nama].append(sil)

    hasil = {}
    for nama in ["K-Means", "BIRCH"]:
        preds = prediksi_map[nama]
        skor_ari = [
            float(adjusted_rand_score(preds[i], preds[j]))
            for i, j in combinations(range(len(preds)), 2)
        ]
        hasil[nama] = {
            "ari_pairwise": [round(x, 6) for x in skor_ari],
            "ari_mean": float(np.mean(skor_ari)),
            "silhouette_test_per_seed": {
                str(s): (None if np.isnan(v) else round(v, 6))
                for s, v in zip(seeds, silhouette_test_map[nama])
            },
        }
    return hasil


def eksperimen_pemilihan_k(data_bersih: pd.DataFrame, data_latih: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    """Jalankan eksperimen variasi K=2..8 pada 9 fitur sesuai Cell 16, 18, dan ARI."""
    print("[2/6] Menjalankan eksperimen pemilihan K (K=2..8) pada 9 fitur...")
    X_scaled_9 = StandardScaler().fit_transform(data_latih[FITUR_9])
    threshold_9 = hitung_threshold_birch(X_scaled_9, seed=SEED)

    baris_eval = []
    for k in range(2, 9):
        stabilitas_k = uji_stabilitas_ari(data_bersih, FITUR_9, k)

        # K-Means
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED)
        t0 = time.perf_counter()
        label_km = km.fit_predict(X_scaled_9)
        waktu_km = time.perf_counter() - t0
        skor_km = evaluasi_clustering(X_scaled_9, label_km)
        baris_eval.append(
            {
                "Algoritma": "K-Means",
                "K": k,
                "Cluster Terbentuk": int(len(np.unique(label_km))),
                "Inertia": float(km.inertia_),
                "Silhouette": skor_km["silhouette"],
                "DBI": skor_km["davies_bouldin"],
                "CH": skor_km["calinski_harabasz"],
                "ARI": stabilitas_k["K-Means"]["ari_mean"],
                "Waktu Training (s)": waktu_km,
            }
        )

        # BIRCH
        bi = Birch(n_clusters=k, threshold=threshold_9, branching_factor=50)
        t0 = time.perf_counter()
        label_bi = bi.fit_predict(X_scaled_9)
        waktu_bi = time.perf_counter() - t0
        skor_bi = evaluasi_clustering(X_scaled_9, label_bi)
        baris_eval.append(
            {
                "Algoritma": "BIRCH",
                "K": k,
                "Cluster Terbentuk": int(len(np.unique(label_bi))),
                "Inertia": np.nan,
                "Silhouette": skor_bi["silhouette"],
                "DBI": skor_bi["davies_bouldin"],
                "CH": skor_bi["calinski_harabasz"],
                "ARI": stabilitas_k["BIRCH"]["ari_mean"],
                "Waktu Training (s)": waktu_bi,
            }
        )

    evaluasi_df = pd.DataFrame(baris_eval)

    # Pilih K_FINAL sesuai Cell 18
    valid = evaluasi_df[evaluasi_df["Cluster Terbentuk"] == evaluasi_df["K"]].dropna(
        subset=["Silhouette"]
    )
    ringkasan_k = valid.groupby("K").agg(
        rata_silhouette=("Silhouette", "mean"),
        jumlah_model=("Algoritma", "nunique"),
    )
    ringkasan_k = ringkasan_k[ringkasan_k["jumlah_model"] == 2]
    if ringkasan_k.empty:
        raise ValueError("Tidak ada nilai K yang valid untuk kedua model.")

    k_final = int(ringkasan_k["rata_silhouette"].idxmax())
    print(f"      K_FINAL terpilih: {k_final}")
    return k_final, evaluasi_df


def eksperimen_scaling_dan_fitur(data_latih: pd.DataFrame, k_final: int) -> dict:
    """Jalankan eksperimen perbandingan scaler & 9 vs 5 fitur (Cell 19 & 20)."""
    hasil_scaling = []
    for nama_scaler, scaler_uji in [("StandardScaler", StandardScaler()), ("MinMaxScaler", MinMaxScaler())]:
        X_uji = scaler_uji.fit_transform(data_latih[FITUR_9])
        thresh = hitung_threshold_birch(X_uji, seed=SEED)
        for nama_algo in ["K-Means", "BIRCH"]:
            if nama_algo == "K-Means":
                model = KMeans(n_clusters=k_final, n_init=10, random_state=SEED)
            else:
                model = Birch(n_clusters=k_final, threshold=thresh, branching_factor=50)
            labels = model.fit_predict(X_uji)
            skor = evaluasi_clustering(X_uji, labels)
            hasil_scaling.append({"Scaler": nama_scaler, "Algoritma": nama_algo, **skor})

    hasil_fitur = []
    for nama_fitur, daftar_fitur in [("9 Fitur", FITUR_9), ("5 Fitur", FITUR_FINAL)]:
        X_uji = StandardScaler().fit_transform(data_latih[daftar_fitur])
        thresh = hitung_threshold_birch(X_uji, seed=SEED)
        for nama_algo in ["K-Means", "BIRCH"]:
            if nama_algo == "K-Means":
                model = KMeans(n_clusters=k_final, n_init=10, random_state=SEED)
            else:
                model = Birch(n_clusters=k_final, threshold=thresh, branching_factor=50)
            labels = model.fit_predict(X_uji)
            skor = evaluasi_clustering(X_uji, labels)
            hasil_fitur.append({"Fitur": nama_fitur, "Algoritma": nama_algo, **skor})

    return {"perbandingan_scaler": hasil_scaling, "perbandingan_fitur": hasil_fitur}


def tentukan_nama_cluster(profil_df: pd.DataFrame) -> dict[int, str]:
    """Tentukan mapping nama cluster berdasarkan profil fitur (tidak sekadar asumsi label 0/1)."""
    if len(profil_df) == 2:
        urut_energy = profil_df["energy"].sort_values(ascending=False).index.tolist()
        return {
            int(urut_energy[0]): "Cenderung Energik",
            int(urut_energy[1]): "Cenderung Tenang dan Akustik",
        }
    return {int(idx): f"Cluster {idx}" for idx in profil_df.index}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ekstrak model & katalog lagu TuneCluster dari logika notebook."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path opsional ke file spotify-tracks-dataset.csv atau .xlsx",
    )
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    dataset_path = cari_dataset(args.input)
    data_bersih = muat_dan_bersihkan_data(dataset_path)

    # Sampel pelatihan tetap 15.000 lagu (Cell 12 & Cell 34)
    n_train = min(SAMPLE_SIZE, len(data_bersih))
    data_latih = data_bersih.sample(n=n_train, random_state=SEED).reset_index(drop=True)

    # 1. Penentuan K_FINAL & tabel perbandingan K=2..8
    k_final, evaluasi_perbandingan = eksperimen_pemilihan_k(data_bersih, data_latih)
    eksperimen_tambahan = eksperimen_scaling_dan_fitur(data_latih, k_final)

    # 2. Training model final pada 5 fitur (FITUR_FINAL) + StandardScaler
    print("[3/6] Melatih model final K-Means dan BIRCH (5 fitur, StandardScaler)...")
    scaler_final = StandardScaler()
    X_train_final = scaler_final.fit_transform(data_latih[FITUR_FINAL])
    threshold_birch = hitung_threshold_birch(X_train_final, seed=SEED)

    kmeans_final = KMeans(n_clusters=k_final, n_init=10, random_state=SEED)
    t0 = time.perf_counter()
    label_km_train = kmeans_final.fit_predict(X_train_final)
    waktu_km_final = time.perf_counter() - t0

    birch_final = Birch(
        n_clusters=k_final,
        threshold=threshold_birch,
        branching_factor=50,
    )
    t0 = time.perf_counter()
    label_bi_train = birch_final.fit_predict(X_train_final)
    waktu_bi_final = time.perf_counter() - t0

    eval_km_final = evaluasi_clustering(X_train_final, label_km_train)
    eval_bi_final = evaluasi_clustering(X_train_final, label_bi_train)
    stabilitas_final = uji_stabilitas_ari(data_bersih, FITUR_FINAL, k_final)

    # 3. Prediksi seluruh lagu unik & penamaan cluster
    print("[4/6] Melakukan clustering pada seluruh katalog lagu unik...")
    X_semua_final = scaler_final.transform(data_bersih[FITUR_FINAL])
    hasil_final = data_bersih.copy()
    hasil_final["cluster_kmeans"] = kmeans_final.predict(X_semua_final).astype(int)
    hasil_final["cluster_birch"] = birch_final.predict(X_semua_final).astype(int)
    hasil_final["cluster_final"] = hasil_final["cluster_kmeans"]

    profil_rata = hasil_final.groupby("cluster_final")[FITUR_FINAL].mean()
    nama_cluster = tentukan_nama_cluster(profil_rata)
    hasil_final["nama_cluster"] = hasil_final["cluster_final"].map(nama_cluster)

    # 4. Simpan artefak model ke folder models/
    print("[5/6] Menyimpan model dan konfigurasi ke folder models/...")
    joblib.dump(kmeans_final, MODELS_DIR / "kmeans_model.joblib")
    joblib.dump(birch_final, MODELS_DIR / "birch_model.joblib")
    joblib.dump(scaler_final, MODELS_DIR / "scaler.joblib")

    model_config = {
        "fitur_final": FITUR_FINAL,
        "nama_cluster": {str(k): v for k, v in nama_cluster.items()},
        "K_FINAL": k_final,
        "threshold_birch": float(threshold_birch),
        "branching_factor_birch": 50,
        "seed": SEED,
        "sample_size_train": int(n_train),
        "jumlah_lagu_katalog": int(len(hasil_final)),
        "evaluasi": {
            "kmeans": {
                **eval_km_final,
                "inertia": float(kmeans_final.inertia_),
                "waktu_training_detik": float(waktu_km_final),
                **stabilitas_final["K-Means"],
            },
            "birch": {
                **eval_bi_final,
                "waktu_training_detik": float(waktu_bi_final),
                **stabilitas_final["BIRCH"],
            },
        },
        "eksperimen_tambahan": eksperimen_tambahan,
    }
    with open(MODELS_DIR / "model_config.json", "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2, ensure_ascii=False)

    # 5. Simpan data katalog & artefak data ke folder data/
    print("[6/6] Menyimpan katalog lagu dan data analisis ke folder data/...")
    kolom_katalog = [
        "track_id",
        "track_name",
        "artists",
        "popularity",
        "genre_gabungan",
        "cluster_kmeans",
        "cluster_birch",
        "cluster_final",
        "nama_cluster",
        "danceability",
        "energy",
        "valence",
        "acousticness",
        "instrumentalness",
    ]
    hasil_final[kolom_katalog].to_csv(
        DATA_DIR / "katalog_lagu.csv",
        index=False,
        encoding="utf-8",
    )

    # Bangun data/genre_index.csv (pemetaan genre_norm ke daftar track_id)
    genre_df = hasil_final[["track_id", "genre_gabungan"]].copy()
    genre_df["genre"] = genre_df["genre_gabungan"].fillna("").str.split(" | ", regex=False)
    genre_df = genre_df.explode("genre")
    genre_df["genre_norm"] = genre_df["genre"].map(normalisasi_genre)
    genre_df = genre_df[genre_df["genre_norm"] != ""].drop_duplicates(["track_id", "genre_norm"])

    genre_index_df = (
        genre_df.groupby("genre_norm")["track_id"]
        .agg(
            jumlah_lagu="count",
            track_ids=lambda s: "|".join(s.astype(str)),
        )
        .reset_index()
        .sort_values("genre_norm")
    )
    genre_index_df.to_csv(DATA_DIR / "genre_index.csv", index=False, encoding="utf-8")

    # Simpan data/target_aktivitas.json
    with open(DATA_DIR / "target_aktivitas.json", "w", encoding="utf-8") as f:
        json.dump(TARGET_AKTIVITAS, f, indent=2, ensure_ascii=False)

    # Simpan data/evaluasi_perbandingan.csv
    evaluasi_perbandingan.to_csv(
        DATA_DIR / "evaluasi_perbandingan.csv",
        index=False,
        encoding="utf-8",
    )

    # Simpan data/profil_cluster.csv
    jumlah_per_cluster = hasil_final["cluster_final"].value_counts().sort_index()
    profil_cluster_df = profil_rata.copy()
    profil_cluster_df.insert(0, "nama_cluster", profil_cluster_df.index.map(nama_cluster))
    profil_cluster_df.insert(1, "jumlah_lagu", jumlah_per_cluster)
    profil_cluster_df.insert(
        2,
        "persentase",
        (jumlah_per_cluster / len(hasil_final) * 100).round(2),
    )
    profil_cluster_df = profil_cluster_df.reset_index()
    profil_cluster_df.to_csv(DATA_DIR / "profil_cluster.csv", index=False, encoding="utf-8")

    print("\n=== EXPORT SELESAI ===")
    print(f"K_FINAL         : {k_final}")
    print(f"Threshold BIRCH : {threshold_birch:.4f}")
    print(f"Nama Cluster    : {nama_cluster}")
    print(f"Katalog Lagu    : {len(hasil_final):,} lagu unik")
    print(f"Genre Terindeks : {len(genre_index_df)} genre")
    print("Evaluasi Model Final (5 Fitur):")
    print(
        f"  K-Means -> Silhouette={eval_km_final['silhouette']:.4f}, "
        f"DBI={eval_km_final['davies_bouldin']:.4f}, "
        f"CH={eval_km_final['calinski_harabasz']:.2f}, "
        f"ARI={stabilitas_final['K-Means']['ari_mean']:.4f}"
    )
    print(
        f"  BIRCH   -> Silhouette={eval_bi_final['silhouette']:.4f}, "
        f"DBI={eval_bi_final['davies_bouldin']:.4f}, "
        f"CH={eval_bi_final['calinski_harabasz']:.2f}, "
        f"ARI={stabilitas_final['BIRCH']['ari_mean']:.4f}"
    )


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as err:
        print(f"\n[ERROR] {err}", file=sys.stderr)
        sys.exit(1)

"""
recommender.py — Mesin rekomendasi playlist TuneCluster berbasis clustering K-Means & BIRCH.

Mengimplementasikan logika rekomendasi dari notebook TuneCluster_TAS_SPOTIFY_Upgrade.ipynb
(eksplorasi audio target berdasarkan aktivitas & mood, penyelarasan genre, dan
perhitungan jarak Euclidean pada ruang fitur StandardScaler 5 dimensi).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent

ALIAS_GENRE: dict[str, str] = {"r&b": "r-n-b"}

DAFTAR_AKTIVITAS_DEFAULT: list[str] = [
    "Olahraga",
    "Belajar",
    "Santai",
    "Perjalanan",
]

DAFTAR_MOOD: list[str] = [
    "Senang/Happy",
    "Sedih/Sad",
    "Energik",
    "Tenang/Calm",
    "Fokus",
]

PENYESUAIAN_MOOD: dict[str, dict[str, float]] = {
    "Senang/Happy": {"valence": 0.10, "energy": 0.05},
    "Sedih/Sad": {"valence": -0.15, "energy": -0.10},
    "Energik": {"energy": 0.15, "danceability": 0.10},
    "Tenang/Calm": {"energy": -0.10, "acousticness": 0.10},
    "Fokus": {"danceability": -0.10, "instrumentalness": 0.15},
}


def normalisasi_genre(nama: str) -> str:
    """Normalisasi nama genre menjadi huruf kecil dan terapkan alias eksplisit."""
    standar = str(nama).strip().lower()
    return ALIAS_GENRE.get(standar, standar)


def track_has_genre(genre_gabungan: object, genre_pilihan: str) -> bool:
    """Return whether a track has the selected genre across supported separators."""
    selected = normalisasi_genre(genre_pilihan)
    if not selected:
        return False
    combined_genres = "" if genre_gabungan is None else str(genre_gabungan)
    track_genres = {
        normalisasi_genre(genre)
        for genre in re.split(r"[|·,;]", combined_genres)
        if normalisasi_genre(genre)
    }
    return selected in track_genres


def _tentukan_nama_cluster_dari_profil(
    katalog: pd.DataFrame,
    kolom_cluster: str,
    fitur: list[str],
    default_mapping: dict[int, str],
) -> dict[int, str]:
    """Tentukan nama cluster berdasarkan profil rata-rata fitur audio."""
    if kolom_cluster == "cluster_final" or kolom_cluster == "cluster_kmeans":
        return default_mapping

    profil = katalog.groupby(kolom_cluster)[fitur].mean()
    if len(profil) == 2 and "energy" in profil.columns:
        urut = profil["energy"].sort_values(ascending=False).index.tolist()
        return {
            int(urut[0]): "Cenderung Energik",
            int(urut[1]): "Cenderung Tenang dan Akustik",
        }
    return {int(idx): default_mapping.get(int(idx), f"Cluster {idx}") for idx in profil.index}


@st.cache_resource(show_spinner="Memuat model dan katalog TuneCluster...")
def _muat_artefak_tunecluster(base_dir_str: str) -> dict[str, Any]:
    """Muat model, scaler, konfigurasi, dan dataset katalog sekali saja (cached)."""
    root = Path(base_dir_str)
    models_dir = root / "models"
    data_dir = root / "data"

    path_wajib = {
        "kmeans_model": models_dir / "kmeans_model.joblib",
        "birch_model": models_dir / "birch_model.joblib",
        "scaler": models_dir / "scaler.joblib",
        "model_config": models_dir / "model_config.json",
        "katalog_lagu": data_dir / "katalog_lagu.csv",
        "genre_index": data_dir / "genre_index.csv",
        "target_aktivitas": data_dir / "target_aktivitas.json",
    }
    hilang = [f"{k}: {p}" for k, p in path_wajib.items() if not p.exists()]
    if hilang:
        raise FileNotFoundError(
            "File artefak TuneCluster tidak lengkap. Jalankan `export_models.py` terlebih dahulu.\n"
            "File yang tidak ditemukan:\n- " + "\n- ".join(hilang)
        )

    kmeans_model = joblib.load(path_wajib["kmeans_model"])
    birch_model = joblib.load(path_wajib["birch_model"])
    scaler = joblib.load(path_wajib["scaler"])

    with open(path_wajib["model_config"], "r", encoding="utf-8") as f:
        config = json.load(f)

    with open(path_wajib["target_aktivitas"], "r", encoding="utf-8") as f:
        target_aktivitas = json.load(f)

    katalog = pd.read_csv(path_wajib["katalog_lagu"], encoding="utf-8")
    katalog = katalog.drop_duplicates(subset="track_id", keep="first").reset_index(drop=True)

    df_genre = pd.read_csv(path_wajib["genre_index"], encoding="utf-8")
    genre_index: dict[str, set[str]] = {}
    for row in df_genre.itertuples(index=False):
        genre_key = normalisasi_genre(row.genre_norm)
        raw_ids = getattr(row, "track_ids", "")
        if pd.notna(raw_ids) and str(raw_ids).strip():
            genre_index[genre_key] = set(str(raw_ids).split("|"))
        else:
            genre_index[genre_key] = set()

    fitur_final: list[str] = list(config["fitur_final"])
    nama_cluster_kmeans = {int(k): str(v) for k, v in config["nama_cluster"].items()}
    nama_cluster_birch = _tentukan_nama_cluster_dari_profil(
        katalog, "cluster_birch", fitur_final, nama_cluster_kmeans
    )

    # Pre-compute matriks fitur terstandarisasi untuk inferensi jarak cepat
    x_katalog_scaled = scaler.transform(katalog[fitur_final])

    evaluasi_perbandingan: list[dict[str, Any]] = []
    path_eval_csv = data_dir / "evaluasi_perbandingan.csv"
    if path_eval_csv.exists():
        df_eval = pd.read_csv(path_eval_csv, encoding="utf-8")
        evaluasi_perbandingan = df_eval.to_dict(orient="records")

    return {
        "kmeans_model": kmeans_model,
        "birch_model": birch_model,
        "scaler": scaler,
        "config": config,
        "fitur_final": fitur_final,
        "nama_cluster_kmeans": nama_cluster_kmeans,
        "nama_cluster_birch": nama_cluster_birch,
        "katalog": katalog,
        "x_katalog_scaled": x_katalog_scaled,
        "genre_index": genre_index,
        "target_aktivitas": target_aktivitas,
        "evaluasi_perbandingan": evaluasi_perbandingan,
    }


class TuneClusterRecommender:
    """Mesin rekomendasi lagu Spotify berbasis clustering K-Means dan BIRCH."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        """
        Inisialisasi recommender dengan memuat seluruh model, scaler, config, dan katalog
        menggunakan cache Streamlit (`@st.cache_resource`).

        Parameters
        ----------
        base_dir : str | Path | None, optional
            Path root folder project TuneCluster. Jika None, otomatis menggunakan folder
            induk dari `utils/`.
        """
        resolved_dir = Path(base_dir).resolve() if base_dir is not None else BASE_DIR
        artefak = _muat_artefak_tunecluster(str(resolved_dir))

        self.base_dir: Path = resolved_dir
        self.kmeans_model = artefak["kmeans_model"]
        self.birch_model = artefak["birch_model"]
        self.scaler = artefak["scaler"]
        self.config: dict[str, Any] = artefak["config"]
        self.fitur_final: list[str] = artefak["fitur_final"]
        self.nama_cluster_map: dict[str, dict[int, str]] = {
            "kmeans": artefak["nama_cluster_kmeans"],
            "birch": artefak["nama_cluster_birch"],
        }
        self.katalog: pd.DataFrame = artefak["katalog"]
        self._x_katalog_scaled: np.ndarray = artefak["x_katalog_scaled"]
        self.genre_index: dict[str, set[str]] = artefak["genre_index"]
        self.genre_tersedia: set[str] = set(self.genre_index.keys())
        self.target_aktivitas: dict[str, dict[str, float]] = artefak["target_aktivitas"]
        self.evaluasi_perbandingan: list[dict[str, Any]] = artefak["evaluasi_perbandingan"]

    def _validasi_algoritma(self, algoritma: str) -> str:
        """Validasi dan normalisasi nama algoritma clustering ('kmeans' atau 'birch')."""
        if not isinstance(algoritma, str):
            raise TypeError("Parameter 'algoritma' harus berupa string ('kmeans' atau 'birch').")
        algo = algoritma.strip().lower().replace("-", "")
        if algo not in {"kmeans", "birch"}:
            raise ValueError(
                f"Algoritma '{algoritma}' tidak didukung. Pilih 'kmeans' atau 'birch'."
            )
        return algo

    def _validasi_mood(self, mood: str) -> str:
        """Validasi nama mood terhadap daftar mood yang didukung (case-insensitive)."""
        if not isinstance(mood, str):
            raise TypeError("Parameter 'mood' harus berupa string.")
        mood_clean = mood.strip()
        mood_lookup = {m.lower(): m for m in DAFTAR_MOOD}
        if mood_clean.lower() not in mood_lookup:
            raise ValueError(
                f"Mood '{mood}' tidak valid. Pilih salah satu dari: {DAFTAR_MOOD}"
            )
        return mood_lookup[mood_clean.lower()]

    def _validasi_aktivitas(self, aktivitas: str) -> str:
        """Validasi nama aktivitas terhadap TARGET_AKTIVITAS (case-insensitive)."""
        if not isinstance(aktivitas, str):
            raise TypeError("Parameter 'aktivitas' harus berupa string.")
        akt_clean = aktivitas.strip()
        akt_lookup = {k.lower(): k for k in self.target_aktivitas.keys()}
        if akt_clean.lower() not in akt_lookup:
            raise ValueError(
                f"Aktivitas '{aktivitas}' tidak valid. Pilih salah satu dari: {self.get_daftar_aktivitas()}"
            )
        return akt_lookup[akt_clean.lower()]

    def _bangun_vektor_target(self, aktivitas: str, mood: str) -> dict[str, float]:
        """Bangun vektor target 5 fitur audio dari aktivitas lalu sesuaikan dengan mood dan clip [0, 1]."""
        vektor = dict(self.target_aktivitas[aktivitas])
        penyesuaian = PENYESUAIAN_MOOD[mood]
        for fitur, delta in penyesuaian.items():
            if fitur in vektor:
                vektor[fitur] = vektor[fitur] + delta

        return {
            fitur: float(np.clip(vektor[fitur], 0.0, 1.0))
            for fitur in self.fitur_final
        }

    def rekomendasi(
        self,
        genre_user: list[str] | None,
        aktivitas: str,
        mood: str,
        n: int = 10,
        algoritma: str = "kmeans",
        prioritaskan_populer: bool = False,
    ) -> pd.DataFrame:
        """
        Hasilkan rekomendasi top-N lagu berdasarkan preferensi genre, aktivitas, dan mood.

        Parameters
        ----------
        genre_user : list[str] | None
            Daftar genre pilihan pengguna. Jika kosong atau tidak cocok, sistem otomatis
            menggunakan fallback ke seluruh lagu dalam cluster target.
        aktivitas : str
            Aktivitas pengguna: salah satu dari ["Olahraga", "Belajar", "Santai", "Perjalanan"].
        mood : str
            Mood pengguna: salah satu dari ["Senang/Happy", "Sedih/Sad", "Energik", "Tenang/Calm", "Fokus"].
        n : int, default=10
            Jumlah lagu rekomendasi yang dikembalikan (minimal 1).
        algoritma : str, default="kmeans"
            Model clustering yang dipakai ("kmeans" atau "birch").
        prioritaskan_populer : bool, default=False
            Jika True, urutkan kandidat yang sama berdasarkan popularity, lalu jarak audio.

        Returns
        -------
        pd.DataFrame
            DataFrame berisi kolom:
            ["track_id", "track_name", "artists", "genre_gabungan", "nama_cluster", "jarak"].
            Informasi tambahan (fallback_audio, genre_cocok, genre_tidak_tersedia,
            target_cluster, target_vektor) disimpan di `df.attrs`.
        """
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("Parameter 'n' harus berupa bilangan bulat >= 1.")
        if not isinstance(prioritaskan_populer, bool):
            raise TypeError("Parameter 'prioritaskan_populer' harus berupa bool.")
        if prioritaskan_populer and "popularity" not in self.katalog.columns:
            raise ValueError(
                "Kolom popularity tidak tersedia. Perbarui katalog dengan menjalankan "
                "`export_models.py`."
            )

        if genre_user is None:
            genre_list: list[str] = []
        elif isinstance(genre_user, str):
            genre_list = [genre_user]
        elif isinstance(genre_user, (list, tuple, set)):
            genre_list = [str(g) for g in genre_user if str(g).strip()]
        else:
            raise TypeError("Parameter 'genre_user' harus berupa list string genre atau None.")

        aktivitas_valid = self._validasi_aktivitas(aktivitas)
        mood_valid = self._validasi_mood(mood)
        algo_valid = self._validasi_algoritma(algoritma)

        # 1 & 2. Bangun vektor target dari aktivitas + penyesuaian mood (clipped 0-1)
        target_vektor = self._bangun_vektor_target(aktivitas_valid, mood_valid)

        # 3. Scale vektor target dengan scaler yang sudah di-fit
        target_df = pd.DataFrame([target_vektor])[self.fitur_final]
        target_scaled = self.scaler.transform(target_df)

        # 4. Prediksi cluster menggunakan model yang dipilih
        model = self.kmeans_model if algo_valid == "kmeans" else self.birch_model
        kolom_cluster = "cluster_kmeans" if algo_valid == "kmeans" else "cluster_birch"
        nama_cluster_dict = self.nama_cluster_map[algo_valid]
        target_cluster = int(model.predict(target_scaled)[0])

        # 5. Filter katalog berdasarkan cluster target dan kecocokan genre
        mask_cluster = self.katalog[kolom_cluster] == target_cluster
        if not mask_cluster.any():
            # Pengaman jika cluster target tidak memiliki anggota di katalog
            mask_cluster = pd.Series(True, index=self.katalog.index)

        genre_diminta = [normalisasi_genre(g) for g in genre_list]
        genre_cocok = sorted(set(genre_diminta) & self.genre_tersedia)
        genre_tidak_tersedia = sorted(set(genre_diminta) - self.genre_tersedia)

        track_cocok: set[str] = (
            set().union(*(self.genre_index[g] for g in genre_cocok))
            if genre_cocok
            else set()
        )
        mask_genre = mask_cluster & self.katalog["track_id"].isin(track_cocok)

        gunakan_fallback = not bool(mask_genre.any())
        idx_kandidat = self.katalog.index[mask_cluster if gunakan_fallback else mask_genre].to_numpy()

        # 6. Hitung Euclidean distance di ruang StandardScaler 5 fitur
        x_kandidat = self._x_katalog_scaled[idx_kandidat]
        jarak = np.linalg.norm(x_kandidat - target_scaled, axis=1)

        # 7 & 8. Urutkan jarak terdekat dan kembalikan top-N
        hasil = self.katalog.iloc[idx_kandidat][
            ["track_id", "track_name", "artists", "genre_gabungan"]
        ].copy()
        hasil["nama_cluster"] = nama_cluster_dict.get(target_cluster, f"Cluster {target_cluster}")
        hasil["jarak"] = jarak

        if prioritaskan_populer:
            popularitas = pd.to_numeric(
                self.katalog.iloc[idx_kandidat]["popularity"],
                errors="coerce",
            )
            if not popularitas.notna().any():
                raise ValueError(
                    "Tidak ada nilai popularity yang valid pada kandidat rekomendasi."
                )
            hasil["popularity"] = popularitas.to_numpy()
            hasil = (
                hasil.sort_values(
                    ["popularity", "jarak", "track_name"],
                    ascending=[False, True, True],
                    na_position="last",
                    kind="mergesort",
                )
                .head(n)
                .reset_index(drop=True)
            )
        else:
            hasil = (
                hasil.sort_values(["jarak", "track_name"], ascending=[True, True])
                .head(n)
                .reset_index(drop=True)
            )

        # Simpan metadata proses untuk ditampilkan di UI bila diperlukan
        hasil.attrs["algoritma"] = algo_valid
        hasil.attrs["aktivitas"] = aktivitas_valid
        hasil.attrs["mood"] = mood_valid
        hasil.attrs["target_cluster"] = target_cluster
        hasil.attrs["nama_cluster"] = nama_cluster_dict.get(target_cluster, f"Cluster {target_cluster}")
        hasil.attrs["target_vektor"] = target_vektor
        hasil.attrs["genre_cocok"] = genre_cocok
        hasil.attrs["genre_tidak_tersedia"] = genre_tidak_tersedia
        hasil.attrs["fallback_audio"] = gunakan_fallback
        hasil.attrs["jumlah_kandidat"] = int(len(idx_kandidat))
        hasil.attrs["prioritaskan_populer"] = prioritaskan_populer

        return hasil

    def cari_lagu(self, query: str, limit: int = 10) -> pd.DataFrame:
        """Cari lagu berdasarkan substring judul atau artis di dalam katalog."""
        if not isinstance(query, str):
            raise TypeError("Parameter 'query' harus berupa string.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Parameter 'limit' harus berupa bilangan bulat >= 1.")

        kolom_hasil = [
            "track_id",
            "track_name",
            "artists",
            "genre_gabungan",
            "cluster_kmeans",
            "nama_cluster",
            "cluster_birch",
            "nama_cluster_birch",
        ]
        query_bersih = query.strip()
        if not query_bersih:
            return pd.DataFrame(columns=kolom_hasil)

        cocok = self.katalog["track_name"].str.contains(
            query_bersih, case=False, regex=False, na=False
        ) | self.katalog["artists"].str.contains(
            query_bersih, case=False, regex=False, na=False
        )
        hasil = self.katalog.loc[cocok].head(limit)[
            [
                "track_id",
                "track_name",
                "artists",
                "genre_gabungan",
                "cluster_kmeans",
                "cluster_birch",
            ]
        ].copy()
        hasil["nama_cluster"] = hasil["cluster_kmeans"].map(
            self.nama_cluster_map["kmeans"]
        )
        hasil["nama_cluster_birch"] = hasil["cluster_birch"].map(
            self.nama_cluster_map["birch"]
        )
        return hasil.reindex(columns=kolom_hasil).reset_index(drop=True)

    def cari_lagu_serupa(self, track_id: str, n: int = 10) -> pd.DataFrame:
        """Cari tetangga audio terdekat berdasarkan jarak Euclidean fitur terstandarisasi."""
        if not isinstance(track_id, str) or not track_id.strip():
            raise ValueError("Parameter 'track_id' harus berupa string yang tidak kosong.")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("Parameter 'n' harus berupa bilangan bulat >= 1.")

        seed_matches = self.katalog.index[
            self.katalog["track_id"].astype(str) == track_id.strip()
        ]
        if len(seed_matches) == 0:
            raise ValueError(f"Lagu dengan track_id '{track_id}' tidak ditemukan di katalog.")

        seed_idx = int(seed_matches[0])
        jarak = np.linalg.norm(
            self._x_katalog_scaled - self._x_katalog_scaled[seed_idx],
            axis=1,
        )
        jarak[seed_idx] = np.inf

        jumlah_hasil = min(n, len(self.katalog) - 1)
        if jumlah_hasil == 0:
            return pd.DataFrame(
                columns=[
                    "track_id",
                    "track_name",
                    "artists",
                    "genre_gabungan",
                    "cluster_kmeans",
                    "nama_cluster",
                    "cluster_birch",
                    "nama_cluster_birch",
                    "jarak",
                ]
            )

        kandidat_idx = np.argpartition(jarak, jumlah_hasil - 1)[:jumlah_hasil]
        kandidat_idx = sorted(
            kandidat_idx.tolist(),
            key=lambda idx: (
                float(jarak[idx]),
                str(self.katalog.iloc[idx]["track_name"]),
                str(self.katalog.iloc[idx]["track_id"]),
            ),
        )

        hasil = self.katalog.iloc[kandidat_idx][
            [
                "track_id",
                "track_name",
                "artists",
                "genre_gabungan",
                "cluster_kmeans",
                "cluster_birch",
            ]
        ].copy()
        hasil["nama_cluster"] = hasil["cluster_kmeans"].map(
            self.nama_cluster_map["kmeans"]
        )
        hasil["nama_cluster_birch"] = hasil["cluster_birch"].map(
            self.nama_cluster_map["birch"]
        )
        hasil["jarak"] = jarak[kandidat_idx]
        return hasil.reset_index(drop=True)

    def rekomendasi_genre(
        self,
        genre_user: list[str] | None,
        aktivitas: str,
        mood: str,
        n_lagu: int = 20,
        top_genre: int = 5,
        algoritma: str = "kmeans",
    ) -> pd.DataFrame:
        """
        Kembalikan top-genre yang paling sering muncul pada `n_lagu` rekomendasi teratas
        (mengikuti logika Cell 50 notebook).
        """
        if not isinstance(top_genre, int) or isinstance(top_genre, bool) or top_genre < 1:
            raise ValueError("Parameter 'top_genre' harus berupa bilangan bulat >= 1.")

        df_rekom = self.rekomendasi(
            genre_user=genre_user,
            aktivitas=aktivitas,
            mood=mood,
            n=n_lagu,
            algoritma=algoritma,
        )
        genres_series = (
            df_rekom["genre_gabungan"]
            .fillna("")
            .str.split(" | ", regex=False)
            .explode()
            .map(normalisasi_genre)
        )
        genres_series = genres_series[genres_series != ""]
        hitung = genres_series.value_counts().head(top_genre)
        return pd.DataFrame(
            {
                "genre": hitung.index,
                "jumlah_lagu": hitung.values,
            }
        )

    def get_profil_cluster(self, algoritma: str = "kmeans") -> pd.DataFrame:
        """
        Kembalikan rata-rata 5 fitur audio per cluster beserta jumlah lagu, persentase,
        dan nama cluster.

        Parameters
        ----------
        algoritma : str, default="kmeans"
            Model clustering ("kmeans" atau "birch").

        Returns
        -------
        pd.DataFrame
            DataFrame profil per cluster terindeks nomor cluster.
        """
        algo_valid = self._validasi_algoritma(algoritma)
        kolom_cluster = "cluster_kmeans" if algo_valid == "kmeans" else "cluster_birch"
        nama_cluster_dict = self.nama_cluster_map[algo_valid]

        profil = self.katalog.groupby(kolom_cluster)[self.fitur_final].mean()
        jumlah = self.katalog[kolom_cluster].value_counts().sort_index()
        persen = (jumlah / len(self.katalog) * 100).round(2)

        profil.insert(
            0,
            "nama_cluster",
            [nama_cluster_dict.get(int(idx), f"Cluster {idx}") for idx in profil.index],
        )
        profil.insert(1, "jumlah_lagu", jumlah)
        profil.insert(2, "persentase", persen)
        profil.index.name = "cluster"
        return profil

    def get_evaluasi(self) -> dict[str, Any]:
        """
        Kembalikan dictionary metrik evaluasi perbandingan K-Means vs BIRCH.

        Returns
        -------
        dict[str, Any]
            Berisi metrik K-Means & BIRCH untuk K_FINAL (Silhouette, DBI, CH, ARI,
            waktu training), `k_final`, `threshold_birch`, `eksperimen_tambahan`,
            serta `perbandingan_k` (tabel K=2..8).
        """
        evaluasi = self.config.get("evaluasi", {})
        return {
            "k_final": self.config.get("K_FINAL"),
            "threshold_birch": self.config.get("threshold_birch"),
            "fitur_final": list(self.fitur_final),
            "kmeans": dict(evaluasi.get("kmeans", {})),
            "birch": dict(evaluasi.get("birch", {})),
            "eksperimen_tambahan": dict(self.config.get("eksperimen_tambahan", {})),
            "perbandingan_k": list(self.evaluasi_perbandingan),
        }

    def get_daftar_genre(self) -> list[str]:
        """Kembalikan daftar semua genre unik yang tersedia di katalog (terurut alfabetis)."""
        return sorted(self.genre_tersedia)

    def get_daftar_aktivitas(self) -> list[str]:
        """Kembalikan daftar aktivitas yang didukung mesin rekomendasi."""
        urutan = [a for a in DAFTAR_AKTIVITAS_DEFAULT if a in self.target_aktivitas]
        tambahan = [a for a in self.target_aktivitas if a not in urutan]
        return urutan + tambahan

    def get_daftar_mood(self) -> list[str]:
        """Kembalikan daftar mood yang didukung mesin rekomendasi."""
        return list(DAFTAR_MOOD)


@st.cache_resource(show_spinner="Menyiapkan mesin rekomendasi TuneCluster...")
def get_recommender(base_dir: str | Path | None = None) -> TuneClusterRecommender:
    """Factory function ber-cache untuk mendapatkan instance `TuneClusterRecommender`."""
    return TuneClusterRecommender(base_dir=base_dir)


if __name__ == "__main__":
    print("=== PENGUJIAN TuneClusterRecommender ===")
    rec = TuneClusterRecommender()

    print("Daftar aktivitas :", rec.get_daftar_aktivitas())
    print("Daftar mood      :", rec.get_daftar_mood())
    print("Total genre      :", len(rec.get_daftar_genre()))

    print("\n--- Profil Cluster K-Means ---")
    print(rec.get_profil_cluster("kmeans").round(3))

    print("\n--- Profil Cluster BIRCH ---")
    print(rec.get_profil_cluster("birch").round(3))

    evaluasi = rec.get_evaluasi()
    print("\n--- Evaluasi K-Means vs BIRCH (K_FINAL =", evaluasi["k_final"], ") ---")
    print(
        f"K-Means -> Silhouette: {evaluasi['kmeans']['silhouette']:.4f}, "
        f"DBI: {evaluasi['kmeans']['davies_bouldin']:.4f}, "
        f"CH: {evaluasi['kmeans']['calinski_harabasz']:.2f}, "
        f"ARI: {evaluasi['kmeans']['ari_mean']:.4f}"
    )
    print(
        f"BIRCH   -> Silhouette: {evaluasi['birch']['silhouette']:.4f}, "
        f"DBI: {evaluasi['birch']['davies_bouldin']:.4f}, "
        f"CH: {evaluasi['birch']['calinski_harabasz']:.2f}, "
        f"ARI: {evaluasi['birch']['ari_mean']:.4f}"
    )

    print("\n--- Tes Rekomendasi (K-Means, Olahraga + Energik, genre cocok) ---")
    hasil_km = rec.rekomendasi(
        genre_user=["Rock", "R&B", "Synth-pop"],
        aktivitas="Olahraga",
        mood="Energik",
        n=5,
        algoritma="kmeans",
    )
    print("Metadata:", {k: hasil_km.attrs[k] for k in ["target_cluster", "nama_cluster", "genre_cocok", "fallback_audio"]})
    print(hasil_km.to_string(index=False))

    print("\n--- Tes Rekomendasi (BIRCH, Belajar + Fokus) ---")
    hasil_bi = rec.rekomendasi(
        genre_user=["Classical", "Ambient"],
        aktivitas="Belajar",
        mood="Fokus",
        n=5,
        algoritma="birch",
    )
    print("Metadata:", {k: hasil_bi.attrs[k] for k in ["target_cluster", "nama_cluster", "genre_cocok", "fallback_audio"]})
    print(hasil_bi.to_string(index=False))

    print("\n--- Tes Fallback Genre Tidak Tersedia ---")
    hasil_fb = rec.rekomendasi(
        genre_user=["Dangdut", "Lo-Fi"],
        aktivitas="Santai",
        mood="Tenang/Calm",
        n=5,
        algoritma="kmeans",
    )
    print("Fallback aktif:", hasil_fb.attrs["fallback_audio"], "| Genre tak tersedia:", hasil_fb.attrs["genre_tidak_tersedia"])
    print(hasil_fb.to_string(index=False))

    print("\n--- Tes Error Handling ---")
    for label, fn in [
        ("Aktivitas invalid", lambda: rec.rekomendasi(["rock"], "Tidur", "Tenang/Calm")),
        ("Mood invalid", lambda: rec.rekomendasi(["rock"], "Belajar", "Marah")),
        ("Algoritma invalid", lambda: rec.rekomendasi(["rock"], "Belajar", "Fokus", algoritma="dbscan")),
        ("n invalid", lambda: rec.rekomendasi(["rock"], "Belajar", "Fokus", n=0)),
    ]:
        try:
            fn()
            raise AssertionError(f"Seharusnya gagal: {label}")
        except ValueError as e:
            print(f"OK ({label}): {e}")

    print("\nSEMUA PENGUJIAN SELESAI & LULUS!")

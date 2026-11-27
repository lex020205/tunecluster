import unittest

import numpy as np
import pandas as pd

from utils.recommender import TuneClusterRecommender, track_has_genre


class RecommenderSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recommender = TuneClusterRecommender()

    def test_search_matches_track_name_and_artist_case_insensitively(self) -> None:
        track = self.recommender.katalog.iloc[0]

        by_title = self.recommender.cari_lagu(str(track["track_name"])[:8].swapcase(), limit=5)
        by_artist = self.recommender.cari_lagu(str(track["artists"]), limit=5)

        self.assertIn(track["track_id"], by_title["track_id"].tolist())
        self.assertIn(track["track_id"], by_artist["track_id"].tolist())
        self.assertLessEqual(len(by_title), 5)
        self.assertIn("nama_cluster_birch", by_title.columns)

    def test_selected_genre_matches_case_insensitively_across_separators(self) -> None:
        self.assertTrue(track_has_genre("J-pop · Anime; Pop, R&B | Rock", "anime"))
        self.assertTrue(track_has_genre("R&B", "r-n-b"))
        self.assertFalse(track_has_genre("J-pop · Anime", "rock"))

    def test_empty_and_unmatched_search_return_no_results(self) -> None:
        self.assertTrue(self.recommender.cari_lagu("").empty)
        self.assertTrue(self.recommender.cari_lagu("no tunecluster track matches this").empty)

    def test_similar_tracks_are_sorted_by_scaled_audio_distance(self) -> None:
        seed_idx = 0
        seed = self.recommender.katalog.iloc[seed_idx]

        similar = self.recommender.cari_lagu_serupa(str(seed["track_id"]), n=5)

        distances = np.linalg.norm(
            self.recommender._x_katalog_scaled
            - self.recommender._x_katalog_scaled[seed_idx],
            axis=1,
        )
        distances[seed_idx] = np.inf
        expected = np.sort(distances)[:5]

        self.assertEqual(len(similar), 5)
        self.assertNotIn(seed["track_id"], similar["track_id"].tolist())
        np.testing.assert_allclose(similar["jarak"].to_numpy(), expected)

    def test_search_and_similarity_validate_limits_and_track_ids(self) -> None:
        with self.assertRaises(ValueError):
            self.recommender.cari_lagu("music", limit=0)
        with self.assertRaises(ValueError):
            self.recommender.cari_lagu_serupa("missing-track-id")
        with self.assertRaises(ValueError):
            self.recommender.cari_lagu_serupa(str(self.recommender.katalog.iloc[0]["track_id"]), n=0)

    def test_popularity_mode_reranks_candidates_without_changing_audio_distances(self) -> None:
        parameters = {
            "genre_user": None,
            "aktivitas": "Belajar",
            "mood": "Fokus",
            "n": 10,
        }
        default = self.recommender.rekomendasi(**parameters)
        explicit_default = self.recommender.rekomendasi(
            **parameters,
            prioritaskan_populer=False,
        )
        popular = self.recommender.rekomendasi(
            **parameters,
            prioritaskan_populer=True,
        )

        pd.testing.assert_frame_equal(default, explicit_default)
        self.assertEqual(
            default.attrs["jumlah_kandidat"],
            popular.attrs["jumlah_kandidat"],
        )
        self.assertTrue(popular["popularity"].is_monotonic_decreasing)

        target = self.recommender._bangun_vektor_target("Belajar", "Fokus")
        target_scaled = self.recommender.scaler.transform(
            pd.DataFrame([target])[self.recommender.fitur_final]
        )
        for row in popular.itertuples():
            idx = self.recommender.katalog.index[
                self.recommender.katalog["track_id"] == row.track_id
            ][0]
            expected_distance = np.linalg.norm(
                self.recommender._x_katalog_scaled[idx] - target_scaled,
                axis=1,
            )[0]
            self.assertAlmostEqual(row.jarak, float(expected_distance))

    def test_popularity_mode_requires_available_numeric_popularity(self) -> None:
        catalog = self.recommender.katalog
        self.recommender.katalog = catalog.drop(columns=["popularity"])
        try:
            with self.assertRaisesRegex(ValueError, "Kolom popularity tidak tersedia"):
                self.recommender.rekomendasi(
                    genre_user=None,
                    aktivitas="Belajar",
                    mood="Fokus",
                    prioritaskan_populer=True,
                )
        finally:
            self.recommender.katalog = catalog

        with self.assertRaises(TypeError):
            self.recommender.rekomendasi(
                genre_user=None,
                aktivitas="Belajar",
                mood="Fokus",
                prioritaskan_populer="yes",
            )


if __name__ == "__main__":
    unittest.main()

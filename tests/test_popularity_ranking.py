import unittest

import numpy as np
import pandas as pd

from utils.recommender import TuneClusterRecommender


class PopularityRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recommender = TuneClusterRecommender()

    def test_all_candidates_remain_sorted_by_audio_distance(self) -> None:
        parameters = {
            "genre_user": None,
            "aktivitas": "Belajar",
            "mood": "Fokus",
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
        self.assertEqual(len(default), default.attrs["jumlah_kandidat"])
        self.assertEqual(len(popular), popular.attrs["jumlah_kandidat"])
        self.assertTrue(default["jarak"].is_monotonic_increasing)
        self.assertTrue(popular["jarak"].is_monotonic_increasing)

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

    def test_popularity_mode_validates_column_and_option(self) -> None:
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

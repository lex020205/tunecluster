import unittest

import pandas as pd

from utils.recommender import score_recommendations


class RecommendationScoringTests(unittest.TestCase):
    def test_keeps_exactly_fifty_percent_and_sorts_all_matches(self) -> None:
        candidates = pd.DataFrame(
            {
                "track_name": ["below", "exact", "best", "worst"],
                "jarak": [2.201, 2.2, 0.0, 4.0],
            }
        )
        candidates.attrs["target_cluster"] = 4

        scored = score_recommendations(candidates)

        self.assertEqual(scored["track_name"].tolist(), ["best", "exact"])
        self.assertEqual(float(scored.iloc[-1]["skor_kemiripan"]), 50.0)
        self.assertEqual(scored.attrs["target_cluster"], 4)

    def test_empty_results_keep_a_typed_similarity_column(self) -> None:
        scored = score_recommendations(pd.DataFrame(columns=["track_name", "jarak"]))

        self.assertTrue(scored.empty)
        self.assertIn("skor_kemiripan", scored.columns)


if __name__ == "__main__":
    unittest.main()

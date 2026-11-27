import csv
import io
import unittest

import pandas as pd

from utils.playlist_export import playlist_to_csv, playlist_to_text


class PlaylistExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.playlist = pd.DataFrame(
            [
                {
                    "track_id": "track-1",
                    "track_name": 'Song, "One"',
                    "artists": "Artist A",
                    "genre_gabungan": "pop | indie",
                    "nama_cluster": "Energetik",
                    "skor_kemiripan": 92.5,
                    "spotify_search_url": "https://open.spotify.com/search/Song%2C+%22One%22",
                }
            ]
        )

    def test_plain_text_lists_track_titles_and_artists(self) -> None:
        self.assertEqual(
            playlist_to_text(self.playlist),
            '1. Song, "One" — Artist A',
        )

    def test_csv_preserves_playlist_fields_and_quoted_values(self) -> None:
        csv_text = playlist_to_csv(self.playlist).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Judul"], 'Song, "One"')
        self.assertEqual(rows[0]["Artis"], "Artist A")
        self.assertEqual(rows[0]["Genre"], "pop | indie")
        self.assertEqual(rows[0]["Spotify Search URL"], self.playlist.iloc[0]["spotify_search_url"])

    def test_export_helpers_report_missing_required_columns(self) -> None:
        with self.assertRaises(ValueError):
            playlist_to_text(pd.DataFrame({"track_name": ["Song"]}))
        with self.assertRaises(ValueError):
            playlist_to_csv(pd.DataFrame({"track_name": ["Song"]}))


if __name__ == "__main__":
    unittest.main()

"""Helpers for exporting TuneCluster recommendation playlists."""

from __future__ import annotations

import pandas as pd

PLAYLIST_CSV_COLUMNS = {
    "track_id": "Spotify Track ID",
    "track_name": "Judul",
    "artists": "Artis",
    "genre_gabungan": "Genre",
    "nama_cluster": "Cluster",
    "skor_kemiripan": "Skor Kemiripan (%)",
    "spotify_search_url": "Spotify Search URL",
}


def playlist_to_text(playlist: pd.DataFrame) -> str:
    """Format playlist titles and artists as a plain-text list."""
    required_columns = {"track_name", "artists"}
    missing_columns = required_columns.difference(playlist.columns)
    if missing_columns:
        raise ValueError(f"Kolom playlist tidak tersedia: {', '.join(sorted(missing_columns))}")

    return "\n".join(
        f"{index}. {row['track_name']} — {row['artists']}"
        for index, (_, row) in enumerate(playlist.iterrows(), start=1)
    )


def playlist_to_csv(playlist: pd.DataFrame) -> bytes:
    """Serialize playlist metadata as an Excel-friendly UTF-8 CSV file."""
    required_columns = {"track_name", "artists", "genre_gabungan"}
    missing_columns = required_columns.difference(playlist.columns)
    if missing_columns:
        raise ValueError(f"Kolom playlist tidak tersedia: {', '.join(sorted(missing_columns))}")

    export_columns = [
        column for column in PLAYLIST_CSV_COLUMNS if column in playlist.columns
    ]
    exported = playlist.loc[:, export_columns].rename(columns=PLAYLIST_CSV_COLUMNS)
    return exported.to_csv(index=False).encode("utf-8-sig")

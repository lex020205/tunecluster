import tempfile
import unittest
from pathlib import Path

from utils.database import (
    get_saved_tracks,
    init_db,
    login_user,
    register_user,
    remove_saved_track,
    save_track,
)


class SavedTrackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "users.db"
        init_db(self.db_path)
        init_db(self.db_path)

        self.assertTrue(
            register_user("listener_a", "Listener A", 24, "password-a", db_path=self.db_path)[0]
        )
        self.assertTrue(
            register_user("listener_b", "Listener B", 25, "password-b", db_path=self.db_path)[0]
        )
        self.user_a = login_user("listener_a", "password-a", db_path=self.db_path)
        self.user_b = login_user("listener_b", "password-b", db_path=self.db_path)
        self.assertIsNotNone(self.user_a)
        self.assertIsNotNone(self.user_b)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_saves_are_unique_per_user_and_filterable(self) -> None:
        user_a_id = self.user_a["user_id"]
        user_b_id = self.user_b["user_id"]
        self.assertTrue(save_track(user_a_id, "track-1", "Belajar", "Fokus", db_path=self.db_path))
        self.assertFalse(save_track(user_a_id, "track-1", "Santai", "Tenang", db_path=self.db_path))
        self.assertTrue(save_track(user_a_id, "track-2", "Santai", "Tenang", db_path=self.db_path))
        self.assertTrue(save_track(user_b_id, "track-1", "Belajar", "Fokus", db_path=self.db_path))

        all_user_a = get_saved_tracks(user_a_id, db_path=self.db_path)
        study_tracks = get_saved_tracks(
            user_a_id,
            aktivitas="Belajar",
            db_path=self.db_path,
        )
        calm_tracks = get_saved_tracks(user_a_id, mood="Tenang", db_path=self.db_path)
        user_b_tracks = get_saved_tracks(user_b_id, db_path=self.db_path)

        self.assertEqual({row["track_id"] for row in all_user_a}, {"track-1", "track-2"})
        self.assertEqual([row["track_id"] for row in study_tracks], ["track-1"])
        self.assertEqual([row["track_id"] for row in calm_tracks], ["track-2"])
        self.assertEqual([row["track_id"] for row in user_b_tracks], ["track-1"])

    def test_delete_is_scoped_to_the_owner(self) -> None:
        user_a_id = self.user_a["user_id"]
        user_b_id = self.user_b["user_id"]
        save_track(user_a_id, "track-1", "Belajar", "Fokus", db_path=self.db_path)

        self.assertFalse(remove_saved_track(user_b_id, "track-1", db_path=self.db_path))
        self.assertTrue(remove_saved_track(user_a_id, "track-1", db_path=self.db_path))
        self.assertEqual(get_saved_tracks(user_a_id, db_path=self.db_path), [])

    def test_invalid_saved_track_data_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_track(self.user_a["user_id"], " ", "Belajar", "Fokus", db_path=self.db_path)
        with self.assertRaises(ValueError):
            get_saved_tracks("invalid", db_path=self.db_path)
        with self.assertRaises(ValueError):
            remove_saved_track(self.user_a["user_id"], " ", db_path=self.db_path)


if __name__ == "__main__":
    unittest.main()

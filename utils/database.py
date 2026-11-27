"""
database.py — Pengelolaan database SQLite untuk profil pengguna dan riwayat rekomendasi TuneCluster.

Database disimpan di `data/tunecluster_users.db` dengan empat tabel utama:
- `users`        : akun dan profil pengguna (password di-hash dengan SHA-256)
- `user_genres`  : daftar genre favorit per pengguna
- `user_history` : riwayat rekomendasi aktivitas, mood, dan track_id hasil rekomendasi
- `saved_tracks` : lagu tersimpan dari Beranda/Rekomendasi beserta metadata media
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from collections import Counter
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tunecluster_users.db"


def _hash_password(password: str) -> str:
    """Hash password menggunakan SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verifikasi kecocokan password plaintext terhadap hash SHA-256."""
    return hmac.compare_digest(_hash_password(password), password_hash)


def _bersihkan_daftar_genre(genre_list: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    """Bersihkan whitespace dan hilangkan duplikasi genre (case-insensitive) sambil menjaga urutan."""
    if not genre_list:
        return []
    hasil: list[str] = []
    terlihat: set[str] = set()
    for g in genre_list:
        teks = str(g).strip()
        if teks and teks.lower() not in terlihat:
            terlihat.add(teks.lower())
            hasil.append(teks)
    return hasil


@contextmanager
def _koneksi_db(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """
    Context manager koneksi SQLite menggunakan `sqlite3.connect(...)` dengan
    `closing` dan transaksi `with conn:` agar commit/rollback otomatis terjadi
    sebelum koneksi selalu ditutup.
    """
    target_path = Path(db_path) if db_path is not None else DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(target_path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        with conn:
            yield conn


def init_db(db_path: str | Path | None = None) -> None:
    """
    Buat database SQLite beserta tabel `users`, `user_genres`, `user_history`,
    dan `saved_tracks` jika belum ada.

    Parameters
    ----------
    db_path : str | Path | None, optional
        Path file SQLite. Jika None, menggunakan `data/tunecluster_users.db`.
    """
    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    nama_lengkap TEXT NOT NULL,
                    umur INTEGER NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_genres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    genre TEXT NOT NULL,
                    UNIQUE(user_id, genre)
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    aktivitas TEXT NOT NULL,
                    mood TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rekomendasi_json TEXT
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    track_id TEXT NOT NULL,
                    aktivitas TEXT NOT NULL,
                    mood TEXT NOT NULL,
                    cover_url TEXT,
                    preview_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, track_id)
                );
                """
            )
            saved_track_columns = {
                row["name"] for row in cursor.execute("PRAGMA table_info(saved_tracks)")
            }
            for column in ("cover_url", "preview_url"):
                if column not in saved_track_columns:
                    cursor.execute(f"ALTER TABLE saved_tracks ADD COLUMN {column} TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_genres_uid ON user_genres(user_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_history_uid ON user_history(user_id);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_tracks_uid ON saved_tracks(user_id);"
            )
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menginisialisasi database: {err}") from err


def register_user(
    username: str,
    nama_lengkap: str,
    umur: int,
    password: str,
    genre_list: list[str] | None = None,
    *,
    db_path: str | Path | None = None,
) -> tuple[bool, str]:
    """
    Daftarkan pengguna baru ke database beserta daftar genre favorit awalnya.

    Parameters
    ----------
    username : str
        Username unik pengguna.
    nama_lengkap : str
        Nama lengkap pengguna.
    umur : int
        Usia pengguna (>= 1).
    password : str
        Password plaintext (akan disimpan sebagai SHA-256 hash).
    genre_list : list[str] | None, optional
        Daftar genre favorit awal pengguna.

    Returns
    -------
    tuple[bool, str]
        `(True, pesan_sukses)` jika berhasil, atau `(False, pesan_error)` jika gagal.
    """
    username_clean = str(username).strip() if username is not None else ""
    nama_clean = str(nama_lengkap).strip() if nama_lengkap is not None else ""

    if not username_clean:
        return False, "Username tidak boleh kosong."
    if " " in username_clean:
        return False, "Username tidak boleh mengandung spasi."
    if not nama_clean:
        return False, "Nama lengkap tidak boleh kosong."

    try:
        umur_int = int(umur)
    except (TypeError, ValueError):
        return False, "Umur harus berupa bilangan bulat."
    if umur_int < 1 or umur_int > 120:
        return False, "Umur harus berada di rentang 1–120 tahun."

    if not isinstance(password, str) or not password:
        return False, "Password tidak boleh kosong."

    genres_bersih = _bersihkan_daftar_genre(genre_list)
    password_hash = _hash_password(password)

    try:
        init_db(db_path)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            sudah_ada = cursor.execute(
                "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)",
                (username_clean,),
            ).fetchone()
            if sudah_ada is not None:
                return False, f"Username '{username_clean}' sudah terdaftar."

            cursor.execute(
                """
                INSERT INTO users (username, nama_lengkap, umur, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (username_clean, nama_clean, umur_int, password_hash),
            )
            user_id = cursor.lastrowid
            if genres_bersih:
                cursor.executemany(
                    "INSERT INTO user_genres (user_id, genre) VALUES (?, ?)",
                    [(user_id, g) for g in genres_bersih],
                )
        return True, "Registrasi berhasil!"
    except sqlite3.IntegrityError:
        return False, f"Username '{username_clean}' sudah terdaftar."
    except sqlite3.Error as err:
        return False, f"Kesalahan database saat registrasi: {err}"


def login_user(
    username: str,
    password: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Verifikasi kredensial login pengguna dan perbarui `last_login`.

    Returns
    -------
    dict[str, Any] | None
        Dictionary info profil pengguna (tanpa password_hash) jika valid, atau `None`.
    """
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username_clean = username.strip()
    if not username_clean or not password:
        return None

    try:
        init_db(db_path)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                """
                SELECT user_id, password_hash
                FROM users
                WHERE LOWER(username) = LOWER(?)
                """,
                (username_clean,),
            ).fetchone()
            if row is None or not _verify_password(password, row["password_hash"]):
                return None

            user_id = int(row["user_id"])
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,),
            )

        return get_user_profile(user_id, db_path=db_path)
    except sqlite3.Error as err:
        raise RuntimeError(f"Kesalahan database saat login: {err}") from err


def get_user_profile(
    user_id: int,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Ambil seluruh informasi profil pengguna beserta daftar genre favoritnya.

    Returns
    -------
    dict[str, Any] | None
        Dictionary profil pengguna (`user_id`, `username`, `nama_lengkap`, `umur`,
        `created_at`, `last_login`, `genres`), atau `None` jika `user_id` tidak ditemukan.
    """
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None

    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                """
                SELECT user_id, username, nama_lengkap, umur, created_at, last_login
                FROM users
                WHERE user_id = ?
                """,
                (uid,),
            ).fetchone()
            if row is None:
                return None

            genre_rows = cursor.execute(
                "SELECT genre FROM user_genres WHERE user_id = ? ORDER BY id ASC",
                (uid,),
            ).fetchall()

        return {
            "user_id": int(row["user_id"]),
            "username": row["username"],
            "nama_lengkap": row["nama_lengkap"],
            "umur": int(row["umur"]),
            "created_at": row["created_at"],
            "last_login": row["last_login"],
            "genres": [r["genre"] for r in genre_rows],
        }
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal mengambil profil pengguna: {err}") from err


def update_genres(
    user_id: int,
    genre_list: list[str],
    *,
    db_path: str | Path | None = None,
) -> bool:
    """
    Perbarui daftar genre favorit pengguna dengan menghapus seluruh genre lama
    lalu menyisipkan daftar genre baru.

    Returns
    -------
    bool
        `True` jika berhasil, `False` jika `user_id` tidak ditemukan.
    """
    genres_bersih = _bersihkan_daftar_genre(genre_list)
    try:
        uid = int(user_id)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            ada = cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (uid,)
            ).fetchone()
            if ada is None:
                return False

            cursor.execute("DELETE FROM user_genres WHERE user_id = ?", (uid,))
            if genres_bersih:
                cursor.executemany(
                    "INSERT INTO user_genres (user_id, genre) VALUES (?, ?)",
                    [(uid, g) for g in genres_bersih],
                )
        return True
    except (TypeError, ValueError):
        return False
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal memperbarui genre pengguna: {err}") from err


def add_genre(
    user_id: int,
    genre: str,
    *,
    db_path: str | Path | None = None,
) -> bool:
    """
    Tambahkan satu genre ke daftar favorit pengguna.

    Returns
    -------
    bool
        `True` jika genre baru berhasil ditambahkan, `False` jika input kosong,
        pengguna tidak ditemukan, atau genre sudah ada.
    """
    if not isinstance(genre, str) or not genre.strip():
        return False
    genre_clean = genre.strip()

    try:
        uid = int(user_id)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            ada_user = cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (uid,)
            ).fetchone()
            if ada_user is None:
                return False

            sudah_ada = cursor.execute(
                "SELECT 1 FROM user_genres WHERE user_id = ? AND LOWER(genre) = LOWER(?)",
                (uid, genre_clean),
            ).fetchone()
            if sudah_ada is not None:
                return False

            cursor.execute(
                "INSERT INTO user_genres (user_id, genre) VALUES (?, ?)",
                (uid, genre_clean),
            )
        return True
    except (TypeError, ValueError, sqlite3.IntegrityError):
        return False
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menambahkan genre: {err}") from err


def remove_genre(
    user_id: int,
    genre: str,
    *,
    db_path: str | Path | None = None,
) -> bool:
    """
    Hapus satu genre dari daftar favorit pengguna.

    Returns
    -------
    bool
        `True` jika genre ditemukan dan dihapus, `False` jika tidak ada.
    """
    if not isinstance(genre, str) or not genre.strip():
        return False
    genre_clean = genre.strip()

    try:
        uid = int(user_id)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_genres WHERE user_id = ? AND LOWER(genre) = LOWER(?)",
                (uid, genre_clean),
            )
            return cursor.rowcount > 0
    except (TypeError, ValueError):
        return False
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menghapus genre: {err}") from err


def update_profile(
    user_id: int,
    nama_lengkap: str | None = None,
    umur: int | None = None,
    *,
    db_path: str | Path | None = None,
) -> bool:
    """
    Perbarui informasi profil pengguna (`nama_lengkap` dan/atau `umur`).

    Returns
    -------
    bool
        `True` jika berhasil diperbarui, `False` jika `user_id` tidak ditemukan.

    Raises
    ------
    ValueError
        Jika `nama_lengkap` kosong atau `umur` di luar rentang 1–120.
    """
    fields: list[str] = []
    values: list[Any] = []

    if nama_lengkap is not None:
        nama_clean = str(nama_lengkap).strip()
        if not nama_clean:
            raise ValueError("Nama lengkap tidak boleh kosong.")
        fields.append("nama_lengkap = ?")
        values.append(nama_clean)

    if umur is not None:
        try:
            umur_int = int(umur)
        except (TypeError, ValueError) as err:
            raise ValueError("Umur harus berupa bilangan bulat.") from err
        if umur_int < 1 or umur_int > 120:
            raise ValueError("Umur harus berada di rentang 1–120 tahun.")
        fields.append("umur = ?")
        values.append(umur_int)

    try:
        uid = int(user_id)
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            ada = cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (uid,)
            ).fetchone()
            if ada is None:
                return False

            if not fields:
                return True

            values.append(uid)
            cursor.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?",
                tuple(values),
            )
            return cursor.rowcount > 0
    except (TypeError, ValueError) as err:
        if isinstance(err, ValueError) and ("Nama" in str(err) or "Umur" in str(err)):
            raise
        return False
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal memperbarui profil pengguna: {err}") from err


def save_history(
    user_id: int,
    aktivitas: str,
    mood: str,
    rekomendasi_track_ids: list[str] | tuple[str, ...],
    *,
    db_path: str | Path | None = None,
) -> int:
    """
    Simpan riwayat rekomendasi musik ke tabel `user_history`.

    Parameters
    ----------
    user_id : int
        ID pengguna.
    aktivitas : str
        Aktivitas yang dipilih pengguna.
    mood : str
        Mood yang dipilih pengguna.
    rekomendasi_track_ids : list[str] | tuple[str, ...]
        Daftar `track_id` lagu yang direkomendasikan.

    Returns
    -------
    int
        ID baris riwayat (`id`) yang baru dibuat.
    """
    if not isinstance(aktivitas, str) or not aktivitas.strip():
        raise ValueError("Parameter 'aktivitas' tidak boleh kosong.")
    if not isinstance(mood, str) or not mood.strip():
        raise ValueError("Parameter 'mood' tidak boleh kosong.")
    if not isinstance(rekomendasi_track_ids, (list, tuple)):
        raise TypeError("Parameter 'rekomendasi_track_ids' harus berupa list atau tuple.")

    uid = int(user_id)
    track_list = [str(tid) for tid in rekomendasi_track_ids]
    rekom_json = json.dumps(track_list, ensure_ascii=False)

    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            ada = cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (uid,)
            ).fetchone()
            if ada is None:
                raise ValueError(f"User dengan user_id={uid} tidak ditemukan.")

            cursor.execute(
                """
                INSERT INTO user_history (user_id, aktivitas, mood, rekomendasi_json)
                VALUES (?, ?, ?, ?)
                """,
                (uid, aktivitas.strip(), mood.strip(), rekom_json),
            )
            return int(cursor.lastrowid)
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menyimpan riwayat rekomendasi: {err}") from err


def get_history(
    user_id: int,
    limit: int = 10,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Ambil daftar riwayat rekomendasi terbaru milik pengguna.

    Parameters
    ----------
    user_id : int
        ID pengguna.
    limit : int, default=10
        Jumlah maksimal riwayat yang diambil.

    Returns
    -------
    list[dict[str, Any]]
        List dictionary riwayat terbaru berisi `id`, `user_id`, `aktivitas`, `mood`,
        `timestamp`, `rekomendasi_track_ids` (list), dan `rekomendasi_json` (str).
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Parameter 'limit' harus berupa bilangan bulat >= 1.")

    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return []

    try:
        with _koneksi_db(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, aktivitas, mood, timestamp, rekomendasi_json
                FROM user_history
                WHERE user_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (uid, limit),
            ).fetchall()

        hasil: list[dict[str, Any]] = []
        for r in rows:
            raw_json = r["rekomendasi_json"] or "[]"
            try:
                parsed_tracks = json.loads(raw_json)
                if not isinstance(parsed_tracks, list):
                    parsed_tracks = []
            except json.JSONDecodeError:
                parsed_tracks = []

            hasil.append(
                {
                    "id": int(r["id"]),
                    "user_id": int(r["user_id"]),
                    "aktivitas": r["aktivitas"],
                    "mood": r["mood"],
                    "timestamp": r["timestamp"],
                    "rekomendasi_track_ids": parsed_tracks,
                    "rekomendasi_json": raw_json,
                }
            )
        return hasil
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal mengambil riwayat rekomendasi: {err}") from err


def save_track(
    user_id: int,
    track_id: str,
    aktivitas: str,
    mood: str,
    *,
    cover_url: str | None = None,
    preview_url: str | None = None,
    db_path: str | Path | None = None,
) -> bool:
    """Simpan lagu dan metadata media; perbarui media jika lagu sudah tersimpan."""
    if not isinstance(track_id, str) or not track_id.strip():
        raise ValueError("Parameter 'track_id' tidak boleh kosong.")
    if not isinstance(aktivitas, str) or not aktivitas.strip():
        raise ValueError("Parameter 'aktivitas' tidak boleh kosong.")
    if not isinstance(mood, str) or not mood.strip():
        raise ValueError("Parameter 'mood' tidak boleh kosong.")
    for field, value in (("cover_url", cover_url), ("preview_url", preview_url)):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"Parameter '{field}' harus berupa string atau None.")
    cover_clean = (cover_url.strip() or None) if cover_url is not None else None
    preview_clean = (preview_url.strip() or None) if preview_url is not None else None
    try:
        uid = int(user_id)
    except (TypeError, ValueError) as err:
        raise ValueError("Parameter 'user_id' harus berupa bilangan bulat.") from err

    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            exists = cursor.execute(
                "SELECT 1 FROM users WHERE user_id = ?",
                (uid,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"User dengan user_id={uid} tidak ditemukan.")

            cursor.execute(
                """
                INSERT OR IGNORE INTO saved_tracks
                    (user_id, track_id, aktivitas, mood, cover_url, preview_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    track_id.strip(),
                    aktivitas.strip(),
                    mood.strip(),
                    cover_clean,
                    preview_clean,
                ),
            )
            inserted = cursor.rowcount > 0
            if cover_clean or preview_clean:
                cursor.execute(
                    """
                    UPDATE saved_tracks
                    SET cover_url = COALESCE(?, cover_url),
                        preview_url = COALESCE(?, preview_url)
                    WHERE user_id = ? AND track_id = ?
                    """,
                    (
                        cover_clean,
                        preview_clean,
                        uid,
                        track_id.strip(),
                    ),
                )
            return inserted
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menyimpan lagu: {err}") from err


def remove_saved_track(
    user_id: int,
    track_id: str,
    *,
    db_path: str | Path | None = None,
) -> bool:
    """Hapus lagu tersimpan milik pengguna, tanpa memengaruhi pengguna lain."""
    if not isinstance(track_id, str) or not track_id.strip():
        raise ValueError("Parameter 'track_id' tidak boleh kosong.")
    try:
        uid = int(user_id)
    except (TypeError, ValueError) as err:
        raise ValueError("Parameter 'user_id' harus berupa bilangan bulat.") from err

    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM saved_tracks WHERE user_id = ? AND track_id = ?",
                (uid, track_id.strip()),
            )
            return cursor.rowcount > 0
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal menghapus lagu tersimpan: {err}") from err


def get_saved_tracks(
    user_id: int,
    aktivitas: str | None = None,
    mood: str | None = None,
    *,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Ambil lagu tersimpan pengguna dengan filter aktivitas dan/atau mood."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError) as err:
        raise ValueError("Parameter 'user_id' harus berupa bilangan bulat.") from err

    conditions = ["user_id = ?"]
    values: list[Any] = [uid]
    for column, value in (("aktivitas", aktivitas), ("mood", mood)):
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(f"Filter '{column}' harus berupa string atau None.")
            if value.strip():
                conditions.append(f"{column} = ?")
                values.append(value.strip())

    query = f"""
        SELECT id, user_id, track_id, aktivitas, mood, cover_url, preview_url, created_at
        FROM saved_tracks
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC, id DESC
    """
    try:
        with _koneksi_db(db_path) as conn:
            rows = conn.execute(query, tuple(values)).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal mengambil lagu tersimpan: {err}") from err


def get_user_stats(
    user_id: int,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Hitung statistik aktivitas & preferensi pengguna.

    Returns
    -------
    dict[str, Any]
        Dictionary berisi:
        - `total_rekomendasi` (int): total sesi rekomendasi di `user_history`
        - `total_lagu_direkomendasikan` (int): total akumulasi track_id dari riwayat
        - `jumlah_genre` (int): jumlah genre favorit tersimpan di `user_genres`
        - `genre_terfavorit` (str | None): genre favorit utama/pertama pengguna
        - `daftar_genre_favorit` (list[str]): seluruh daftar genre favorit pengguna
        - `aktivitas_terfavorit` (str | None): aktivitas terbanyak di `user_history`
        - `mood_terfavorit` (str | None): mood terbanyak di `user_history`
        - `distribusi_aktivitas` (dict[str, int]): jumlah rekomendasi per aktivitas
    """
    kosong: dict[str, Any] = {
        "total_rekomendasi": 0,
        "total_lagu_direkomendasikan": 0,
        "jumlah_genre": 0,
        "genre_terfavorit": None,
        "daftar_genre_favorit": [],
        "aktivitas_terfavorit": None,
        "mood_terfavorit": None,
        "distribusi_aktivitas": {},
    }

    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return kosong

    try:
        with _koneksi_db(db_path) as conn:
            cursor = conn.cursor()
            genre_rows = cursor.execute(
                "SELECT genre FROM user_genres WHERE user_id = ? ORDER BY id ASC",
                (uid,),
            ).fetchall()
            history_rows = cursor.execute(
                """
                SELECT aktivitas, mood, rekomendasi_json
                FROM user_history
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (uid,),
            ).fetchall()

        daftar_genre = [r["genre"] for r in genre_rows]
        total_rekom = len(history_rows)

        aktivitas_counts: Counter[str] = Counter()
        mood_counts: Counter[str] = Counter()
        total_lagu = 0

        for r in history_rows:
            aktivitas_counts[r["aktivitas"]] += 1
            mood_counts[r["mood"]] += 1
            if r["rekomendasi_json"]:
                try:
                    tracks = json.loads(r["rekomendasi_json"])
                    if isinstance(tracks, list):
                        total_lagu += len(tracks)
                except json.JSONDecodeError:
                    pass

        aktivitas_fav = aktivitas_counts.most_common(1)[0][0] if aktivitas_counts else None
        mood_fav = mood_counts.most_common(1)[0][0] if mood_counts else None

        return {
            "total_rekomendasi": total_rekom,
            "total_lagu_direkomendasikan": total_lagu,
            "jumlah_genre": len(daftar_genre),
            "genre_terfavorit": daftar_genre[0] if daftar_genre else None,
            "daftar_genre_favorit": daftar_genre,
            "aktivitas_terfavorit": aktivitas_fav,
            "mood_terfavorit": mood_fav,
            "distribusi_aktivitas": dict(aktivitas_counts),
        }
    except sqlite3.Error as err:
        raise RuntimeError(f"Gagal mengambil statistik pengguna: {err}") from err


if __name__ == "__main__":
    import tempfile

    print("=== PENGUJIAN utils/database.py ===")
    # Pastikan database utama terinisialisasi tanpa data dummy
    init_db()
    print(f"Database utama terinisialisasi di: {DB_PATH} (ada={DB_PATH.exists()})")

    # Jalankan seluruh pengujian CRUD pada database sementara agar DB utama tetap bersih
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_users.db"
        init_db(test_db)

        # 1. Register user
        ok, msg = register_user(
            "alya_p",
            "Alya Putri",
            24,
            "rahasia123",
            ["Rock", "Synth-pop", "R&B", "rock"],
            db_path=test_db,
        )
        assert ok is True, msg
        print("Register valid       :", ok, "|", msg)

        # 2. Register duplikat (case-insensitive)
        ok_dup, msg_dup = register_user(
            "Alya_P", "Alya Lain", 22, "pass", ["Jazz"], db_path=test_db
        )
        assert ok_dup is False
        print("Register duplikat    :", ok_dup, "|", msg_dup)

        # 3. Login salah & login benar
        assert login_user("alya_p", "salah", db_path=test_db) is None
        user = login_user("alya_p", "rahasia123", db_path=test_db)
        assert user is not None
        assert "password_hash" not in user
        assert user["genres"] == ["Rock", "Synth-pop", "R&B"]
        uid = user["user_id"]
        print("Login valid          :", user["username"], "| genres:", user["genres"])

        # 4. get_user_profile & update_profile
        assert update_profile(uid, nama_lengkap="Alya Putri S.", umur=25, db_path=test_db)
        profil = get_user_profile(uid, db_path=test_db)
        assert profil is not None and profil["nama_lengkap"] == "Alya Putri S." and profil["umur"] == 25
        print("Update profil        :", profil["nama_lengkap"], "| umur:", profil["umur"])

        # 5. add_genre, remove_genre, update_genres
        assert add_genre(uid, "Jazz", db_path=test_db) is True
        assert add_genre(uid, "jazz", db_path=test_db) is False  # sudah ada
        assert remove_genre(uid, "R&B", db_path=test_db) is True
        assert get_user_profile(uid, db_path=test_db)["genres"] == ["Rock", "Synth-pop", "Jazz"]

        assert update_genres(uid, ["Classical", "Ambient"], db_path=test_db) is True
        assert get_user_profile(uid, db_path=test_db)["genres"] == ["Classical", "Ambient"]
        print("Update genres        :", get_user_profile(uid, db_path=test_db)["genres"])

        # 6. save_history & get_history
        h1 = save_history(uid, "Belajar", "Fokus", ["t1", "t2", "t3"], db_path=test_db)
        h2 = save_history(uid, "Olahraga", "Energik", ["t4", "t5"], db_path=test_db)
        h3 = save_history(uid, "Belajar", "Tenang/Calm", ["t6", "t7", "t8"], db_path=test_db)
        assert h1 < h2 < h3

        riwayat = get_history(uid, limit=2, db_path=test_db)
        assert len(riwayat) == 2
        assert riwayat[0]["id"] == h3 and riwayat[0]["rekomendasi_track_ids"] == ["t6", "t7", "t8"]
        print("Riwayat terbaru (2)  :", [(r["aktivitas"], r["mood"], r["rekomendasi_track_ids"]) for r in riwayat])

        # 7. get_user_stats
        stats = get_user_stats(uid, db_path=test_db)
        assert stats["total_rekomendasi"] == 3
        assert stats["total_lagu_direkomendasikan"] == 8
        assert stats["genre_terfavorit"] == "Classical"
        assert stats["aktivitas_terfavorit"] == "Belajar"
        print("Statistik user       :", stats)

    print("\nSEMUA PENGUJIAN database.py LULUS!")

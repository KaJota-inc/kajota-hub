"""SQLite persistence layer.

Schema is a direct mirror of the React app's localStorage keys in
``src/data/storage.ts`` — but normalised so each row can be independently
addressed and audio takes have a first-class table.

Design choices:

* **Collections stored as JSON documents** (``sessions``, ``vocab``,
  ``writing_drafts``, ``band_mocks``, ``drill_checkoffs``) under the ``kv``
  table. The whole-collection sync model keeps the backend tiny — the client
  continues to read and write collections atomically, exactly as it did
  against localStorage.
* **Audio takes** live in their own table because they are large binary
  blobs that must be streamed, not JSON-encoded.
* **Singletons** (``target_bands``, ``plan_start``, feature flags) live in
  the ``kv`` table too — same table, string keys.
* **Updated_at** on every write so we can later layer last-write-wins
  conflict resolution if the single-user assumption changes.

The database file lives at ``$KH_IELTS_DB_PATH`` or
``/srv/data/ielts-sda-prep-api.sqlite3`` in production (Render disk mount),
``./ielts-sda-prep-api.sqlite3`` in local dev.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_takes (
  id             TEXT PRIMARY KEY,
  session_id     TEXT,
  kind           TEXT,
  duration_sec   INTEGER,
  content_type   TEXT NOT NULL,
  size_bytes     INTEGER NOT NULL,
  created_at     INTEGER NOT NULL,
  blob           BLOB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audio_session ON audio_takes(session_id);
CREATE INDEX IF NOT EXISTS idx_audio_created ON audio_takes(created_at DESC);
"""


def db_path() -> Path:
    override = os.environ.get("KH_IELTS_DB_PATH")
    if override:
        p = Path(override)
    else:
        # Default to a persistent disk mount in production, local file in dev.
        default = "/srv/data/ielts-sda-prep-api.sqlite3" if Path("/srv/data").is_dir() \
            else "./ielts-sda-prep-api.sqlite3"
        p = Path(default)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_initialised = False


def init() -> None:
    global _initialised
    if _initialised:
        return
    with connect() as con:
        con.executescript(SCHEMA)
    _initialised = True


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(str(db_path()), isolation_level=None, timeout=10)
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA synchronous = NORMAL;")
    con.execute("PRAGMA foreign_keys = ON;")
    try:
        yield con
    finally:
        con.close()


def now_ms() -> int:
    return int(time.time() * 1000)


# ---- KV helpers (collections + singletons live here) --------------------


def kv_get(key: str) -> str | None:
    with connect() as con:
        row = con.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None


def kv_set(key: str, value: str) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, value, now_ms()),
        )


def kv_delete(key: str) -> None:
    with connect() as con:
        con.execute("DELETE FROM kv WHERE key = ?", (key,))


def kv_all() -> dict[str, str]:
    with connect() as con:
        rows = con.execute("SELECT key, value FROM kv").fetchall()
        return {k: v for k, v in rows}

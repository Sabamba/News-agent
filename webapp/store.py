"""SQLite persistence for the Company Voice Blog Generator.

The database holds collected research sources, the analysed company voice
profile, and generated blog posts (with their revision history). It never
stores the user's API key — that lives only in the browser and is sent per
request.
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

DB_PATH = os.environ.get("APP_DB", str(Path(__file__).parent / "data" / "app.db"))
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# SQLite connections aren't shareable across threads, so we open one per call
# and serialise writes with a lock. Traffic is low (single-user tool), so this
# is plenty.
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL,
                title      TEXT,
                content    TEXT,
                kind       TEXT NOT NULL DEFAULT 'data',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS posts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT,
                content    TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS revisions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                feedback   TEXT,
                content    TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


# --- Sources -------------------------------------------------------------

def add_source(url: str, title: str, content: str, kind: str = "data") -> dict:
    with _lock, _conn() as conn:
        cur = conn.execute(
            "INSERT INTO sources (url, title, content, kind) VALUES (?, ?, ?, ?)",
            (url, title, content, kind),
        )
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def get_source(source_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None


def list_sources(kind: str | None = None) -> list[dict]:
    with _conn() as conn:
        if kind:
            rows = conn.execute(
                "SELECT * FROM sources WHERE kind = ? ORDER BY created_at DESC", (kind,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def delete_source(source_id: int) -> None:
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))


# --- Settings (voice profile, etc.) -------------------------------------

def set_setting(key: str, value) -> None:
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )


def get_setting(key: str, default=None):
    with _conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default


# --- Posts & revisions ---------------------------------------------------

def add_post(title: str, content: str) -> dict:
    with _lock, _conn() as conn:
        cur = conn.execute(
            "INSERT INTO posts (title, content) VALUES (?, ?)", (title, content)
        )
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (cur.lastrowid,)).fetchone()
        post = dict(row)
        post["revisions"] = []
        return post


def get_post(post_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None
        post = dict(row)
        revs = conn.execute(
            "SELECT * FROM revisions WHERE post_id = ? ORDER BY created_at ASC", (post_id,)
        ).fetchall()
        post["revisions"] = [dict(r) for r in revs]
        return post


def list_posts() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_post(post_id: int, title: str, content: str) -> dict:
    with _lock, _conn() as conn:
        conn.execute(
            "UPDATE posts SET title = ?, content = ?, updated_at = datetime('now') WHERE id = ?",
            (title, content, post_id),
        )
    return get_post(post_id)


def add_revision(post_id: int, feedback: str, content: str) -> None:
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO revisions (post_id, feedback, content) VALUES (?, ?, ?)",
            (post_id, feedback, content),
        )


def delete_post(post_id: int) -> None:
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM revisions WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))

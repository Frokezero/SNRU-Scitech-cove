"""
database.py — Unified DB adapter
  • Production (Render): uses PostgreSQL via DATABASE_URL env var
  • Local development:   uses SQLite (database.sqlite)

The public API is identical in both modes so app.py requires zero changes.
SQLite uses '?' placeholders; psycopg2 uses '%s'.
The wrapper converts automatically.
"""
import os
import re
import sqlite3
import json

# ── Detect environment ────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Render gives  postgres://...  but psycopg2 needs  postgresql://...
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = bool(DATABASE_URL)

# ── SQLite fallback path ──────────────────────────────────────────────────────
_DATA_DIR = '/data' if os.path.isdir('/data') else '.'
SQLITE_FILE = os.path.join(_DATA_DIR, 'database.sqlite')


def _sqlite_to_pg(sql: str) -> str:
    """Convert SQLite-style '?' placeholders → psycopg2 '%s'."""
    return sql.replace('?', '%s')


# ══════════════════════════════════════════════════════════════════════════════
#  PostgreSQL connection wrapper (mimics sqlite3.Connection interface)
# ══════════════════════════════════════════════════════════════════════════════
class PgConnection:
    """Thin wrapper around a psycopg2 connection that behaves like sqlite3."""

    def __init__(self, raw_conn):
        self._conn = raw_conn
        self._cursor = raw_conn.cursor()

    # ── sqlite3-compatible helpers ───────────────────────────────────────────
    def execute(self, sql, params=()):
        sql = _sqlite_to_pg(sql)
        self._cursor.execute(sql, params)
        return PgCursor(self._cursor)

    def cursor(self):
        new_cur = self._conn.cursor()
        return PgCursor(new_cur, self._conn)

    def commit(self):
        self._conn.commit()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class PgCursor:
    """Cursor wrapper that converts SQL and returns dict-like rows."""

    def __init__(self, raw_cursor, conn=None):
        self._cur = raw_cursor
        self._conn = conn

    def execute(self, sql, params=()):
        sql = _sqlite_to_pg(sql)
        self._cur.execute(sql, params)
        return self

    def executemany(self, sql, seq):
        sql = _sqlite_to_pg(sql)
        self._cur.executemany(sql, seq)

    def fetchall(self):
        rows = self._cur.fetchall()
        if rows and self._cur.description:
            cols = [d[0] for d in self._cur.description]
            return [_DictRow(dict(zip(cols, r))) for r in rows]
        return rows or []

    def fetchone(self):
        row = self._cur.fetchone()
        if row and self._cur.description:
            cols = [d[0] for d in self._cur.description]
            return _DictRow(dict(zip(cols, row)))
        return row

    @property
    def lastrowid(self):
        # PostgreSQL: fetch last inserted id via RETURNING or lastval()
        try:
            self._cur.execute('SELECT lastval()')
            return self._cur.fetchone()[0]
        except Exception:
            return None

    @property
    def rowcount(self):
        return self._cur.rowcount

    def commit(self):
        if self._conn:
            self._conn.commit()

    def close(self):
        self._cur.close()


class _DictRow(dict):
    """dict subclass that also supports attribute-style and index access."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def keys(self):
        return super().keys()


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════
def get_db_connection():
    if USE_POSTGRES:
        import psycopg2
        raw = psycopg2.connect(DATABASE_URL)
        raw.autocommit = False
        return PgConnection(raw)
    else:
        conn = sqlite3.connect(SQLITE_FILE, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn


# ══════════════════════════════════════════════════════════════════════════════
#  Schema initialisation
# ══════════════════════════════════════════════════════════════════════════════
_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    major TEXT,
    role TEXT NOT NULL DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT,
    category TEXT,
    location TEXT,
    owner TEXT,
    description TEXT,
    registration_open INTEGER DEFAULT 0,
    max_participants INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS participations (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    student_name TEXT,
    major TEXT,
    event_id TEXT,
    event_title TEXT,
    event_date TEXT,
    score INTEGER DEFAULT 0,
    timestamp TEXT,
    image_url TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(username) REFERENCES users(username),
    FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS registrations (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_title TEXT,
    event_date TEXT,
    username TEXT NOT NULL,
    name TEXT,
    major TEXT,
    email TEXT,
    timestamp TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(event_id) REFERENCES events(id),
    FOREIGN KEY(username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    major TEXT,
    role TEXT NOT NULL DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT,
    category TEXT,
    location TEXT,
    owner TEXT,
    description TEXT,
    registration_open INTEGER DEFAULT 0,
    max_participants INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS participations (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    student_name TEXT,
    major TEXT,
    event_id TEXT,
    event_title TEXT,
    event_date TEXT,
    score INTEGER DEFAULT 0,
    timestamp TEXT,
    image_url TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(username) REFERENCES users(username),
    FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE TABLE IF NOT EXISTS registrations (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    event_title TEXT,
    event_date TEXT,
    username TEXT NOT NULL,
    name TEXT,
    major TEXT,
    email TEXT,
    timestamp TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY(event_id) REFERENCES events(id),
    FOREIGN KEY(username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
);
"""


def init_db():
    conn = get_db_connection()
    if USE_POSTGRES:
        cur = conn.cursor()
        for stmt in _SCHEMA_PG.strip().split(';\n\n'):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        conn.commit()
    else:
        # SQLite supports executing the whole script at once
        conn.executescript(_SCHEMA_SQLITE)
    conn.close()


if __name__ == '__main__':
    init_db()
    mode = 'PostgreSQL' if USE_POSTGRES else 'SQLite'
    print(f"Database initialised successfully ({mode}).")

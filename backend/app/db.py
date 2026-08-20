import os
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager

# DATA_DIR lets production hosting point this at a persistent disk mounted
# outside the code directory (e.g. Render's disk mounts would otherwise hide
# backend/app/* if pointed at backend/ itself). Defaults to alongside the
# code for local dev.
_DATA_DIR = os.environ.get("DATA_DIR")
DB_PATH = Path(_DATA_DIR) / "data.db" if _DATA_DIR else Path(__file__).resolve().parent.parent / "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    max_attempts INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, name)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    attempt_number INTEGER NOT NULL,
    draft_text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    criteria_result TEXT NOT NULL,
    persona_reactions TEXT NOT NULL,
    is_final INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, attempt_number)
);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def dumps(obj):
    return json.dumps(obj)


def loads(text, default=None):
    if text is None:
        return default
    return json.loads(text)

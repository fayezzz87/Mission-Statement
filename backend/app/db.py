import os
import json
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (now()::text),
    max_attempts INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (now()::text),
    UNIQUE(session_id, name)
);

CREATE TABLE IF NOT EXISTS attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    attempt_number INTEGER NOT NULL,
    draft_text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    criteria_result TEXT NOT NULL,
    persona_reactions TEXT NOT NULL,
    is_final INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (now()::text),
    UNIQUE(student_id, attempt_number)
);
"""


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)


class _CursorWrapper:
    """Makes a psycopg2 cursor behave like the sqlite3 `conn.execute(...)`
    pattern the routes are written against: '?' placeholders, chained
    .fetchone()/.fetchall(), and a `.lastrowid` populated via RETURNING id."""

    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None

    def execute(self, sql, params=()):
        pg_sql = sql.replace("?", "%s")
        self._cur.execute(pg_sql, params)
        if "returning" in sql.lower():
            row = self._cur.fetchone()
            self.lastrowid = row["id"] if row else None
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


@contextmanager
def get_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()
    wrapper = _CursorWrapper(cur)
    try:
        yield wrapper
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
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

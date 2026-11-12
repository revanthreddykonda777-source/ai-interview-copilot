"""Database connections: Postgres when DATABASE_URL is set, otherwise local SQLite.

The app's SQL is written for SQLite (``?`` placeholders, ``INSERT OR IGNORE``).
On Postgres a thin wrapper translates those, so the rest of the code doesn't care
which database it is talking to. Rows support ``row["column"]`` on both.
"""
import os
import sqlite3
import threading

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQLITE_PATH = os.path.join(BASE_DIR, "data", "database.db")

_pool = None
_pool_lock = threading.Lock()


def database_url():
    return (os.getenv("DATABASE_URL") or "").strip()


def is_postgres():
    return database_url().startswith(("postgres://", "postgresql://"))


class PgConnection:
    """Gives a psycopg connection the small sqlite3-style API the app uses."""

    def __init__(self, conn, pool=None):
        self._conn = conn
        self._pool = pool

    @staticmethod
    def _sql(sql):
        sql = sql.replace("%", "%%").replace("?", "%s")
        if "INSERT OR IGNORE" in sql:
            sql = sql.replace("INSERT OR IGNORE", "INSERT").rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        return sql

    def execute(self, sql, params=()):
        return self._conn.execute(self._sql(sql), params)

    def executemany(self, sql, seq_of_params):
        with self._conn.cursor() as cur:
            cur.executemany(self._sql(sql), list(seq_of_params))

    def cursor(self):
        return self

    def commit(self):
        self._conn.commit()

    def close(self):
        if self._pool is not None:
            # End any read-only transaction ourselves so the pool doesn't warn, then hand it back.
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._pool.putconn(self._conn)
            self._pool = None
        else:
            self._conn.close()


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                from psycopg.rows import dict_row
                from psycopg_pool import ConnectionPool

                _pool = ConnectionPool(
                    database_url(),
                    min_size=1,
                    max_size=5,
                    kwargs={"row_factory": dict_row},
                    # Neon suspends idle databases; verify a pooled connection before use.
                    check=ConnectionPool.check_connection,
                    max_idle=240,
                    open=True,
                )
    return _pool


def connect(sqlite_path=None):
    """Open a connection; callers must close() it."""
    if is_postgres():
        pool = _get_pool()
        return PgConnection(pool.getconn(), pool)
    path = sqlite_path or SQLITE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

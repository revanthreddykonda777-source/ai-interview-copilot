"""Inspect all tables, row counts, and question topics in data/database.db."""

import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import DEFAULT_DB_PATH


def inspect_database(db_path=DEFAULT_DB_PATH):
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Database: {db_path}\n")
    tables = [
        r["name"]
        for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
        ).fetchall()
    ]

    print("=== TABLES & ROW COUNTS ===")
    for table in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cols = [c["name"] for c in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        print(f"- {table} ({count} rows): {', '.join(cols)}")

    print("\n=== USERS (PASSWORDS MASKED) ===")
    users = cursor.execute("SELECT id, fullname, email, role, password FROM users ORDER BY id").fetchall()
    if not users:
        print("  (no users)")
    for u in users:
        scheme = u["password"].split(":", 1)[0] if isinstance(u["password"], str) and ":" in u["password"] else "UNHASHED"
        print(f"  id={u['id']} | {u['fullname']} <{u['email']}> | role={u['role']} | password=[{scheme} hashed]")

    print("\n=== QUESTIONS BY TOPIC ===")
    topic_rows = cursor.execute(
        "SELECT topic_id, COUNT(*) AS cnt FROM questions GROUP BY topic_id ORDER BY topic_id"
    ).fetchall()
    for tr in topic_rows:
        print(f"  {tr['topic_id']}: {tr['cnt']} questions")

    conn.close()


if __name__ == "__main__":
    inspect_database()

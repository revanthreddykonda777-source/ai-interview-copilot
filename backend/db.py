from werkzeug.security import generate_password_hash

from backend.database import SQLITE_PATH, connect, is_postgres

DEFAULT_DB_PATH = SQLITE_PATH
HASH_PREFIXES = ("scrypt:", "pbkdf2:")

# Columns added to `users` after the first release; older databases get them on startup.
USER_MIGRATION_COLUMNS = {
    "role": "TEXT NOT NULL DEFAULT 'user'",
    "resume_feedback": "TEXT",
    "target_role": "TEXT",
    "reset_token_hash": "TEXT",
    "reset_token_expires": "INTEGER",
}


def _enforce_password_hashing(conn):
    """Ensure every stored user password uses a strong salted hash, never plaintext."""
    rows = conn.execute("SELECT id, password FROM users").fetchall()
    for row in rows:
        pwd = row["password"]
        if not isinstance(pwd, str) or not pwd.startswith(HASH_PREFIXES):
            hashed = generate_password_hash(pwd or "", method="scrypt")
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, row["id"]))


def _schema(pk, ts):
    return [
        f"""
        CREATE TABLE IF NOT EXISTS users(
            id {pk},
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            resume_text TEXT,
            resume_skills TEXT,
            resume_feedback TEXT,
            target_role TEXT,
            reset_token_hash TEXT,
            reset_token_expires INTEGER
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS questions(
            id {pk},
            topic_id TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            type TEXT DEFAULT 'theoretical',
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint TEXT NOT NULL
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS sessions(
            id {pk},
            user_id INTEGER NOT NULL,
            topic_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            date {ts} DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS bookmarks(
            id {pk},
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS question_attempts(
            id {pk},
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            topic_id TEXT NOT NULL,
            passed INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS coach_attempts(
            id {pk},
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            feedback TEXT NOT NULL,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_attempts_user ON question_attempts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_coach_user ON coach_attempts(user_id)",
    ]


def create_database(db_path=DEFAULT_DB_PATH):
    conn = connect(db_path)
    try:
        if is_postgres():
            # TIMESTAMP(0): whole seconds, so dates display like SQLite's ("2026-11-12 17:22:36").
            statements = _schema("SERIAL PRIMARY KEY", "TIMESTAMP(0)")
        else:
            statements = _schema("INTEGER PRIMARY KEY AUTOINCREMENT", "TIMESTAMP")
        for stmt in statements:
            conn.execute(stmt)

        if is_postgres():
            for col, decl in USER_MIGRATION_COLUMNS.items():
                conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {decl}")
        else:
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            for col, decl in USER_MIGRATION_COLUMNS.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")

        _enforce_password_hashing(conn)
        conn.commit()
    finally:
        conn.close()

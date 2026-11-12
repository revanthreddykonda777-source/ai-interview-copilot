import os
import sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "database.db")
HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def _enforce_password_hashing(cursor):
    """Ensure every stored user password uses a strong salted hash, never plaintext."""
    rows = cursor.execute("SELECT id, password FROM users").fetchall()
    for user_id, pwd in rows:
        if not isinstance(pwd, str) or not pwd.startswith(HASH_PREFIXES):
            hashed = generate_password_hash(pwd or "", method="scrypt")
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))


def create_database(db_path=DEFAULT_DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    )
    """)

    # Safely migrate existing databases missing columns
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "resume_feedback" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN resume_feedback TEXT")
    if "target_role" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN target_role TEXT")
    if "reset_token_hash" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token_hash TEXT")
    if "reset_token_expires" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expires INTEGER")

    _enforce_password_hashing(cursor)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        type TEXT DEFAULT 'theoretical',
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        hint TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic_id TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_attempts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        topic_id TEXT NOT NULL,
        passed INTEGER NOT NULL,
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coach_attempts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        score INTEGER NOT NULL DEFAULT 0,
        feedback TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

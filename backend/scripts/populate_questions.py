"""Seed the question bank: 15 core tracks from question_bank.json + 5 AI role tracks."""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import connect
from backend.db import DEFAULT_DB_PATH
from backend.scripts.seed_ai_roles import seed_ai_roles

QUESTION_BANK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "question_bank.json")


def load_question_bank(path=QUESTION_BANK_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def populate_all_questions(db_path=DEFAULT_DB_PATH):
    bank = load_question_bank()
    conn = connect(db_path)
    total_inserted = 0
    try:
        for topic_id, questions in bank.items():
            # Only replace this track's rows, so resume_<user_id> questions are never touched.
            conn.execute("DELETE FROM questions WHERE topic_id = ?", (topic_id,))
            rows = [
                (topic_id, q["difficulty"], q["type"], q["question"], q["answer"], q["hint"])
                for q in questions
            ]
            conn.executemany(
                "INSERT INTO questions (topic_id, difficulty, type, question, answer, hint) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            total_inserted += len(rows)
        conn.commit()
    finally:
        conn.close()

    total_ai = seed_ai_roles(db_path=db_path)
    print(f"Seeded {total_inserted} core + {total_ai} AI role questions.")
    return total_inserted + total_ai


if __name__ == "__main__":
    populate_all_questions()

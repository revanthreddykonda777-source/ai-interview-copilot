"""CLI utility to inspect users or promote/demote an admin account."""

import argparse
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import DEFAULT_DB_PATH, create_database


def main():
    parser = argparse.ArgumentParser(description="Manage admin roles in AI Interview Copilot.")
    parser.add_argument("--list", action="store_true", help="List all registered users and roles")
    parser.add_argument("--promote", metavar="EMAIL", help="Promote a user email to admin")
    parser.add_argument("--demote", metavar="EMAIL", help="Demote an admin email back to user")
    args = parser.parse_args()

    create_database(DEFAULT_DB_PATH)
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row

    if args.promote:
        email = args.promote.strip().lower()
        cur = conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
        conn.commit()
        print(f"Promoted {email} to admin." if cur.rowcount else f"User not found: {email}")

    if args.demote:
        email = args.demote.strip().lower()
        cur = conn.execute("UPDATE users SET role = 'user' WHERE email = ?", (email,))
        conn.commit()
        print(f"Demoted {email} to user." if cur.rowcount else f"User not found: {email}")

    if args.list or (not args.promote and not args.demote):
        rows = conn.execute("SELECT id, fullname, email, role FROM users ORDER BY id").fetchall()
        for r in rows:
            print(f"id={r['id']} | {r['fullname']} <{r['email']}> | role={r['role']}")

    conn.close()


if __name__ == "__main__":
    main()


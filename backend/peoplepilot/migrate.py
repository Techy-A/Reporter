"""One-off migration, run as the database OWNER before the apps start.

    python -m peoplepilot.migrate

Creates tables, then (on Postgres) the per-process roles and row-level-security policies from
migrations/postgres_rls.sql. Role passwords are taken from each process's database URL, so the
SQL file never needs editing.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from .db import get_engine, init_db

SQL = Path(__file__).resolve().parent.parent / "migrations" / "postgres_rls.sql"
ROLE_ENV = {
    "admin": "PP_ADMIN_DATABASE_URL",
    "portal": "PP_PORTAL_DATABASE_URL",
    "bot": "PP_BOT_DATABASE_URL",
    "worker": "PP_WORKER_DATABASE_URL",
}


def main() -> None:
    init_db()
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        print("Tables created (SQLite: row-level security not applicable).")
        return
    sql = SQL.read_text(encoding="utf-8")
    for role, env in ROLE_ENV.items():
        url = os.environ.get(env)
        if not url:
            raise SystemExit(f"{env} is required so the pp_{role} role gets a real password")
        password = make_url(url).password
        if not password or password.startswith("CHANGE_ME"):
            raise SystemExit(f"Set a real password in {env}")
        sql = sql.replace(f"'CHANGE_ME_{role}'", "'" + password.replace("'", "''") + "'")
    with engine.begin() as conn:
        conn.execute(text(sql))
        # Roles already existed from an earlier run: keep their passwords in sync.
        for role, env in ROLE_ENV.items():
            pw = make_url(os.environ[env]).password.replace("'", "''")
            conn.execute(text(f"ALTER ROLE pp_{role} PASSWORD '{pw}'"))
    print("Tables, roles and row-level security policies are in place.")


if __name__ == "__main__":
    main()

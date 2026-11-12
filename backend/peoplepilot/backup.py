"""Back up the database and show what must be backed up by hand.

    python -m peoplepilot.backup [folder]        (default folder: ./backups)

SQLite: a consistent copy made with SQLite's own backup API (safe while the apps are running).
Postgres: runs `pg_dump` (must be installed) with the owner URL in PP_DATABASE_URL.

This does NOT back up .env. Keep an offline copy of PP_DATA_KEY: without it the encrypted columns
(phone numbers, tickets, channel tokens) in any backup cannot be read.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from .config import get_settings


def main(folder: str = "backups") -> Path:
    url = make_url(get_settings().database_url)
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if url.get_backend_name() == "sqlite":
        out = out_dir / f"reporter-{stamp}.db"
        src, dst = sqlite3.connect(url.database), sqlite3.connect(out)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    else:
        out = out_dir / f"reporter-{stamp}.sql"
        subprocess.run(
            ["pg_dump", "--no-owner", "-f", str(out), url.render_as_string(hide_password=False)],
            check=True,
        )
    print(f"Backup written to {out}")
    print("Reminder: also keep PP_DATA_KEY safe offline; backups are unreadable without it.")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:2])

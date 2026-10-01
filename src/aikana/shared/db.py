"""The single `fastlite` Database connection every repository_sqlite.py imports, per ../architecture.sdd."""

from pathlib import Path

from fastlite import Database, database

DB_PATH = Path("/data/app.db")

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = database(DB_PATH)
    return _db

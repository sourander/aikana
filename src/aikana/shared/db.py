"""@create_database opens the `fastlite` Database main.py injects into repositories, per ../architecture.sdd."""

from pathlib import Path

from fastlite import Database, database

DB_PATH = Path("/data/app.db")


def create_database(path: Path = DB_PATH) -> Database:
    """Open the `fastlite` Database at `path`, creating the parent directory when it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return database(path)

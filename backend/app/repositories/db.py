import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def database_path(database_url: str) -> Path:
    value = database_url.removeprefix("sqlite:///")
    path = Path(value)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Database:
    def __init__(self, database_url: str):
        self.path = database_path(database_url)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS deals (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    company TEXT NOT NULL,
                    contact_name TEXT,
                    location TEXT,
                    stage TEXT NOT NULL,
                    value REAL,
                    decision_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    deal_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    interaction_date TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    source TEXT,
                    participants_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outcomes (
                    id TEXT PRIMARY KEY,
                    deal_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(deals)").fetchall()}
            if "contact_name" not in columns:
                conn.execute("ALTER TABLE deals ADD COLUMN contact_name TEXT")
            if "location" not in columns:
                conn.execute("ALTER TABLE deals ADD COLUMN location TEXT")


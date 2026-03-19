"""SQLite connection and schema management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from .exceptions import DatabaseInitializationError

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_meta(key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS sleep_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes INTEGER CHECK(duration_minutes IS NULL OR duration_minutes >= 0),
    quality_score INTEGER CHECK(quality_score IS NULL OR quality_score BETWEEN 1 AND 5),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(end_time IS NULL OR end_time >= start_time)
);

CREATE INDEX IF NOT EXISTS idx_sleep_sessions_start_time
ON sleep_sessions(start_time DESC);

CREATE INDEX IF NOT EXISTS idx_sleep_sessions_end_time
ON sleep_sessions(end_time DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sleep_sessions_single_active
ON sleep_sessions((1))
WHERE end_time IS NULL;
"""


class DatabaseManager:
    """Owns DB path, connection settings and schema bootstrap."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path).expanduser()
        if not path.is_absolute():
            path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute("PRAGMA busy_timeout = 5000;")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Transaction-scoped connection."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create database schema if missing."""
        try:
            with self.connection() as conn:
                conn.executescript(SCHEMA_SQL)
        except sqlite3.Error as exc:
            raise DatabaseInitializationError(
                f"初始化 SQLite 数据库结构失败（{self.db_path}）：{exc}"
            ) from exc

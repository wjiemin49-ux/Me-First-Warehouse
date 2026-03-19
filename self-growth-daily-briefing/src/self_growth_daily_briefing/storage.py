from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import SendResult, SourceItem


def _theme_hash(theme: str) -> str:
    return hashlib.sha256(theme.strip().lower().encode("utf-8")).hexdigest()


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS seen_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    keyword_score REAL NOT NULL,
                    UNIQUE(canonical_url, published_at)
                );

                CREATE TABLE IF NOT EXISTS themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_date TEXT NOT NULL,
                    theme_hash TEXT NOT NULL UNIQUE,
                    theme TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_date TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    artifact_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS send_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_date TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def record_seen_items(self, items: list[SourceItem]) -> None:
        if not items:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO seen_items (
                    canonical_url, title, published_at, source_name, collected_at, keyword_score
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.canonical_url,
                        item.title,
                        item.published_at.isoformat(),
                        item.source_name,
                        item.collected_at.isoformat(),
                        item.keyword_score,
                    )
                    for item in items
                ],
            )

    def recent_themes(self, days: int, now: datetime | None = None) -> list[str]:
        reference_time = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
        cutoff = (reference_time - timedelta(days=days)).date().isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT theme FROM themes WHERE issue_date >= ? ORDER BY issue_date DESC",
                (cutoff,),
            ).fetchall()
        return [str(row["theme"]) for row in rows]

    def was_theme_recent(self, theme: str, days: int, now: datetime | None = None) -> bool:
        target = _theme_hash(theme)
        recent = {_theme_hash(item) for item in self.recent_themes(days, now=now)}
        return target in recent

    def record_theme(self, issue_date: str, theme: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO themes (issue_date, theme_hash, theme) VALUES (?, ?, ?)",
                (issue_date, _theme_hash(theme), theme),
            )

    def record_run(self, issue_date: str, status: str, artifact_path: Path | None = None, error: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (issue_date, status, artifact_path, error, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(issue_date) DO UPDATE SET
                    status=excluded.status,
                    artifact_path=excluded.artifact_path,
                    error=excluded.error,
                    created_at=excluded.created_at
                """,
                (
                    issue_date,
                    status,
                    str(artifact_path) if artifact_path else None,
                    error,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def record_send_result(self, issue_date: str, result: SendResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO send_attempts (issue_date, subject, status, attempts, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    issue_date,
                    result.subject,
                    result.status,
                    result.attempts,
                    result.error,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def write_run_artifact(self, runs_dir: Path, issue_date: str, payload: dict[str, Any]) -> Path:
        runs_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = runs_dir / f"{issue_date}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact_path

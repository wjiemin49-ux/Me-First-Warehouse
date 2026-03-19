"""Repository that provides CRUD operations for sleep sessions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from .database import DatabaseManager
from .exceptions import (
    ActiveSessionExistsError,
    NoActiveSessionError,
    SessionNotFoundError,
    SleepTrackerDataError,
)
from .models import SleepSession, datetime_to_iso, utc_now


class SleepSessionRepository:
    """CRUD operations for sleep_sessions table."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def initialize(self) -> None:
        """Initialize schema."""
        self.db_manager.initialize_schema()

    def start_session(
        self,
        start_time: datetime | None = None,
        note: str = "",
    ) -> SleepSession:
        """Start a new active session."""
        start = start_time or utc_now()
        start_iso = datetime_to_iso(start)
        clean_note = note.strip()

        try:
            with self.db_manager.connection() as conn:
                now_iso = datetime_to_iso(utc_now())
                cursor = conn.execute(
                    """
                    INSERT INTO sleep_sessions (
                        start_time, end_time, duration_minutes, quality_score, note, created_at, updated_at
                    ) VALUES (?, NULL, NULL, NULL, ?, ?, ?)
                    """,
                    (start_iso, clean_note, now_iso, now_iso),
                )
                row = conn.execute(
                    "SELECT * FROM sleep_sessions WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ActiveSessionExistsError(
                "已有进行中的睡眠会话，请先结束后再开始新的会话。"
            ) from exc
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"开始睡眠会话失败：{exc}") from exc

        if row is None:
            raise SleepTrackerDataError("加载新建会话失败。")
        return SleepSession.from_row(row)

    def end_active_session(
        self,
        end_time: datetime | None = None,
        quality_score: int | None = None,
        note: str | None = None,
    ) -> SleepSession:
        """End current active session and compute duration."""
        active = self.get_active_session()
        if active is None:
            raise NoActiveSessionError("当前没有可结束的睡眠会话。")

        finished_at = end_time or utc_now()
        if finished_at.tzinfo is None:
            finished_at = finished_at.replace(tzinfo=timezone.utc)
        if finished_at <= active.start_time:
            raise SleepTrackerDataError("结束时间必须晚于开始时间。")

        if quality_score is not None and not (1 <= quality_score <= 5):
            raise SleepTrackerDataError("质量评分必须在 1 到 5 之间。")

        duration_minutes = int((finished_at - active.start_time).total_seconds() // 60)
        ended_iso = datetime_to_iso(finished_at)
        updated_iso = datetime_to_iso(utc_now())
        updated_note = (note if note is not None else active.note).strip()

        try:
            with self.db_manager.connection() as conn:
                conn.execute(
                    """
                    UPDATE sleep_sessions
                    SET end_time = ?, duration_minutes = ?, quality_score = ?, note = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        ended_iso,
                        duration_minutes,
                        quality_score,
                        updated_note,
                        updated_iso,
                        active.id,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM sleep_sessions WHERE id = ?",
                    (active.id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"结束睡眠会话失败：{exc}") from exc

        if row is None:
            raise SleepTrackerDataError("加载已结束会话失败。")
        return SleepSession.from_row(row)

    def create_session(
        self,
        start_time: datetime,
        end_time: datetime,
        note: str = "",
        quality_score: int | None = None,
    ) -> SleepSession:
        """Create a completed session directly."""
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        if end_time <= start_time:
            raise SleepTrackerDataError("结束时间必须晚于开始时间。")
        if quality_score is not None and not (1 <= quality_score <= 5):
            raise SleepTrackerDataError("质量评分必须在 1 到 5 之间。")

        duration_minutes = int((end_time - start_time).total_seconds() // 60)
        start_iso = datetime_to_iso(start_time)
        end_iso = datetime_to_iso(end_time)
        now_iso = datetime_to_iso(utc_now())
        clean_note = note.strip()

        try:
            with self.db_manager.connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO sleep_sessions (
                        start_time, end_time, duration_minutes, quality_score, note, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        start_iso,
                        end_iso,
                        duration_minutes,
                        quality_score,
                        clean_note,
                        now_iso,
                        now_iso,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM sleep_sessions WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"创建睡眠会话失败：{exc}") from exc

        if row is None:
            raise SleepTrackerDataError("加载已创建会话失败。")
        return SleepSession.from_row(row)

    def get_session_by_id(self, session_id: int) -> SleepSession:
        """Get one session by id."""
        try:
            with self.db_manager.connection() as conn:
                row = conn.execute(
                    "SELECT * FROM sleep_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"查询会话失败：{exc}") from exc

        if row is None:
            raise SessionNotFoundError(f"睡眠会话 id={session_id} 不存在。")
        return SleepSession.from_row(row)

    def get_active_session(self) -> SleepSession | None:
        """Get current active session if present."""
        try:
            with self.db_manager.connection() as conn:
                row = conn.execute(
                    """
                    SELECT * FROM sleep_sessions
                    WHERE end_time IS NULL
                    ORDER BY start_time DESC
                    LIMIT 1
                    """
                ).fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(
                f"查询进行中睡眠会话失败：{exc}"
            ) from exc

        if row is None:
            return None
        return SleepSession.from_row(row)

    def list_sessions(self, limit: int = 100, offset: int = 0) -> list[SleepSession]:
        """List sessions ordered by start_time descending."""
        if limit <= 0:
            raise SleepTrackerDataError("limit 必须是正整数。")
        if offset < 0:
            raise SleepTrackerDataError("offset 不能为负数。")

        try:
            with self.db_manager.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM sleep_sessions
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"列出睡眠会话失败：{exc}") from exc

        return [SleepSession.from_row(row) for row in rows]

    def get_recent_sessions(self, days: int = 7) -> list[SleepSession]:
        """List sessions in the recent N days."""
        if days <= 0:
            raise SleepTrackerDataError("days 必须是正整数。")

        begin = utc_now() - timedelta(days=days)
        begin_iso = datetime_to_iso(begin)

        try:
            with self.db_manager.connection() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM sleep_sessions
                    WHERE start_time >= ?
                    ORDER BY start_time ASC
                    """,
                    (begin_iso,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(
                f"列出最近睡眠会话失败：{exc}"
            ) from exc

        return [SleepSession.from_row(row) for row in rows]

    def update_note(self, session_id: int, note: str) -> SleepSession:
        """Update note for one session."""
        clean_note = note.strip()
        updated_iso = datetime_to_iso(utc_now())

        try:
            with self.db_manager.connection() as conn:
                conn.execute(
                    """
                    UPDATE sleep_sessions
                    SET note = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (clean_note, updated_iso, session_id),
                )
                row = conn.execute(
                    "SELECT * FROM sleep_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"更新会话备注失败：{exc}") from exc

        if row is None:
            raise SessionNotFoundError(f"睡眠会话 id={session_id} 不存在。")
        return SleepSession.from_row(row)

    def delete_session(self, session_id: int) -> None:
        """Delete a session by id."""
        try:
            with self.db_manager.connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM sleep_sessions WHERE id = ?",
                    (session_id,),
                )
                if cursor.rowcount == 0:
                    raise SessionNotFoundError(
                        f"睡眠会话 id={session_id} 不存在。"
                    )
        except SessionNotFoundError:
            raise
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"删除会话失败：{exc}") from exc

    def count_sessions(self) -> int:
        """Count all persisted sessions."""
        try:
            with self.db_manager.connection() as conn:
                row = conn.execute("SELECT COUNT(*) AS total FROM sleep_sessions").fetchone()
        except sqlite3.Error as exc:
            raise SleepTrackerDataError(f"统计会话数量失败：{exc}") from exc

        if row is None:
            return 0
        return int(row["total"])

"""Domain models for persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sqlite3 import Row


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(tz=timezone.utc)


def datetime_to_iso(value: datetime) -> str:
    """Normalize datetime to UTC and convert into ISO text for SQLite."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def iso_to_datetime(value: str) -> datetime:
    """Parse ISO text from SQLite into a UTC datetime."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(slots=True)
class SleepSession:
    """Represents one sleep record."""

    id: int
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int | None
    note: str
    quality_score: int | None
    created_at: datetime
    updated_at: datetime

    @property
    def duration_hours(self) -> float | None:
        """Duration in hours if available."""
        if self.duration_minutes is None:
            return None
        return round(self.duration_minutes / 60.0, 2)

    @property
    def is_active(self) -> bool:
        """Whether this session is still running."""
        return self.end_time is None

    @classmethod
    def from_row(cls, row: Row) -> "SleepSession":
        """Create a model instance from sqlite row."""
        return cls(
            id=int(row["id"]),
            start_time=iso_to_datetime(row["start_time"]),
            end_time=iso_to_datetime(row["end_time"]) if row["end_time"] else None,
            duration_minutes=row["duration_minutes"],
            note=row["note"] or "",
            quality_score=row["quality_score"],
            created_at=iso_to_datetime(row["created_at"]),
            updated_at=iso_to_datetime(row["updated_at"]),
        )

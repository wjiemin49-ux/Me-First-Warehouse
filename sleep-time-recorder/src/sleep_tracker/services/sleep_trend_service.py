"""Business logic for daily sleep trend aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import isnan
from typing import Iterable

from sleep_tracker.data import SleepSession
from sleep_tracker.data.models import utc_now


@dataclass(slots=True, frozen=True)
class DailySleepTrend:
    """Aggregated trend information for one day."""

    day: date
    label: str
    total_minutes: int
    session_count: int
    average_quality_rating: float | None

    @property
    def total_hours(self) -> float:
        """Total sleep hours for the day."""
        return round(self.total_minutes / 60.0, 2)

    def quality_index(self, goal_hours: float) -> float | None:
        """Return quality index (0-100) derived from duration and optional rating."""
        if self.total_minutes <= 0:
            return None

        goal_minutes = max(1, int(goal_hours * 60))
        duration_component = min(100.0, (self.total_minutes / goal_minutes) * 100.0)

        if self.average_quality_rating is None:
            return round(duration_component, 1)

        rating_component = min(100.0, (self.average_quality_rating / 5.0) * 100.0)
        blended = duration_component * 0.7 + rating_component * 0.3
        if isnan(blended):
            return round(duration_component, 1)
        return round(blended, 1)


class SleepTrendService:
    """Computes trend data points from session records."""

    def build_daily_trend(
        self,
        sessions: Iterable[SleepSession],
        *,
        goal_hours: float,
        days: int = 7,
        reference_time: datetime | None = None,
    ) -> list[DailySleepTrend]:
        """Build complete day-by-day trend for the latest N days."""
        if days <= 0:
            raise ValueError("days 必须大于 0。")

        local_now = (reference_time or utc_now()).astimezone()
        end_day = local_now.date()
        start_day = end_day - timedelta(days=days - 1)

        buckets: dict[date, dict[str, object]] = {}
        for offset in range(days):
            current_day = start_day + timedelta(days=offset)
            buckets[current_day] = {
                "total_minutes": 0,
                "session_count": 0,
                "quality_ratings": [],
            }

        for session in sessions:
            if session.duration_minutes is None or session.end_time is None:
                continue
            local_day = session.start_time.astimezone().date()
            bucket = buckets.get(local_day)
            if bucket is None:
                continue

            bucket["total_minutes"] = int(bucket["total_minutes"]) + int(session.duration_minutes)
            bucket["session_count"] = int(bucket["session_count"]) + 1

            quality_list = bucket["quality_ratings"]
            assert isinstance(quality_list, list)
            if session.quality_score is not None:
                quality_list.append(float(session.quality_score))

        trends: list[DailySleepTrend] = []
        for day in sorted(buckets.keys()):
            bucket = buckets[day]
            quality_list = bucket["quality_ratings"]
            assert isinstance(quality_list, list)

            avg_quality: float | None = None
            if quality_list:
                avg_quality = round(sum(quality_list) / len(quality_list), 2)

            trends.append(
                DailySleepTrend(
                    day=day,
                    label=day.strftime("%m-%d"),
                    total_minutes=int(bucket["total_minutes"]),
                    session_count=int(bucket["session_count"]),
                    average_quality_rating=avg_quality,
                )
            )

        return trends

    @staticmethod
    def summarize_week(
        trends: list[DailySleepTrend],
        *,
        goal_hours: float,
    ) -> dict[str, float | int]:
        """Return summary values used by the trend panel."""
        if not trends:
            return {
                "total_hours": 0.0,
                "avg_hours": 0.0,
                "avg_quality_index": 0.0,
                "goal_hit_days": 0,
            }

        total_hours = sum(point.total_hours for point in trends)
        avg_hours = total_hours / len(trends)
        quality_points = [point.quality_index(goal_hours) for point in trends]
        filtered_quality = [point for point in quality_points if point is not None]
        avg_quality_index = (
            sum(filtered_quality) / len(filtered_quality) if filtered_quality else 0.0
        )
        goal_hit_days = sum(
            1
            for point in trends
            if point.total_minutes >= int(max(goal_hours, 0.1) * 60)
        )

        return {
            "total_hours": round(total_hours, 2),
            "avg_hours": round(avg_hours, 2),
            "avg_quality_index": round(avg_quality_index, 1),
            "goal_hit_days": goal_hit_days,
        }

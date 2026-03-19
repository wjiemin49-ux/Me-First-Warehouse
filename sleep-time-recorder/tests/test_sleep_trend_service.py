"""Tests for sleep trend aggregation service."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.data import DatabaseManager, SleepSessionRepository
from sleep_tracker.services import SleepTrendService


class SleepTrendServiceTestCase(unittest.TestCase):
    """Coverage for trend building and summary metrics."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "trend_service.db"
        repo = SleepSessionRepository(DatabaseManager(db_path=db_path))
        repo.initialize()
        self.repo = repo
        self.service = SleepTrendService()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_daily_trend_and_summary(self) -> None:
        local_now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)

        day1_start = (local_now - timedelta(days=1)).replace(hour=0)
        day2_start = (local_now - timedelta(days=2)).replace(hour=1)
        day4_start = (local_now - timedelta(days=4)).replace(hour=23)

        self.repo.create_session(
            start_time=day1_start,
            end_time=day1_start + timedelta(hours=7),
            note="day1",
            quality_score=4,
        )
        self.repo.create_session(
            start_time=day2_start,
            end_time=day2_start + timedelta(hours=8, minutes=30),
            note="day2-main",
            quality_score=5,
        )
        self.repo.create_session(
            start_time=day2_start + timedelta(hours=12),
            end_time=day2_start + timedelta(hours=13),
            note="day2-nap",
            quality_score=None,
        )
        self.repo.create_session(
            start_time=day4_start,
            end_time=day4_start + timedelta(hours=6),
            note="day4",
            quality_score=3,
        )

        sessions = self.repo.get_recent_sessions(days=14)
        trend = self.service.build_daily_trend(
            sessions=sessions,
            goal_hours=8.0,
            days=7,
            reference_time=local_now,
        )
        self.assertEqual(len(trend), 7)

        lookup = {point.day: point for point in trend}
        day1 = (local_now - timedelta(days=1)).date()
        day2 = (local_now - timedelta(days=2)).date()
        day4 = (local_now - timedelta(days=4)).date()

        self.assertEqual(lookup[day1].total_minutes, 420)
        self.assertEqual(lookup[day1].session_count, 1)
        self.assertEqual(lookup[day1].average_quality_rating, 4.0)

        self.assertEqual(lookup[day2].total_minutes, 570)
        self.assertEqual(lookup[day2].session_count, 2)
        self.assertEqual(lookup[day2].average_quality_rating, 5.0)
        self.assertEqual(lookup[day2].quality_index(8.0), 100.0)

        self.assertEqual(lookup[day4].total_minutes, 360)
        self.assertEqual(lookup[day4].average_quality_rating, 3.0)
        self.assertIsNone(lookup[local_now.date()].quality_index(8.0))

        summary = self.service.summarize_week(trend, goal_hours=8.0)
        self.assertEqual(summary["goal_hit_days"], 1)
        self.assertAlmostEqual(float(summary["total_hours"]), 22.5, places=2)
        self.assertGreater(float(summary["avg_quality_index"]), 0.0)

    def test_invalid_days_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.build_daily_trend(sessions=[], goal_hours=8.0, days=0)


if __name__ == "__main__":
    unittest.main()

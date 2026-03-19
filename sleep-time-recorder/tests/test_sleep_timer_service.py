"""Unit tests for timer orchestration service."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest

from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.data import DatabaseManager, SleepSessionRepository
from sleep_tracker.data.models import utc_now
from sleep_tracker.services import SleepTimerService


class SleepTimerServiceTestCase(unittest.TestCase):
    """Timer and repository orchestration tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_timer_records.db"
        repo = SleepSessionRepository(DatabaseManager(db_path=db_path))
        repo.initialize()
        self.repo = repo
        self.service = SleepTimerService(session_repository=self.repo, update_interval_ms=50)

    def tearDown(self) -> None:
        self.service.shutdown()
        self.temp_dir.cleanup()

    def test_format_elapsed(self) -> None:
        self.assertEqual(self.service.format_elapsed(0), "00:00:00")
        self.assertEqual(self.service.format_elapsed(65), "00:01:05")
        self.assertEqual(self.service.format_elapsed(3661), "01:01:01")

    def test_start_then_end_session(self) -> None:
        states: list[bool] = []
        starts: list[object] = []
        ends: list[object] = []
        ticks: list[tuple[str, int]] = []

        self.service.state_changed.connect(states.append)
        self.service.session_started.connect(starts.append)
        self.service.session_ended.connect(ends.append)
        self.service.tick.connect(lambda text, seconds: ticks.append((text, seconds)))

        started = self.service.start_session(note="test")
        self.assertIsNotNone(started)
        self.assertTrue(self.service.is_running)
        self.assertEqual(len(starts), 1)
        self.assertTrue(any(state is True for state in states))
        self.assertGreaterEqual(len(ticks), 1)

        ended = self.service.end_session(
            end_time=started.start_time + timedelta(hours=7, minutes=30) if started else None
        )
        self.assertIsNotNone(ended)
        self.assertFalse(self.service.is_running)
        self.assertEqual(len(ends), 1)
        self.assertTrue(any(state is False for state in states))
        self.assertEqual(ended.duration_minutes if ended else -1, 450)

    def test_restore_active_session_on_init(self) -> None:
        active = self.repo.start_session(start_time=utc_now() - timedelta(minutes=2))
        self.assertIsNotNone(active)

        service = SleepTimerService(session_repository=self.repo, update_interval_ms=1000)
        try:
            self.assertTrue(service.is_running)
            self.assertIsNotNone(service.active_session)
            self.assertGreaterEqual(service.elapsed_seconds(), 120)
        finally:
            service.shutdown()

    def test_duplicate_start_emits_error(self) -> None:
        errors: list[str] = []
        self.service.error_occurred.connect(errors.append)

        self.service.start_session()
        duplicate = self.service.start_session()

        self.assertIsNone(duplicate)
        self.assertGreaterEqual(len(errors), 1)
        self.assertIn("已有进行中的睡眠会话", errors[-1])


if __name__ == "__main__":
    unittest.main()

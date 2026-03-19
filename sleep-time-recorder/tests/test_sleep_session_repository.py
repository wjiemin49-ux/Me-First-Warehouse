"""Unit tests for SQLite repository layer."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.data import (
    ActiveSessionExistsError,
    DatabaseManager,
    NoActiveSessionError,
    SessionNotFoundError,
    SleepSessionRepository,
)
from sleep_tracker.data.models import utc_now


class SleepSessionRepositoryTestCase(unittest.TestCase):
    """CRUD and lifecycle tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_sleep_records.db"
        self.repo = SleepSessionRepository(DatabaseManager(db_path=db_path))
        self.repo.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_start_and_end_session(self) -> None:
        started = self.repo.start_session(note="night sleep")
        self.assertTrue(started.is_active)

        ended = self.repo.end_active_session(
            end_time=started.start_time + timedelta(hours=8),
            quality_score=4,
        )
        self.assertFalse(ended.is_active)
        self.assertEqual(ended.duration_minutes, 480)
        self.assertEqual(ended.quality_score, 4)

    def test_prevent_multiple_active_sessions(self) -> None:
        self.repo.start_session()
        with self.assertRaises(ActiveSessionExistsError):
            self.repo.start_session()

    def test_end_without_active_session_raises(self) -> None:
        with self.assertRaises(NoActiveSessionError):
            self.repo.end_active_session()

    def test_crud_cycle(self) -> None:
        start = utc_now() - timedelta(hours=9)
        end = start + timedelta(hours=7, minutes=45)

        created = self.repo.create_session(
            start_time=start,
            end_time=end,
            note="manual input",
            quality_score=5,
        )
        self.assertEqual(created.duration_minutes, 465)

        updated = self.repo.update_note(created.id, "updated note")
        self.assertEqual(updated.note, "updated note")

        fetched = self.repo.get_session_by_id(created.id)
        self.assertEqual(fetched.id, created.id)

        self.repo.delete_session(created.id)
        with self.assertRaises(SessionNotFoundError):
            self.repo.get_session_by_id(created.id)


if __name__ == "__main__":
    unittest.main()

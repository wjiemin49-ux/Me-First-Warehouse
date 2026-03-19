"""Tests for history list widget behavior."""

from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.data import DatabaseManager, SleepSessionRepository
from sleep_tracker.data.models import utc_now
from sleep_tracker.widgets import HistoryListWidget


class HistoryListWidgetTestCase(unittest.TestCase):
    """History list loading and editing tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "history_widget.db"
        repo = SleepSessionRepository(DatabaseManager(db_path=db_path))
        repo.initialize()

        base = utc_now() - timedelta(hours=10)
        repo.create_session(
            start_time=base - timedelta(hours=8),
            end_time=base - timedelta(hours=1),
            note="old note",
            quality_score=4,
        )
        repo.create_session(
            start_time=base - timedelta(days=1, hours=9),
            end_time=base - timedelta(days=1, hours=2),
            note="older note",
            quality_score=3,
        )

        self.repo = repo
        self.widget = HistoryListWidget(session_repository=self.repo)

    def tearDown(self) -> None:
        self.widget.deleteLater()
        self.temp_dir.cleanup()

    def test_load_rows(self) -> None:
        self.widget.refresh_data()
        self.assertEqual(self.widget.table.rowCount(), 2)

    def test_update_note(self) -> None:
        first_id = self._session_id_at_row(0)
        updated = self.widget.update_note_for_session(first_id, "updated from test")
        self.assertIsNotNone(updated)
        fetched = self.repo.get_session_by_id(first_id)
        self.assertEqual(fetched.note, "updated from test")

    def test_delete_session(self) -> None:
        first_id = self._session_id_at_row(0)
        deleted = self.widget.delete_session(first_id, confirm=False)
        self.assertTrue(deleted)
        self.assertEqual(self.repo.count_sessions(), 1)

    def test_active_session_cannot_be_deleted(self) -> None:
        active = self.repo.start_session()
        self.widget.refresh_data()
        deleted = self.widget.delete_session(active.id, confirm=False)
        self.assertFalse(deleted)
        self.assertIsNotNone(self.repo.get_active_session())

    def _session_id_at_row(self, row: int) -> int:
        item = self.widget.table.item(row, 0)
        assert item is not None
        data = item.data(Qt.ItemDataRole.UserRole)
        assert data is not None
        return int(data)


if __name__ == "__main__":
    unittest.main()

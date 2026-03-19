"""Integration tests for main window orchestration."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.data import DatabaseManager, SleepSessionRepository
from sleep_tracker.services import SleepReminderService, SleepTimerService
from sleep_tracker.ui import SleepMainWindow, ThemeManager


class MainWindowIntegrationTestCase(unittest.TestCase):
    """Main window behavior tests with real services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "main_window.db"
        self.repo = SleepSessionRepository(DatabaseManager(db_path=db_path))
        self.repo.initialize()

        self.settings = {
            "theme": "dark",
            "daily_sleep_goal_hours": 8.0,
            "notifications_enabled": True,
            "reminder_time": "22:30",
            "minimize_to_tray": False,
            "auto_start_timer_on_launch": False,
            "database_path": str(db_path),
        }

        self.theme_manager = ThemeManager(self.qt_app)
        self.theme_manager.apply_theme("dark")
        self.timer_service = SleepTimerService(self.repo, update_interval_ms=50)
        self.reminder_service = SleepReminderService(check_interval_ms=1000)
        self.window = SleepMainWindow(
            settings=self.settings,
            session_repository=self.repo,
            timer_service=self.timer_service,
            reminder_service=self.reminder_service,
            theme_manager=self.theme_manager,
        )

    def tearDown(self) -> None:
        self.window._allow_close = True  # type: ignore[attr-defined]
        self.window.close()
        self.temp_dir.cleanup()

    def test_trend_widget_lazy_loaded(self) -> None:
        self.assertIsNone(self.window.trend_widget)
        self.window.main_tabs.setCurrentIndex(1)
        self.assertIsNotNone(self.window.trend_widget)


if __name__ == "__main__":
    unittest.main()

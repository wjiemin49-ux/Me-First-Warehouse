"""Tests for bedtime reminder service."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

from PySide6.QtCore import QCoreApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.services import SleepReminderService


class _NowProvider:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current


class SleepReminderServiceTestCase(unittest.TestCase):
    """Reminder trigger and config validation tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QCoreApplication.instance() or QCoreApplication([])

    def test_trigger_once_per_day(self) -> None:
        base = datetime.now().astimezone().replace(hour=22, minute=29, second=0, microsecond=0)
        now_provider = _NowProvider(base)
        service = SleepReminderService(now_provider=now_provider, check_interval_ms=1000)
        messages: list[str] = []
        service.reminder_due.connect(messages.append)

        self.assertTrue(service.configure(enabled=True, reminder_time="22:30"))

        self.assertFalse(service.check_now())
        now_provider.current = now_provider.current + timedelta(minutes=1)
        self.assertTrue(service.check_now())
        self.assertEqual(len(messages), 1)

        # Same day should not trigger twice.
        now_provider.current = now_provider.current + timedelta(seconds=20)
        self.assertFalse(service.check_now())
        self.assertEqual(len(messages), 1)

        # Next day at same time should trigger again.
        now_provider.current = now_provider.current + timedelta(days=1)
        self.assertTrue(service.check_now())
        self.assertEqual(len(messages), 2)

    def test_invalid_time_disables_service(self) -> None:
        base = datetime.now().astimezone().replace(hour=22, minute=30, second=0, microsecond=0)
        now_provider = _NowProvider(base)
        service = SleepReminderService(now_provider=now_provider, check_interval_ms=1000)
        errors: list[str] = []
        service.config_error.connect(errors.append)

        self.assertFalse(service.configure(enabled=True, reminder_time="99:99"))
        self.assertFalse(service.enabled)
        self.assertEqual(len(errors), 1)
        self.assertFalse(service.check_now())

    def test_disabled_notifications_no_trigger(self) -> None:
        base = datetime.now().astimezone().replace(hour=22, minute=30, second=0, microsecond=0)
        now_provider = _NowProvider(base)
        service = SleepReminderService(now_provider=now_provider, check_interval_ms=1000)
        messages: list[str] = []
        service.reminder_due.connect(messages.append)

        self.assertTrue(service.configure(enabled=False, reminder_time="22:30"))
        self.assertFalse(service.check_now())
        self.assertEqual(messages, [])


if __name__ == "__main__":
    unittest.main()

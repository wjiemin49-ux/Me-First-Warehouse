"""Tests for settings panel widget payload behavior."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.widgets import SettingsPanelWidget


class SettingsPanelWidgetTestCase(unittest.TestCase):
    """Form read/write tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_collect_payload(self) -> None:
        widget = SettingsPanelWidget(
            {
                "daily_sleep_goal_hours": 8.0,
                "notifications_enabled": True,
                "reminder_time": "22:30",
                "theme": "dark",
                "minimize_to_tray": True,
                "auto_start_timer_on_launch": False,
            }
        )

        captured: list[dict] = []
        widget.settings_applied.connect(captured.append)

        widget.goal_hours_spin.setValue(7.5)
        widget.notifications_checkbox.setChecked(False)
        widget.reminder_time_edit.setTime(QTime(23, 15))
        widget.theme_combo.setCurrentIndex(widget.theme_combo.findData("light"))
        widget.tray_checkbox.setChecked(False)
        widget.auto_start_checkbox.setChecked(True)

        widget.apply_button.click()
        self.assertEqual(len(captured), 1)

        payload = captured[0]
        self.assertEqual(payload["daily_sleep_goal_hours"], 7.5)
        self.assertFalse(payload["notifications_enabled"])
        self.assertEqual(payload["reminder_time"], "23:15")
        self.assertEqual(payload["theme"], "light")
        self.assertFalse(payload["minimize_to_tray"])
        self.assertTrue(payload["auto_start_timer_on_launch"])

        widget.deleteLater()

    def test_set_settings_syncs_controls(self) -> None:
        widget = SettingsPanelWidget({})
        widget.set_settings(
            {
                "daily_sleep_goal_hours": 6.5,
                "notifications_enabled": True,
                "reminder_time": "21:40",
                "theme": "light",
                "minimize_to_tray": False,
                "auto_start_timer_on_launch": True,
            }
        )

        self.assertAlmostEqual(widget.goal_hours_spin.value(), 6.5, places=1)
        self.assertTrue(widget.notifications_checkbox.isChecked())
        self.assertEqual(widget.reminder_time_edit.time().toString("HH:mm"), "21:40")
        self.assertEqual(widget.theme_combo.currentData(), "light")
        self.assertFalse(widget.tray_checkbox.isChecked())
        self.assertTrue(widget.auto_start_checkbox.isChecked())

        widget.deleteLater()


if __name__ == "__main__":
    unittest.main()

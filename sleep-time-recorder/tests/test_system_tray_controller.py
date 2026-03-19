"""Tests for system tray controller behavior."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.ui import SystemTrayController


class SystemTrayControllerTestCase(unittest.TestCase):
    """Tray setup and action state tests."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_setup_and_action_signals(self) -> None:
        controller = SystemTrayController(app_name="睡眠时间记录器")
        if not controller.is_available:
            self.skipTest("System tray not available in this environment.")

        self.assertTrue(controller.setup())
        self.assertTrue(controller.is_ready)

        events = {"toggle": 0, "start": 0, "end": 0, "quit": 0}
        controller.toggle_window_requested.connect(
            lambda: events.__setitem__("toggle", events["toggle"] + 1)
        )
        controller.quick_start_requested.connect(
            lambda: events.__setitem__("start", events["start"] + 1)
        )
        controller.quick_end_requested.connect(
            lambda: events.__setitem__("end", events["end"] + 1)
        )
        controller.quit_requested.connect(
            lambda: events.__setitem__("quit", events["quit"] + 1)
        )

        assert controller.open_action is not None
        assert controller.quick_start_action is not None
        assert controller.quick_end_action is not None
        assert controller.quit_action is not None

        controller.set_session_running(False)
        self.assertTrue(controller.quick_start_action.isEnabled())
        self.assertFalse(controller.quick_end_action.isEnabled())

        controller.set_session_running(True)
        self.assertFalse(controller.quick_start_action.isEnabled())
        self.assertTrue(controller.quick_end_action.isEnabled())

        controller.set_window_hidden(True)
        self.assertEqual(controller.open_action.text(), "打开窗口")
        controller.set_window_hidden(False)
        self.assertEqual(controller.open_action.text(), "隐藏窗口")

        controller.open_action.trigger()
        controller.quick_start_action.trigger()
        controller.quick_end_action.trigger()
        controller.quit_action.trigger()

        self.assertEqual(events["toggle"], 1)
        self.assertEqual(events["start"], 1)
        self.assertEqual(events["end"], 1)
        self.assertEqual(events["quit"], 1)

        controller.shutdown()
        self.assertFalse(controller.is_ready)


if __name__ == "__main__":
    unittest.main()

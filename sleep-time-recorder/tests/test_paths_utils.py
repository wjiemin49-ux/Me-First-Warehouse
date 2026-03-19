"""Tests for runtime path helpers."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sleep_tracker.utils import config_dir, qss_dir, runtime_root


class PathUtilsTestCase(unittest.TestCase):
    """Basic path utility assertions in development mode."""

    def test_runtime_root_exists(self) -> None:
        self.assertTrue(runtime_root().exists())

    def test_config_dir_points_to_project_config(self) -> None:
        self.assertTrue((config_dir() / "default_settings.json").exists())

    def test_qss_dir_contains_dark_theme(self) -> None:
        self.assertTrue((qss_dir() / "dark.qss").exists())


if __name__ == "__main__":
    unittest.main()

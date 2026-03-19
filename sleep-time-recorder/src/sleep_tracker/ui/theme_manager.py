"""Application theme manager based on QSS files."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sleep_tracker.utils import qss_dir as resolve_qss_dir

logger = logging.getLogger(__name__)


class ThemeManager:
    """Loads and applies theme stylesheet to QApplication."""

    THEME_FILES = {
        "dark": "dark.qss",
        "light": "light.qss",
    }

    def __init__(self, app: QApplication, qss_dir: Path | None = None) -> None:
        self._app = app
        self._qss_dir = qss_dir or resolve_qss_dir()
        self._current_theme = "dark"

    @property
    def current_theme(self) -> str:
        """Current applied theme name."""
        return self._current_theme

    def apply_theme(self, theme: str) -> str:
        """Apply a theme name and return actual applied one."""
        normalized = theme if theme in self.THEME_FILES else "dark"
        stylesheet_path = self._qss_dir / self.THEME_FILES[normalized]

        try:
            stylesheet = stylesheet_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "Failed to read stylesheet %s: %s. Falling back to no stylesheet.",
                stylesheet_path,
                exc,
            )
            self._app.setStyleSheet("")
            self._current_theme = normalized
            return normalized

        self._app.setStyleSheet(stylesheet)
        self._current_theme = normalized
        return normalized

    def toggle_theme(self) -> str:
        """Switch between dark and light themes."""
        target = "light" if self._current_theme == "dark" else "dark"
        return self.apply_theme(target)

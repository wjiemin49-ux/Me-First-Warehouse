"""System tray controller for quick actions and window visibility."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon, QWidget

logger = logging.getLogger(__name__)


class SystemTrayController(QObject):
    """Wraps QSystemTrayIcon interactions and exposes simple signals."""

    toggle_window_requested = Signal()
    quick_start_requested = Signal()
    quick_end_requested = Signal()
    quit_requested = Signal()

    def __init__(self, *, app_name: str, parent_window: QWidget | None = None) -> None:
        super().__init__(parent_window)
        self.app_name = app_name
        self.parent_window = parent_window

        self.tray_icon: QSystemTrayIcon | None = None
        self.menu: QMenu | None = None
        self.open_action: QAction | None = None
        self.quick_start_action: QAction | None = None
        self.quick_end_action: QAction | None = None
        self.quit_action: QAction | None = None

    @property
    def is_available(self) -> bool:
        """Return whether current platform supports system tray."""
        return QSystemTrayIcon.isSystemTrayAvailable()

    @property
    def is_ready(self) -> bool:
        """Return whether tray icon is created and visible."""
        return self.tray_icon is not None

    def setup(self) -> bool:
        """Create tray icon, context menu and bind actions."""
        if not self.is_available:
            logger.info("System tray is not available on this platform/session.")
            return False

        try:
            tray = QSystemTrayIcon(self._resolve_icon(), self)
            tray.setToolTip(self.app_name)

            menu = QMenu(self.parent_window)
            open_action = menu.addAction("打开 / 隐藏")
            menu.addSeparator()
            quick_start_action = menu.addAction("快捷开始睡眠")
            quick_end_action = menu.addAction("快捷结束睡眠")
            menu.addSeparator()
            quit_action = menu.addAction("退出")

            open_action.triggered.connect(self.toggle_window_requested.emit)
            quick_start_action.triggered.connect(self.quick_start_requested.emit)
            quick_end_action.triggered.connect(self.quick_end_requested.emit)
            quit_action.triggered.connect(self.quit_requested.emit)
            tray.activated.connect(self._on_tray_activated)
            tray.setContextMenu(menu)
            tray.show()

            self.tray_icon = tray
            self.menu = menu
            self.open_action = open_action
            self.quick_start_action = quick_start_action
            self.quick_end_action = quick_end_action
            self.quit_action = quit_action
            self.set_session_running(False)
            return True
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            logger.warning("Failed to initialize system tray: %s", exc)
            self.shutdown()
            return False

    def set_session_running(self, running: bool) -> None:
        """Enable/disable quick start/end actions by timer state."""
        if self.quick_start_action is not None:
            self.quick_start_action.setEnabled(not running)
        if self.quick_end_action is not None:
            self.quick_end_action.setEnabled(running)

    def set_window_hidden(self, hidden: bool) -> None:
        """Update action text to indicate current visibility."""
        if self.open_action is None:
            return
        self.open_action.setText("打开窗口" if hidden else "隐藏窗口")

    def show_message(self, title: str, message: str, timeout_ms: int = 2500) -> None:
        """Display tray balloon message when supported."""
        if self.tray_icon is None:
            return
        if not self.tray_icon.supportsMessages():
            return
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            timeout_ms,
        )

    def shutdown(self) -> None:
        """Hide tray icon and release references."""
        if self.tray_icon is not None:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
        if self.menu is not None:
            self.menu.deleteLater()

        self.tray_icon = None
        self.menu = None
        self.open_action = None
        self.quick_start_action = None
        self.quick_end_action = None
        self.quit_action = None

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window_requested.emit()

    def _resolve_icon(self) -> QIcon:
        if self.parent_window is not None:
            style = self.parent_window.style()
        else:
            style = QApplication.style()
        return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

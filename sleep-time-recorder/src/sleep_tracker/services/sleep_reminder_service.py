"""Notification reminder service for bedtime prompts."""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class SleepReminderService(QObject):
    """Checks local time periodically and emits reminder signal once per day."""

    reminder_due = Signal(str)
    config_error = Signal(str)

    def __init__(
        self,
        *,
        check_interval_ms: int = 30_000,
        now_provider: Callable[[], datetime] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._enabled = False
        self._reminder_time: str | None = None
        self._last_triggered_date: date | None = None
        self._now_provider = now_provider or datetime.now

        self._timer = QTimer(self)
        self._timer.setInterval(check_interval_ms)
        self._timer.timeout.connect(self.check_now)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def reminder_time(self) -> str | None:
        return self._reminder_time

    def configure(self, *, enabled: bool, reminder_time: str) -> bool:
        """Apply settings and start/stop timer accordingly."""
        self._enabled = bool(enabled)

        if not self._enabled:
            self._reminder_time = None
            self.stop()
            return True

        normalized = self._normalize_time(reminder_time)
        if normalized is None:
            message = "提醒时间格式无效，应为 HH:MM。"
            logger.warning(message)
            self.config_error.emit(message)
            self._enabled = False
            self._reminder_time = None
            self.stop()
            return False

        self._reminder_time = normalized
        self.start()
        return True

    def start(self) -> None:
        if self._enabled and self._reminder_time is not None and not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def shutdown(self) -> None:
        self.stop()

    def check_now(self) -> bool:
        """Run one reminder check. Returns whether reminder fired."""
        if not self._enabled or self._reminder_time is None:
            return False

        now = self._now_provider().astimezone()
        now_key = now.strftime("%H:%M")
        if now_key != self._reminder_time:
            return False

        if self._last_triggered_date == now.date():
            return False

        self._last_triggered_date = now.date()
        message = f"睡前提醒（{self._reminder_time}）：建议现在开始记录睡眠。"
        self.reminder_due.emit(message)
        return True

    @staticmethod
    def _normalize_time(value: str) -> str | None:
        text = (value or "").strip()
        try:
            parsed = datetime.strptime(text, "%H:%M")
        except ValueError:
            return None
        return parsed.strftime("%H:%M")

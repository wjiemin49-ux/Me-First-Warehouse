"""Timer service for sleep session start/end and real-time elapsed updates."""

from __future__ import annotations

from datetime import datetime
import logging

from PySide6.QtCore import QObject, QTimer, Signal

from sleep_tracker.data import (
    ActiveSessionExistsError,
    NoActiveSessionError,
    SleepSession,
    SleepSessionRepository,
    SleepTrackerDataError,
)
from sleep_tracker.data.models import utc_now

logger = logging.getLogger(__name__)


class SleepTimerService(QObject):
    """Orchestrates sleep timing behavior and emits UI-friendly signals."""

    tick = Signal(str, int)
    state_changed = Signal(bool)
    session_started = Signal(object)
    session_ended = Signal(object)
    error_occurred = Signal(str)

    def __init__(
        self,
        session_repository: SleepSessionRepository,
        update_interval_ms: int = 1000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = session_repository
        self._active_session: SleepSession | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(update_interval_ms)
        self._timer.timeout.connect(self._on_timeout)
        self.restore_active_session()

    @property
    def active_session(self) -> SleepSession | None:
        """Current active session in memory."""
        return self._active_session

    @property
    def is_running(self) -> bool:
        """Whether a session is active and timer is ticking."""
        return self._active_session is not None

    def restore_active_session(self) -> SleepSession | None:
        """Load active session from repository and sync timer state."""
        try:
            self._active_session = self._repo.get_active_session()
        except SleepTrackerDataError as exc:
            self._emit_error(f"恢复进行中的会话失败：{exc}")
            self._active_session = None

        self._sync_internal_timer_state()
        self._emit_tick()
        return self._active_session

    def start_session(self, note: str = "") -> SleepSession | None:
        """Start a new session and begin real-time updates."""
        if self._active_session is not None:
            self._emit_error("已有进行中的睡眠会话。")
            return None

        try:
            session = self._repo.start_session(note=note)
        except ActiveSessionExistsError:
            self._emit_error("已有进行中的睡眠会话。")
            return None
        except SleepTrackerDataError as exc:
            self._emit_error(f"开始睡眠会话失败：{exc}")
            return None

        self._active_session = session
        self._sync_internal_timer_state()
        self._emit_tick()
        self.session_started.emit(session)
        return session

    def end_session(
        self,
        *,
        end_time: datetime | None = None,
        quality_score: int | None = None,
        note: str | None = None,
    ) -> SleepSession | None:
        """End active session and stop updates."""
        if self._active_session is None:
            self._emit_error("当前没有可结束的睡眠会话。")
            return None

        try:
            session = self._repo.end_active_session(
                end_time=end_time,
                quality_score=quality_score,
                note=note,
            )
        except NoActiveSessionError:
            self._emit_error("当前没有可结束的睡眠会话。")
            self._active_session = None
            self._sync_internal_timer_state()
            self._emit_tick()
            return None
        except SleepTrackerDataError as exc:
            self._emit_error(f"结束睡眠会话失败：{exc}")
            return None

        self._active_session = None
        self._sync_internal_timer_state()
        self.tick.emit(self.format_elapsed_from_minutes(session.duration_minutes), 0)
        self.session_ended.emit(session)
        return session

    def elapsed_seconds(self) -> int:
        """Return elapsed seconds for active session."""
        if self._active_session is None:
            return 0
        elapsed = int((utc_now() - self._active_session.start_time).total_seconds())
        return max(0, elapsed)

    @staticmethod
    def format_elapsed(elapsed_seconds: int) -> str:
        """Format elapsed seconds as HH:MM:SS."""
        safe_seconds = max(0, int(elapsed_seconds))
        hours, remainder = divmod(safe_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def format_elapsed_from_minutes(duration_minutes: int | None) -> str:
        """Format duration minutes as HH:MM:SS."""
        if duration_minutes is None:
            return "00:00:00"
        return SleepTimerService.format_elapsed(duration_minutes * 60)

    def shutdown(self) -> None:
        """Stop the internal timer."""
        if self._timer.isActive():
            self._timer.stop()

    def _on_timeout(self) -> None:
        self._emit_tick()

    def _emit_tick(self) -> None:
        elapsed = self.elapsed_seconds()
        self.tick.emit(self.format_elapsed(elapsed), elapsed)

    def _sync_internal_timer_state(self) -> None:
        should_run = self._active_session is not None
        if should_run and not self._timer.isActive():
            self._timer.start()
        if not should_run and self._timer.isActive():
            self._timer.stop()
        self.state_changed.emit(should_run)

    def _emit_error(self, message: str) -> None:
        logger.warning(message)
        self.error_occurred.emit(message)

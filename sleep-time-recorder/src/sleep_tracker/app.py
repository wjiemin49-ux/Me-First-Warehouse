"""Application bootstrap module."""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from sleep_tracker.core.constants import APP_NAME
from sleep_tracker.data import (
    DatabaseInitializationError,
    DatabaseManager,
    SleepSessionRepository,
)
from sleep_tracker.services import SleepReminderService, SleepTimerService
from sleep_tracker.ui import SleepMainWindow, ThemeManager
from sleep_tracker.utils import config_dir, runtime_root

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Initialize logging from config/logging.ini when available."""
    config_path = config_dir() / "logging.ini"
    if config_path.exists():
        try:
            logging.config.fileConfig(config_path, disable_existing_loggers=False)
            return
        except Exception:
            # Fallback to basic config to avoid startup failure.
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_default_settings() -> dict:
    """Load settings from config/default_settings.json with safe fallback."""
    settings_path = config_dir() / "default_settings.json"
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "theme": "dark",
            "daily_sleep_goal_hours": 8.0,
            "notifications_enabled": True,
            "reminder_time": "22:30",
            "minimize_to_tray": True,
            "auto_start_timer_on_launch": False,
            "database_path": "sleep_records.db",
        }


def save_settings(settings: dict) -> None:
    """Persist settings to config/default_settings.json."""
    settings_path = config_dir() / "default_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings, ensure_ascii=False, indent=2)
    settings_path.write_text(payload, encoding="utf-8")


def resolve_database_path(settings: dict) -> Path:
    """Resolve DB path from settings, defaulting to project root."""
    raw_path = settings.get("database_path", "sleep_records.db")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = runtime_root() / candidate
    return candidate.resolve()


def run() -> int:
    """Run Qt event loop."""
    configure_logging()
    app = QApplication(sys.argv)
    settings = load_default_settings()

    theme_manager = ThemeManager(app=app)
    applied_theme = theme_manager.apply_theme(settings.get("theme", "dark"))
    settings["theme"] = applied_theme

    try:
        db_path = resolve_database_path(settings)
        db_manager = DatabaseManager(db_path=db_path)
        session_repository = SleepSessionRepository(db_manager=db_manager)
        session_repository.initialize()
    except DatabaseInitializationError as exc:
        logger.exception("Database initialization failed")
        QMessageBox.critical(
            None,
            APP_NAME,
            f"数据库初始化失败：\n{exc}",
        )
        return 1

    timer_service = SleepTimerService(session_repository=session_repository)
    if bool(settings.get("auto_start_timer_on_launch", False)) and not timer_service.is_running:
        timer_service.start_session(note="应用启动自动开始")

    window = SleepMainWindow(
        settings=settings,
        session_repository=session_repository,
        timer_service=timer_service,
        reminder_service=SleepReminderService(),
        theme_manager=theme_manager,
        on_settings_changed=save_settings,
    )
    window.show()
    return app.exec()

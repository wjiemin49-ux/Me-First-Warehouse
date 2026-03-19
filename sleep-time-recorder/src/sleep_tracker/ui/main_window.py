"""Main window UI shell for Sleep Time Recorder."""

from __future__ import annotations

from collections.abc import Callable
import logging

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sleep_tracker.core.constants import (
    APP_NAME,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from sleep_tracker.data import SleepSession, SleepSessionRepository
from sleep_tracker.services import SleepReminderService, SleepTimerService
from sleep_tracker.ui.system_tray_controller import SystemTrayController
from sleep_tracker.ui.theme_manager import ThemeManager
from sleep_tracker.widgets import HistoryListWidget, MetricCard, SettingsPanelWidget, SleepTrendWidget

logger = logging.getLogger(__name__)


class SleepMainWindow(QMainWindow):
    """Main shell window with dashboard and timer interactions."""

    def __init__(
        self,
        settings: dict,
        session_repository: SleepSessionRepository,
        timer_service: SleepTimerService,
        reminder_service: SleepReminderService,
        theme_manager: ThemeManager,
        on_settings_changed: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.session_repository = session_repository
        self.timer_service = timer_service
        self.reminder_service = reminder_service
        self.theme_manager = theme_manager
        self.on_settings_changed = on_settings_changed

        self.tray_controller: SystemTrayController | None = None
        self.trend_widget: SleepTrendWidget | None = None

        self._allow_close = False
        self._tray_hint_shown = False
        self._pending_history_refresh = False
        self._pending_trend_refresh = False
        self._trend_tab_index = -1

        self._data_refresh_timer = QTimer(self)
        self._data_refresh_timer.setSingleShot(True)
        self._data_refresh_timer.setInterval(150)
        self._data_refresh_timer.timeout.connect(self._run_scheduled_refresh)

        self.setWindowTitle(APP_NAME)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._build_ui()
        self._bind_timer_signals()
        self._setup_system_tray()
        self._setup_reminder_service()
        self._refresh_dashboard()
        self._sync_theme_controls()
        self._sync_timer_cards()
        self.settings_widget.set_settings(self.settings)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Minimize to tray when enabled, otherwise close cleanly."""
        if self._should_minimize_to_tray():
            event.ignore()
            self._minimize_to_tray(show_message=True)
            return

        if self.tray_controller is not None:
            self.tray_controller.shutdown()
            self.tray_controller = None
        self.reminder_service.shutdown()
        self.timer_service.shutdown()
        super().closeEvent(event)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        """Handle minimize-to-tray behavior."""
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self._should_minimize_to_tray()
        ):
            QTimer.singleShot(0, lambda: self._minimize_to_tray(show_message=True))
        super().changeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)

        page_layout = QVBoxLayout(root)
        page_layout.setContentsMargins(20, 20, 20, 20)
        page_layout.setSpacing(14)

        page_layout.addWidget(self._build_header())
        page_layout.addLayout(self._build_metrics_row())
        page_layout.addLayout(self._build_body_row())
        page_layout.addWidget(self._build_tabs(), stretch=1)
        page_layout.setStretch(3, 1)

    def _build_header(self) -> QWidget:
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")

        layout = QHBoxLayout(header_card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        title_label = QLabel("睡眠时间记录器")
        title_label.setObjectName("WindowTitleLabel")
        subtitle_label = QLabel("通过实时计时与本地历史记录，追踪你的睡眠")
        subtitle_label.setObjectName("WindowSubtitleLabel")
        subtitle_label.setWordWrap(True)

        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)

        actions_col = QVBoxLayout()
        actions_col.setSpacing(8)
        actions_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.theme_state_label = QLabel("")
        self.theme_state_label.setObjectName("ThemeBadgeLabel")

        self.theme_button = QPushButton("")
        self.theme_button.setObjectName("SecondaryButton")
        self.theme_button.clicked.connect(self._toggle_theme)

        actions_col.addWidget(self.theme_state_label, alignment=Qt.AlignmentFlag.AlignRight)
        actions_col.addWidget(self.theme_button, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(title_col, stretch=1)
        layout.addLayout(actions_col)
        return header_card

    def _build_metrics_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        goal_hours = float(self.settings.get("daily_sleep_goal_hours", 8.0))
        self.goal_card = MetricCard("睡眠目标", f"{goal_hours:.1f} 小时", "每日目标")
        self.records_card = MetricCard("总记录数", "0", "已保存会话")
        self.session_state_card = MetricCard("当前状态", "空闲", "暂无进行中的会话")

        row.addWidget(self.goal_card, stretch=1)
        row.addWidget(self.records_card, stretch=1)
        row.addWidget(self.session_state_card, stretch=1)
        return row

    def _build_body_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        timer_card = QFrame()
        timer_card.setObjectName("PanelCard")
        timer_layout = QVBoxLayout(timer_card)
        timer_layout.setContentsMargins(20, 18, 20, 18)
        timer_layout.setSpacing(10)

        timer_title = QLabel("睡眠计时器")
        timer_title.setObjectName("SectionTitleLabel")

        self.timer_display_label = QLabel("00:00:00")
        self.timer_display_label.setObjectName("TimerDisplayLabel")
        self.timer_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timer_status_label = QLabel("暂无进行中的睡眠记录")
        self.timer_status_label.setObjectName("TimerStatusLabel")
        self.timer_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.start_button = QPushButton("开始睡眠")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(self._handle_start_clicked)

        self.end_button = QPushButton("结束睡眠")
        self.end_button.setObjectName("SecondaryButton")
        self.end_button.clicked.connect(self._handle_end_clicked)

        button_row.addWidget(self.start_button, stretch=1)
        button_row.addWidget(self.end_button, stretch=1)

        timer_layout.addWidget(timer_title)
        timer_layout.addWidget(self.timer_display_label, stretch=1)
        timer_layout.addWidget(self.timer_status_label)
        timer_layout.addLayout(button_row)

        side_card = QFrame()
        side_card.setObjectName("PanelCard")
        side_layout = QVBoxLayout(side_card)
        side_layout.setContentsMargins(20, 18, 20, 18)
        side_layout.setSpacing(8)

        side_title = QLabel("项目进度")
        side_title.setObjectName("SectionTitleLabel")

        self.quick_summary_label = QLabel(
            "第 10 步已完成：应用已整合优化，可直接打包。"
        )
        self.quick_summary_label.setObjectName("BodyMutedLabel")
        self.quick_summary_label.setWordWrap(True)

        side_layout.addWidget(side_title)
        side_layout.addWidget(self.quick_summary_label)
        side_layout.addStretch(1)

        row.addWidget(timer_card, stretch=2)
        row.addWidget(side_card, stretch=1)
        return row

    def _build_tabs(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setObjectName("MainTabs")
        tabs.currentChanged.connect(self._on_tab_changed)

        self.history_widget = HistoryListWidget(self.session_repository)
        self.history_widget.session_deleted.connect(self._on_history_session_deleted)
        self.history_widget.session_note_updated.connect(self._on_history_session_note_updated)
        self.history_widget.refresh_failed.connect(self._on_history_refresh_failed)

        self.trend_host = QWidget()
        trend_host_layout = QVBoxLayout(self.trend_host)
        trend_host_layout.setContentsMargins(8, 8, 8, 8)
        trend_host_layout.setSpacing(0)
        self.trend_placeholder_label = QLabel("打开此标签页时将按需加载趋势图。")
        self.trend_placeholder_label.setObjectName("BodyMutedLabel")
        self.trend_placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        trend_host_layout.addWidget(self.trend_placeholder_label, stretch=1)

        tabs.addTab(self.history_widget, "历史记录")
        self._trend_tab_index = tabs.addTab(
            self._wrap_tab_with_scroll(self.trend_host, min_height=760),
            "趋势图",
        )
        tabs.addTab(
            self._wrap_tab_with_scroll(self._build_settings_tab(), min_height=720),
            "系统设置",
        )

        self.main_tabs = tabs
        return tabs

    def _wrap_tab_with_scroll(self, content: QWidget, *, min_height: int) -> QScrollArea:
        """Wrap tab content with vertical scrolling to avoid clipping in small windows."""
        content.setMinimumHeight(min_height)
        scroll = QScrollArea()
        scroll.setObjectName("TabScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        return scroll

    def _build_settings_tab(self) -> QWidget:
        self.settings_widget = SettingsPanelWidget(self.settings)
        self.settings_widget.settings_applied.connect(self._on_settings_applied)
        return self.settings_widget

    def _on_tab_changed(self, index: int) -> None:
        if index == self._trend_tab_index:
            self._ensure_trend_widget()

    def _ensure_trend_widget(self) -> SleepTrendWidget:
        if self.trend_widget is not None:
            return self.trend_widget

        widget = SleepTrendWidget(
            self.session_repository,
            goal_hours=float(self.settings.get("daily_sleep_goal_hours", 8.0)),
            theme=self.theme_manager.current_theme,
            days=7,
        )
        widget.setMinimumHeight(760)
        widget.refresh_failed.connect(self._on_trend_refresh_failed)

        host_layout = self.trend_host.layout()
        assert isinstance(host_layout, QVBoxLayout)
        while host_layout.count():
            item = host_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()
        host_layout.addWidget(widget, stretch=1)

        self.trend_widget = widget
        return widget

    def _schedule_data_refresh(self, *, refresh_history: bool, refresh_trend: bool) -> None:
        self._pending_history_refresh = self._pending_history_refresh or refresh_history
        self._pending_trend_refresh = self._pending_trend_refresh or refresh_trend
        if not self._data_refresh_timer.isActive():
            self._data_refresh_timer.start()

    def _run_scheduled_refresh(self) -> None:
        if self._pending_history_refresh:
            self.history_widget.refresh_data()
        if self._pending_trend_refresh and self.trend_widget is not None:
            self.trend_widget.refresh_data()
        self._pending_history_refresh = False
        self._pending_trend_refresh = False

    def _bind_timer_signals(self) -> None:
        self.timer_service.tick.connect(self._on_timer_tick)
        self.timer_service.state_changed.connect(self._on_timer_state_changed)
        self.timer_service.session_started.connect(self._on_session_started)
        self.timer_service.session_ended.connect(self._on_session_ended)
        self.timer_service.error_occurred.connect(self._on_timer_error)
        self.reminder_service.reminder_due.connect(self._on_reminder_due)
        self.reminder_service.config_error.connect(self._on_reminder_config_error)

    def _setup_reminder_service(self) -> None:
        self._configure_reminder_service_from_settings()

    def _setup_system_tray(self) -> None:
        if not bool(self.settings.get("minimize_to_tray", True)):
            return

        controller = SystemTrayController(app_name=APP_NAME, parent_window=self)
        if not controller.setup():
            self.tray_controller = None
            return

        controller.toggle_window_requested.connect(self._toggle_window_from_tray)
        controller.quick_start_requested.connect(self._on_tray_quick_start)
        controller.quick_end_requested.connect(self._on_tray_quick_end)
        controller.quit_requested.connect(self._quit_from_tray)
        controller.set_window_hidden(False)
        controller.set_session_running(self.timer_service.is_running)
        self.tray_controller = controller

    def _sync_tray_with_settings(self) -> None:
        tray_enabled = bool(self.settings.get("minimize_to_tray", True))
        if tray_enabled and self.tray_controller is None:
            self._setup_system_tray()
            return
        if not tray_enabled and self.tray_controller is not None:
            self.tray_controller.shutdown()
            self.tray_controller = None

    def _configure_reminder_service_from_settings(self) -> None:
        self.reminder_service.configure(
            enabled=bool(self.settings.get("notifications_enabled", True)),
            reminder_time=str(self.settings.get("reminder_time", "22:30")),
        )

    def _should_minimize_to_tray(self) -> bool:
        return (
            not self._allow_close
            and bool(self.settings.get("minimize_to_tray", True))
            and self.tray_controller is not None
            and self.tray_controller.is_ready
        )

    def _minimize_to_tray(self, *, show_message: bool) -> None:
        if self.tray_controller is None:
            return

        self.hide()
        self.tray_controller.set_window_hidden(True)

        if show_message and not self._tray_hint_shown:
            self._notify_tray("托盘运行中", "应用已最小化到系统托盘，右键可使用快捷操作。")
            self._tray_hint_shown = True

    def _restore_from_tray(self) -> None:
        if self.tray_controller is not None:
            self.tray_controller.set_window_hidden(False)
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_window_from_tray(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self._minimize_to_tray(show_message=False)
            return
        self._restore_from_tray()

    def _quit_from_tray(self) -> None:
        self._allow_close = True
        self.close()

    def _on_tray_quick_start(self) -> None:
        session = self.timer_service.start_session(note="从托盘快速开始")
        if session is None:
            return
        self._notify_tray(
            "睡眠已开始",
            f"开始时间 {session.start_time.astimezone().strftime('%H:%M:%S')}",
        )

    def _on_tray_quick_end(self) -> None:
        session = self.timer_service.end_session()
        if session is None:
            return
        self._notify_tray(
            "睡眠已结束",
            f"时长：{self._duration_label(session.duration_minutes)}",
        )

    def _notify_tray(self, title: str, message: str) -> None:
        if not bool(self.settings.get("notifications_enabled", True)):
            return
        if self.tray_controller is None:
            return
        self.tray_controller.show_message(title, message)

    def _refresh_dashboard(self) -> None:
        total = self.session_repository.count_sessions()
        self.records_card.set_value(str(total))
        self.records_card.set_helper_text("已保存会话")

        goal_hours = float(self.settings.get("daily_sleep_goal_hours", 8.0))
        self.goal_card.set_value(f"{goal_hours:.1f} 小时")
        if self.trend_widget is not None:
            self.trend_widget.set_goal_hours(goal_hours)

    def _sync_timer_cards(self) -> None:
        active = self.timer_service.active_session
        if active is None:
            self.session_state_card.set_value("空闲")
            self.session_state_card.set_helper_text("暂无进行中的会话")
            self.timer_status_label.setText("暂无进行中的睡眠记录")
            self.start_button.setEnabled(True)
            self.end_button.setEnabled(False)
            self.timer_display_label.setText("00:00:00")
            return

        self.session_state_card.set_value("进行中")
        self.session_state_card.set_helper_text("会话进行中")
        self.timer_status_label.setText(
            f"开始于 {active.start_time.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.timer_display_label.setText(
            self.timer_service.format_elapsed(self.timer_service.elapsed_seconds())
        )

    def _handle_start_clicked(self) -> None:
        self.start_button.setEnabled(False)
        session = self.timer_service.start_session()
        if session is None:
            self.start_button.setEnabled(True)

    def _handle_end_clicked(self) -> None:
        self.end_button.setEnabled(False)
        session = self.timer_service.end_session()
        if session is None:
            self.end_button.setEnabled(True)
            return
        self._show_session_summary(session)

    def _on_timer_tick(self, display_text: str, _elapsed_seconds: int) -> None:
        self.timer_display_label.setText(display_text)

    def _on_timer_state_changed(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.end_button.setEnabled(running)
        if self.tray_controller is not None:
            self.tray_controller.set_session_running(running)
        if running:
            self.session_state_card.set_value("进行中")
            self.session_state_card.set_helper_text("会话进行中")
        else:
            self.session_state_card.set_value("空闲")
            self.session_state_card.set_helper_text("暂无进行中的会话")

    def _on_session_started(self, session: SleepSession) -> None:
        self.timer_status_label.setText(
            f"记录中... 开始于 {session.start_time.astimezone().strftime('%H:%M:%S')}"
        )
        self._refresh_dashboard()
        self._schedule_data_refresh(refresh_history=True, refresh_trend=True)

    def _on_session_ended(self, session: SleepSession) -> None:
        self.timer_status_label.setText(
            f"已完成，时长 {self._duration_label(session.duration_minutes)}"
        )
        self._refresh_dashboard()
        self._schedule_data_refresh(refresh_history=True, refresh_trend=True)

    def _on_history_session_deleted(self, _session_id: int) -> None:
        self._refresh_dashboard()
        self._sync_timer_cards()
        self._schedule_data_refresh(refresh_history=False, refresh_trend=True)

    def _on_history_session_note_updated(self, _session: SleepSession) -> None:
        return

    def _on_history_refresh_failed(self, message: str) -> None:
        self.timer_status_label.setText(message)

    def _on_trend_refresh_failed(self, message: str) -> None:
        self.timer_status_label.setText(message)

    def _on_settings_applied(self, updates: dict) -> None:
        self._apply_settings_updates(updates, persist=True, refresh_trend=True)

    def _apply_settings_updates(
        self,
        updates: dict,
        *,
        persist: bool,
        refresh_trend: bool,
    ) -> None:
        self.settings.update(updates)

        applied_theme = self.theme_manager.apply_theme(str(self.settings.get("theme", "dark")))
        self.settings["theme"] = applied_theme
        if self.trend_widget is not None:
            self.trend_widget.set_theme(applied_theme)
        self._sync_theme_controls()

        self._sync_tray_with_settings()
        self._configure_reminder_service_from_settings()
        self._refresh_dashboard()
        if refresh_trend:
            self._schedule_data_refresh(refresh_history=False, refresh_trend=True)
        self.settings_widget.set_settings(self.settings)

        if persist and self.on_settings_changed is not None:
            try:
                self.on_settings_changed(self.settings)
            except OSError as exc:
                logger.warning("Failed to persist settings: %s", exc)
                self.timer_status_label.setText("设置保存失败。")

    def _on_timer_error(self, message: str) -> None:
        self.timer_status_label.setText(message)
        if self.isVisible():
            QMessageBox.warning(self, APP_NAME, message)
        else:
            self._notify_tray(APP_NAME, message)
        self._sync_timer_cards()

    def _on_reminder_due(self, message: str) -> None:
        self.timer_status_label.setText(message)
        if self.isVisible() and not self.isMinimized():
            QMessageBox.information(self, APP_NAME, message)
        self._notify_tray("睡眠提醒", message)

    def _on_reminder_config_error(self, message: str) -> None:
        self.timer_status_label.setText(message)
        if self.isVisible():
            QMessageBox.warning(self, APP_NAME, message)

    def _show_session_summary(self, session: SleepSession) -> None:
        QMessageBox.information(
            self,
            APP_NAME,
            (
                "睡眠记录已保存。\n"
                f"时长：{self._duration_label(session.duration_minutes)}\n"
                f"开始：{session.start_time.astimezone().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"结束：{session.end_time.astimezone().strftime('%Y-%m-%d %H:%M:%S') if session.end_time else '-'}"
            ),
        )

    def _toggle_theme(self) -> None:
        new_theme = "light" if self.theme_manager.current_theme == "dark" else "dark"
        self._apply_settings_updates({"theme": new_theme}, persist=True, refresh_trend=False)

    def _sync_theme_controls(self) -> None:
        theme = self.theme_manager.current_theme
        if theme == "dark":
            self.theme_state_label.setText("主题：深色")
            self.theme_button.setText("切换到浅色")
        else:
            self.theme_state_label.setText("主题：浅色")
            self.theme_button.setText("切换到深色")

    @staticmethod
    def _duration_label(duration_minutes: int | None) -> str:
        if duration_minutes is None:
            return "0分钟"
        hours, minutes = divmod(duration_minutes, 60)
        if hours == 0:
            return f"{minutes}分钟"
        return f"{hours}小时 {minutes}分钟"

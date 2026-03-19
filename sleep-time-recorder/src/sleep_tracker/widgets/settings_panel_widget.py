"""Settings center widget."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class SettingsPanelWidget(QWidget):
    """Settings form for sleep goals, reminder, theme and tray behavior."""

    settings_applied = Signal(dict)

    def __init__(self, settings: dict) -> None:
        super().__init__()
        self._settings = dict(settings)
        self._build_ui()
        self.set_settings(self._settings)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        title = QLabel("设置中心")
        title.setObjectName("SectionTitleLabel")
        subtitle = QLabel("自定义目标、提醒、主题和托盘行为。")
        subtitle.setObjectName("BodyMutedLabel")

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        form.setFormAlignment(form.formAlignment())
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.goal_hours_spin = QDoubleSpinBox()
        self.goal_hours_spin.setRange(3.0, 12.0)
        self.goal_hours_spin.setSingleStep(0.5)
        self.goal_hours_spin.setDecimals(1)
        self.goal_hours_spin.setSuffix(" 小时")

        self.notifications_checkbox = QCheckBox("启用睡前提醒通知")
        self.notifications_checkbox.toggled.connect(self._sync_reminder_enabled_state)

        self.reminder_time_edit = QTimeEdit()
        self.reminder_time_edit.setDisplayFormat("HH:mm")
        self.reminder_time_edit.setTime(QTime(22, 30))

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("深色", "dark")
        self.theme_combo.addItem("浅色", "light")

        self.tray_checkbox = QCheckBox("最小化到系统托盘")
        self.auto_start_checkbox = QCheckBox("应用启动时自动开始计时")

        form.addRow("每日睡眠目标", self.goal_hours_spin)
        form.addRow("主题", self.theme_combo)
        form.addRow("提醒通知", self.notifications_checkbox)
        form.addRow("提醒时间", self.reminder_time_edit)
        form.addRow("托盘行为", self.tray_checkbox)
        form.addRow("启动行为", self.auto_start_checkbox)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)

        self.reset_button = QPushButton("重置")
        self.reset_button.setObjectName("SecondaryButton")
        self.reset_button.clicked.connect(self._on_reset_clicked)

        self.apply_button = QPushButton("应用设置")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self._on_apply_clicked)

        actions.addWidget(self.reset_button)
        actions.addWidget(self.apply_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("SettingsStatusLabel")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addLayout(form)
        card_layout.addLayout(actions)
        card_layout.addWidget(self.status_label)

        root.addWidget(card)
        root.addStretch(1)

    def set_settings(self, settings: dict) -> None:
        """Load control values from settings dict."""
        self._settings = dict(settings)

        goal = float(self._settings.get("daily_sleep_goal_hours", 8.0))
        notifications = bool(self._settings.get("notifications_enabled", True))
        reminder = str(self._settings.get("reminder_time", "22:30"))
        theme = str(self._settings.get("theme", "dark"))
        minimize_to_tray = bool(self._settings.get("minimize_to_tray", True))
        auto_start = bool(self._settings.get("auto_start_timer_on_launch", False))

        with QSignalBlocker(self.notifications_checkbox):
            self.notifications_checkbox.setChecked(notifications)

        with QSignalBlocker(self.goal_hours_spin):
            self.goal_hours_spin.setValue(goal)

        reminder_qtime = QTime.fromString(reminder, "HH:mm")
        if not reminder_qtime.isValid():
            reminder_qtime = QTime(22, 30)
        with QSignalBlocker(self.reminder_time_edit):
            self.reminder_time_edit.setTime(reminder_qtime)

        theme_index = self.theme_combo.findData(theme)
        if theme_index < 0:
            theme_index = self.theme_combo.findData("dark")
        with QSignalBlocker(self.theme_combo):
            self.theme_combo.setCurrentIndex(max(0, theme_index))

        with QSignalBlocker(self.tray_checkbox):
            self.tray_checkbox.setChecked(minimize_to_tray)

        with QSignalBlocker(self.auto_start_checkbox):
            self.auto_start_checkbox.setChecked(auto_start)

        self._sync_reminder_enabled_state(notifications)

    def _on_apply_clicked(self) -> None:
        payload = self.collect_settings_payload()
        self.settings_applied.emit(payload)
        self.status_label.setText("设置已应用。")

    def _on_reset_clicked(self) -> None:
        self.set_settings(self._settings)
        self.status_label.setText("已还原未保存更改。")

    def collect_settings_payload(self) -> dict:
        """Collect current form values into a settings update payload."""
        reminder_time = self.reminder_time_edit.time().toString("HH:mm")
        return {
            "daily_sleep_goal_hours": float(self.goal_hours_spin.value()),
            "notifications_enabled": bool(self.notifications_checkbox.isChecked()),
            "reminder_time": reminder_time,
            "theme": str(self.theme_combo.currentData()),
            "minimize_to_tray": bool(self.tray_checkbox.isChecked()),
            "auto_start_timer_on_launch": bool(self.auto_start_checkbox.isChecked()),
        }

    def _sync_reminder_enabled_state(self, enabled: bool) -> None:
        self.reminder_time_edit.setEnabled(bool(enabled))

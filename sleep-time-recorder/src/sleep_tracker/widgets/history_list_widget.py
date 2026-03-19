"""History list widget with note editing and delete actions."""

from __future__ import annotations

from datetime import datetime
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sleep_tracker.data import SessionNotFoundError, SleepSession, SleepSessionRepository
from sleep_tracker.data.exceptions import SleepTrackerDataError

logger = logging.getLogger(__name__)

SESSION_ID_ROLE = Qt.ItemDataRole.UserRole
ORIGINAL_NOTE_ROLE = Qt.ItemDataRole.UserRole + 1


class HistoryListWidget(QWidget):
    """Scrollable list of persisted sleep sessions."""

    session_deleted = Signal(int)
    session_note_updated = Signal(object)
    refresh_failed = Signal(str)

    def __init__(self, session_repository: SleepSessionRepository, page_size: int = 300) -> None:
        super().__init__()
        self.session_repository = session_repository
        self.page_size = page_size
        self._is_loading = False
        self._session_by_id: dict[int, SleepSession] = {}

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("HistoryHeaderCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        title = QLabel("睡眠历史记录")
        title.setObjectName("SectionTitleLabel")
        subtitle = QLabel("滚动查看记录，可直接在表格里编辑备注，已完成会话支持删除。")
        subtitle.setObjectName("BodyMutedLabel")

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_data)

        header_layout.addLayout(title_box, stretch=1)
        header_layout.addWidget(self.refresh_button)

        self.table = QTableWidget()
        self.table.setObjectName("HistoryTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["开始时间", "结束时间", "时长", "质量", "备注（可编辑）", "操作"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.itemChanged.connect(self._on_item_changed)

        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(0, header_view.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, header_view.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, header_view.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, header_view.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, header_view.ResizeMode.Stretch)
        header_view.setSectionResizeMode(5, header_view.ResizeMode.ResizeToContents)

        self.status_label = QLabel("")
        self.status_label.setObjectName("HistoryStatusLabel")

        root_layout.addWidget(header)
        root_layout.addWidget(self.table, stretch=1)
        root_layout.addWidget(self.status_label)

    def refresh_data(self) -> None:
        """Reload rows from repository while keeping current scroll position."""
        scrollbar = self.table.verticalScrollBar()
        previous_scroll = scrollbar.value()

        try:
            sessions = self.session_repository.list_sessions(limit=self.page_size, offset=0)
        except SleepTrackerDataError as exc:
            message = f"加载历史记录失败：{exc}"
            logger.warning(message)
            self.refresh_failed.emit(message)
            self.status_label.setText(message)
            return

        self._session_by_id = {session.id: session for session in sessions}
        self._is_loading = True
        try:
            self.table.setRowCount(len(sessions))
            for row, session in enumerate(sessions):
                self._write_row(row, session)
        finally:
            self._is_loading = False

        scrollbar.setValue(min(previous_scroll, scrollbar.maximum()))
        self.status_label.setText(f"已加载 {len(sessions)} 条记录。")

    def update_note_for_session(self, session_id: int, note: str) -> SleepSession | None:
        """Persist note update and emit result signal."""
        try:
            updated = self.session_repository.update_note(session_id=session_id, note=note)
        except (SessionNotFoundError, SleepTrackerDataError) as exc:
            message = f"更新备注失败：{exc}"
            logger.warning(message)
            self.refresh_failed.emit(message)
            self.status_label.setText(message)
            return None

        self._session_by_id[session_id] = updated
        self.session_note_updated.emit(updated)
        self.status_label.setText(f"会话 #{session_id} 备注已更新。")
        return updated

    def delete_session(self, session_id: int, *, confirm: bool = True) -> bool:
        """Delete one completed session. Active sessions are protected."""
        session = self._session_by_id.get(session_id)
        if session is not None and session.is_active:
            self.status_label.setText("进行中的会话不能删除。")
            return False

        if confirm:
            reply = QMessageBox.question(
                self,
                "删除记录",
                f"确定删除会话 #{session_id} 吗？此操作不可撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        try:
            self.session_repository.delete_session(session_id=session_id)
        except (SessionNotFoundError, SleepTrackerDataError) as exc:
            message = f"删除会话失败：{exc}"
            logger.warning(message)
            self.refresh_failed.emit(message)
            self.status_label.setText(message)
            return False

        self.session_deleted.emit(session_id)
        self.refresh_data()
        self.status_label.setText(f"已删除会话 #{session_id}。")
        return True

    def _write_row(self, row: int, session: SleepSession) -> None:
        start_item = QTableWidgetItem(self._fmt_datetime(session.start_time))
        end_item = QTableWidgetItem(self._fmt_datetime(session.end_time))
        duration_item = QTableWidgetItem(self._fmt_duration(session.duration_minutes))
        quality_item = QTableWidgetItem(self._fmt_quality(session.quality_score))
        note_item = QTableWidgetItem(session.note)

        for item in (start_item, end_item, duration_item, quality_item, note_item):
            item.setData(SESSION_ID_ROLE, session.id)

        note_item.setData(ORIGINAL_NOTE_ROLE, session.note)
        if session.is_active:
            note_item.setToolTip("会话进行中时也可编辑备注。")

        start_item.setFlags(start_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        end_item.setFlags(end_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setItem(row, 0, start_item)
        self.table.setItem(row, 1, end_item)
        self.table.setItem(row, 2, duration_item)
        self.table.setItem(row, 3, quality_item)
        self.table.setItem(row, 4, note_item)

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        delete_button = QPushButton("删除")
        delete_button.setObjectName("DangerButton")
        delete_button.setProperty("sessionId", session.id)
        if session.is_active:
            delete_button.setEnabled(False)
            delete_button.setToolTip("进行中的会话不能删除。")
        else:
            delete_button.clicked.connect(
                lambda _checked=False, sid=session.id: self.delete_session(sid, confirm=True)
            )
        action_layout.addWidget(delete_button)
        action_layout.addStretch(1)
        self.table.setCellWidget(row, 5, action_widget)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_loading:
            return
        if item.column() != 4:
            return

        session_id_data = item.data(SESSION_ID_ROLE)
        if session_id_data is None:
            return

        session_id = int(session_id_data)
        new_note = (item.text() or "").strip()
        original_note = (item.data(ORIGINAL_NOTE_ROLE) or "").strip()
        if new_note == original_note:
            return

        updated = self.update_note_for_session(session_id=session_id, note=new_note)
        if updated is None:
            self._is_loading = True
            try:
                item.setText(original_note)
            finally:
                self._is_loading = False
            return

        self._is_loading = True
        try:
            item.setText(updated.note)
            item.setData(ORIGINAL_NOTE_ROLE, updated.note)
        finally:
            self._is_loading = False

    @staticmethod
    def _fmt_datetime(value: datetime | None) -> str:
        if value is None:
            return "进行中"
        return value.astimezone().strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def _fmt_duration(duration_minutes: int | None) -> str:
        if duration_minutes is None:
            return "--"
        hours, minutes = divmod(duration_minutes, 60)
        return f"{hours}小时 {minutes}分钟"

    @staticmethod
    def _fmt_quality(quality_score: int | None) -> str:
        if quality_score is None:
            return "-"
        safe = max(1, min(quality_score, 5))
        return f"{safe}/5"

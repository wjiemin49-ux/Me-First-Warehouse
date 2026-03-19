"""Placeholder panel for not-yet-implemented modules."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class PlaceholderPanel(QFrame):
    """Simple framed placeholder with title and description."""

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName("PlaceholderPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("PlaceholderTitleLabel")

        description_label = QLabel(description)
        description_label.setObjectName("PlaceholderDescriptionLabel")
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch(1)

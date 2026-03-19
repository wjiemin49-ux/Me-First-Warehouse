"""Metric summary card widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """A compact card for key metrics in dashboard."""

    def __init__(self, title: str, value: str, helper_text: str = "") -> None:
        super().__init__()
        self.setObjectName("MetricCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitleLabel")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValueLabel")

        self.helper_label = QLabel(helper_text)
        self.helper_label.setObjectName("MetricHelperLabel")
        self.helper_label.setVisible(bool(helper_text))

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.helper_label)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        """Update metric value text."""
        self.value_label.setText(value)

    def set_helper_text(self, helper_text: str) -> None:
        """Update optional helper text."""
        self.helper_label.setText(helper_text)
        self.helper_label.setVisible(bool(helper_text))

"""Matplotlib-based trend widget for the latest 7-day sleep quality view."""

from __future__ import annotations

import logging

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sleep_tracker.data import SleepSessionRepository
from sleep_tracker.data.exceptions import SleepTrackerDataError
from sleep_tracker.services import DailySleepTrend, SleepTrendService

logger = logging.getLogger(__name__)


class SleepTrendWidget(QWidget):
    """Displays last N days of sleep duration and quality trends."""

    refresh_failed = Signal(str)

    _THEME_STYLE = {
        "dark": {
            "figure_face": "#101c31",
            "axes_face": "#12233c",
            "text": "#e4edff",
            "muted_text": "#9eb4d8",
            "duration": "#68adff",
            "quality": "#ffbe68",
            "goal": "#79d3a6",
            "grid": "#3b5d87",
            "legend_face": "#142842",
            "legend_edge": "#456a98",
        },
        "light": {
            "figure_face": "#f6fbff",
            "axes_face": "#f1f7ff",
            "text": "#27466a",
            "muted_text": "#6282a6",
            "duration": "#4f8fe0",
            "quality": "#d48634",
            "goal": "#49a27f",
            "grid": "#b2c8e4",
            "legend_face": "#ffffff",
            "legend_edge": "#bfd2ea",
        },
    }

    def __init__(
        self,
        session_repository: SleepSessionRepository,
        *,
        goal_hours: float = 8.0,
        theme: str = "dark",
        days: int = 7,
    ) -> None:
        super().__init__()
        self.session_repository = session_repository
        self.goal_hours = max(0.1, float(goal_hours))
        self.days = max(3, int(days))
        self.theme = theme if theme in self._THEME_STYLE else "dark"

        self._trend_service = SleepTrendService()
        self._cached_trends: list[DailySleepTrend] = []

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(10)

        header_card = QFrame()
        header_card.setObjectName("TrendHeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_label = QLabel("睡眠质量趋势")
        title_label.setObjectName("SectionTitleLabel")
        subtitle_label = QLabel("最近 7 天：时长柱状图 + 质量指数折线")
        subtitle_label.setObjectName("BodyMutedLabel")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_data)

        header_layout.addLayout(title_box, stretch=1)
        header_layout.addWidget(self.refresh_button)

        chart_card = QFrame()
        chart_card.setObjectName("TrendCanvasCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(10, 10, 10, 10)

        self.figure = Figure(figsize=(7.0, 3.8))
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("TrendSummaryLabel")
        self.summary_label.setWordWrap(True)

        self.status_label = QLabel("")
        self.status_label.setObjectName("TrendStatusLabel")

        root_layout.addWidget(header_card)
        root_layout.addWidget(chart_card, stretch=1)
        root_layout.addWidget(self.summary_label)
        root_layout.addWidget(self.status_label)

    def set_theme(self, theme: str) -> None:
        """Apply chart color scheme and redraw."""
        normalized = theme if theme in self._THEME_STYLE else "dark"
        if normalized == self.theme and self._cached_trends:
            return
        self.theme = normalized
        if self._cached_trends:
            self._render_chart(self._cached_trends)

    def set_goal_hours(self, goal_hours: float) -> None:
        """Update target duration and redraw summary/chart."""
        normalized = max(0.1, float(goal_hours))
        if abs(normalized - self.goal_hours) < 1e-6:
            return
        self.goal_hours = normalized
        if self._cached_trends:
            self._render_chart(self._cached_trends)

    def refresh_data(self) -> None:
        """Query recent sessions and redraw chart."""
        fetch_days = max(self.days + 2, 14)
        try:
            sessions = self.session_repository.get_recent_sessions(days=fetch_days)
            trends = self._trend_service.build_daily_trend(
                sessions=sessions,
                goal_hours=self.goal_hours,
                days=self.days,
            )
        except (SleepTrackerDataError, ValueError) as exc:
            message = f"构建趋势数据失败：{exc}"
            logger.warning(message)
            self.refresh_failed.emit(message)
            self.status_label.setText(message)
            return

        self._cached_trends = trends
        self._render_chart(trends)
        self.status_label.setText(f"已加载 {len(trends)} 天数据。")

    def _render_chart(self, trends: list[DailySleepTrend]) -> None:
        style = self._THEME_STYLE[self.theme]
        self.figure.clear()
        self.figure.patch.set_facecolor(style["figure_face"])

        ax_duration = self.figure.add_subplot(111)
        ax_quality = ax_duration.twinx()

        ax_duration.set_facecolor(style["axes_face"])
        ax_quality.set_facecolor("none")

        labels = [point.label for point in trends]
        positions = list(range(len(trends)))
        duration_hours = [point.total_hours for point in trends]
        quality_index_values = [point.quality_index(self.goal_hours) for point in trends]
        quality_line = [
            value if value is not None else float("nan") for value in quality_index_values
        ]

        bars = ax_duration.bar(
            positions,
            duration_hours,
            width=0.58,
            color=style["duration"],
            alpha=0.9,
            label="时长（小时）",
        )
        goal_line = ax_duration.axhline(
            self.goal_hours,
            color=style["goal"],
            linestyle="--",
            linewidth=1.5,
            label=f"目标（{self.goal_hours:.1f}小时）",
        )
        quality_plot, = ax_quality.plot(
            positions,
            quality_line,
            color=style["quality"],
            linewidth=2.0,
            marker="o",
            markersize=5,
            label="质量指数",
        )

        max_hours = max(duration_hours + [self.goal_hours, 1.0])
        ax_duration.set_ylim(0, max_hours * 1.35)
        ax_quality.set_ylim(0, 100)

        ax_duration.set_xticks(positions, labels)
        ax_duration.set_ylabel("小时", color=style["text"])
        ax_quality.set_ylabel("质量（0-100）", color=style["text"])
        ax_duration.set_title(
            f"最近 {self.days} 天睡眠趋势",
            color=style["text"],
            fontsize=12,
            pad=12,
        )

        ax_duration.grid(axis="y", linestyle="--", linewidth=0.8, color=style["grid"], alpha=0.4)

        ax_duration.tick_params(axis="x", colors=style["muted_text"])
        ax_duration.tick_params(axis="y", colors=style["muted_text"])
        ax_quality.tick_params(axis="y", colors=style["muted_text"])

        for axis in (ax_duration, ax_quality):
            axis.spines["top"].set_visible(False)
            axis.spines["left"].set_color(style["grid"])
            axis.spines["right"].set_color(style["grid"])
            axis.spines["bottom"].set_color(style["grid"])

        handles = [bars, goal_line, quality_plot]
        labels_legend = [handle.get_label() for handle in handles]
        legend = ax_duration.legend(
            handles,
            labels_legend,
            loc="upper left",
            frameon=True,
            facecolor=style["legend_face"],
            edgecolor=style["legend_edge"],
        )
        for text in legend.get_texts():
            text.set_color(style["text"])

        if all(point.total_minutes == 0 for point in trends):
            ax_duration.text(
                0.5,
                0.5,
                "该时间段内暂无已完成睡眠记录。",
                transform=ax_duration.transAxes,
                ha="center",
                va="center",
                color=style["muted_text"],
                fontsize=11,
            )

        for idx, point in enumerate(trends):
            if point.total_minutes <= 0:
                continue
            ax_duration.text(
                idx,
                point.total_hours + max_hours * 0.03,
                f"{point.total_hours:.1f}小时",
                ha="center",
                va="bottom",
                color=style["muted_text"],
                fontsize=8,
            )

        summary = self._trend_service.summarize_week(trends, goal_hours=self.goal_hours)
        self.summary_label.setText(
            "7天总时长："
            f"{summary['total_hours']:.2f}小时 | "
            f"日均：{summary['avg_hours']:.2f}小时 | "
            f"平均质量：{summary['avg_quality_index']:.1f}/100 | "
            f"达标天数：{summary['goal_hit_days']}/{len(trends)}"
        )

        self.canvas.draw_idle()

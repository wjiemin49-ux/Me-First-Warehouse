"""活动热力图分析器"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .storage import HistoryStorage

LOGGER = logging.getLogger(__name__)

# 周内星期名称（ISO weekday: 1=周一 ... 7=周日）
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOUR_LABELS = [f"{h:02d}" for h in range(24)]


class ActivityAnalyzer:
    """分析文件夹活动的时间模式，生成热力图数据"""

    def __init__(self, storage: HistoryStorage):
        self.storage = storage
        self.logger = LOGGER

    def get_hourly_heatmap(
        self, folder_path: Path, days: int = 30
    ) -> dict[int, int]:
        """按小时统计活动（新增文件数）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            {hour: file_count} 字典，hour 范围 0-23
        """
        history = self.storage.get_folder_trend(folder_path, days)

        hourly: dict[int, int] = defaultdict(int)
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            hour = scan_time.hour
            hourly[hour] += record["new_file_count"]

        # 确保 0-23 全部存在
        return {h: hourly.get(h, 0) for h in range(24)}

    def get_weekday_heatmap(
        self, folder_path: Path, days: int = 30
    ) -> dict[int, int]:
        """按星期统计活动（新增文件数）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            {weekday: file_count} 字典，weekday 范围 1-7（1=周一）
        """
        history = self.storage.get_folder_trend(folder_path, days)

        weekday_map: dict[int, int] = defaultdict(int)
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            weekday = scan_time.isoweekday()  # 1=Mon, 7=Sun
            weekday_map[weekday] += record["new_file_count"]

        return {w: weekday_map.get(w, 0) for w in range(1, 8)}

    def get_daily_heatmap(
        self, folder_path: Path, days: int = 30
    ) -> list[tuple[date, int]]:
        """按日期统计活动（新增文件数）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            [(date, file_count), ...] 列表，按日期升序
        """
        history = self.storage.get_folder_trend(folder_path, days)

        daily_map: dict[date, int] = defaultdict(int)
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            day = scan_time.date()
            daily_map[day] = max(daily_map[day], record["new_file_count"])

        # 填充缺失日期
        start_date = datetime.now().date() - timedelta(days=days - 1)
        all_days = [start_date + timedelta(days=i) for i in range(days)]
        return [(d, daily_map.get(d, 0)) for d in all_days]

    def get_peak_hours(self, folder_path: Path, days: int = 30) -> list[int]:
        """获取活动高峰小时列表（高于均值的小时）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            高峰小时列表（0-23）
        """
        hourly = self.get_hourly_heatmap(folder_path, days)
        values = list(hourly.values())
        if not any(values):
            return []

        total = sum(values)
        if total == 0:
            return []

        avg = total / 24
        return sorted(
            [h for h, count in hourly.items() if count > avg],
            key=lambda h: hourly[h],
            reverse=True,
        )

    def render_ascii_heatmap(
        self, folder_path: Path, days: int = 30
    ) -> str:
        """渲染 ASCII 周活动热力图（行=星期，列=小时）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            ASCII 热力图字符串
        """
        history = self.storage.get_folder_trend(folder_path, days)

        # 构建 weekday x hour 的二维计数矩阵
        matrix: dict[tuple[int, int], int] = defaultdict(int)
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            weekday = scan_time.isoweekday()  # 1-7
            hour = scan_time.hour
            matrix[(weekday, hour)] += record["new_file_count"]

        if not any(matrix.values()):
            return "(无活动数据)"

        max_val = max(matrix.values()) if matrix else 1

        # 热力图字符（从低到高）
        LEVELS = " ░▒▓█"

        lines = []
        # 标题行（每隔 3 小时显示一个时间）
        header = "     " + "".join(
            f"{h:02d}" if h % 3 == 0 else "  " for h in range(24)
        )
        lines.append(header)

        for weekday in range(1, 8):
            row = f"{WEEKDAY_NAMES[weekday-1]:3s}  "
            for hour in range(24):
                count = matrix.get((weekday, hour), 0)
                # 将计数映射到热力等级
                level_idx = int((count / max_val) * (len(LEVELS) - 1))
                char = LEVELS[level_idx]
                row += char * 2
            lines.append(row)

        return "\n".join(lines)

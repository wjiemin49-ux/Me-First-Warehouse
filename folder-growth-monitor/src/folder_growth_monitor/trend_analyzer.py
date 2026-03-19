"""趋势分析器"""

import logging
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import Anomaly, TrendData
from .storage import HistoryStorage

LOGGER = logging.getLogger(__name__)


class TrendAnalyzer:
    """对历史数据进行趋势分析和异常检测"""

    def __init__(self, storage: HistoryStorage):
        self.storage = storage
        self.logger = LOGGER

    def analyze_folder_trend(self, folder_path: Path, days: int = 7) -> TrendData | None:
        """分析文件夹增长趋势

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            趋势数据，数据不足返回 None
        """
        history = self.storage.get_folder_trend(folder_path, days)

        if not history:
            self.logger.debug(f"无历史数据: {folder_path}")
            return None

        # 按日期聚合（每天取最大新增文件数）
        daily_map: dict[date, int] = {}
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            day = scan_time.date()
            new_files = record["new_file_count"]
            daily_map[day] = max(daily_map.get(day, 0), new_files)

        # 填充缺失日期为 0
        start_date = datetime.now().date() - timedelta(days=days - 1)
        all_days = [start_date + timedelta(days=i) for i in range(days)]
        daily_growth = [(d, daily_map.get(d, 0)) for d in all_days]

        values = [count for _, count in daily_growth]
        avg = statistics.mean(values) if values else 0.0

        # 计算增长率（线性回归斜率近似）
        trend_direction, growth_rate = self._calc_trend(values)

        self.logger.debug(
            f"趋势分析完成: {folder_path.name}, 方向={trend_direction}, 增长率={growth_rate:.2f}"
        )

        return TrendData(
            folder_path=folder_path,
            daily_growth=daily_growth,
            avg_daily_growth=avg,
            trend_direction=trend_direction,
            growth_rate=growth_rate,
        )

    def detect_anomalies(
        self, folder_path: Path, days: int = 14
    ) -> list[Anomaly]:
        """检测异常增长（均值 + 2 倍标准差）

        Args:
            folder_path: 文件夹路径
            days: 分析天数

        Returns:
            异常列表
        """
        history = self.storage.get_folder_trend(folder_path, days)

        if len(history) < 3:
            return []

        # 按日期聚合
        daily_map: dict[date, int] = {}
        for record in history:
            scan_time = datetime.fromisoformat(record["scan_time"])
            day = scan_time.date()
            new_files = record["new_file_count"]
            daily_map[day] = max(daily_map.get(day, 0), new_files)

        values = list(daily_map.values())
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0

        high_threshold = mean + 2 * stdev
        low_threshold = max(0.0, mean - 2 * stdev)

        anomalies = []
        for day, count in daily_map.items():
            if count > high_threshold:
                anomalies.append(
                    Anomaly(
                        date=day,
                        value=count,
                        expected_range=(low_threshold, high_threshold),
                        severity="high" if count > mean + 3 * stdev else "medium",
                    )
                )

        anomalies.sort(key=lambda x: x.date)
        self.logger.info(
            f"异常检测完成: {folder_path.name}，发现 {len(anomalies)} 个异常"
        )
        return anomalies

    def get_top_growing_folders(
        self, days: int = 7, top_n: int = 5
    ) -> list[TrendData]:
        """获取增长最快的文件夹列表

        Args:
            days: 分析天数
            top_n: 返回数量

        Returns:
            趋势数据列表（按平均日增长量降序）
        """
        recent_scans = self.storage.get_recent_scans(days)

        if not recent_scans:
            return []

        # 收集所有唯一文件夹路径
        folder_paths: set[Path] = set()
        for scan in recent_scans:
            scan_id = scan["id"]
            rows = self.storage.get_folder_trend(
                Path("."), days  # 占位，下面单独查
            )

        # 直接查所有文件夹路径
        folder_paths = self._get_all_folder_paths(days)

        trends = []
        for folder_path in folder_paths:
            trend = self.analyze_folder_trend(folder_path, days)
            if trend and trend.avg_daily_growth > 0:
                trends.append(trend)

        trends.sort(key=lambda x: x.avg_daily_growth, reverse=True)
        return trends[:top_n]

    def _get_all_folder_paths(self, days: int) -> set[Path]:
        """从历史记录中获取所有文件夹路径"""
        recent_scans = self.storage.get_recent_scans(days)
        folder_paths: set[Path] = set()

        for scan in recent_scans:
            scan_id = scan["id"]
            # 直接查询 folder_growth_history
            rows = self._query_folders_for_scan(scan_id)
            for row in rows:
                folder_paths.add(Path(row["folder_path"]))

        return folder_paths

    def _query_folders_for_scan(self, scan_id: int) -> list[dict]:
        """查询某次扫描的所有文件夹记录"""
        with self.storage.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT folder_path FROM folder_growth_history WHERE scan_id = ?",
                (scan_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _calc_trend(
        self, values: list[int]
    ) -> tuple[str, float]:
        """计算趋势方向和增长率（最小二乘法线性回归）

        Args:
            values: 时间序列值列表

        Returns:
            (趋势方向, 增长率)
        """
        n = len(values)
        if n < 2:
            return "stable", 0.0

        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator  # 每天变化量

        # 判断趋势方向（相对于均值的阈值）
        y_mean_safe = y_mean if y_mean != 0 else 1.0
        relative_slope = slope / y_mean_safe

        if relative_slope > 0.1:
            direction = "rising"
        elif relative_slope < -0.1:
            direction = "falling"
        else:
            direction = "stable"

        return direction, slope

"""增长分析器"""

import logging
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path

from .config import Config
from .models import FileRecord, FileTypeStats, FolderGrowth

LOGGER = logging.getLogger(__name__)


class GrowthAnalyzer:
    """增长分析器，负责判断文件增长情况并聚合统计"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = LOGGER
        self.time_range = self._calculate_time_range()

    def _calculate_time_range(self) -> tuple[datetime, datetime]:
        """计算时间范围

        Returns:
            (开始时间, 结束时间)
        """
        now = datetime.now()

        if self.config.time.mode == "today":
            # 今天 00:00:00 到现在
            start = datetime.combine(now.date(), time.min)
            end = now
        elif self.config.time.mode == "last_24h":
            # 最近 24 小时
            from datetime import timedelta
            start = now - timedelta(hours=24)
            end = now
        else:
            # 默认使用今天模式
            start = datetime.combine(now.date(), time.min)
            end = now

        self.logger.info(f"时间范围: {start} 至 {end}")
        return start, end

    def analyze(self, file_records: dict[Path, list[FileRecord]]) -> list[FolderGrowth]:
        """分析文件记录，生成文件夹增长统计

        Args:
            file_records: 按文件夹分组的文件记录

        Returns:
            文件夹增长统计列表
        """
        folder_growths = []

        for folder_path, files in file_records.items():
            # 更新文件记录的今日标记
            for file in files:
                file.is_new_today = self._is_new_today(file)
                file.is_modified_today = self._is_modified_today(file)

            # 聚合文件夹增长数据
            folder_growth = self._aggregate_folder_growth(folder_path, files)
            folder_growths.append(folder_growth)

        self.logger.info(f"分析完成，共 {len(folder_growths)} 个文件夹")
        return folder_growths

    def _is_new_today(self, file: FileRecord) -> bool:
        """判断文件是否今天新增（基于创建时间）

        Args:
            file: 文件记录

        Returns:
            True 表示今天新增
        """
        start, end = self.time_range
        return start <= file.created_time <= end

    def _is_modified_today(self, file: FileRecord) -> bool:
        """判断文件是否今天修改（基于修改时间）

        Args:
            file: 文件记录

        Returns:
            True 表示今天修改
        """
        start, end = self.time_range
        # 修改时间在范围内，且不是今天新增的文件
        return start <= file.modified_time <= end and not self._is_new_today(file)

    def _aggregate_folder_growth(self, folder_path: Path, files: list[FileRecord]) -> FolderGrowth:
        """聚合单个文件夹的增长数据

        Args:
            folder_path: 文件夹路径
            files: 文件记录列表

        Returns:
            文件夹增长统计
        """
        new_file_count = 0
        new_file_size = 0
        modified_file_count = 0
        modified_file_size = 0
        latest_activity_time = None

        for file in files:
            if file.is_new_today:
                new_file_count += 1
                new_file_size += file.size
                # 更新最后活跃时间
                if latest_activity_time is None or file.created_time > latest_activity_time:
                    latest_activity_time = file.created_time

            if file.is_modified_today:
                modified_file_count += 1
                modified_file_size += file.size
                # 更新最后活跃时间
                if latest_activity_time is None or file.modified_time > latest_activity_time:
                    latest_activity_time = file.modified_time

        return FolderGrowth(
            folder_path=folder_path,
            folder_name=folder_path.name,
            new_file_count=new_file_count,
            new_file_size=new_file_size,
            modified_file_count=modified_file_count,
            modified_file_size=modified_file_size,
            latest_activity_time=latest_activity_time,
            composite_score=0.0,  # 将由 ranker 计算
        )

    def analyze_file_types(
        self,
        file_records: dict[Path, list[FileRecord]],
    ) -> dict[Path, list[FileTypeStats]]:
        """分析文件类型分布

        Args:
            file_records: 文件记录字典

        Returns:
            按文件夹分组的文件类型统计
        """
        results: dict[Path, list[FileTypeStats]] = {}

        for folder_path, files in file_records.items():
            # 按扩展名分组统计
            type_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "size": 0})

            for file in files:
                # 只统计今天新增或修改的文件
                if file.is_new_today or file.is_modified_today:
                    ext = file.path.suffix.lower() or ".no_extension"
                    type_stats[ext]["count"] += 1
                    type_stats[ext]["size"] += file.size

            # 转换为 FileTypeStats 对象
            stats_list = [
                FileTypeStats(
                    extension=ext,
                    file_count=data["count"],
                    total_size=data["size"],
                    folder_path=folder_path,
                )
                for ext, data in type_stats.items()
            ]

            # 按文件数量降序排序
            stats_list.sort(key=lambda x: x.file_count, reverse=True)

            if stats_list:
                results[folder_path] = stats_list

        self.logger.info(f"文件类型分析完成，共 {len(results)} 个文件夹")
        return results

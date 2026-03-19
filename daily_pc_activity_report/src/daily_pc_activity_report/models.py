"""数据模型定义"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class FileActivity:
    """文件活动记录"""
    path: Path
    activity_type: str  # "created" 或 "modified"
    timestamp: datetime
    size: int
    extension: str
    category: str  # downloads, screenshots, projects 等


@dataclass
class DirectoryStats:
    """目录统计信息"""
    path: Path
    category: str
    files_created: int = 0
    files_modified: int = 0
    total_size: int = 0
    file_types: dict[str, int] = field(default_factory=dict)

    @property
    def activity_score(self) -> int:
        """活动分数：创建文件权重更高"""
        return self.files_created * 2 + self.files_modified

    @property
    def total_files(self) -> int:
        """总文件数"""
        return self.files_created + self.files_modified


@dataclass
class DailyReport:
    """每日报告"""
    date: date
    total_files_created: int
    total_files_modified: int
    total_size: int
    directory_stats: list[DirectoryStats]
    top_directories: list[DirectoryStats]
    file_type_distribution: dict[str, int]
    category_stats: dict[str, DirectoryStats]
    summary: str

    @property
    def total_files(self) -> int:
        """总文件数"""
        return self.total_files_created + self.total_files_modified

"""数据模型定义"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FileRecord:
    """单个文件的记录"""
    path: Path
    size: int
    created_time: datetime
    modified_time: datetime
    is_new_today: bool
    is_modified_today: bool


@dataclass(slots=True)
class FolderGrowth:
    """文件夹增长统计"""
    folder_path: Path
    folder_name: str
    new_file_count: int
    new_file_size: int
    modified_file_count: int
    modified_file_size: int
    latest_activity_time: datetime | None
    composite_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "folder_path": str(self.folder_path),
            "folder_name": self.folder_name,
            "new_file_count": self.new_file_count,
            "new_file_size": self.new_file_size,
            "modified_file_count": self.modified_file_count,
            "modified_file_size": self.modified_file_size,
            "latest_activity_time": self.latest_activity_time.isoformat() if self.latest_activity_time else None,
            "composite_score": self.composite_score,
        }


@dataclass(slots=True)
class ScanResult:
    """扫描结果汇总"""
    scan_time: datetime
    time_range_start: datetime
    time_range_end: datetime
    total_folders_scanned: int
    folders_with_growth: int
    total_new_files: int
    total_new_size: int
    total_modified_files: int
    folder_growths: list[FolderGrowth]

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "scan_time": self.scan_time.isoformat(),
            "time_range_start": self.time_range_start.isoformat(),
            "time_range_end": self.time_range_end.isoformat(),
            "total_folders_scanned": self.total_folders_scanned,
            "folders_with_growth": self.folders_with_growth,
            "total_new_files": self.total_new_files,
            "total_new_size": self.total_new_size,
            "total_modified_files": self.total_modified_files,
            "folder_growths": [fg.to_dict() for fg in self.folder_growths],
        }


@dataclass(slots=True)
class FileTypeStats:
    """文件类型统计"""
    extension: str
    file_count: int
    total_size: int
    folder_path: Path


@dataclass(slots=True)
class LargeFile:
    """大文件记录"""
    path: Path
    size: int
    created_time: datetime
    folder_path: Path


@dataclass(slots=True)
class TrendData:
    """趋势数据"""
    folder_path: Path
    daily_growth: list[tuple[date, int]]
    avg_daily_growth: float
    trend_direction: str  # "rising" | "falling" | "stable"
    growth_rate: float


@dataclass(slots=True)
class Anomaly:
    """异常记录"""
    date: date
    value: int
    expected_range: tuple[float, float]
    severity: str  # "high" | "medium"

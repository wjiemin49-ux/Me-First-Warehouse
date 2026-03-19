"""文件系统扫描器"""
from __future__ import annotations

import logging
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

from .config import Config
from .models import FileActivity
from .utils import get_today_range

logger = logging.getLogger(__name__)


def should_exclude(path: Path, exclude_patterns: dict[str, list[str]]) -> bool:
    """判断路径是否应该被排除"""
    # 检查目录排除
    for pattern in exclude_patterns.get("directories", []):
        if pattern in path.parts:
            return True

    # 检查文件排除
    if path.is_file():
        for pattern in exclude_patterns.get("files", []):
            if fnmatch(path.name, pattern):
                return True

    return False


def is_today(timestamp: datetime, timezone_str: str) -> bool:
    """判断时间戳是否在今天"""
    today_start, today_end = get_today_range(timezone_str)
    return today_start <= timestamp <= today_end


def get_file_stats(path: Path, timezone_str: str) -> tuple[datetime, datetime, int]:
    """获取文件统计信息：创建时间、修改时间、大小"""
    try:
        from zoneinfo import ZoneInfo
        stat = path.stat()
        tz = ZoneInfo(timezone_str)
        # Windows 上 st_ctime 是创建时间
        created = datetime.fromtimestamp(stat.st_ctime, tz=tz)
        modified = datetime.fromtimestamp(stat.st_mtime, tz=tz)
        size = stat.st_size
        return created, modified, size
    except Exception as e:
        logger.debug(f"无法获取文件统计信息 {path}: {e}")
        raise


def scan_directory(
    path: Path,
    category: str,
    config: Config,
    current_depth: int = 0
) -> list[FileActivity]:
    """扫描目录获取今日活动"""
    activities = []
    exclude_patterns = config.exclude_patterns
    timezone = config.timezone
    max_depth = config.get_max_depth(category)
    recursive = config.is_recursive(category)

    # 检查深度限制
    if max_depth is not None and current_depth > max_depth:
        return activities

    try:
        if not path.exists():
            logger.warning(f"目录不存在，跳过: {path}")
            return activities

        if not path.is_dir():
            logger.warning(f"路径不是目录，跳过: {path}")
            return activities

        # 遍历目录
        for item in path.iterdir():
            try:
                # 检查排除模式
                if should_exclude(item, exclude_patterns):
                    logger.debug(f"已排除: {item}")
                    continue

                if item.is_file():
                    # 获取文件统计信息
                    created, modified, size = get_file_stats(item, timezone)
                    extension = item.suffix.lower()

                    # 检查是否今天创建
                    if is_today(created, timezone):
                        activities.append(FileActivity(
                            path=item,
                            activity_type="created",
                            timestamp=created,
                            size=size,
                            extension=extension,
                            category=category
                        ))
                        logger.debug(f"今日新增: {item}")

                    # 检查是否今天修改（且不是今天创建的）
                    elif is_today(modified, timezone):
                        activities.append(FileActivity(
                            path=item,
                            activity_type="modified",
                            timestamp=modified,
                            size=size,
                            extension=extension,
                            category=category
                        ))
                        logger.debug(f"今日修改: {item}")

                elif item.is_dir() and recursive:
                    # 递归扫描子目录
                    sub_activities = scan_directory(
                        item,
                        category,
                        config,
                        current_depth + 1
                    )
                    activities.extend(sub_activities)

            except PermissionError:
                logger.warning(f"权限被拒绝，跳过: {item}")
            except Exception as e:
                logger.warning(f"处理文件时出错 {item}: {e}")

    except PermissionError:
        logger.warning(f"权限被拒绝，无法访问目录: {path}")
    except Exception as e:
        logger.error(f"扫描目录时出错 {path}: {e}")

    return activities


def scan_all_directories(config: Config) -> list[FileActivity]:
    """扫描所有配置的目录"""
    all_activities = []

    for category, dir_config in config.scan_directories.items():
        logger.info(f"开始扫描类别: {category}")

        path = config.get_scan_directory_path(category)
        if path is None:
            logger.warning(f"类别 {category} 没有配置路径，跳过")
            continue

        activities = scan_directory(path, category, config)
        all_activities.extend(activities)

        logger.info(f"类别 {category} 扫描完成，找到 {len(activities)} 个活动")

    return all_activities

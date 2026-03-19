"""工具函数"""
from __future__ import annotations

import logging
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo


def get_today_range(timezone_str: str = "Asia/Shanghai") -> tuple[datetime, datetime]:
    """获取今天的时间范围（00:00 到现在）"""
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    today_start = datetime.combine(now.date(), time.min, tzinfo=tz)
    return today_start, now


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def expand_user_path(path_str: str) -> Path:
    """展开用户路径，支持 {username} 占位符"""
    username = os.environ.get("USERNAME", os.environ.get("USER", ""))
    expanded = path_str.replace("{username}", username)
    return Path(expanded).expanduser().resolve()


def ensure_directory(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """设置日志系统"""
    ensure_directory(log_dir)

    log_file = log_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

"""工具函数"""

import os
from pathlib import Path
from typing import Any


def format_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式

    Args:
        size_bytes: 字节数

    Returns:
        格式化后的字符串，如 "1.23 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def safe_resolve_path(path: str | Path) -> Path | None:
    """安全解析路径

    Args:
        path: 路径字符串或 Path 对象

    Returns:
        解析后的 Path 对象，失败返回 None
    """
    try:
        p = Path(path).expanduser()
        return p.resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def ensure_directory(path: Path) -> bool:
    """确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        成功返回 True，失败返回 False
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def normalize_path(path: str) -> str:
    """规范化路径，处理 Windows 路径格式

    Args:
        path: 原始路径字符串

    Returns:
        规范化后的路径字符串
    """
    # 替换反斜杠为正斜杠（Python 内部统一使用正斜杠）
    normalized = path.replace("\\", "/")
    # 移除末尾的斜杠
    normalized = normalized.rstrip("/")
    return normalized


def load_env_file(env_path: Path) -> dict[str, str]:
    """加载 .env 文件

    Args:
        env_path: .env 文件路径

    Returns:
        环境变量字典
    """
    env_vars = {}
    if not env_path.exists():
        return env_vars

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue
                # 解析 KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except (OSError, UnicodeDecodeError):
        pass

    return env_vars


def normalize_value(value: float, all_values: list[float]) -> float:
    """Min-Max 归一化

    Args:
        value: 待归一化的值
        all_values: 所有值的列表

    Returns:
        归一化后的值 (0-1)
    """
    if not all_values or len(all_values) == 0:
        return 0.0

    min_val = min(all_values)
    max_val = max(all_values)

    # 避免除以零
    if max_val == min_val:
        return 1.0 if value > 0 else 0.0

    return (value - min_val) / (max_val - min_val)

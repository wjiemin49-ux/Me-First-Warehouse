"""配置加载器"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .utils import expand_user_path

logger = logging.getLogger(__name__)


class Config:
    """配置类"""

    def __init__(self, config_dict: dict[str, Any]):
        self._config = config_dict

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        """加载配置文件"""
        if config_path is None:
            # 默认配置路径
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        logger.info(f"已加载配置文件: {config_path}")
        return cls(config_dict)

    @property
    def scan_directories(self) -> dict[str, dict[str, Any]]:
        """扫描目录配置"""
        return self._config.get("scan_directories", {})

    @property
    def exclude_patterns(self) -> dict[str, list[str]]:
        """排除模式"""
        return self._config.get("exclude_patterns", {
            "directories": [".git", "node_modules", "__pycache__", ".venv", "venv"],
            "files": ["*.tmp", "*.log", "*.cache", "Thumbs.db"]
        })

    @property
    def report_output_dir(self) -> Path:
        """报告输出目录"""
        output_dir = self._config.get("report", {}).get("output_dir", "./output")
        return Path(output_dir).resolve()

    @property
    def report_format(self) -> str:
        """报告格式"""
        return self._config.get("report", {}).get("format", "markdown")

    @property
    def report_top_n(self) -> int:
        """报告显示前 N 个"""
        return self._config.get("report", {}).get("top_n", 10)

    @property
    def timezone(self) -> str:
        """时区"""
        return self._config.get("report", {}).get("timezone", "Asia/Shanghai")

    @property
    def log_level(self) -> str:
        """日志级别"""
        return self._config.get("logging", {}).get("level", "INFO")

    @property
    def log_dir(self) -> Path:
        """日志目录"""
        log_dir = self._config.get("logging", {}).get("log_dir", "./logs")
        return Path(log_dir).resolve()

    def get_scan_directory_path(self, category: str) -> Path | None:
        """获取扫描目录路径"""
        dir_config = self.scan_directories.get(category)
        if not dir_config:
            return None

        path_str = dir_config.get("path")
        if not path_str:
            return None

        return expand_user_path(path_str)

    def is_recursive(self, category: str) -> bool:
        """是否递归扫描"""
        dir_config = self.scan_directories.get(category, {})
        return dir_config.get("recursive", False)

    def get_max_depth(self, category: str) -> int | None:
        """获取最大递归深度"""
        dir_config = self.scan_directories.get(category, {})
        return dir_config.get("max_depth")

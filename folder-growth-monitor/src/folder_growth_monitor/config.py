"""配置管理"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .utils import safe_resolve_path

LOGGER = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误"""
    pass


@dataclass
class ScanConfig:
    """扫描配置"""
    target_directories: list[Path]
    recursive: bool
    max_depth: int


@dataclass
class IgnoreConfig:
    """忽略规则配置"""
    directories: list[str]
    file_extensions: list[str]
    hidden_files: bool


@dataclass
class TimeConfig:
    """时间配置"""
    mode: str  # "today" | "last_24h"
    timezone: str


@dataclass
class AnalysisConfig:
    """分析配置"""
    metrics: list[str]


@dataclass
class CompositeWeights:
    """综合评分权重"""
    new_file_count: float
    new_file_size: float
    modified_file_count: float


@dataclass
class RankingConfig:
    """排序配置"""
    sort_by: str  # "new_file_count" | "new_file_size" | "modified_file_count" | "composite"
    composite_weights: CompositeWeights
    top_n: int


@dataclass
class OutputConfig:
    """输出配置"""
    formats: list[str]
    output_dir: Path
    filename_template: str


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str
    log_dir: Path
    log_file: str


@dataclass
class DatabaseConfig:
    """数据库配置"""
    enabled: bool
    db_path: Path
    retention_days: int


@dataclass
class EmailConfig:
    """邮件通知配置"""
    enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    use_tls: bool
    sender: str
    recipients: list[str]
    subject_template: str
    min_new_files: int  # 新增文件数超过此值才发送


@dataclass
class PerformanceConfig:
    """性能优化配置"""
    parallel_scan: bool
    max_workers: int
    large_file_threshold_mb: int


@dataclass
class Config:
    """主配置类"""
    scan: ScanConfig
    ignore: IgnoreConfig
    time: TimeConfig
    analysis: AnalysisConfig
    ranking: RankingConfig
    output: OutputConfig
    logging: LoggingConfig
    database: DatabaseConfig
    performance: PerformanceConfig
    email: EmailConfig


def load_config(config_path: Path | None = None) -> Config:
    """加载配置文件

    Args:
        config_path: 配置文件路径，默认为 config/settings.yaml

    Returns:
        Config 对象

    Raises:
        ConfigError: 配置加载或验证失败
    """
    # 加载 .env 文件
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # 确定配置文件路径
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

    if not config_path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    # 加载 YAML 配置
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigError(f"配置文件加载失败: {e}")

    # 验证并构建配置对象
    try:
        return _build_config(config_data)
    except Exception as e:
        raise ConfigError(f"配置验证失败: {e}")


def _build_config(data: dict[str, Any]) -> Config:
    """构建配置对象"""
    # 扫描配置
    scan_data = data.get("scan", {})
    target_dirs = []
    for dir_str in scan_data.get("target_directories", []):
        resolved = safe_resolve_path(dir_str)
        if resolved:
            target_dirs.append(resolved)
        else:
            LOGGER.warning(f"无法解析目录路径: {dir_str}")

    scan_config = ScanConfig(
        target_directories=target_dirs,
        recursive=scan_data.get("recursive", False),
        max_depth=scan_data.get("max_depth", 1),
    )

    # 忽略规则配置
    ignore_data = data.get("ignore", {})
    ignore_config = IgnoreConfig(
        directories=ignore_data.get("directories", []),
        file_extensions=ignore_data.get("file_extensions", []),
        hidden_files=ignore_data.get("hidden_files", True),
    )

    # 时间配置
    time_data = data.get("time", {})
    time_config = TimeConfig(
        mode=time_data.get("mode", "today"),
        timezone=time_data.get("timezone", "Asia/Shanghai"),
    )

    # 分析配置
    analysis_data = data.get("analysis", {})
    analysis_config = AnalysisConfig(
        metrics=analysis_data.get("metrics", ["new_file_count", "new_file_size", "modified_file_count"]),
    )

    # 排序配置
    ranking_data = data.get("ranking", {})
    weights_data = ranking_data.get("composite_weights", {})
    composite_weights = CompositeWeights(
        new_file_count=weights_data.get("new_file_count", 0.5),
        new_file_size=weights_data.get("new_file_size", 0.3),
        modified_file_count=weights_data.get("modified_file_count", 0.2),
    )
    ranking_config = RankingConfig(
        sort_by=ranking_data.get("sort_by", "composite"),
        composite_weights=composite_weights,
        top_n=ranking_data.get("top_n", 10),
    )

    # 输出配置
    output_data = data.get("output", {})
    output_dir = Path(output_data.get("output_dir", "./output"))
    output_config = OutputConfig(
        formats=output_data.get("formats", ["console", "markdown"]),
        output_dir=output_dir,
        filename_template=output_data.get("filename_template", "folder_growth_{date}.md"),
    )

    # 日志配置
    logging_data = data.get("logging", {})
    log_dir = Path(logging_data.get("log_dir", "./logs"))
    logging_config = LoggingConfig(
        level=logging_data.get("level", "INFO"),
        log_dir=log_dir,
        log_file=logging_data.get("log_file", "folder_monitor.log"),
    )

    # 数据库配置
    database_data = data.get("database", {})
    db_path = Path(database_data.get("db_path", "./data/folder_growth.db"))
    database_config = DatabaseConfig(
        enabled=database_data.get("enabled", False),
        db_path=db_path,
        retention_days=database_data.get("retention_days", 90),
    )

    # 性能配置
    performance_data = data.get("performance", {})
    max_workers = performance_data.get("max_workers", 0)
    if max_workers == 0:
        import os
        max_workers = os.cpu_count() or 4
    performance_config = PerformanceConfig(
        parallel_scan=performance_data.get("parallel_scan", False),
        max_workers=max_workers,
        large_file_threshold_mb=performance_data.get("large_file_threshold_mb", 100),
    )

    # 邮件配置
    email_data = data.get("email", {})
    email_config = EmailConfig(
        enabled=email_data.get("enabled", False),
        smtp_host=os.getenv("SMTP_HOST", email_data.get("smtp_host", "smtp.gmail.com")),
        smtp_port=int(os.getenv("SMTP_PORT", email_data.get("smtp_port", 587))),
        smtp_user=os.getenv("SMTP_USER", email_data.get("smtp_user", "")),
        smtp_password=os.getenv("SMTP_PASSWORD", email_data.get("smtp_password", "")),
        use_tls=email_data.get("use_tls", True),
        sender=os.getenv("SMTP_SENDER", email_data.get("sender", "")),
        recipients=email_data.get("recipients", []),
        subject_template=email_data.get("subject_template", "[Folder Monitor] {date} 扫描报告"),
        min_new_files=email_data.get("min_new_files", 1),
    )

    return Config(
        scan=scan_config,
        ignore=ignore_config,
        time=time_config,
        analysis=analysis_config,
        ranking=ranking_config,
        output=output_config,
        logging=logging_config,
        database=database_config,
        performance=performance_config,
        email=email_config,
    )

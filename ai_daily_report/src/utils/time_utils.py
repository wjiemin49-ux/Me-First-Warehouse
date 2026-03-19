"""时间工具函数"""
from datetime import datetime, timedelta, timezone


def get_time_window(hours: int = 24) -> tuple[datetime, datetime]:
    """获取时间窗口 (since_utc, now_utc)"""
    now_utc = datetime.now(timezone.utc)
    since_utc = now_utc - timedelta(hours=hours)
    return since_utc, now_utc


def format_datetime_zh(dt: datetime) -> str:
    """格式化日期时间为中文友好格式"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # 转换为 UTC+8 (中国时区)
    dt_cn = dt.astimezone(timezone(timedelta(hours=8)))
    return dt_cn.strftime('%Y年%m月%d日 %H:%M')


def format_datetime_utc(dt: datetime) -> str:
    """格式化为 UTC 时间字符串"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M UTC')


def parse_datetime(dt_str: str) -> datetime:
    """解析日期时间字符串"""
    # 尝试多种格式
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S%z',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析日期时间: {dt_str}")

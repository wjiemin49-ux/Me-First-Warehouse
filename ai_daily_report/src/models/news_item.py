"""数据模型定义"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class NewsItem:
    """单条新闻项"""
    id: str                      # SHA256 hash of (url + title)
    source: str                  # 来源名称
    title: str                   # 原始标题
    title_zh: str               # 中文标题
    url: str                     # 原始链接
    published_utc: datetime      # 发布时间 (UTC)
    summary: str                # 原始摘要/描述
    summary_zh: str             # 中文摘要
    fetched_at: datetime        # 抓取时间
    priority: int               # 优先级 1-5 (5=最高)

    @staticmethod
    def generate_id(url: str, title: str) -> str:
        """生成唯一ID"""
        content = f"{url}|{title}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


@dataclass
class DailyReport:
    """每日报告容器"""
    date: date
    items: list[NewsItem]
    total_fetched: int          # 总抓取数
    total_after_dedup: int      # 去重后数量
    total_sent: int             # 实际发送数量

    @property
    def summary_stats(self) -> dict[str, int]:
        """统计摘要"""
        return {
            'total_fetched': self.total_fetched,
            'total_after_dedup': self.total_after_dedup,
            'total_sent': self.total_sent,
        }

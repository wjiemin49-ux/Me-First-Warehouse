"""RSS 抓取器"""
from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)


class RSSFetcher:
    """RSS Feed 抓取器"""

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建 HTTP 会话"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "ai-daily-report/1.0 (+https://github.com/; RSS fetcher; "
                "contact: automation-script)"
            )
        })
        return session

    def fetch(self, source_config: dict, since_utc: datetime) -> list[dict]:
        """
        抓取单个 RSS 源

        Args:
            source_config: 源配置字典
            since_utc: 起始时间

        Returns:
            原始新闻项列表
        """
        source_name = source_config['name']
        source_url = source_config['url']

        try:
            resp = self.session.get(source_url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"RSS 获取失败: {source_name} ({source_url}) - {e}")
            return []

        try:
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning(f"RSS 解析失败: {source_name} - {e}")
            return []
        finally:
            resp.close()

        if not getattr(parsed, "version", ""):
            logger.warning(f"RSS 返回内容不是有效 Feed: {source_name}")
            return []

        if getattr(parsed, "bozo", 0):
            exc = getattr(parsed, "bozo_exception", None)
            logger.warning(f"RSS 解析存在异常: {source_name} - {exc}")

        # 提取条目
        items = []
        for entry in parsed.entries:
            item = self._parse_entry(entry, source_name, since_utc)
            if item:
                items.append(item)

        logger.info(f"从 {source_name} 获取到 {len(items)} 条新闻")
        return items

    def _parse_entry(self, entry: object, source_name: str, since_utc: datetime) -> Optional[dict]:
        """解析单个 RSS 条目"""
        # 提取标题
        title = (getattr(entry, "title", None) or "").strip()
        if not title:
            return None

        # 提取链接
        url = (getattr(entry, "link", None) or "").strip()
        if not url:
            return None

        # 提取发布时间
        published_utc = self._extract_datetime(entry)
        if published_utc is None:
            logger.debug(f"跳过无时间戳的条目: {title}")
            return None

        # 时间过滤
        if published_utc < since_utc:
            return None

        # 提取摘要
        summary = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "").strip()

        return {
            'source': source_name,
            'title': title,
            'url': url,
            'published_utc': published_utc,
            'summary': summary,
            'fetched_at': datetime.now(timezone.utc),
        }

    def _extract_datetime(self, entry: object) -> Optional[datetime]:
        """提取条目时间"""
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            value = getattr(entry, key, None)
            if value:
                try:
                    return datetime.fromtimestamp(
                        calendar.timegm(value),
                        tz=timezone.utc
                    )
                except Exception:
                    continue
        return None

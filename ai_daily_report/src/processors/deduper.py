"""去重器"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher

from ..models.news_item import NewsItem
from ..storage.store import Store

logger = logging.getLogger(__name__)


class Deduplicator:
    """去重器"""

    def __init__(self, store: Store, similarity_threshold: float = 0.85):
        self.store = store
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, items: list[dict]) -> list[dict]:
        """去重"""
        unique_items = []
        seen_ids = set()
        seen_urls = set()
        seen_titles = []

        for item in items:
            # 生成 ID
            item_id = NewsItem.generate_id(item['url'], item['title'])

            # 检查数据库
            if self.store.is_duplicate(item_id, item['url']):
                logger.debug(f"数据库中已存在: {item['title']}")
                continue

            # 检查当前批次
            if item_id in seen_ids or item['url'] in seen_urls:
                logger.debug(f"当前批次中重复: {item['title']}")
                continue

            # 检查相似标题
            if self._has_similar_title(item['title'], seen_titles):
                logger.debug(f"相似标题已存在: {item['title']}")
                continue

            # 添加到唯一列表
            item['id'] = item_id
            unique_items.append(item)
            seen_ids.add(item_id)
            seen_urls.add(item['url'])
            seen_titles.append(item['title'])

        logger.info(f"去重完成: {len(items)} -> {len(unique_items)} 条")
        return unique_items

    def _has_similar_title(self, title: str, seen_titles: list[str]) -> bool:
        """检查是否有相似标题"""
        for seen_title in seen_titles:
            similarity = SequenceMatcher(None, title.lower(), seen_title.lower()).ratio()
            if similarity >= self.similarity_threshold:
                return True
        return False

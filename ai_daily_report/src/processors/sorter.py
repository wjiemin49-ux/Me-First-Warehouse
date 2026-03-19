"""排序器"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Sorter:
    """新闻排序器"""

    # 高优先级关键词
    HIGH_PRIORITY_KEYWORDS = [
        'release', 'launch', 'announce', 'breakthrough', 'unveil',
        'introduce', 'debut', 'new model', 'open source', 'funding',
        'acquisition', 'partnership', 'collaboration',
        '发布', '推出', '宣布', '突破', '开源', '融资', '收购', '合作',
    ]

    def sort(self, items: list[dict], source_configs: dict = None) -> list[dict]:
        """排序新闻项"""
        # 计算优先级
        for item in items:
            item['priority'] = self._calculate_priority(item, source_configs)

        # 按优先级和时间排序
        sorted_items = sorted(
            items,
            key=lambda x: (x['priority'], x['published_utc']),
            reverse=True
        )

        logger.info(f"排序完成: {len(sorted_items)} 条新闻")
        return sorted_items

    def _calculate_priority(self, item: dict, source_configs: dict = None) -> int:
        """计算优先级 (1-5)"""
        priority = 3  # 默认中等优先级

        # 来源优先级加成
        if source_configs:
            source_config = source_configs.get(item['source'], {})
            priority_boost = source_config.get('priority_boost', 0)
            priority += priority_boost

        # 关键词加成
        text = f"{item['title']} {item.get('summary', '')}".lower()
        for keyword in self.HIGH_PRIORITY_KEYWORDS:
            if keyword.lower() in text:
                priority += 1
                break

        # 时间新鲜度加成
        now = datetime.now(timezone.utc)
        age_hours = (now - item['published_utc']).total_seconds() / 3600
        if age_hours < 6:
            priority += 1
        elif age_hours < 12:
            priority += 0.5

        # 限制范围 1-5
        priority = max(1, min(5, int(priority)))

        return priority

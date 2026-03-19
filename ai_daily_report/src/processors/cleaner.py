"""内容清洗器"""
from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import urlparse, parse_qs, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Cleaner:
    """内容清洗器"""

    # AI 相关关键词
    AI_KEYWORDS = [
        'ai', 'artificial intelligence', 'machine learning', 'deep learning',
        'neural network', 'llm', 'large language model', 'gpt', 'claude',
        'chatbot', 'generative', 'transformer', 'diffusion', 'stable diffusion',
        'midjourney', 'dall-e', 'computer vision', 'nlp', 'natural language',
        'reinforcement learning', 'model', 'training', 'inference', 'embedding',
        'fine-tuning', 'prompt', 'agent', 'rag', 'retrieval', 'vector',
    ]

    def clean(self, raw_items: list[dict]) -> list[dict]:
        """清洗原始新闻项"""
        cleaned = []
        for item in raw_items:
            try:
                cleaned_item = self._clean_item(item)
                if cleaned_item and self._is_ai_related(cleaned_item):
                    cleaned.append(cleaned_item)
            except Exception as e:
                logger.warning(f"清洗条目失败: {item.get('title', 'unknown')} - {e}")

        logger.info(f"清洗完成: {len(raw_items)} -> {len(cleaned)} 条")
        return cleaned

    def _clean_item(self, item: dict) -> dict:
        """清洗单个条目"""
        # 清洗标题
        title = self._clean_text(item['title'])

        # 清洗摘要
        summary = self._clean_html(item.get('summary', ''))

        # 清洗 URL
        url = self._clean_url(item['url'])

        return {
            'source': item['source'],
            'title': title,
            'url': url,
            'published_utc': item['published_utc'],
            'summary': summary,
            'fetched_at': item['fetched_at'],
        }

    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # HTML 解码
        text = unescape(text)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _clean_html(self, html: str) -> str:
        """清洗 HTML 内容"""
        if not html:
            return ""

        # 使用 BeautifulSoup 提取纯文本
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text(separator=' ', strip=True)

        # 清洗文本
        text = self._clean_text(text)

        # 限制长度
        if len(text) > 500:
            text = text[:497] + "..."

        return text

    def _clean_url(self, url: str) -> str:
        """清洗 URL，移除跟踪参数"""
        try:
            parsed = urlparse(url)

            # 移除常见跟踪参数
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', 'ref', 'source',
            }

            query_params = parse_qs(parsed.query)
            cleaned_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in tracking_params
            }

            # 重建查询字符串
            if cleaned_params:
                query_string = '&'.join(f"{k}={v[0]}" for k, v in cleaned_params.items())
            else:
                query_string = ''

            # 重建 URL
            cleaned_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                ''  # 移除 fragment
            ))

            return cleaned_url
        except Exception:
            return url

    def _is_ai_related(self, item: dict) -> bool:
        """判断是否与 AI 相关"""
        text = f"{item['title']} {item['summary']}".lower()

        # 检查关键词
        for keyword in self.AI_KEYWORDS:
            if keyword in text:
                return True

        return False

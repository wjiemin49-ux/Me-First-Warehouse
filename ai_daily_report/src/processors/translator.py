"""翻译器 - 支持基础模式和 LLM 增强模式"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class Translator:
    """翻译器"""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.anthropic_client = None

        if self.use_llm:
            try:
                import anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    logger.info("LLM 翻译模式已启用")
                else:
                    logger.warning("未找到 ANTHROPIC_API_KEY，使用基础翻译模式")
                    self.use_llm = False
            except ImportError:
                logger.warning("anthropic 库未安装，使用基础翻译模式")
                self.use_llm = False

    def translate(self, items: list[dict]) -> list[dict]:
        """翻译新闻项"""
        if self.use_llm and self.anthropic_client:
            return self._translate_with_llm(items)
        else:
            return self._translate_basic(items)

    def _translate_basic(self, items: list[dict]) -> list[dict]:
        """基础翻译模式 - 保留原文"""
        logger.info(f"使用基础翻译模式处理 {len(items)} 条新闻")

        for item in items:
            item['title_zh'] = item['title']
            item['summary_zh'] = item.get('summary', '暂无摘要')

        return items

    def _translate_with_llm(self, items: list[dict]) -> list[dict]:
        """LLM 增强翻译模式"""
        logger.info(f"使用 LLM 翻译模式处理 {len(items)} 条新闻")

        # 批量处理，每次 5 条
        batch_size = 5
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            try:
                self._translate_batch(batch)
            except Exception as e:
                logger.error(f"LLM 翻译失败，回退到基础模式: {e}")
                # 回退到基础模式
                for item in batch:
                    if 'title_zh' not in item:
                        item['title_zh'] = item['title']
                    if 'summary_zh' not in item:
                        item['summary_zh'] = item.get('summary', '暂无摘要')

        return items

    def _translate_batch(self, batch: list[dict]):
        """翻译一批新闻"""
        # 构建提示词
        news_list = []
        for idx, item in enumerate(batch, 1):
            news_list.append(f"{idx}. 标题: {item['title']}")
            if item.get('summary'):
                news_list.append(f"   摘要: {item['summary'][:200]}")

        prompt = f"""请将以下 AI 相关新闻翻译成中文。要求：
1. 标题翻译要简洁、准确、易读
2. 摘要用 2-3 句话概括核心内容
3. 保持专业术语的准确性
4. 输出格式严格按照：

新闻1:
标题: [中文标题]
摘要: [中文摘要]

新闻2:
标题: [中文标题]
摘要: [中文摘要]

原文新闻：
{chr(10).join(news_list)}
"""

        try:
            response = self.anthropic_client.messages.create(
                model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # 解析响应
            content = response.content[0].text
            self._parse_translation_response(content, batch)

        except Exception as e:
            logger.error(f"调用 Claude API 失败: {e}")
            raise

    def _parse_translation_response(self, content: str, batch: list[dict]):
        """解析翻译响应"""
        lines = content.strip().split('\n')
        current_idx = -1
        current_title = None
        current_summary = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测新闻编号
            if line.startswith('新闻') and ':' in line:
                # 保存上一条
                if current_idx >= 0 and current_title:
                    if current_idx < len(batch):
                        batch[current_idx]['title_zh'] = current_title
                        batch[current_idx]['summary_zh'] = ' '.join(current_summary)

                # 开始新的一条
                current_idx += 1
                current_title = None
                current_summary = []

            elif line.startswith('标题:') or line.startswith('标题：'):
                current_title = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()

            elif line.startswith('摘要:') or line.startswith('摘要：'):
                summary_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                current_summary.append(summary_text)

            elif current_title and not line.startswith('新闻'):
                # 继续摘要内容
                current_summary.append(line)

        # 保存最后一条
        if current_idx >= 0 and current_title and current_idx < len(batch):
            batch[current_idx]['title_zh'] = current_title
            batch[current_idx]['summary_zh'] = ' '.join(current_summary)

        # 检查是否所有项都已翻译
        for item in batch:
            if 'title_zh' not in item:
                item['title_zh'] = item['title']
            if 'summary_zh' not in item:
                item['summary_zh'] = item.get('summary', '暂无摘要')

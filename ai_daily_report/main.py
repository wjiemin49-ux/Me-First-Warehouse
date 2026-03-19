"""AI 每日新闻自动化脚本 - 主程序"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.sources import get_enabled_sources, get_source_config_map
from src.fetchers import RSSFetcher
from src.mail import EmailSender
from src.models import DailyReport, NewsItem
from src.processors import Cleaner, Deduplicator, Sorter, Translator
from src.storage import Store
from src.utils import setup_logging, get_time_window

logger = logging.getLogger(__name__)


def main(argv: list[str] = None) -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="AI 每日新闻自动化脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅生成报告，不发送邮件")
    parser.add_argument("--no-llm", action="store_true", help="不使用 LLM 翻译")
    parser.add_argument("--hours", type=int, default=24, help="抓取时间窗口（小时）")
    parser.add_argument("--max-items", type=int, default=15, help="最大发送条数")
    args = parser.parse_args(argv)

    # 加载环境变量
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"已加载环境变量: {env_path}")
    else:
        logger.warning(f"未找到 .env 文件: {env_path}")

    # 配置日志
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = project_root / 'logs' / f"ai_daily_report_{date.today().isoformat()}.log"
    setup_logging(log_level, str(log_file))

    logger.info("=" * 60)
    logger.info("AI 每日新闻自动化脚本启动")
    logger.info("=" * 60)

    try:
        # 1. 初始化组件
        logger.info("初始化组件...")
        db_path = os.getenv('DATABASE_PATH', 'data/sent_records.db')
        store = Store(str(project_root / db_path))
        fetcher = RSSFetcher()
        cleaner = Cleaner()
        deduper = Deduplicator(store)
        sorter = Sorter()
        use_llm = not args.no_llm and os.getenv('USE_LLM_TRANSLATION', 'true').lower() == 'true'
        translator = Translator(use_llm=use_llm)

        # 2. 获取时间窗口
        since_utc, now_utc = get_time_window(args.hours)
        logger.info(f"时间窗口: {since_utc} 至 {now_utc}")

        # 3. 抓取所有源
        logger.info("开始抓取新闻...")
        sources = get_enabled_sources()
        source_config_map = get_source_config_map()
        raw_items = []

        for source in sources:
            try:
                items = fetcher.fetch(source, since_utc)
                raw_items.extend(items)
            except Exception as e:
                logger.error(f"抓取失败: {source['name']} - {e}")

        logger.info(f"总共抓取: {len(raw_items)} 条原始新闻")

        if not raw_items:
            logger.warning("未抓取到任何新闻，发送空报告")
            # 发送空报告
            if not args.dry_run:
                empty_report = DailyReport(
                    date=date.today(),
                    items=[],
                    total_fetched=0,
                    total_after_dedup=0,
                    total_sent=0
                )
                sender = EmailSender()
                sender.send(empty_report)
            return 0

        # 4. 清洗
        logger.info("清洗内容...")
        cleaned_items = cleaner.clean(raw_items)

        # 5. 去重
        logger.info("去重...")
        unique_items = deduper.deduplicate(cleaned_items)

        # 6. 排序
        logger.info("排序...")
        sorted_items = sorter.sort(unique_items, source_config_map)

        # 7. 选取 Top N
        top_items = sorted_items[:args.max_items]
        logger.info(f"选取 Top {len(top_items)} 条新闻")

        # 8. 翻译
        logger.info("翻译成中文...")
        translated_items = translator.translate(top_items)

        # 9. 构建 NewsItem 对象
        news_items = []
        for item in translated_items:
            news_item = NewsItem(
                id=item['id'],
                source=item['source'],
                title=item['title'],
                title_zh=item['title_zh'],
                url=item['url'],
                published_utc=item['published_utc'],
                summary=item.get('summary', ''),
                summary_zh=item['summary_zh'],
                fetched_at=item['fetched_at'],
                priority=item['priority']
            )
            news_items.append(news_item)

        # 10. 生成报告
        report = DailyReport(
            date=date.today(),
            items=news_items,
            total_fetched=len(raw_items),
            total_after_dedup=len(unique_items),
            total_sent=len(news_items)
        )

        # 11. 保存到本地
        output_path = project_root / os.getenv('OUTPUT_PATH', 'output/latest_report.html')
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 12. 发送邮件
        if args.dry_run:
            logger.info("Dry-run 模式，跳过邮件发送")
            logger.info(f"报告已保存到: {output_path}")
            return 0

        logger.info("发送邮件...")
        sender = EmailSender()
        success = sender.send(report)

        if success:
            # 13. 标记为已发送
            items_data = [
                {
                    'id': item.id,
                    'source': item.source,
                    'title': item.title,
                    'url': item.url,
                    'published_utc': item.published_utc.isoformat(),
                    'fetched_at': item.fetched_at.isoformat(),
                }
                for item in news_items
            ]
            store.mark_as_sent([item.id for item in news_items], items_data)

            # 14. 清理旧记录
            store.cleanup_old_records(days=30)

            logger.info("=" * 60)
            logger.info("✅ 任务完成！邮件已发送")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("邮件发送失败")
            return 1

    except Exception as e:
        logger.exception(f"脚本执行失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

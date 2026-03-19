"""CLI 入口点"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from . import __version__
from .analyzer import analyze_activities
from .config import Config
from .reporter import generate_markdown_report, generate_text_report, print_console_report
from .scanner import scan_all_directories
from .utils import setup_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="每日电脑活动简报生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 生成今天的报告
  %(prog)s --date 2026-03-17            # 生成指定日期的报告
  %(prog)s --config custom.yaml         # 使用自定义配置
  %(prog)s --format text                # 生成文本格式报告
  %(prog)s --verbose                    # 启用详细日志
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--date",
        type=str,
        help="指定日期 (格式: YYYY-MM-DD)，默认为今天"
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="配置文件路径，默认为 config/settings.yaml"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="输出目录，覆盖配置文件中的设置"
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "text", "console"],
        help="报告格式，默认为 markdown"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细日志 (DEBUG 级别)"
    )

    return parser.parse_args()


def main() -> int:
    """主函数"""
    args = parse_args()

    try:
        # 加载配置
        config = Config.load(args.config)

        # 设置日志
        log_level = "DEBUG" if args.verbose else config.log_level
        setup_logging(config.log_dir, log_level)

        logger.info("=" * 60)
        logger.info("每日电脑活动简报生成器启动")
        logger.info("=" * 60)

        # 解析日期
        if args.date:
            try:
                report_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                logger.error(f"日期格式错误: {args.date}，应为 YYYY-MM-DD")
                return 1
        else:
            report_date = date.today()

        logger.info(f"报告日期: {report_date}")

        # 扫描文件系统
        logger.info("开始扫描文件系统...")
        activities = scan_all_directories(config)
        logger.info(f"扫描完成，共找到 {len(activities)} 个文件活动")

        if not activities:
            logger.warning("未找到任何文件活动")
            print("\n警告: 今天没有检测到任何文件活动。")
            print("请检查配置文件中的扫描目录是否正确。\n")
            return 0

        # 分析活动
        logger.info("开始分析活动...")
        report = analyze_activities(activities, report_date, config.report_top_n)
        logger.info("分析完成")

        # 生成报告
        output_format = args.format or config.report_format
        output_dir = args.output or config.report_output_dir

        if output_format == "console":
            print_console_report(report)
        else:
            # 生成文件报告
            filename = f"daily_report_{report_date.strftime('%Y-%m-%d')}"

            if output_format == "markdown":
                output_path = output_dir / f"{filename}.md"
                generate_markdown_report(report, output_path)
                print(f"\n成功: Markdown 报告已生成: {output_path}\n")
            elif output_format == "text":
                output_path = output_dir / f"{filename}.txt"
                generate_text_report(report, output_path)
                print(f"\n成功: 文本报告已生成: {output_path}\n")

            # 同时在控制台显示简要信息
            print_console_report(report)

        logger.info("报告生成完成")
        logger.info("=" * 60)
        return 0

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        print(f"\n错误: {e}\n")
        return 1
    except Exception as e:
        logger.exception(f"发生错误: {e}")
        print(f"\n错误: {e}")
        print("详细信息请查看日志文件。\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

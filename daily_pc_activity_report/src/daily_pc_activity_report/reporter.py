"""报告生成器"""
from __future__ import annotations

import logging
from pathlib import Path

from .models import DailyReport
from .utils import format_size

logger = logging.getLogger(__name__)


def generate_markdown_report(report: DailyReport, output_path: Path) -> None:
    """生成 Markdown 格式报告"""
    lines = []

    # 标题
    lines.append(f"# 每日电脑活动简报")
    lines.append(f"\n**日期：** {report.date.strftime('%Y年%m月%d日')}\n")

    # 今日总览
    lines.append("## 今日总览\n")
    lines.append(f"- **新增文件：** {report.total_files_created} 个")
    lines.append(f"- **修改文件：** {report.total_files_modified} 个")
    lines.append(f"- **总文件数：** {report.total_files} 个")
    lines.append(f"- **总大小：** {format_size(report.total_size)}\n")

    # 今日总结
    lines.append("## 今日总结\n")
    lines.append(f"{report.summary}\n")

    # 活跃目录排行
    if report.top_directories:
        lines.append("## 活跃目录排行\n")
        for i, dir_stat in enumerate(report.top_directories, 1):
            lines.append(f"### {i}. {dir_stat.path}")
            lines.append(f"- **类别：** {dir_stat.category}")
            lines.append(f"- **新增：** {dir_stat.files_created} 个文件")
            lines.append(f"- **修改：** {dir_stat.files_modified} 个文件")
            lines.append(f"- **大小：** {format_size(dir_stat.total_size)}")
            lines.append(f"- **活动分数：** {dir_stat.activity_score}\n")

    # 文件类型分布
    if report.file_type_distribution:
        lines.append("## 文件类型分布\n")
        sorted_types = sorted(
            report.file_type_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )
        lines.append("| 文件类型 | 数量 |")
        lines.append("|---------|------|")
        for ext, count in sorted_types[:15]:  # 只显示前15个
            ext_display = ext if ext else "无扩展名"
            lines.append(f"| {ext_display} | {count} |")
        lines.append("")

    # 分类统计
    if report.category_stats:
        lines.append("## 分类统计\n")
        sorted_categories = sorted(
            report.category_stats.items(),
            key=lambda x: x[1].activity_score,
            reverse=True
        )
        for category, stats in sorted_categories:
            lines.append(f"### {category}")
            lines.append(f"- **新增：** {stats.files_created} 个文件")
            lines.append(f"- **修改：** {stats.files_modified} 个文件")
            lines.append(f"- **大小：** {format_size(stats.total_size)}")

            # 显示该类别的主要文件类型
            if stats.file_types:
                top_types = sorted(stats.file_types.items(), key=lambda x: x[1], reverse=True)[:5]
                type_str = ", ".join([f"{ext}({count})" for ext, count in top_types])
                lines.append(f"- **主要类型：** {type_str}")
            lines.append("")

    # 写入文件
    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Markdown 报告已生成: {output_path}")


def generate_text_report(report: DailyReport, output_path: Path) -> None:
    """生成纯文本格式报告"""
    lines = []

    # 标题
    lines.append("=" * 60)
    lines.append("每日电脑活动简报".center(60))
    lines.append("=" * 60)
    lines.append(f"\n日期: {report.date.strftime('%Y年%m月%d日')}\n")

    # 今日总览
    lines.append("-" * 60)
    lines.append("今日总览")
    lines.append("-" * 60)
    lines.append(f"新增文件: {report.total_files_created} 个")
    lines.append(f"修改文件: {report.total_files_modified} 个")
    lines.append(f"总文件数: {report.total_files} 个")
    lines.append(f"总大小: {format_size(report.total_size)}\n")

    # 今日总结
    lines.append("-" * 60)
    lines.append("今日总结")
    lines.append("-" * 60)
    lines.append(f"{report.summary}\n")

    # 活跃目录排行
    if report.top_directories:
        lines.append("-" * 60)
        lines.append("活跃目录排行")
        lines.append("-" * 60)
        for i, dir_stat in enumerate(report.top_directories, 1):
            lines.append(f"\n{i}. {dir_stat.path}")
            lines.append(f"   类别: {dir_stat.category}")
            lines.append(f"   新增: {dir_stat.files_created} 个 | 修改: {dir_stat.files_modified} 个")
            lines.append(f"   大小: {format_size(dir_stat.total_size)} | 活动分数: {dir_stat.activity_score}")

    # 写入文件
    content = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"文本报告已生成: {output_path}")


def print_console_report(report: DailyReport) -> None:
    """在控制台打印报告"""
    print("\n" + "=" * 60)
    print("每日电脑活动简报".center(60))
    print("=" * 60)
    print(f"\n日期: {report.date.strftime('%Y年%m月%d日')}\n")

    print("-" * 60)
    print("今日总览")
    print("-" * 60)
    print(f"新增文件: {report.total_files_created} 个")
    print(f"修改文件: {report.total_files_modified} 个")
    print(f"总文件数: {report.total_files} 个")
    print(f"总大小: {format_size(report.total_size)}\n")

    print("-" * 60)
    print("今日总结")
    print("-" * 60)
    print(f"{report.summary}\n")

    if report.top_directories:
        print("-" * 60)
        print("活跃目录排行 (前5)")
        print("-" * 60)
        for i, dir_stat in enumerate(report.top_directories[:5], 1):
            print(f"\n{i}. {dir_stat.path}")
            print(f"   新增: {dir_stat.files_created} | 修改: {dir_stat.files_modified} | 分数: {dir_stat.activity_score}")

    print("\n" + "=" * 60 + "\n")

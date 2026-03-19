"""活动分析器"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date

from .models import DailyReport, DirectoryStats, FileActivity

logger = logging.getLogger(__name__)


def analyze_activities(activities: list[FileActivity], report_date: date, top_n: int = 10) -> DailyReport:
    """分析文件活动并生成报告"""

    # 按目录分组统计
    dir_stats_map: dict[tuple[str, str], DirectoryStats] = {}  # (path, category) -> stats
    category_stats_map: dict[str, DirectoryStats] = {}  # category -> stats
    file_type_dist: dict[str, int] = defaultdict(int)

    total_created = 0
    total_modified = 0
    total_size = 0

    for activity in activities:
        # 更新总计
        if activity.activity_type == "created":
            total_created += 1
        else:
            total_modified += 1
        total_size += activity.size

        # 更新文件类型分布
        ext = activity.extension if activity.extension else "无扩展名"
        file_type_dist[ext] += 1

        # 获取父目录
        parent_dir = activity.path.parent
        key = (str(parent_dir), activity.category)

        # 更新目录统计
        if key not in dir_stats_map:
            dir_stats_map[key] = DirectoryStats(
                path=parent_dir,
                category=activity.category
            )

        stats = dir_stats_map[key]
        if activity.activity_type == "created":
            stats.files_created += 1
        else:
            stats.files_modified += 1
        stats.total_size += activity.size
        stats.file_types[ext] = stats.file_types.get(ext, 0) + 1

        # 更新类别统计
        if activity.category not in category_stats_map:
            category_stats_map[activity.category] = DirectoryStats(
                path=parent_dir,  # 使用第一个遇到的路径
                category=activity.category
            )

        cat_stats = category_stats_map[activity.category]
        if activity.activity_type == "created":
            cat_stats.files_created += 1
        else:
            cat_stats.files_modified += 1
        cat_stats.total_size += activity.size
        cat_stats.file_types[ext] = cat_stats.file_types.get(ext, 0) + 1

    # 转换为列表并排序
    all_dir_stats = list(dir_stats_map.values())
    all_dir_stats.sort(key=lambda x: x.activity_score, reverse=True)

    # 获取前 N 个最活跃目录
    top_directories = all_dir_stats[:top_n]

    # 生成总结
    summary = generate_summary(category_stats_map, file_type_dist, total_created, total_modified)

    return DailyReport(
        date=report_date,
        total_files_created=total_created,
        total_files_modified=total_modified,
        total_size=total_size,
        directory_stats=all_dir_stats,
        top_directories=top_directories,
        file_type_distribution=dict(file_type_dist),
        category_stats=category_stats_map,
        summary=summary
    )


def generate_summary(
    category_stats: dict[str, DirectoryStats],
    file_type_dist: dict[str, int],
    total_created: int,
    total_modified: int
) -> str:
    """基于规则生成今日总结"""

    if not category_stats:
        return "今天电脑上没有明显的文件活动。"

    # 找出最活跃的类别
    most_active_category = max(category_stats.items(), key=lambda x: x[1].activity_score)
    category_name = most_active_category[0]
    category_stat = most_active_category[1]

    # 找出最常见的文件类型
    top_file_types = sorted(file_type_dist.items(), key=lambda x: x[1], reverse=True)[:3]

    summary_parts = []

    # 基于类别判断主要活动
    if category_name == "projects":
        summary_parts.append("今天主要在进行项目开发")
    elif category_name == "study":
        summary_parts.append("今天主要在学习和整理资料")
    elif category_name in ["screenshots", "downloads"]:
        summary_parts.append("今天主要在收集和整理信息")
    elif category_name == "notes":
        summary_parts.append("今天主要在编写笔记")
    else:
        summary_parts.append(f"今天主要活动集中在 {category_name} 目录")

    # 添加文件类型信息
    if ".md" in [ft[0] for ft in top_file_types]:
        summary_parts.append("，编写了不少 Markdown 文档")
    elif ".py" in [ft[0] for ft in top_file_types]:
        summary_parts.append("，编写了一些 Python 代码")
    elif ".png" in [ft[0] for ft in top_file_types] or ".jpg" in [ft[0] for ft in top_file_types]:
        summary_parts.append("，处理了不少图片文件")
    elif ".pdf" in [ft[0] for ft in top_file_types]:
        summary_parts.append("，查看或下载了一些 PDF 文档")

    # 添加活动强度信息
    if total_created > 50:
        summary_parts.append(f"。今天创建了 {total_created} 个新文件，活动量较大")
    elif total_created > 20:
        summary_parts.append(f"。今天创建了 {total_created} 个新文件，活动量适中")
    elif total_created > 0:
        summary_parts.append(f"。今天创建了 {total_created} 个新文件")

    if total_modified > 30:
        summary_parts.append(f"，修改了 {total_modified} 个文件")

    summary_parts.append("。")

    return "".join(summary_parts)

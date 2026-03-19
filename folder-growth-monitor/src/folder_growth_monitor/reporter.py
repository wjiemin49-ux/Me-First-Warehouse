"""报告生成器"""

import logging
from datetime import datetime
from pathlib import Path

from .config import Config
from .models import ScanResult, TrendData, Anomaly
from .utils import ensure_directory, format_size

LOGGER = logging.getLogger(__name__)


class Reporter:
    """报告生成器，负责生成各种格式的报告"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = LOGGER

    def generate_report(self, scan_result: ScanResult) -> None:
        """生成所有配置的报告格式

        Args:
            scan_result: 扫描结果
        """
        formats = self.config.output.formats

        if "console" in formats:
            self._console_report(scan_result)

        if "markdown" in formats:
            output_path = self._markdown_report(scan_result)
            if output_path:
                self.logger.info(f"Markdown 报告已生成: {output_path}")

    def generate_trend_report(
        self,
        trends: list[TrendData],
        anomalies_map: dict[Path, list[Anomaly]],
        heatmap_map: dict[Path, str],
    ) -> None:
        """输出趋势分析报告到控制台

        Args:
            trends: 趋势数据列表
            anomalies_map: 各文件夹异常数据
            heatmap_map: 各文件夹 ASCII 热力图
        """
        if not trends:
            return

        print("\n" + "=" * 80)
        print("趋势分析报告".center(80))
        print("=" * 80)

        for trend in trends:
            direction_icon = {"rising": "↑", "falling": "↓", "stable": "→"}.get(
                trend.trend_direction, "→"
            )
            print(f"\n{direction_icon} {trend.folder_path.name}")
            print(f"  平均日增长: {trend.avg_daily_growth:.1f} 个文件/天")
            print(f"  趋势方向:   {trend.trend_direction}")
            print(f"  增长率:     {trend.growth_rate:+.2f} 个/天")

            # 最近 7 天简单趋势条
            recent = trend.daily_growth[-7:]
            if any(count > 0 for _, count in recent):
                max_count = max(count for _, count in recent) or 1
                bar_line = "  最近7天: "
                for day, count in recent:
                    bar_height = int((count / max_count) * 5)
                    bar_char = [" ", "▁", "▂", "▄", "▆", "█"][bar_height]
                    bar_line += bar_char
                bar_line += f"  ({recent[-1][0].strftime('%m/%d')})"
                print(bar_line)

            # 异常
            anomalies = anomalies_map.get(trend.folder_path, [])
            if anomalies:
                print(f"  ⚠ 检测到 {len(anomalies)} 个异常:")
                for anomaly in anomalies[:3]:
                    print(
                        f"    {anomaly.date} - {anomaly.value} 个文件 "
                        f"[{anomaly.severity}] (正常范围: "
                        f"{anomaly.expected_range[0]:.1f}-{anomaly.expected_range[1]:.1f})"
                    )

            # ASCII 热力图
            heatmap = heatmap_map.get(trend.folder_path)
            if heatmap and heatmap != "(无活动数据)":
                print("  活动热力图 (行=星期, 列=小时):")
                for line in heatmap.split("\n"):
                    print(f"    {line}")

        print("\n" + "=" * 80)

    def _console_report(self, scan_result: ScanResult) -> None:
        """输出到控制台

        Args:
            scan_result: 扫描结果
        """
        print("\n" + "=" * 80)
        print("文件夹增长报告".center(80))
        print("=" * 80)
        print(f"\n生成时间: {scan_result.scan_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"统计范围: {scan_result.time_range_start.strftime('%Y-%m-%d %H:%M:%S')} 至 "
              f"{scan_result.time_range_end.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "-" * 80)
        print("总体统计".center(80))
        print("-" * 80)
        print(f"扫描目录数: {scan_result.total_folders_scanned}")
        print(f"有增长的目录: {scan_result.folders_with_growth}")
        print(f"总新增文件数: {scan_result.total_new_files}")
        print(f"总新增体积: {format_size(scan_result.total_new_size)}")
        print(f"总修改文件数: {scan_result.total_modified_files}")

        if scan_result.folder_growths:
            print("\n" + "-" * 80)
            print(f"增长排行榜 (Top {len(scan_result.folder_growths)})".center(80))
            print("-" * 80)

            for idx, growth in enumerate(scan_result.folder_growths, 1):
                print(f"\n{idx}. {growth.folder_name}")
                print(f"   路径: {growth.folder_path}")
                print(f"   新增文件: {growth.new_file_count} 个")
                print(f"   新增体积: {format_size(growth.new_file_size)}")
                print(f"   修改文件: {growth.modified_file_count} 个")
                if growth.latest_activity_time:
                    print(f"   最后活跃: {growth.latest_activity_time.strftime('%Y-%m-%d %H:%M:%S')}")
                if self.config.ranking.sort_by == "composite":
                    print(f"   综合评分: {growth.composite_score:.2f}")
        else:
            print("\n未发现任何文件夹增长")

        print("\n" + "=" * 80 + "\n")

    def _markdown_report(self, scan_result: ScanResult) -> Path | None:
        """生成 Markdown 文件

        Args:
            scan_result: 扫描结果

        Returns:
            生成的文件路径，失败返回 None
        """
        # 确保输出目录存在
        output_dir = self.config.output.output_dir
        if not ensure_directory(output_dir):
            self.logger.error(f"无法创建输出目录: {output_dir}")
            return None

        # 生成文件名
        date_str = scan_result.scan_time.strftime("%Y-%m-%d")
        filename = self.config.output.filename_template.format(date=date_str)
        output_path = output_dir / filename

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # 标题
                f.write("# 文件夹增长报告\n\n")

                # 基本信息
                f.write(f"**生成时间：** {scan_result.scan_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**统计范围：** {scan_result.time_range_start.strftime('%Y-%m-%d %H:%M:%S')} 至 "
                       f"{scan_result.time_range_end.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # 总体统计
                f.write("## 📊 总体统计\n\n")
                f.write(f"- 扫描目录数：{scan_result.total_folders_scanned}\n")
                f.write(f"- 有增长的目录：{scan_result.folders_with_growth}\n")
                f.write(f"- 总新增文件数：{scan_result.total_new_files}\n")
                f.write(f"- 总新增体积：{format_size(scan_result.total_new_size)}\n")
                f.write(f"- 总修改文件数：{scan_result.total_modified_files}\n\n")

                # 排行榜
                if scan_result.folder_growths:
                    f.write(f"## 🏆 增长排行榜 (Top {len(scan_result.folder_growths)})\n\n")

                    # 表格头
                    if self.config.ranking.sort_by == "composite":
                        f.write("| 排名 | 文件夹 | 新增文件 | 新增体积 | 修改文件 | 综合评分 |\n")
                        f.write("|------|--------|----------|----------|----------|----------|\n")
                    else:
                        f.write("| 排名 | 文件夹 | 新增文件 | 新增体积 | 修改文件 |\n")
                        f.write("|------|--------|----------|----------|----------|\n")

                    # 表格内容
                    for idx, growth in enumerate(scan_result.folder_growths, 1):
                        if self.config.ranking.sort_by == "composite":
                            f.write(f"| {idx} | {growth.folder_name} | {growth.new_file_count} | "
                                   f"{format_size(growth.new_file_size)} | {growth.modified_file_count} | "
                                   f"{growth.composite_score:.2f} |\n")
                        else:
                            f.write(f"| {idx} | {growth.folder_name} | {growth.new_file_count} | "
                                   f"{format_size(growth.new_file_size)} | {growth.modified_file_count} |\n")

                    # 详细信息
                    f.write("\n## 📁 详细信息\n\n")
                    for idx, growth in enumerate(scan_result.folder_growths, 1):
                        f.write(f"### {idx}. {growth.folder_name}\n\n")
                        f.write(f"- **完整路径：** `{growth.folder_path}`\n")
                        f.write(f"- **新增文件数：** {growth.new_file_count}\n")
                        f.write(f"- **新增体积：** {format_size(growth.new_file_size)}\n")
                        f.write(f"- **修改文件数：** {growth.modified_file_count}\n")
                        if growth.latest_activity_time:
                            f.write(f"- **最后活跃时间：** {growth.latest_activity_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        if self.config.ranking.sort_by == "composite":
                            f.write(f"- **综合评分：** {growth.composite_score:.2f}\n")
                        f.write("\n")
                else:
                    f.write("## 📁 增长排行榜\n\n")
                    f.write("未发现任何文件夹增长。\n\n")

                # 页脚
                f.write("---\n\n")
                f.write("*报告由 Folder Growth Monitor 自动生成*\n")

            return output_path

        except Exception as e:
            self.logger.error(f"生成 Markdown 报告失败: {e}")
            return None

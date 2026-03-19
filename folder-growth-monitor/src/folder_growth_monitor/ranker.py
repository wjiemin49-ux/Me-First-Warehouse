"""排序器"""

import logging

from .config import Config
from .models import FolderGrowth
from .utils import normalize_value

LOGGER = logging.getLogger(__name__)


class FolderRanker:
    """文件夹排序器，负责对文件夹增长数据进行排序"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = LOGGER

    def rank(self, folder_growths: list[FolderGrowth]) -> list[FolderGrowth]:
        """根据配置的排序方式对文件夹排序

        Args:
            folder_growths: 文件夹增长统计列表

        Returns:
            排序后的文件夹增长统计列表
        """
        if not folder_growths:
            return []

        sort_by = self.config.ranking.sort_by

        if sort_by == "new_file_count":
            # 按新增文件数排序
            sorted_growths = sorted(
                folder_growths,
                key=lambda x: x.new_file_count,
                reverse=True
            )
            self.logger.info("按新增文件数排序")

        elif sort_by == "new_file_size":
            # 按新增文件体积排序
            sorted_growths = sorted(
                folder_growths,
                key=lambda x: x.new_file_size,
                reverse=True
            )
            self.logger.info("按新增文件体积排序")

        elif sort_by == "modified_file_count":
            # 按修改文件数排序
            sorted_growths = sorted(
                folder_growths,
                key=lambda x: x.modified_file_count,
                reverse=True
            )
            self.logger.info("按修改文件数排序")

        elif sort_by == "composite":
            # 计算综合评分并排序
            self._calculate_composite_scores(folder_growths)
            sorted_growths = sorted(
                folder_growths,
                key=lambda x: x.composite_score,
                reverse=True
            )
            self.logger.info("按综合评分排序")

        else:
            # 默认按新增文件数排序
            sorted_growths = sorted(
                folder_growths,
                key=lambda x: x.new_file_count,
                reverse=True
            )
            self.logger.warning(f"未知的排序方式: {sort_by}，使用默认排序（新增文件数）")

        # 只返回 Top N
        top_n = self.config.ranking.top_n
        return sorted_growths[:top_n]

    def _calculate_composite_scores(self, folder_growths: list[FolderGrowth]) -> None:
        """计算综合评分（原地修改）

        Args:
            folder_growths: 文件夹增长统计列表
        """
        if not folder_growths:
            return

        # 提取所有指标
        new_counts = [g.new_file_count for g in folder_growths]
        new_sizes = [g.new_file_size for g in folder_growths]
        mod_counts = [g.modified_file_count for g in folder_growths]

        # 获取权重
        weights = self.config.ranking.composite_weights

        # 计算每个文件夹的综合评分
        for growth in folder_growths:
            # 归一化各项指标
            norm_new_count = normalize_value(growth.new_file_count, new_counts)
            norm_new_size = normalize_value(growth.new_file_size, new_sizes)
            norm_mod_count = normalize_value(growth.modified_file_count, mod_counts)

            # 加权求和
            score = (
                weights.new_file_count * norm_new_count +
                weights.new_file_size * norm_new_size +
                weights.modified_file_count * norm_mod_count
            )

            # 缩放到 0-10 分
            growth.composite_score = round(score * 10, 2)

        self.logger.debug("综合评分计算完成")

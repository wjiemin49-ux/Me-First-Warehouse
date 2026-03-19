"""文件扫描器"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from .config import Config
from .models import FileRecord, LargeFile

LOGGER = logging.getLogger(__name__)


class FileScanner:
    """文件扫描器，负责遍历目录并收集文件元数据"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = LOGGER

    def scan_directories(self, target_dirs: list[Path]) -> dict[Path, list[FileRecord]]:
        """扫描多个目录，返回按文件夹分组的文件记录

        Args:
            target_dirs: 目标目录列表

        Returns:
            字典，键为文件夹路径，值为该文件夹下的文件记录列表
        """
        # 根据配置选择并行或串行扫描
        if self.config.performance.parallel_scan and len(target_dirs) > 1:
            return self._scan_directories_parallel(target_dirs)
        else:
            return self._scan_directories_sequential(target_dirs)

    def _scan_directories_sequential(self, target_dirs: list[Path]) -> dict[Path, list[FileRecord]]:
        """串行扫描多个目录"""
        results: dict[Path, list[FileRecord]] = {}

        for directory in target_dirs:
            self.logger.info(f"开始扫描目录: {directory}")

            if not directory.exists():
                self.logger.warning(f"目录不存在，跳过: {directory}")
                continue

            if not directory.is_dir():
                self.logger.warning(f"路径不是目录，跳过: {directory}")
                continue

            try:
                file_records = self._scan_single_directory(directory)
                if file_records:
                    results[directory] = file_records
                    self.logger.info(f"扫描完成: {directory}，找到 {len(file_records)} 个文件")
                else:
                    self.logger.debug(f"目录为空或无可访问文件: {directory}")
            except Exception as e:
                self.logger.error(f"扫描目录失败: {directory}，错误: {e}")
                continue

        return results

    def _scan_directories_parallel(self, target_dirs: list[Path]) -> dict[Path, list[FileRecord]]:
        """并行扫描多个目录"""
        results: dict[Path, list[FileRecord]] = {}
        max_workers = self.config.performance.max_workers

        self.logger.info(f"使用并行扫描，工作线程数: {max_workers}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_dir = {
                executor.submit(self._scan_single_directory, directory): directory
                for directory in target_dirs
                if directory.exists() and directory.is_dir()
            }

            for future in as_completed(future_to_dir):
                directory = future_to_dir[future]
                try:
                    file_records = future.result(timeout=300)
                    if file_records:
                        results[directory] = file_records
                        self.logger.info(f"扫描完成: {directory}，找到 {len(file_records)} 个文件")
                except Exception as e:
                    self.logger.error(f"扫描目录失败: {directory}，错误: {e}")

        return results

    def _scan_single_directory(self, directory: Path) -> list[FileRecord]:
        """扫描单个目录

        Args:
            directory: 目录路径

        Returns:
            文件记录列表
        """
        file_records = []

        try:
            # 根据配置决定是否递归扫描
            if self.config.scan.recursive:
                pattern = "**/*"
            else:
                pattern = "*"

            for item in directory.glob(pattern):
                # 跳过目录，只处理文件
                if not item.is_file():
                    continue

                # 应用忽略规则
                if self._should_ignore(item):
                    self.logger.debug(f"忽略文件: {item}")
                    continue

                # 获取文件元数据
                file_record = self._get_file_metadata(item)
                if file_record:
                    file_records.append(file_record)

        except PermissionError:
            self.logger.warning(f"权限不足，无法访问目录: {directory}")
        except Exception as e:
            self.logger.error(f"扫描目录时出错: {directory}，错误: {e}")

        return file_records

    def _should_ignore(self, path: Path) -> bool:
        """判断是否应该忽略该路径

        Args:
            path: 文件或目录路径

        Returns:
            True 表示应该忽略
        """
        # 忽略隐藏文件
        if self.config.ignore.hidden_files and path.name.startswith("."):
            return True

        # 忽略特定目录
        for ignored_dir in self.config.ignore.directories:
            if ignored_dir in path.parts:
                return True

        # 忽略特定扩展名
        if path.suffix.lower() in self.config.ignore.file_extensions:
            return True

        return False

    def _get_file_metadata(self, file_path: Path) -> FileRecord | None:
        """获取文件元数据

        Args:
            file_path: 文件路径

        Returns:
            FileRecord 对象，失败返回 None
        """
        try:
            stat = file_path.stat()

            # 获取文件大小
            size = stat.st_size

            # 获取创建时间和修改时间
            # Windows 下 st_ctime 是创建时间
            created_time = datetime.fromtimestamp(stat.st_ctime)
            modified_time = datetime.fromtimestamp(stat.st_mtime)

            # 创建文件记录（is_new_today 和 is_modified_today 将由 analyzer 填充）
            return FileRecord(
                path=file_path,
                size=size,
                created_time=created_time,
                modified_time=modified_time,
                is_new_today=False,  # 占位，稍后由 analyzer 更新
                is_modified_today=False,  # 占位，稍后由 analyzer 更新
            )

        except PermissionError:
            self.logger.debug(f"权限不足，无法访问文件: {file_path}")
            return None
        except FileNotFoundError:
            self.logger.debug(f"文件不存在（可能已被删除）: {file_path}")
            return None
        except OSError as e:
            self.logger.debug(f"无法获取文件元数据: {file_path}，错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"获取文件元数据时发生未知错误: {file_path}，错误: {e}")
            return None

    def find_large_files(
        self,
        file_records: dict[Path, list[FileRecord]],
        threshold_mb: int | None = None,
    ) -> list[LargeFile]:
        """查找大文件

        Args:
            file_records: 文件记录字典
            threshold_mb: 大小阈值（MB），None 则使用配置值

        Returns:
            大文件列表
        """
        if threshold_mb is None:
            threshold_mb = self.config.performance.large_file_threshold_mb

        threshold_bytes = threshold_mb * 1024 * 1024
        large_files = []

        for folder_path, files in file_records.items():
            for file in files:
                if file.size >= threshold_bytes:
                    large_files.append(
                        LargeFile(
                            path=file.path,
                            size=file.size,
                            created_time=file.created_time,
                            folder_path=folder_path,
                        )
                    )

        # 按大小降序排序
        large_files.sort(key=lambda x: x.size, reverse=True)
        self.logger.info(f"找到 {len(large_files)} 个大文件（>= {threshold_mb} MB）")
        return large_files

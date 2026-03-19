"""数据库持久化层"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from .models import FileTypeStats, FolderGrowth, LargeFile, ScanResult

LOGGER = logging.getLogger(__name__)


class DatabaseManager:
    """数据库连接和架构管理"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = LOGGER

        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库架构
        self.initialize_schema()

    @contextmanager
    def connection(self):
        """数据库连接上下文管理器（事务作用域）"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"数据库事务失败: {e}")
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """初始化数据库架构"""
        with self.connection() as conn:
            cursor = conn.cursor()

            # 扫描历史主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_time TEXT NOT NULL,
                    time_range_start TEXT NOT NULL,
                    time_range_end TEXT NOT NULL,
                    total_folders_scanned INTEGER NOT NULL,
                    folders_with_growth INTEGER NOT NULL,
                    total_new_files INTEGER NOT NULL,
                    total_new_size INTEGER NOT NULL,
                    total_modified_files INTEGER NOT NULL,
                    config_snapshot TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 文件夹增长详情
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS folder_growth_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    folder_path TEXT NOT NULL,
                    folder_name TEXT NOT NULL,
                    new_file_count INTEGER NOT NULL,
                    new_file_size INTEGER NOT NULL,
                    modified_file_count INTEGER NOT NULL,
                    modified_file_size INTEGER NOT NULL,
                    latest_activity_time TEXT,
                    composite_score REAL NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scan_history(id) ON DELETE CASCADE
                )
            """)

            # 文件类型统计
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_type_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    folder_path TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    file_count INTEGER NOT NULL,
                    total_size INTEGER NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scan_history(id) ON DELETE CASCADE
                )
            """)

            # 大文件追踪
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS large_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_time TEXT NOT NULL,
                    folder_path TEXT NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scan_history(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_history_scan_time
                ON scan_history(scan_time DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_folder_growth_scan_id
                ON folder_growth_history(scan_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_folder_growth_folder_path
                ON folder_growth_history(folder_path)
            """)

            self.logger.info(f"数据库架构初始化完成: {self.db_path}")

    def cleanup_old_records(self, retention_days: int) -> int:
        """清理旧记录

        Args:
            retention_days: 保留天数

        Returns:
            删除的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.isoformat()

        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM scan_history WHERE scan_time < ?",
                (cutoff_str,)
            )
            deleted_count = cursor.rowcount
            self.logger.info(f"清理了 {deleted_count} 条旧记录（{retention_days} 天前）")
            return deleted_count


class HistoryStorage:
    """扫描历史的 CRUD 操作"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = LOGGER

    def save_scan_result(
        self,
        scan_result: ScanResult,
        file_type_stats: dict[Path, list[FileTypeStats]],
        large_files: list[LargeFile],
    ) -> int:
        """保存扫描结果

        Args:
            scan_result: 扫描结果
            file_type_stats: 文件类型统计（按文件夹分组）
            large_files: 大文件列表

        Returns:
            scan_id
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()

            # 1. 保存扫描历史主记录
            cursor.execute("""
                INSERT INTO scan_history (
                    scan_time, time_range_start, time_range_end,
                    total_folders_scanned, folders_with_growth,
                    total_new_files, total_new_size, total_modified_files,
                    config_snapshot, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_result.scan_time.isoformat(),
                scan_result.time_range_start.isoformat(),
                scan_result.time_range_end.isoformat(),
                scan_result.total_folders_scanned,
                scan_result.folders_with_growth,
                scan_result.total_new_files,
                scan_result.total_new_size,
                scan_result.total_modified_files,
                None,  # config_snapshot 暂时不保存
                datetime.now().isoformat(),
            ))

            scan_id = cursor.lastrowid

            # 2. 保存文件夹增长详情
            for folder_growth in scan_result.folder_growths:
                cursor.execute("""
                    INSERT INTO folder_growth_history (
                        scan_id, folder_path, folder_name,
                        new_file_count, new_file_size,
                        modified_file_count, modified_file_size,
                        latest_activity_time, composite_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scan_id,
                    str(folder_growth.folder_path),
                    folder_growth.folder_name,
                    folder_growth.new_file_count,
                    folder_growth.new_file_size,
                    folder_growth.modified_file_count,
                    folder_growth.modified_file_size,
                    folder_growth.latest_activity_time.isoformat() if folder_growth.latest_activity_time else None,
                    folder_growth.composite_score,
                ))

            # 3. 保存文件类型统计
            for folder_path, stats_list in file_type_stats.items():
                for stats in stats_list:
                    cursor.execute("""
                        INSERT INTO file_type_stats (
                            scan_id, folder_path, file_extension,
                            file_count, total_size
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        scan_id,
                        str(folder_path),
                        stats.extension,
                        stats.file_count,
                        stats.total_size,
                    ))

            # 4. 保存大文件记录
            for large_file in large_files:
                cursor.execute("""
                    INSERT INTO large_files (
                        scan_id, file_path, file_size,
                        created_time, folder_path
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    scan_id,
                    str(large_file.path),
                    large_file.size,
                    large_file.created_time.isoformat(),
                    str(large_file.folder_path),
                ))

            self.logger.info(f"扫描结果已保存到数据库，scan_id={scan_id}")
            return scan_id

    def get_recent_scans(self, days: int = 7) -> list[dict]:
        """获取最近的扫描记录

        Args:
            days: 最近天数

        Returns:
            扫描记录列表（简化版）
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM scan_history
                WHERE scan_time >= ?
                ORDER BY scan_time DESC
            """, (cutoff_str,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_scan_by_id(self, scan_id: int) -> dict | None:
        """根据 ID 获取扫描记录

        Args:
            scan_id: 扫描 ID

        Returns:
            扫描记录，不存在返回 None
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_history WHERE id = ?", (scan_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_folder_trend(self, folder_path: Path, days: int = 7) -> list[dict]:
        """获取文件夹的增长趋势

        Args:
            folder_path: 文件夹路径
            days: 天数

        Returns:
            增长历史列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fgh.*, sh.scan_time
                FROM folder_growth_history fgh
                JOIN scan_history sh ON fgh.scan_id = sh.id
                WHERE fgh.folder_path = ? AND sh.scan_time >= ?
                ORDER BY sh.scan_time ASC
            """, (str(folder_path), cutoff_str))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_file_type_distribution(self, scan_id: int) -> list[dict]:
        """获取文件类型分布

        Args:
            scan_id: 扫描 ID

        Returns:
            文件类型统计列表
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM file_type_stats
                WHERE scan_id = ?
                ORDER BY total_size DESC
            """, (scan_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_large_files(self, scan_id: int, limit: int = 20) -> list[dict]:
        """获取大文件列表

        Args:
            scan_id: 扫描 ID
            limit: 返回数量限制

        Returns:
            大文件列表
        """
        with self.db_manager.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM large_files
                WHERE scan_id = ?
                ORDER BY file_size DESC
                LIMIT ?
            """, (scan_id, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

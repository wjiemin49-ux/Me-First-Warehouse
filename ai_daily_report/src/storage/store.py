"""SQLite 持久化存储"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Store:
    """新闻记录存储"""

    def __init__(self, db_path: str = "data/sent_records.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS news_items (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_utc TEXT NOT NULL,
                        fetched_at TEXT NOT NULL,
                        sent_at TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON news_items(url)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sent_at ON news_items(sent_at)")
                conn.commit()
                logger.info(f"数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def is_duplicate(self, item_id: str, url: str) -> bool:
        """检查是否重复"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM news_items WHERE id = ? OR url = ?",
                    (item_id, url)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.warning(f"检查重复失败: {e}")
            return False

    def mark_as_sent(self, item_ids: list[str], items_data: list[dict]) -> None:
        """标记为已发送"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                sent_at = datetime.utcnow().isoformat()

                # 插入或更新记录
                for item_data in items_data:
                    conn.execute("""
                        INSERT OR REPLACE INTO news_items
                        (id, source, title, url, published_utc, fetched_at, sent_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_data['id'],
                        item_data['source'],
                        item_data['title'],
                        item_data['url'],
                        item_data['published_utc'],
                        item_data['fetched_at'],
                        sent_at
                    ))

                conn.commit()
                logger.info(f"标记 {len(item_ids)} 条新闻为已发送")
        except Exception as e:
            logger.error(f"标记已发送失败: {e}")

    def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM news_items WHERE created_at < ?",
                    (cutoff,)
                )
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"清理了 {deleted} 条超过 {days} 天的旧记录")
                return deleted
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return 0

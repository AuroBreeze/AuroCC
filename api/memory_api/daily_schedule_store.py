import sqlite3
from pathlib import Path
from datetime import datetime
from ..Logger_owner import Logger
import pytz
from config import env


class DailyScheduleStore:
    def __init__(self):
        self.logger = Logger("DailyScheduleStore")
        self.db_file = Path(env.MEMORY_STORE_PATH + "aurocc_memories.db")
        self.conn = sqlite3.connect(self.db_file)
        # 开启外键支持
        try:
            self.conn.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass
        self.bj_tz = pytz.timezone(env.TIMEZONE)

        self._init_dbs()
        self.logger.info("DailyScheduleStore init")
    
    def _init_dbs(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                done_count INTEGER DEFAULT 0,
                completion_ratio REAL DEFAULT 0.0,
                updated_at TEXT
            )
        ''')
        # 迁移：如果没有 created_at 字段，则添加
        try:
            cursor.execute("PRAGMA table_info(daily_schedule)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'created_at' not in cols:
                cursor.execute("ALTER TABLE daily_schedule ADD COLUMN created_at TEXT")
                self.logger.info("为 daily_schedule 添加 created_at 字段")
            # 迁移摘要字段
            if 'total_count' not in cols:
                cursor.execute("ALTER TABLE daily_schedule ADD COLUMN total_count INTEGER DEFAULT 0")
            if 'done_count' not in cols:
                cursor.execute("ALTER TABLE daily_schedule ADD COLUMN done_count INTEGER DEFAULT 0")
            if 'completion_ratio' not in cols:
                cursor.execute("ALTER TABLE daily_schedule ADD COLUMN completion_ratio REAL DEFAULT 0.0")
            if 'updated_at' not in cols:
                cursor.execute("ALTER TABLE daily_schedule ADD COLUMN updated_at TEXT")
        except Exception as e:
            self.logger.error(f"检查/添加 created_at 字段失败: {e}")
        # 可选：为 created_at 建索引
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_schedule_created_at ON daily_schedule(created_at)")
        except Exception:
            pass
        # 子表：每日程项（带级联删除）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_schedule_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                idx INTEGER,
                start TEXT,
                end TEXT,
                state TEXT,
                importance INTEGER DEFAULT 2,
                done INTEGER DEFAULT 0,
                completed_at TEXT,
                created_at TEXT,
                FOREIGN KEY(schedule_id) REFERENCES daily_schedule(id) ON DELETE CASCADE
            )
        ''')
        # 如已存在旧表且缺少 ON DELETE CASCADE，进行一次性迁移
        try:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_schedule_item'")
            row = cursor.fetchone()
            ddl = row[0] if row else ''
            if 'ON DELETE CASCADE' not in ddl.upper():
                self.logger.info("迁移 daily_schedule_item 以启用 ON DELETE CASCADE")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_schedule_item_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER,
                        idx INTEGER,
                        start TEXT,
                        end TEXT,
                        state TEXT,
                        importance INTEGER DEFAULT 3,
                        done INTEGER DEFAULT 0,
                        completed_at TEXT,
                        created_at TEXT,
                        FOREIGN KEY(schedule_id) REFERENCES daily_schedule(id) ON DELETE CASCADE
                    )
                ''')
                # 拷贝旧数据
                cursor.execute('''
                    INSERT INTO daily_schedule_item_new (id, schedule_id, idx, start, end, state, importance, done, completed_at, created_at)
                    SELECT id, schedule_id, idx, start, end, state, 3 as importance, done, completed_at, created_at FROM daily_schedule_item
                ''')
                cursor.execute('DROP TABLE daily_schedule_item')
                cursor.execute('ALTER TABLE daily_schedule_item_new RENAME TO daily_schedule_item')
        except Exception as e:
            self.logger.error(f"daily_schedule_item 迁移失败: {e}")
        # 若缺少 importance 列（可能来自旧版本但已包含CASCADE），补加该列
        try:
            cursor.execute("PRAGMA table_info(daily_schedule_item)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'importance' not in cols:
                cursor.execute("ALTER TABLE daily_schedule_item ADD COLUMN importance INTEGER DEFAULT 3")
        except Exception:
            pass
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_schedule_item_schedule_id ON daily_schedule_item(schedule_id)")
        except Exception:
            pass
        self.conn.commit()
    
    def _today_str(self):
        return datetime.now(self.bj_tz).strftime('%Y-%m-%d')

    def add_daily_schedule(self, content):
        cursor = self.conn.cursor()
        created_at = self._today_str()
        # 显式列插入，兼容新加列
        try:
            cursor.execute(
                "INSERT INTO daily_schedule (content, status, created_at, total_count, done_count, completion_ratio, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (content, 0, created_at, 0, 0, 0.0, created_at)
            )
        except Exception:
            # 回退：旧表结构（无 created_at）
            cursor.execute(
                "INSERT INTO daily_schedule (content, status) VALUES (?, ?)",
                (content, 0)
            )
        self.conn.commit()
        self.logger.info(f"添加日程成功: {content}")
        return cursor.lastrowid # 返回插入的行ID
    
    def get_all_daily_schedule(self,limit=10): # 获取日程
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM daily_schedule ORDER BY id DESC LIMIT ?
        """,(limit,))
        rows = cursor.fetchall()
        self.logger.info("获取日程成功")
        return rows

    def get_daily_schedule_by_status(self, status: int, limit: int = 10):
        """按状态获取日程：0=未完成，1=已完成"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM daily_schedule WHERE status = ? ORDER BY id DESC LIMIT ?",
            (int(status), int(limit)),
        )
        rows = cursor.fetchall()
        return rows

    def mark_schedule_status(self, schedule_id: int, status: int = 1):
        """更新日程状态，默认标记为已完成(1)"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE daily_schedule SET status = ? WHERE id = ?",
            (int(status), int(schedule_id)),
        )
        self.conn.commit()
        return cursor.rowcount

    def has_schedule_for_date(self, date_str: str) -> bool:
        """判断某日期是否已有日程（基于 created_at）"""
        try:
            cursor = self.conn.cursor()
            # 兼容 created_at 既可能是 'YYYY-MM-DD'，也可能是 'YYYY-MM-DD HH:MM:SS'
            cursor.execute(
                "SELECT 1 FROM daily_schedule WHERE created_at = ? OR created_at LIKE ? || '%' LIMIT 1",
                (date_str, date_str)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            # 若无 created_at 列，回退到“是否至少有一条记录”
            self.logger.error(f"检查日期日程失败，将采用回退逻辑: {e}")
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM daily_schedule LIMIT 1")
            return cursor.fetchone() is not None

    def has_schedule_for_today(self) -> bool:
        return self.has_schedule_for_date(self._today_str())

    def get_today_schedule(self):
        """获取今日最新一条日程，若不存在返回 None"""
        date_str = self._today_str()
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, content, status FROM daily_schedule WHERE created_at = ? OR created_at LIKE ? || '%' ORDER BY id DESC LIMIT 1",
                (date_str, date_str)
            )
            return cursor.fetchone()
        except Exception:
            # 回退：取最新一条
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, content, status FROM daily_schedule ORDER BY id DESC LIMIT 1")
            return cursor.fetchone()

    # ===== 子表：项级操作 =====
    def add_daily_schedule_items(self, schedule_id: int, items: list[dict]):
        """将解析后的日程项批量写入子表，并回填 created_at（当天）。items: [{start,end,state,done}]."""
        created_at = self._today_str()
        cursor = self.conn.cursor()
        for idx, it in enumerate(items):
            cursor.execute(
                """
                INSERT INTO daily_schedule_item (schedule_id, idx, start, end, state, importance, done, completed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(schedule_id),
                    int(idx),
                    str(it.get('start', '')),
                    str(it.get('end', '')),
                    str(it.get('state', '')),
                    (lambda v: (
                        (lambda parsed: max(1, min(5, parsed)))(
                            (lambda s: (3 if s is None or s == '' else (int(s) if str(s).strip('-').isdigit() else 3)))(v)
                        )
                    ))(it.get('importance', 3)),
                    1 if bool(it.get('done')) else 0,
                    created_at if bool(it.get('done')) else None,
                    created_at,
                )
            )
        self.conn.commit()
        return True

    def list_items_by_schedule(self, schedule_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, idx, start, end, state, importance, done, completed_at FROM daily_schedule_item WHERE schedule_id = ? ORDER BY idx ASC",
            (int(schedule_id),)
        )
        return cursor.fetchall()

    def list_items_by_date(self, date_str: str):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT i.id, i.idx, i.start, i.end, i.state, i.importance, i.done, i.completed_at, i.schedule_id
            FROM daily_schedule_item i
            JOIN daily_schedule s ON s.id = i.schedule_id
            WHERE s.created_at = ?
            ORDER BY i.idx ASC
            """,
            (date_str,)
        )
        return cursor.fetchall()

    def mark_item_done(self, item_id: int, done: bool = True):
        cursor = self.conn.cursor()
        completed_at = self._today_str() if done else None
        cursor.execute(
            "UPDATE daily_schedule_item SET done = ?, completed_at = ? WHERE id = ?",
            (1 if done else 0, completed_at, int(item_id))
        )
        self.conn.commit()
        return cursor.rowcount

    def recalc_schedule_stats(self, schedule_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(1), SUM(done) FROM daily_schedule_item WHERE schedule_id = ?",
            (int(schedule_id),)
        )
        row = cursor.fetchone()
        total = int(row[0] or 0)
        done = int(row[1] or 0)
        ratio = float(done / total) if total > 0 else 0.0
        updated_at = datetime.now(self.bj_tz).isoformat()
        cursor.execute(
            "UPDATE daily_schedule SET total_count = ?, done_count = ?, completion_ratio = ?, updated_at = ? WHERE id = ?",
            (total, done, ratio, updated_at, int(schedule_id))
        )
        self.conn.commit()
        return total, done, ratio

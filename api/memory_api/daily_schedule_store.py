import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from ..Logger_owner import Logger
import pytz
from config import env


class DailyScheduleStore:
    def __init__(self):
        self.logger = Logger("DailyScheduleStore")
        self.db_file = Path(env.MEMORY_STORE_PATH + "aurocc_memories.db")
        self.conn = sqlite3.connect(self.db_file)
        self.bj_tz = pytz.timezone(env.TIMEZONE)

        self._init_dbs()
        self.logger.info("DailyScheduleStore init")
    
    def _init_dbs(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                status INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def add_daily_schedule(self, content):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO daily_schedule (content) VALUES (?)
        """, (content,))
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

import sqlite3
import os
from . import lssuing_cfg
from api.Logger_owner import Logger
import pytz

class Store_db:
    """
    存储数据库，，用来存储授权的群，功能和时间
    """
    def __init__(self):
        self.logger = Logger("Lssuing_store_db")
        self.db_path = lssuing_cfg.DB_PATH
        self.timezone = lssuing_cfg.TIMEZONE
        self.bj_tz = pytz.timezone(self.timezone)
        self.conn = sqlite3.connect(self.db_path)

    def _init_dbs(self):
        cursor = self.conn.cursor()
        # 创建短期记忆表
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS authorization_groups (
            group_id TEXT PRIMARY KEY,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            features TEXT NOT NULL,  -- JSON格式存储授权功能
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_authorization_groups_time 
        ON authorization_groups(start_time, end_time)
        """)
        
        
        self.conn.commit()


    def add_authorization(self, group_id, start_time, end_time, features):
        """添加或更新群组授权"""
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO authorization_groups 
        (group_id, start_time, end_time, features, update_time)
        VALUES (?, ?, ?, ?, datetime('now'))
        """, (group_id, start_time, end_time, features))
        self.conn.commit()
        return True

    def get_authorization(self, group_id):
        """获取群组授权信息"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM authorization_groups WHERE group_id = ?
        """, (group_id,))
        return cursor.fetchone()

    def delete_authorization(self, group_id):
        """删除群组授权"""
        cursor = self.conn.cursor()
        cursor.execute("""
        DELETE FROM authorization_groups WHERE group_id = ?
        """, (group_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_active_authorizations(self):
        """列出当前有效的授权"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM authorization_groups 
        WHERE datetime('now') BETWEEN start_time AND end_time
        """)
        return cursor.fetchall()

    def __str__(self):
        return "create database for admin and user"

if __name__ == '__main__':
    print(Store_db())

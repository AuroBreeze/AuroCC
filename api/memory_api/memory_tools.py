import sqlite3
import json
from pathlib import Path
from ..Logger_owner import Logger
from config import env


class MemoryStore_Tools:
    def __init__(self):
        self.user_id = env.QQ_ADMIN
        # 使用统一数据库文件
        self.db_file = Path(env.MEMORY_STORE_PATH + "aurocc_memories.db")
        self.conn = sqlite3.connect(self.db_file)
        self._init_dbs()
        self.logger = Logger("MemoryStore_Tools")
    
    def _init_dbs(self):
        cursor = self.conn.cursor()
        # 创建短期记忆表
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS user_{self.user_id}_short_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 0
        )
        """)
        
        # 创建长期记忆表
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS user_{self.user_id}_long_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 2
        )
        """)
        
        # 创建索引
        cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_user_{self.user_id}_short_time 
        ON user_{self.user_id}_short_memories(timestamp)
        """)
        cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_user_{self.user_id}_long_importance 
        ON user_{self.user_id}_long_memories(importance)
        """)
        
        self.conn.commit()
    def get_memories(self, memory_type=None):
        """分别查询短期和长期记忆并分开返回"""
        short_results = []
        long_results = []
        cursor = self.conn.cursor()

        # 查询短期记忆
        query = f"SELECT content FROM user_{self.user_id}_short_memories"
        params = []
        if memory_type:
            query += " WHERE memory_type = ?"
            params.append(memory_type)
        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        short_results.extend(json.loads(row[0]) for row in cursor.fetchall())

        # 查询长期记忆
        query = f"SELECT content FROM user_{self.user_id}_long_memories"
        params = []
        if memory_type:
            query += " WHERE memory_type = ?"
            params.append(memory_type)
        query += " ORDER BY importance DESC, timestamp DESC"
        cursor.execute(query, params)
        long_results.extend(json.loads(row[0]) for row in cursor.fetchall())

        return {"short": short_results, "long": long_results}
    def get_memory_short_time(self):
        """
        查询最近聊天的时间点
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT timestamp FROM user_{self.user_id}_short_memories 
            ORDER BY timestamp DESC LIMIT 1
        """)
        result = cursor.fetchone()
        if not result:
            return None
        
        return result[0]
    def get_memory_short(self):
        """
        查询最近的短期记忆
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT content FROM user_{self.user_id}_short_memories 
            ORDER BY timestamp DESC LIMIT 1
        """)
        result = cursor.fetchone()
        if not result:
            return None
        return json.loads(result[0])
    def get_memory_long(self):
        """
        查询最近的长期记忆
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT content FROM user_{self.user_id}_long_memories 
            ORDER BY timestamp DESC LIMIT 1
        """)
        result = cursor.fetchone()
        if not result:
            return None
        return json.loads(result[0])

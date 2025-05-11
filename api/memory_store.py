import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from .Logger_owner import Logger
import pytz

class MemoryStore:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.short_term_db = Path(f"user_memories_short_{user_id}.db")
        self.long_term_db = Path(f"user_memories_long_{user_id}.db")
        self.bj_tz = pytz.timezone('Asia/Shanghai')
        self._init_dbs()
        self.logger = Logger()
        
    def _init_dbs(self):
        # 短期记忆库(保存7天)
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp DATETIME,
            memory_type TEXT,
            content TEXT,
            importance INTEGER DEFAULT 0
        )
        """)
        conn.commit()
        conn.close()
        
        # 长期记忆库(精选重要记忆)
        conn = sqlite3.connect(self.long_term_db)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp DATETIME,
            memory_type TEXT,
            content TEXT,
            importance INTEGER DEFAULT 2,
            last_reviewed DATETIME,
            next_review DATETIME
        )
        """)
        conn.commit()
        conn.close()
        
    def add_memory(self, memory_type, content, importance=0):
        """添加记忆到短期和长期数据库
        importance: 
        0-普通 1-一般重要 2-重要 3-很重 4-非常重要 5-极其重要
        content: 可以是字符串或包含完整对话上下文的字典
        """
        now = datetime.now(self.bj_tz).isoformat()
        
        # 处理content为字典或字符串
        if isinstance(content, dict):
            content_data = json.dumps(content, ensure_ascii=False)
        else:
            content_data = json.dumps({"role":"assistant","content": str(content)}, ensure_ascii=False)
        #print(f"[MemoryStore] 添加记忆: {type(content_data)} {content_data}")
        self.logger.info(f"添加记忆: {type(content_data)} {content_data}")
        
        
        # 添加到短期记忆库(确保importance为整数)
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO memories (user_id, timestamp, memory_type, content, importance) VALUES (?, ?, ?, ?, ?)",
                (self.user_id, now, memory_type, content_data, int(importance))
            )
            conn.commit()
        except sqlite3.Error as e:
            self.Logger.error(f"存储记忆失败: {str(e)}")
            raise
        finally:
            conn.close()
        
        # 重要记忆(importance>=3)直接添加到长期记忆库
        if importance >= 3:
            next_review = self._calculate_next_review(now, importance)
            conn = sqlite3.connect(self.long_term_db)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (user_id, timestamp, memory_type, content, importance, last_reviewed, next_review) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.user_id, now, memory_type, content_data, 
                 importance, now, next_review)
            )
            conn.commit()
            conn.close()
        
    def migrate_memories(self):
        """迁移记忆并清理过期记忆"""
        week_ago = (datetime.now(self.bj_tz) - timedelta(days=7)).isoformat()
        
        # 从短期库获取所有7天前的记忆
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, memory_type, content, importance 
            FROM memories 
            WHERE user_id = ? AND timestamp <= ?
        """, (self.user_id, week_ago))
        
        important_memories = cursor.fetchall()
        
        # 添加到长期库
        long_conn = sqlite3.connect(self.long_term_db)
        long_cursor = long_conn.cursor()
        
        for mem in important_memories:
            timestamp, mem_type, content, imp = mem
            next_review = self._calculate_next_review(timestamp, imp)
            long_cursor.execute("""
                INSERT OR IGNORE INTO memories 
                (user_id, timestamp, memory_type, content, importance, last_reviewed, next_review)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.user_id, timestamp, mem_type, content, imp, timestamp, next_review))
        
        # 更新长期库中重要性<=3的记忆
        long_cursor.execute("""
            UPDATE memories 
            SET importance = importance - 1 
            WHERE user_id = ? AND importance <= 3
        """, (self.user_id,))
        
        # 删除长期库中重要性为0的记忆
        long_cursor.execute("""
            DELETE FROM memories 
            WHERE user_id = ? AND importance <= 0
        """, (self.user_id,))
        
        long_conn.commit()
        long_conn.close()
        
        # 清理短期库中所有超过7天的记忆（不管重要性）
        cursor.execute("""
            DELETE FROM memories 
            WHERE user_id = ? AND timestamp <= ?
        """, (self.user_id, week_ago))
        
        conn.commit()
        conn.close()
        
    def get_memories(self, memory_type=None):
        """合并查询两个数据库的记忆"""
        results = []
    

        # 先获取短期记忆
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
    
        query = "SELECT content FROM memories WHERE user_id = ?"
        params = [self.user_id]
    
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        
        query += " ORDER BY timestamp DESC"
    
        cursor.execute(query, params)
        results.extend(json.loads(row[0]) for row in cursor.fetchall())
        conn.close()
        
        # 再获取长期记忆
        conn = sqlite3.connect(self.long_term_db)
        cursor = conn.cursor()
    
        query = "SELECT content FROM memories WHERE user_id = ?"
        params = [self.user_id]
    
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        
        query += " ORDER BY importance DESC, timestamp DESC"
    
        cursor.execute(query, params)
        results.extend(json.loads(row[0]) for row in cursor.fetchall())
        conn.close()
    
        #print(results)
        return results
    def get_memory_short_time(self):
        """
        查询最近聊天的时间点
        """
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp FROM memories WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1
        """, (self.user_id,))
        result = cursor.fetchone()
        if not result:
            return None
        
        return result[0]
    def get_memory_short(self):
        """
        查询最近的短期记忆
        """
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content FROM memories WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1
        """, (self.user_id,))
        result = cursor.fetchone()
        if not result:
            return None
        return json.loads(result[0])
    def get_memory_long(self):
        """
        查询最近的长期记忆
        """
        conn = sqlite3.connect(self.long_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content FROM memories WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1
        """, (self.user_id,))
        result = cursor.fetchone()
        if not result:
            return None
        return json.loads(result[0])
        
    
        


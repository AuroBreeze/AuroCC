import sqlite3
import json
from pathlib import Path
from datetime import datetime

class MemoryStore:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.db_path = Path("user_memories.db")
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT,
            timestamp DATETIME,
            memory_type TEXT,
            content TEXT,
            importance INTEGER DEFAULT 0,
            last_reviewed DATETIME,
            next_review DATETIME,
            review_count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, timestamp, memory_type))
        )
        """)
        conn.commit()
        conn.close()
        
    def add_memory(self, memory_type, content, importance=0):
        """添加记忆，importance: 0-普通 1-重要 2-非常重要"""
        now = datetime.now().isoformat()
        next_review = self._calculate_next_review(now, importance)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, now, memory_type, json.dumps(content),
             importance, now, next_review, 0)
        )
        conn.commit()
        conn.close()
        
    def _calculate_next_review(self, timestamp, importance):
        """根据艾宾浩斯遗忘曲线计算下次复习时间"""
        from datetime import datetime, timedelta
        now = datetime.now()
        if importance == 2:  # 非常重要的记忆
            return (now + timedelta(days=30)).isoformat()
        elif importance == 1:  # 重要记忆
            return (now + timedelta(days=7)).isoformat()
        else:  # 普通记忆
            intervals = [1, 2, 4, 7, 15]  # 天
            return (now + timedelta(days=intervals[0])).isoformat()
        
    def get_memories(self, memory_type=None, limit=10, importance=None):
        """获取记忆，可筛选重要性和类型"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 优先获取需要复习的记忆
        now = datetime.now().isoformat()
        query = """
            SELECT rowid, content, importance FROM memories 
            WHERE user_id = ? AND next_review <= ?
        """
        params = [self.user_id, now]
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        if importance is not None:
            query += " AND importance >= ?"
            params.append(importance)
            
        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            rowid, content, imp = row
            # 更新复习时间和次数
            cursor.execute("""
                UPDATE memories SET 
                last_reviewed = ?,
                next_review = ?,
                review_count = review_count + 1
                WHERE rowid = ?
            """, (
                now,
                self._calculate_next_review(now, imp),
                rowid
            ))
            results.append(json.loads(content))
            
        # 如果不够limit数量，补充其他记忆
        if len(results) < limit:
            remaining = limit - len(results)
            query = "SELECT content FROM memories WHERE user_id = ?"
            params = [self.user_id]
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
            if importance is not None:
                query += " AND importance >= ?"
                params.append(importance)
                
            query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
            params.append(remaining)
            
            cursor.execute(query, params)
            results.extend(json.loads(row[0]) for row in cursor.fetchall())
            
        conn.commit()
        conn.close()
        return results

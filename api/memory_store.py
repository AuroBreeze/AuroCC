import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

class MemoryStore:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.short_term_db = Path(f"user_memories_short_{user_id}.db")
        self.long_term_db = Path(f"user_memories_long_{user_id}.db")
        self._init_dbs()
        
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
        now = datetime.now().isoformat()
        
        # 处理content为字典或字符串
        if isinstance(content, dict):
            content_data = json.dumps(content, ensure_ascii=False)
        else:
            content_data = json.dumps({"content": str(content)}, ensure_ascii=False)
        
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
                (self.user_id, now, memory_type, json.dumps(content), 
                 importance, now, next_review)
            )
            conn.commit()
            conn.close()
        
    def _calculate_next_review(self, timestamp, importance):
        """根据艾宾浩斯遗忘曲线计算下次复习时间
        0-普通: 1天
        1-一般重要: 3天
        2-重要: 7天
        3-很重: 15天
        4-非常重要: 30天
        5-极其重要: 90天
        """
        from datetime import datetime, timedelta
        now = datetime.now()
        intervals = {
            0: 1,
            1: 3,
            2: 7,
            3: 15,
            4: 30,
            5: 90
        }
        return (now + timedelta(days=intervals.get(importance, 1))).isoformat()
        
    def migrate_memories(self):
        """迁移重要记忆到长期库并清理过期记忆"""
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # 从短期库获取重要记忆(importance>=4)
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, memory_type, content, importance 
            FROM memories 
            WHERE user_id = ? AND importance >= 4 AND timestamp <= ?
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
        
        long_conn.commit()
        long_conn.close()
        
        # 清理7天前的普通记忆
        cursor.execute("""
            DELETE FROM memories 
            WHERE user_id = ? AND timestamp <= ? AND importance < 1
        """, (self.user_id, week_ago))
        
        conn.commit()
        conn.close()
        
    def update_memory(self, memory_type, content_update, timestamp=None):
        """更新最近一条记忆的内容
        Args:
            memory_type: 记忆类型
            content_update: 要更新的内容(dict)
            timestamp: 可选，指定要更新的记忆时间
        """
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        
        # 获取最近一条记忆
        query = "SELECT id, content FROM memories WHERE user_id = ? AND memory_type = ?"
        params = [self.user_id, memory_type]
        
        if timestamp:
            query += " AND timestamp = ?"
            params.append(timestamp)
            
        query += " ORDER BY timestamp DESC LIMIT 1"
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        if not result:
            return False
            
        mem_id, old_content = result
        old_data = json.loads(old_content)
        
        # 合并新旧内容
        updated_content = {**old_data, **content_update}
        
        # 更新数据库
        cursor.execute(
            "UPDATE memories SET content = ? WHERE id = ?",
            (json.dumps(updated_content, ensure_ascii=False), mem_id)
        )
        conn.commit()
        conn.close()
        return True
        
    def get_memories(self, memory_type=None, limit=10):
        """合并查询两个数据库的记忆"""
        results = []
        
        # 先获取长期记忆
        conn = sqlite3.connect(self.long_term_db)
        cursor = conn.cursor()
        
        query = "SELECT content FROM memories WHERE user_id = ?"
        params = [self.user_id]
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
            
        query += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results.extend(json.loads(row[0]) for row in cursor.fetchall())
        conn.close()
        
        # 如果不够limit数量，补充短期记忆
        if len(results) < limit:
            remaining = limit - len(results)
            
            conn = sqlite3.connect(self.short_term_db)
            cursor = conn.cursor()
            
            query = "SELECT content FROM memories WHERE user_id = ?"
            params = [self.user_id]
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(remaining)
            
            cursor.execute(query, params)
            results.extend(json.loads(row[0]) for row in cursor.fetchall())
            conn.close()
            
        return results

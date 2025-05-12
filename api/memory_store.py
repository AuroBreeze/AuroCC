import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from .Logger_owner import Logger
import pytz
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle  # 新增导入

class MemoryStore:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.short_term_db = Path(f"user_memories_short_{user_id}.db")
        self.long_term_db = Path(f"user_memories_long_{user_id}.db")
        self.bj_tz = pytz.timezone('Asia/Shanghai')
        self._init_dbs()
        self.logger = Logger()
        
        # 新增向量索引相关属性
        
        # 改用支持中文更好的模型
        self.embedder = SentenceTransformer("./local_model")
        self.dim = self.embedder.get_sentence_embedding_dimension()  # 与模型维度一致
        self.short_term_index = faiss.IndexFlatL2(self.dim)
        self.long_term_index = faiss.IndexFlatL2(self.dim)
        self.id_mapping = {'short': {}, 'long': {}}  # FAISS ID -> 数据库ID
        
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
            importance INTEGER DEFAULT 2
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
            new_short_id = cursor.lastrowid
            conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"存储记忆失败: {str(e)}")
            raise
        finally:
            conn.close()
        
        # 重要记忆(importance>=3)直接添加到长期记忆库
        if importance >= 3:
            conn = sqlite3.connect(self.long_term_db)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (user_id, timestamp, memory_type, content, importance) VALUES (?, ?, ?, ?, ?)",
                (self.user_id, now, memory_type, content_data, importance)
            )
            new_long_id = cursor.lastrowid
            conn.commit()
            conn.close()
        
        # 新增向量索引更新
        text_content = content['content'] if isinstance(content, dict) else content
        vector = self.embedder.encode([text_content])[0]
    
        # 根据存储位置更新对应索引
        if importance >= 3:
            self._update_index('long', vector, new_long_id)
        else:
            self._update_index('short', vector, new_short_id)
        
    def _update_index(self, index_type, vector, db_id):
        """更新指定类型的索引"""
        vector = vector.reshape(1, -1).astype('float32')
        index = self.short_term_index if index_type == 'short' else self.long_term_index
        index.add(vector)
    
        # 记录ID映射
        faiss_id = index.ntotal - 1
        self.id_mapping[index_type][faiss_id] = db_id

    
    def search_memories(self, query_text, top_k=5, time_weight=0.3):
        """混合检索：语义相似度 + 时间衰减"""
        # 生成查询向量
        query_vec = self.embedder.encode([query_text])[0].astype('float32')
    
        # 并行搜索两个索引
        short_dist, short_idx = self.short_term_index.search(query_vec.reshape(1, -1), top_k)
        long_dist, long_idx = self.long_term_index.search(query_vec.reshape(1, -1), top_k)
    
        # 合并结果并加载元数据
        candidates = []
        for idx in short_idx[0]:
            if db_id := self.id_mapping['short'].get(idx):
                record = self._get_memory_by_id('short', db_id)
                candidates.append(self._calculate_score(record, short_dist[0][idx], time_weight))
    
        for idx in long_idx[0]:
            if db_id := self.id_mapping['long'].get(idx):
                record = self._get_memory_by_id('long', db_id)
                candidates.append(self._calculate_score(record, long_dist[0][idx], time_weight))
    
        # 按综合得分排序
        return sorted(candidates, key=lambda x: -x['score'])[:top_k]

    def _get_memory_by_id(self, db_type, db_id):
        """根据ID获取完整记忆"""
        conn = sqlite3.connect(getattr(self, f"{db_type}_term_db"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE id=?", (db_id,))
        result = cursor.fetchone()
        conn.close()
        return {
        'id': result[0],
        'timestamp': result[2],
        'content': json.loads(result[4]),
        'importance': result[5]
        }

    def _calculate_score(self, record, distance, time_weight):
        """计算综合得分"""
        hours_passed = (datetime.now(self.bj_tz) - datetime.fromisoformat(record['timestamp'])).total_seconds() / 3600
        time_score = 1 / (hours_passed + 1)  # 时间衰减因子
        return {
        'content': record['content'],
        'score': (1 - distance/10) + time_weight*time_score + 0.1*record['importance']
        }
    
    def save_indexes(self):
        """保存索引到文件"""
        faiss.write_index(self.short_term_index, f"user_{self.user_id}_short.index")
        faiss.write_index(self.long_term_index, f"user_{self.user_id}_long.index")
        with open(f"user_{self.user_id}_mapping.pkl", 'wb') as f:
            pickle.dump(self.id_mapping, f)

    def load_indexes(self):
        """加载索引文件"""
        self.short_term_index = faiss.read_index(f"user_{self.user_id}_short.index")
        self.long_term_index = faiss.read_index(f"user_{self.user_id}_long.index")
        with open(f"user_{self.user_id}_mapping.pkl", 'rb') as f:
            self.id_mapping = pickle.load(f)
    def clear_memories_long(self):
        """清理7天的过期记忆"""
        week_ago = (datetime.now(self.bj_tz) - timedelta(days=7)).isoformat()
        
        # 从短期库获取所有7天前的记忆
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, memory_type, content, importance 
            FROM memories 
            WHERE user_id = ? AND timestamp <= ?
        """, (self.user_id, week_ago))
        
        # 添加到长期库
        long_conn = sqlite3.connect(self.long_term_db)
        long_cursor = long_conn.cursor()
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
    def clear_memories_short(self):
        """
        删除两天前的重要性小于3的记忆
        """
        conn = sqlite3.connect(self.short_term_db)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM memories 
            WHERE user_id = ? AND importance < 3 AND timestamp < ?
        """, (self.user_id, (datetime.now(self.bj_tz) - timedelta(days=2)).isoformat()))
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
        
    
        


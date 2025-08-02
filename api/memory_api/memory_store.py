import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from ..Logger_owner import Logger
import pytz
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle  # 新增导入
from config import env
from utils.download_model import download


class MemoryStore:

    _model = None  # 新增模型属性
    def __init__(self, user_id):
        self.user_id = str(user_id)
        # 使用统一数据库文件
        self.db_file = Path(env.MEMORY_STORE_PATH + "aurocc_memories.db")
        self.conn = sqlite3.connect(self.db_file)
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self._init_dbs()
        self.logger = Logger("MemoryStore")
        
        # 新增向量索引相关属性
        
        # 改用支持中文更好的模型
        try:
            if not MemoryStore._model: # 减少重复加载模型
                MemoryStore._model = SentenceTransformer(env.MODEL_STORE_PATH) # 加载本地模型
        except Exception as e:
            self.logger.warning(f"加载模型失败: {str(e)}")
            download()  # 下载并加载模型
            MemoryStore._model = SentenceTransformer(env.MODEL_STORE_PATH) # 加载本地模型

        self.embedder = MemoryStore._model  # 新增模型属性
        self.dim = self.embedder.get_sentence_embedding_dimension()  # 与模型维度一致
        self.short_term_index = faiss.IndexFlatL2(self.dim)
        self.long_term_index = faiss.IndexFlatL2(self.dim)
        self.id_mapping = {'short': {}, 'long': {}}  # FAISS ID -> 数据库ID
        
        self.short_index_save_path = env.INDEX_STORE_PATH+f"user_memories_short_{user_id}.index"
        self.long_index_save_path = env.INDEX_STORE_PATH+f"user_memories_long_{user_id}.index"
        self.pkl_save_path = env.INDEX_STORE_PATH+f"user_memories_{user_id}.pkl"
        
        self.logger.info("MemoryStore init success")
        
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
        self.logger.info(f"添加记忆: {type(content_data)} {content_data}")
        
        # 添加到短期记忆库(确保importance为整数)
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                f"INSERT INTO user_{self.user_id}_short_memories (timestamp, memory_type, content, importance) VALUES (?, ?, ?, ?)",
                (now, memory_type, content_data, int(importance))
            )
            new_short_id = cursor.lastrowid
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"存储记忆失败: {str(e)}")
            raise
        
        # 新增向量索引更新
        text_content = content['content'] if isinstance(content, dict) else content
        vector = self.embedder.encode([text_content])[0]
    
        # 总是更新短期索引
        self._update_index('short', vector, new_short_id)
        
        # 手动保存索引(每10次更新保存一次)
    
        self.save_indexes()
        
    def _update_index(self, index_type, vector, db_id):
        """更新指定类型的索引"""
        vector = vector.reshape(1, -1).astype('float32')
        index = self.short_term_index if index_type == 'short' else self.long_term_index
        if index.d != self.dim and index.ntotal > 0:
            raise ValueError(f"向量维度 {self.dim} 与索引维度 {index.d} 不匹配")
        index.add(vector)
    
        # 记录ID映射
        faiss_id = index.ntotal - 1
        self.id_mapping[index_type][faiss_id] = db_id
        
        # 移除自动保存索引，改为在适当时候手动调用
        #self.logger.info(f"{index_type} 索引更新：新增向量 {vector} 到索引 {index.ntotal-1}")
        self.logger.info("向量索引 + 数据库信息 --> 更新成功")
        
        # 验证索引完整性
        if faiss_id not in self.id_mapping[index_type]:
            self.logger.error(f"索引更新失败：ID映射未正确更新")
            raise ValueError("索引更新失败")

    
    def search_memories(self, query_text, top_k=5, time_weight=0.3):
        """混合检索：语义相似度 + 时间衰减"""
        # 生成查询向量
        self.load_indexes()  # 加载索引
        query_vec = self.embedder.encode([query_text])[0].astype('float32')
        
         # 动态调整搜索范围
        max_short = min(top_k, self.short_term_index.ntotal) 
        max_long = min(top_k, self.long_term_index.ntotal)

    
        # 并行搜索两个索引
        short_dist, short_idx = self.short_term_index.search(query_vec.reshape(1, -1), max_short or 1)
        long_dist, long_idx = self.long_term_index.search(query_vec.reshape(1, -1), max_long or 1)
    
        # 合并结果并加载元数据
        candidates = []
        seen_contents = set()  # 用于去重
        
        for i, idx in enumerate(short_idx[0]):
            if db_id := self.id_mapping['short'].get(idx):
                record = self._get_memory_by_id('short', db_id)
                content_str = json.dumps(record['content'], sort_keys=True)
                if content_str not in seen_contents:
                    seen_contents.add(content_str)
                    candidates.append(self._calculate_score(record, short_dist[0][i], time_weight))
    
        for i, idx in enumerate(long_idx[0]):
            if db_id := self.id_mapping['long'].get(idx):
                record = self._get_memory_by_id('long', db_id)
                content_str = json.dumps(record['content'], sort_keys=True)
                if content_str not in seen_contents:
                    seen_contents.add(content_str)
                    candidates.append(self._calculate_score(record, long_dist[0][i], time_weight))
    
        # 按综合得分排序
        return sorted(candidates, key=lambda x: -x['score'])[:top_k]

    def _get_memory_by_id(self, db_type, db_id):
        """根据ID获取完整记忆"""
        cursor = self.conn.cursor()
        table_name = f"user_{self.user_id}_{db_type}_memories"
        cursor.execute(f"SELECT * FROM {table_name} WHERE id=?", (db_id,))
        result = cursor.fetchone()
        print(result)
        return {
        'id': result[0],
        'timestamp': result[1],
        'memory_type': result[2],
        'content': json.loads(result[3]),
        'importance': result[4]
        }

    def _calculate_score(self, record, distance, time_weight):
        """计算综合得分"""

        dt = datetime.fromisoformat(record['timestamp'])
        if not dt.tzinfo:
            dt = self.bj_tz.localize(dt)
        else:
            dt = dt.astimezone(self.bj_tz)
        hours_passed = (datetime.now(self.bj_tz) - dt).total_seconds() / 3600
        time_score = 1 / (hours_passed + 1)  # 时间衰减因子
        # 调整得分计算，增加语义相似度权重
        semantic_score = 1.0 / (1.0 + distance)  # 使用更合理的距离转换
        return {
            'content': record['content'],
            'score': (0.6 * semantic_score) + (0.1 * time_weight*time_score) + (0.3 * record['importance']/5.0)
        }
    
    def save_indexes(self):
        
        """保存索引到文件"""
        faiss.write_index(self.short_term_index, self.short_index_save_path)
        faiss.write_index(self.long_term_index, self.long_index_save_path)
        with open(self.pkl_save_path, 'wb') as f:
            pickle.dump(self.id_mapping, f)
        
        self.logger.info(f"索引保存成功：{self.short_term_index.ntotal} 条短期记忆，{self.long_term_index.ntotal} 条长期记忆")

    def load_indexes(self):
        """加载索引文件"""
        self.short_term_index = faiss.read_index(self.short_index_save_path)
        self.long_term_index = faiss.read_index(self.long_index_save_path)
        with open(self.pkl_save_path, 'rb') as f:
            self.id_mapping = pickle.load(f)
            
    def debug_status(self):
        """打印系统状态"""
        cursor = self.conn.cursor()
        
        # 查询短期记忆记录数
        cursor.execute(f"SELECT COUNT(*) FROM user_{self.user_id}_short_memories")
        count_short = cursor.fetchone()[0]
        
        # 查询长期记忆记录数
        cursor.execute(f"SELECT COUNT(*) FROM user_{self.user_id}_long_memories")
        count_long = cursor.fetchone()[0]
    
        # 索引状态
        print(f"""
        === MemoryStore 调试信息 ===
        短期记忆库记录数: {count_short}
        长期记忆库记录数: {count_long}
        短期索引数量: {self.short_term_index.ntotal}
        长期索引数量: {self.long_term_index.ntotal}
        最后检索耗时: {self.last_search_time:.2f}ms
        """)
    def clear_memories_short(self):
        """
        清理两天前的记忆：
        1. 将重要性>=3的记忆转移到长期数据库
        2. 删除两天前的所有记忆
        """
        two_days_ago = (datetime.now(self.bj_tz) - timedelta(days=2)).isoformat()
        
        try:
            cursor = self.conn.cursor()
            # 1. 先查询两天前重要性>=3的记忆
            cursor.execute(f"""
                SELECT timestamp, memory_type, content, importance 
                FROM user_{self.user_id}_short_memories
                WHERE importance >= 3 AND timestamp < ?
            """, (two_days_ago,))
            
            # 2. 将这些重要记忆转移到长期数据库
            for row in cursor.fetchall():
                cursor.execute(f"""
                    INSERT INTO user_{self.user_id}_long_memories 
                    (timestamp, memory_type, content, importance) 
                    VALUES (?, ?, ?, ?)
                """, (row[0], row[1], row[2], row[3]))
            
            # 3. 删除短期数据库中两天前的所有记忆
            cursor.execute(f"""
                DELETE FROM user_{self.user_id}_short_memories 
                WHERE timestamp < ?
            """, (two_days_ago,))
            
            self.conn.commit()
            
            # 4. 重建索引
            self.rebuild_all_indexes()
            self.save_indexes()
            
        except sqlite3.Error as e:
            self.logger.error(f"清理记忆失败: {str(e)}")
            raise
    
    def _rebuild_index(self, index_type):
        """全量重建指定索引（short 或 long）"""
        cursor = self.conn.cursor()
        table_name = f"user_{self.user_id}_{index_type}_memories"
        cursor.execute(f"SELECT id, content FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            self.logger.info(f"{index_type} 索引重建：没有找到任何记忆。")
            return

        vectors = []
        id_map = {}
        seen_contents = set()
        
        for i, (db_id, content_json) in enumerate(rows):
            try:
                content_dict = json.loads(content_json)
                text = content_dict.get('content', '')
                content_str = json.dumps(content_dict, sort_keys=True)
                
                # 跳过重复内容
                if content_str in seen_contents:
                    self.logger.warning(f"跳过重复内容: {text[:50]}...")
                    continue
                seen_contents.add(content_str)
                
                vector = self.embedder.encode([text])[0]
                vectors.append(vector)
                id_map[i] = db_id
            except Exception as e:
                self.logger.error(f"重建索引时解析出错: {e}")

        index = self.short_term_index if index_type == 'short' else self.long_term_index
        index.reset()
        if vectors:
            index.add(np.array(vectors).astype('float32'))
            self.id_mapping[index_type] = id_map
            self.logger.info(f"{index_type} 索引重建成功，共添加向量 {len(vectors)} 条。")
            
        # 验证索引完整性
        if index.ntotal != len(id_map):
            self.logger.error(f"索引不一致: 索引数量={index.ntotal}, 映射数量={len(id_map)}")
            raise ValueError("索引重建失败: 索引与映射不一致")

    def rebuild_all_indexes(self):
        """全量重建所有索引"""
        self._rebuild_index('short')
        self._rebuild_index('long')
        self.save_indexes()
        
    

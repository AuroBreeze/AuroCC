from api.memory_store import MemoryStore
from api.Logger_owner import Logger
import sqlite3
import json
import numpy as np
import yaml

class DataMigrator:
    def __init__(self, memory_store):
        self.store = memory_store
        self.logger = Logger()
        
    def migrate_existing_data(self, batch_size=500):
        """迁移短期记忆库中的已有数据"""
        conn = sqlite3.connect(self.store.short_term_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM memories")
        
        vectors = []
        db_ids = []
        for row in cursor:
            # 解析内容
            content = json.loads(row[1])['content']
            # 生成向量
            vector = self.store.embedder.encode(content)
            vectors.append(vector)
            db_ids.append(row[0])
            
            # 批量处理
            if len(vectors) >= batch_size:
                self._batch_add('short', vectors, db_ids)
                vectors.clear()
                db_ids.clear()
        
        # 处理剩余数据
        if vectors:
            self._batch_add('short', vectors, db_ids)
            
    def _batch_add(self, index_type, vectors, db_ids):
        """批量添加索引"""
        vectors = np.array(vectors).astype('float32')
        index = getattr(self.store, f"{index_type}_term_index")
        index.add(vectors)
        
        # 更新ID映射
        start_id = index.ntotal - len(db_ids)
        self.store.id_mapping[index_type].update({
            start_id + i: db_id 
            for i, db_id in enumerate(db_ids)
        })
    
def Main_migrator():
    """主函数"""
    memory = MemoryStore("1732373074")
    migrator = DataMigrator(memory)
    migrator.migrate_existing_data()
    memory.save_indexes()  # 保存索引
    Logger().info("数据迁移完成")
    Logger().info(f"短期索引条目数: {memory.short_term_index.ntotal}")
    
    Logger().info("开始测试搜索...")
    res = memory.search_memories("吃饱了", top_k=5, time_weight=0.3)  # 减少top_k以便观察结果
    for i in res:
        #print(i)
        Logger().info(f"[相关度:{i['score']:.2f}] {i['content']['content']}")
    
    Logger().info("测试搜索完成")
        

if __name__ == "__main__":
    try:
        with open("./_config.yml",r,encoding="utf-8") as f:
            config = yaml.load(f,Loader=yaml.FullLoader)
            user_id = str(config["basic_settings"]["QQbot_admin_account"])
    except FileNotFoundError:
        Logger().error("Config file not found.")
        exit()
    memory = MemoryStore(user_id)
    migrator = DataMigrator(memory)

    # 迁移现有数据（首次部署时运行）
    migrator.migrate_existing_data()
    
    memory.save_indexes()  # 保存索引

    # 验证索引数量
    print(f"短期索引条目数: {memory.short_term_index.ntotal}")

    memory.load_indexes()
    #memory.rebuild_all_indexes()  # 重建索引确保使用新的评分算法
    print("索引重建完成，开始测试搜索...")
    res = memory.search_memories("bug", top_k=30, time_weight=0.3)  # 减少top_k以便观察结果

    for i in res:
        #print(i)
        print(f"[相关度:{i['score']:.2f}] {i['content']['content']}")
    
    # memory.add_memory("test",{"role":"user","content":"test"},importance=3)
    # # memory.load_indexes()
    # mem =memory.search_memories("test",top_k=5,time_weight=0.3)
    # memory.add_memory("test",{"role":"user","content":"bug"},importance=3)
    # mem1 = memory.search_memories("bug",top_k=5,time_weight=0.3)
    # print(mem1)
    # memory.save_indexes()
        

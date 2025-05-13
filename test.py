# Please install OpenAI SDK first: `pip3 install openai`

# sudo xvfb-run -a qq --no-sandbox -q 271065523 
# source .venv/bin/activate

# from openai import OpenAI
# import yaml
# with open("_config.yml", "r",encoding="utf-8") as f:
#     config = yaml.safe_load(f)
# api_key = config["basic_settings"]["API_token"]

# GP_PROMPT = """
# 和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
# 回复时务必使用列表进行回复。
# 示例：
# 我： 你好
# 你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]
# """

# client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
# # sudo xvfb-run -a qq --no-sandbox -q 3552638520 
# # source .venv/bin/activate
# messages=[
#         {"role": "system", "content": GP_PROMPT},
#         {"role": "user", "content": "你好"}
#         ]
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=messages,
#     max_tokens=80,
#     )
# print(response)
# print("消耗的总token数：" + str(response.usage.total_tokens))
# print("生成消耗token数：" + str(response.usage.completion_tokens))
# # 使用标准的缓存token字段
# print("缓存复用token数：" + str(response.usage.prompt_tokens_details.cached_tokens))
# json_response = {
#     "role": "assistant",
#     "content": response.choices[0].message.content
# }
# messages.append(json_response)
# print(f"Messages Round 1: {json_response}")
# print(f"Messages: {messages}")

# from api.memory_store import MemoryStore

# memory = MemoryStore("1732373074")
# res = memory.get_memories()
# print(res)

# 使用 pytz（兼容旧版本）
# import pytz
# from datetime import datetime

# bj_tz = pytz.timezone('Asia/Shanghai')
# now = datetime.now(bj_tz)
# print(now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))

# import json
# import ast
# i = str(['(⊙ˍ⊙) 诶？', '这是新型密码吗', '还是在测试', '我的反应呀~', '不管怎样', '收到指令！', '✧٩(ˊωˋ*)و✧'])
# print(ast.literal_eval(i)[4])

# from api.memory_store import MemoryStore

# memory = MemoryStore("1732373074")
# res = memory.get_memories()
# msg = [1,2,3,4,5,6,8]
# mes = []
# for i in reversed(res):
#     mes.append(i)
# print(msg[-2:])
# print(mes[-5:])

# python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('distiluse-base-multilingual-cased-v2'); model.save('local_model')"
from api.memory_store import MemoryStore
import sqlite3
import json
import numpy as np

memory = MemoryStore("1732373074")
# # memory.rebuild_all_indexes()
# class DataMigrator:
#     def __init__(self, memory_store):
#         self.store = memory_store
        
#     def migrate_existing_data(self, batch_size=500):
#         """迁移短期记忆库中的已有数据"""
#         conn = sqlite3.connect(self.store.short_term_db)
#         cursor = conn.cursor()
#         cursor.execute("SELECT id, content FROM memories")
        
#         vectors = []
#         db_ids = []
#         for row in cursor:
#             # 解析内容
#             content = json.loads(row[1])['content']
#             # 生成向量
#             vector = self.store.embedder.encode(content)
#             vectors.append(vector)
#             db_ids.append(row[0])
            
#             # 批量处理
#             if len(vectors) >= batch_size:
#                 self._batch_add('short', vectors, db_ids)
#                 vectors.clear()
#                 db_ids.clear()
        
#         # 处理剩余数据
#         if vectors:
#             self._batch_add('short', vectors, db_ids)
            
#     def _batch_add(self, index_type, vectors, db_ids):
#         """批量添加索引"""
#         vectors = np.array(vectors).astype('float32')
#         index = getattr(self.store, f"{index_type}_term_index")
#         index.add(vectors)
        
#         # 更新ID映射
#         start_id = index.ntotal - len(db_ids)
#         self.store.id_mapping[index_type].update({
#             start_id + i: db_id 
#             for i, db_id in enumerate(db_ids)
#         })

# memory = MemoryStore("1732373074")
# migrator = DataMigrator(memory)

# # 迁移现有数据（首次部署时运行）
# migrator.migrate_existing_data()

# # 验证索引数量
# print(f"短期索引条目数: {memory.short_term_index.ntotal}")

# # 添加测试记忆
# test_memory = {
#     "role": "system", 
#     "content": "Debug模式已开启，当前版本号v1.2.3"
# }
# memory.add_memory("system", test_memory, importance=3)

memory.load_indexes()
#memory.rebuild_all_indexes()  # 重建索引确保使用新的评分算法
#print("索引重建完成，开始测试搜索...")
res = memory.search_memories("网站", top_k=10, time_weight=0.4)  # 减少top_k以便观察结果

for i in res:
    #print(i)
    print(f"[相关度:{i['score']:.2f}] {i['content']['content']}")

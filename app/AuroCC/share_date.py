message_buffer = {} # 存储聊天的缓存，实现多次输入后合并为一条消息


from api.memory_api.memory_store import MemoryStore
from config import env
memory_store = MemoryStore(env.QQ_ADMIN)

message_buffer = {} # 存储聊天的缓存，实现多次输入后合并为一条消息


from api.memory_store import MemoryStore
from config import dev
memory_store = MemoryStore(dev.QQ_ADMIN)

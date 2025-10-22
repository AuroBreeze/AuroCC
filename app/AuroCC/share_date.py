message_buffer = {} # 存储聊天的缓存，实现多次输入后合并为一条消息


#避免多次实例化导致的错误
from api.memory_api.memory_store import MemoryStore
from api.memory_api.daily_schedule_store import DailyScheduleStore
from config import env
memory_store = MemoryStore(env.QQ_ADMIN)
daily_schedule_store = DailyScheduleStore()

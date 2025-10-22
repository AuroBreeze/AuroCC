message_buffer = {} # 存储聊天的缓存，实现多次输入后合并为一条消息


#避免多次实例化导致的错误
from api.memory_api.memory_store import MemoryStore
from api.memory_api.daily_schedule_store import DailyScheduleStore
from config import env
memory_store = MemoryStore(env.QQ_ADMIN)
daily_schedule_store = DailyScheduleStore()
from app.AuroCC.services.schedule_service import ScheduleService
from app.AuroCC.services.scheduler_service import SchedulerService

# 统一在此处实例化服务，供全局复用
schedule_service = ScheduleService(daily_schedule_store)
scheduler_service = SchedulerService(schedule_service)

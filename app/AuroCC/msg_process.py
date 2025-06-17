from datetime import datetime
import pytz
from app.AuroCC.share_date import memory_store
from api.Logger_owner import Logger
from config import env

class MsgProcess:
    def __init__(self, user_id):
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.memory_store = memory_store
        self.logger = Logger()
        pass

    def Extract_msg_center(self):
        # Extract msg center from memory store
        pass

    def Save_indexs_and_rebuild_indexs(self):
        self.memory_store.rebuild_all_indexes()
        self.memory_store.save_indexes()
        self.logger.info("保存索引成功")
    
    def Clear_memories_short(self):
        self.memory_store.clear_memories_short()
        self.logger.info("清理短期数据库成功")

class MsgProcessScheduler:
    def __init__(self, user_id):
        self.msg_process = MsgProcess(user_id)
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        
    async def Start_scheduler(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 10 and now.minute==10:

            self.msg_process.Clear_memories_short()

    
    async def Save_and_rebuild_indexs(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 10 and now.minute == 30:
            self.msg_process.Save_indexs_and_rebuild_indexs()
            
        
            
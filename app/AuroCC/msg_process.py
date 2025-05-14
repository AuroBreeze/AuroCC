from datetime import datetime
import pytz
from api.memory_store import MemoryStore
from api.Logger_owner import Logger
from app.AuroCC.share_date import judge_message_short_task

class MsgProcess:
    def __init__(self, user_id):
        self.bj_tz = pytz.timezone('Asia/Shanghai')
        self.memory_store = MemoryStore(user_id)
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
        self.bj_tz = pytz.timezone('Asia/Shanghai')
        
    async def Start_scheduler(self):
        now = datetime.now(self.bj_tz)
        
        if (now.hour >= 10 and now.hour<=11) or (now.hour >= 22 and now.hour<= 23):
            if judge_message_short_task == False:
                self.msg_process.Clear_memories_short()
                judge_message_short_task = True # 设置为True,完成任务
        else:
            judge_message_short_task = False # 重置为False,等待下一次任务
    
    async def Save_and_rebuild_indexs(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 10 and now.minute == 30:
            self.msg_process.Save_indexs_and_rebuild_indexs()
            
        
            
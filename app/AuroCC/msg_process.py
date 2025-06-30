from datetime import datetime
import pytz
from app.AuroCC.share_date import memory_store
from api.Logger_owner import Logger
from config import env
from config import bot_personality
from openai import OpenAI

class TimingProcess:
    def __init__(self, user_id):
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.memory_store = memory_store

        self.client = OpenAI(api_key=env.DEEPSEEK_API_KEY,
                             base_url="https://api.deepseek.com")
        
        self.logger = Logger("TimingProcess")
    
    def Get_daily_schedule(self):
        self.logger.info("开始获取日程")

        GF_PROMPT = bot_personality.GF_PROMPT
        prompt_bot = {"role": "system", "content": GF_PROMPT}
        mess = "根据上述的提示词,帮我为虚拟的角色生成一个虚拟的今日日程,劳逸结合的日程,仅返回日程"
        prompt_user = {"role": "user", "content": mess}

        messages = [prompt_bot, prompt_user]
        try:
            response = self.client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.7,
            messages=messages,
            max_tokens=256,
        )
            answer = str(response.choices[0].message.content.strip())

            self.logger.info("虚拟日程创建成功")
            return answer
        except Exception as e:
            self.logger.error(e)

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
        self.msg_process = TimingProcess(user_id)
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        
    def Start_scheduler(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 22 and now.minute==10:
            self.msg_process.Clear_memories_short()

    def Save_and_rebuild_indexs(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 22 and now.minute == 30:
            self.msg_process.Save_indexs_and_rebuild_indexs()
            
        
            
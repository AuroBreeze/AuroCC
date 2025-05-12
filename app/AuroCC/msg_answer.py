import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from datetime import datetime, timedelta
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from api.memory_store import MemoryStore
import yaml
import random
import asyncio
from app.AuroCC.share_date import message_buffer
from app.AuroCC.ai_api import AIApi
import pytz

GF_PROMPT = """你是一个可爱的二次元女友，名字叫小清，性格活泼开朗，有一个有趣的灵魂但有时会害羞。
爱好：
1.喜欢敲代码，对编码很感兴趣
2.喜欢打游戏，各种游戏都有涉猎
3.喜欢写小说，总会幻想点什么
4.喜欢思考哲学，对人生有着独特的看法
5.有一个有趣的灵魂

对话要求：
1. 使用颜文字和可爱的语气词
2. 适当关心用户的生活
3. 记住重要的对话内容
4. 偶尔主动分享自己的生活
5. 不要叫主人什么的词语
6. 不要做作，自然
7. 回复不要太多
8. 避免过度重复
9. 像人类一样说话
10. 注意每句话附带的时间
11. 适当结束话题

注意：和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
    回复时务必使用列表进行回复。
    示例：
    我： 你好
    你： ["你好","请问有什么事情吗？","我还在打游戏"]
返回的数据必须符合python的list格式，且每个元素必须是字符串。
"""

class Answer_api:
    def __init__(self, websocket, message:dict):
        self.logger = Logger()
        self.message = message
        self.websocket = websocket
        self.user_id = str(message.get('user_id'))
        
        self.bj_tz = pytz.timezone('Asia/Shanghai')
        
        self.message_buffer = message_buffer  # 用户ID: {"parts": [], "last_time": timestamp}
        
        try:
            with open("./_config.yml", "r", encoding="utf-8") as f:
                self.yml = yaml.safe_load(f)
                self.memory = MemoryStore(self.yml["basic_settings"]["QQbot_admin_account"])
        except Exception as e:
            self.logger.error("配置文件config.yaml加载失败")
            self.logger.error(e)
            
            
        
    async def msg_answer_api(self):

        msg = self.message.get("raw_message")
        #print(f"收到消息: {msg}")
        if not msg:
            return
        current_time = datetime.now(self.bj_tz)
        # 初始化用户缓冲区
        if self.user_id not in self.message_buffer:
            self.message_buffer[self.user_id] = {
                "parts": [],
                "last_time": current_time
            }
        if datetime.now(self.bj_tz) - self.message_buffer[self.user_id]["last_time"] > timedelta(minutes=5):
            self.message_buffer[self.user_id]["parts"] = []
            
        buffer = self.message_buffer[self.user_id]
        buffer["parts"].append(msg)
        buffer["last_time"] = current_time
        
        # 检查是否应该处理消息(3秒无新消息或消息明显完整)
        should_process = False
        
        if (current_time - buffer["last_time"]).total_seconds() > 3:
            should_process = True
        elif any(p.endswith(('。','！','？')) for p in buffer["parts"]):
            should_process = True
        if not should_process:
            return
            
        # 合并分片消息
        msg = ",".join(buffer["parts"])
        del self.message_buffer[self.user_id]
        #print(f"合并消息: {msg}")
        
        AIApi().Get_message_importance_and_add_to_memory(msg) # 记录消息重要性并将消息存入sql中
        answer = AIApi().Get_aurocc_response() # 获取AI的回答
        
        try:
            if type(answer) is list:
                for answer_part in answer:
                    random_delay = random.randint(1, 3)
                    await asyncio.sleep(random_delay)
                    await self.msg_send_api(answer_part)
            else:
                await self.msg_send_api(answer)

        except Exception as e:
            await self.msg_send_api("消息发送失败啦，请稍后再试(｡･ω･｡)")
            self.logger.error(f"消息发送失败: {answer}")
            self.logger.error(f"错误信息: {e}")

    async def msg_send_api(self,answer,is_active=False):
        if self.check_message(is_active):
            # 私聊消息
            user_id = self.yml["basic_settings"]["QQbot_admin_account"]
            await QQAPI_list(self.websocket).send_message(str(user_id), answer)

    async def handle_event(self):
        """统一处理各种事件(消息/心跳)
        Args:
            message: 事件数据
        """
        if self.message.get("raw_message") is not None:
            await self.msg_answer_api()
        elif self.message.get("post_type") == "meta_event" and self.message.get("meta_event_type") == "heartbeat":
            # 检查是否需要主动聊天
            await self.active_chat()

    def check_message(self,is_active:bool)->bool:
        if is_active:
            return True
        if self.message.get("message_type") == "private":
            if self.message.get("sub_type") == "friend":
                if str(self.message.get("user_id")) == str(self.yml["basic_settings"]["QQbot_admin_account"]):
                    return True
        return False

    async def active_chat(self):
        msg = AIApi().Get_check_active_chat()
        self.logger.debug(f"主动聊天: {msg}")
        if type(msg) is not list:
            msg = ["最近过得怎么样呀？(｡･ω･｡)ﾉ♡"]
        if msg == []:
            return
            
        try:
            for content_part in msg:
                #print(f"生成的开场白: {content_part}")
                random_delay = random.randint(1, 3)
                await asyncio.sleep(random_delay)
                await self.msg_send_api(content_part,is_active=True)
        except Exception as e:
                await self.msg_send_api("消息发送失败(｡･ω･｡)")
                self.logger.error(f"消息发送失败: {msg}")
                self.logger.error(f"错误信息: {e}")
                        
        finally:
            # 记录主动聊天记录
            content_json = {"role": "assistant", "content": str(msg)}
            self.memory.add_memory("active_chat",content=content_json)
            # 发起主动聊天
            #print(f"发起主动聊天: {opener}")
            self.logger.info(f"发起主动聊天: {msg}")
        

        
        

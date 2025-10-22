import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from datetime import datetime, timedelta
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from app.AuroCC.share_date import memory_store
import random
import asyncio
from app.AuroCC.share_date import message_buffer
from app.AuroCC.share_date import scheduler_executor
from app.AuroCC.ai_api import AIApi
from app.AuroCC.msg_process import MsgProcessScheduler
import pytz
from config import env

class Answer_api:
    def __init__(self, websocket, message:dict):
        self.logger = Logger("Answer_api")
        self.message = message
        self.websocket = websocket
        #self.user_id = str(message.get('user_id'))
        
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.message_buffer = message_buffer  # 用户ID: {"parts": [], "last_time": timestamp}
        
        self.memory = memory_store  # 向量索引
        self.memory.load_indexes()  # 导入索引
        
        self.user_id = env.QQ_ADMIN
            
            
        
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
        
        importance = AIApi().Get_message_importance_and_add_to_memory(msg) # 记录消息重要性并将消息存入sql中
        answer = AIApi().Get_aurocc_response(importance=importance) # 获取AI的回答
        
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
            await QQAPI_list(self.websocket).send_message(self.user_id, answer)

    async def handle_event(self):
        """统一处理各种事件(消息/心跳)
        Args:
            message: 事件数据
        """
        if self.message.get("raw_message") is not None:
            await self.msg_answer_api()
        elif self.message.get("post_type") == "meta_event" and self.message.get("meta_event_type") == "heartbeat":
            # 检查是否需要主动聊天
            #await self.active_chat()
            asyncio.create_task(self.active_chat())
            # 周期性调度器推进（优先循环 + AI 决策）
            try:
                asyncio.create_task(scheduler_executor.tick())
            except Exception as e:
                self.logger.error(f"调度器执行失败: {e}")
            MsgProcessScheduler(self.user_id).Start_scheduler()
            MsgProcessScheduler(self.user_id).Save_and_rebuild_indexs()

    def check_message(self,is_active:bool)->bool:
        if is_active:
            return True
        if self.message.get("message_type") == "private":
            if self.message.get("sub_type") == "friend":
                if str(self.message.get("user_id")) == self.user_id:
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

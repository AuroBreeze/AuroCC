import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import aiohttp
import json
from datetime import datetime, timedelta
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from api.memory_store import MemoryStore
import yaml
from openai import OpenAI
import random
import json

GF_PROMPT = """你是一个可爱的二次元女友，名字叫欣欣，性格活泼开朗，有一个有趣的灵魂但有时会害羞。
对话要求：
1. 使用颜文字和可爱的语气词
2. 适当关心用户的生活
3. 记住重要的对话内容
4. 偶尔主动分享自己的生活
5. 不要叫主人什么的词语
6. 不要做作，自然

当前对话上下文：
{context}"""

class Answer_api:
    def __init__(self, websocket, message:dict):
        self.Logger = Logger()
        self.message = message
        #print(self.message)
        self.websocket = websocket
        self.user_id = str(message.get('message_sender_id'))
        self.memory = MemoryStore("1732373074")
        self.message_buffer = {}  # 用户ID: {"parts": [], "last_time": timestamp}
        
        try:
            with open("./_config.yml", "r", encoding="utf-8") as f:
                self.yml = yaml.safe_load(f)
        except:
            self.Logger.error("配置文件config.yaml加载失败")
        
    async def msg_answer_api(self, is_active=False):

        msg = self.message.get("raw_message")
        if not msg:
            return
        current_time = datetime.now()
        print(f"收到消息: {msg}")
        
        # 初始化用户缓冲区
        if self.user_id not in self.message_buffer:
            self.message_buffer[self.user_id] = {
                "parts": [],
                "last_time": current_time
            }
        
        buffer = self.message_buffer[self.user_id]
        buffer["parts"].append(msg)
        buffer["last_time"] = current_time
        
        # 检查是否应该处理消息(3秒无新消息或消息明显完整)
        should_process = False
        if (current_time - buffer["last_time"]).total_seconds() > 3:
            should_process = True
        elif any(p.endswith(('。','！','？')) for p in buffer["parts"]):
            should_process = True
        print(1231231)
        if not should_process:
            return
            
        # 合并分片消息
        msg = " ".join(buffer["parts"])
        del self.message_buffer[self.user_id]
        print(f"合并消息: {msg}")
        
        # 使用AI判断消息重要性(0-5级)
        importance_prompt = f"""请严格按以下规则评估消息重要性：
        消息内容：{msg}
        评估标准：
        0 - 普通日常对话
        1 - 一般重要(个人偏好/习惯)
        2 - 重要(情感表达)
        3 - 很重(承诺/约定) 
        4 - 非常重要(重要个人信息)
        5 - 极其重要(关键承诺/秘密)
        只需返回数字0-5"""
        
        importance = 0
        print(111)
        try:
            client = OpenAI(
                api_key=self.yml["basic_settings"]['API_token'],
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": importance_prompt}],
                temperature=0.1
            )
            importance = int(response.choices[0].message.content.strip())
        except:
            importance = 1
            
        # 检查是否已回复过相同内容
        last_ai_msg = self.memory.get_memories("ai_msg", limit=1)
        if last_ai_msg and msg in last_ai_msg[0].get("content", ""):
            return
            
        try:
            # 保存用户消息(带重要性评估)
            self.memory.add_memory("user_msg", {"content": msg}, importance=importance)
            
            # 获取最近对话上下文 (排除合并消息中的重复内容)
            context = []
            seen_msgs = set()
            memories = self.memory.get_memories(limit=10)
            if not memories:
                self.Logger.error("无法获取记忆数据")
                return
                
            for mem in reversed(memories):
                if not isinstance(mem, dict) or "content" not in mem:
                    continue
                if mem["content"] not in seen_msgs:
                    context.append(mem)
                    seen_msgs.add(mem["content"])
                if len(context) >= 5:
                    break
        except Exception as e:
            self.Logger.error(f"保存消息或获取上下文失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        context = list(reversed(context))
        prompt = GF_PROMPT.format(context=json.dumps(context, ensure_ascii=False))
        

        client = OpenAI(
            api_key=self.yml["basic_settings"]['API_token'],
            base_url="https://api.deepseek.com"
        )
        
        # 获取历史对话记录
        history = []
        for mem in self.memory.get_memories(limit=10):
            if mem.get("memory_type") == "user_msg":
                history.append({"role": "user", "content": mem["content"]})
            elif mem.get("memory_type") == "ai_msg":
                history.append({"role": "assistant", "content": mem["content"]})
        
        # 构建多轮对话消息
        messages = [
            {"role": "system", "content": GF_PROMPT},
            *history[-5:],  # 保留最近5轮对话
            {"role": "user", "content": msg}
        ]
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            answer = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    answer += chunk.choices[0].delta.content
        except Exception as e:
            self.Logger.error(f"AI回复生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
        # 保存完整的对话记录
        try:
            # 保存用户消息(带完整对话上下文)
            self.memory.add_memory("user_msg", {
                "content": msg,
                "full_context": messages
            })
            
            # 保存AI回复(带完整对话上下文)
            full_conversation = messages + [{"role": "assistant", "content": answer}]
            self.memory.add_memory("ai_msg", {
                "content": answer,
                "full_context": full_conversation
            })
            
            await self.msg_send_api(answer)
        except Exception as e:
            self.Logger.error(f"保存对话记录失败: {str(e)}")
            import traceback
            traceback.print_exc()

    async def msg_send_api(self,answer):
        if self.check_message():
            # 私聊消息
            user_id = self.Processed_data['message_sender_id']
            await QQAPI_list(self.websocket).send_message(user_id, answer)

    async def handle_event(self):
        """统一处理各种事件(消息/心跳)
        Args:
            message: 事件数据
        """
        if self.message.get("raw_message") != None:
            print(f"收到消息: {self.message.get('raw_message')}")
            await self.msg_answer_api()
        elif self.message.get("post_type") == "meta_event" and self.message.get("meta_event_type") == "heartbeat":
            # 检查是否需要主动聊天
            await self.check_active_chat()

    def check_message(self)->bool:
        if self.message.get("message_type") == "private":
            if self.message.get("sub_type") == "friend":
                if self.message.get("target_id") == self.yml["basic_settings"]["QQbot_admin_account"]:
                    return True
        return False

    async def check_active_chat(self):
        """检查是否需要主动发起聊天"""
        # 获取最后聊天时间
        last_chat = self.memory.get_memories(limit=1)
        if not last_chat:
            return False
            
        last_time = datetime.fromisoformat(last_chat[0].get("timestamp", ""))
        
        if (datetime.now() - last_time).total_seconds() < random.randint(30*60, 240*60):  # 30分钟内聊过
            return False
            
        # 准备主动聊天判断数据
        context = {
            "last_chat": last_chat[0],
            "memories": self.memory.get_memories(limit=5),
            "current_time": datetime.now().isoformat()
        }
        
        # 使用严格提示词判断
        prompt = f"""请根据以下条件判断是否需要主动发起聊天：
        最后聊天时间：{last_time}
        当前时间：{datetime.now()}
        最近聊天内容：{json.dumps(context['memories'], ensure_ascii=False)}
        
        判断标准：
        1. 用户没有明确表示不想聊天
        2. 最后聊天内容有可延续的话题
        3. 当前不是用户通常的休息时间
        只需返回true或false"""
        
        try:
            client = OpenAI(
                api_key=self.yml["basic_settings"]['API_token'],
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            should_chat = response.choices[0].message.content.strip().lower() == "true"
            if should_chat:
                # 生成个性化开场白
                topic_prompt = f"""基于以下记忆生成一个自然的聊天开场白：
                最近聊天记录：{json.dumps(context['memories'], ensure_ascii=False)}
                
                要求：
                1. 使用可爱的语气和颜文字
                2. 结合之前的聊天内容
                3. 自然不做作
                4. 可以是关心、分享或提问
                只需返回生成的开场白内容"""
                
                try:
                    topic_response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": topic_prompt}],
                        temperature=0.7
                    )
                    opener = topic_response.choices[0].message.content.strip()
                    # 发起主动聊天
                    await self.msg_answer_api(opener, is_active=True)
                except Exception as e:
                    self.Logger.error(f"话题生成失败: {str(e)}")
                    # 使用默认开场白
                    await self.msg_answer_api("最近过得怎么样呀？(｡･ω･｡)ﾉ♡", is_active=True)
        except Exception as e:
            self.Logger.error(f"主动聊天判断失败: {str(e)}")

import aiohttp
import json
from datetime import datetime, timedelta
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from api.memory_store import MemoryStore
import yaml

GF_PROMPT = """你是一个可爱的二次元女友，名字叫欣欣，性格活泼开朗，有一个有趣的灵魂但有时会害羞。
对话要求：
1. 使用颜文字和可爱的语气词
2. 适当关心用户的生活
3. 记住重要的对话内容
4. 偶尔主动分享自己的生活

当前对话上下文：
{context}"""

class Answer_api:
    def __init__(self, websocket, message:dict):
        self.Logger = Logger()
        self.message = message
        self.websocket = websocket
        self.user_id = str(message.get('message_sender_id'))
        self.memory = MemoryStore(self.user_id)
        self.message_buffer = {}  # 用户ID: {"parts": [], "last_time": timestamp}
        
        try:
            with open("_config.yml", "r", encoding="utf-8") as f:
                self.yml = yaml.safe_load(f)
        except:
            self.Logger.error("配置文件config.yaml加载失败")
        
    async def msg_answer_api(self):
        msg = self.Processed_data["message_content"]
        current_time = datetime.now()
        
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
            
        if not should_process:
            return
            
        # 合并分片消息
        msg = " ".join(buffer["parts"])
        del self.message_buffer[self.user_id]
        
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
        try:
            client = OpenAI(
                api_key=self.Processed_data['API_token'],
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
            
        # 保存用户消息(带重要性评估)
        self.memory.add_memory("user_msg", {"content": msg}, importance=importance)
        
        # 获取最近对话上下文 (排除合并消息中的重复内容)
        context = []
        seen_msgs = set()
        for mem in reversed(self.memory.get_memories(limit=10)):
            if mem["content"] not in seen_msgs:
                context.append(mem)
                seen_msgs.add(mem["content"])
            if len(context) >= 5:
                break
        context = list(reversed(context))
        prompt = GF_PROMPT.format(context=json.dumps(context, ensure_ascii=False))
        
        # 调用DeepSeek API
        from openai import OpenAI
        client = OpenAI(
            api_key=self.Processed_data['API_token'],
            base_url="https://api.deepseek.com"
        )
        
        messages = [{"role": "user", "content": prompt + "\n用户说: " + msg}]
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
        
        # 保存AI回复
        self.memory.add_memory("ai_msg", {"content": answer})
        await self.msg_send_api(answer)

    async def msg_send_api(self,answer):
        if self.check_message():
            # 私聊消息
            user_id = self.Processed_data['message_sender_id']
            await QQAPI_list(self.websocket).send_message(user_id, answer)

    def check_message(self)->bool:
        if self.message.get("message_type") == "private":
            if self.message.get("sub_type") == "friend":
                if self.message.get("target_id") == self.yml["basic_settings"]["QQbot_admin_account"]:
                    return True
        return False

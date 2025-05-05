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
        
        try:
            with open("_config.yml", "r", encoding="utf-8") as f:
                self.yml = yaml.safe_load(f)
        except:
            self.Logger.error("配置文件config.yaml加载失败")
        
    async def msg_answer_api(self):
        msg = self.Processed_data["message_content"]
        
        # 保存用户消息
        self.memory.add_memory("user_msg", {"content": msg})
        
        # 获取最近对话上下文
        context = self.memory.get_memories(limit=5)
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
        


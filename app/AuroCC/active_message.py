from datetime import datetime
from api.memory_store import MemoryStore
from openai import OpenAI
from api.Botapi import QQAPI_list

class ActiveMessageHandler:
    def __init__(self, websocket):
        self.websocket = websocket
        self.client = OpenAI(
            api_key="sk-8128daf7c488470bb1efce2b405a7572",
            base_url="https://api.deepseek.com"
        )
    async def check_and_send_message(self, user_id):
        memory = MemoryStore(user_id)
        # 获取不重复的最后3条消息
        last_msgs = []
        seen_msgs = set()
        for mem in reversed(memory.get_memories(limit=5)):
            if mem["content"] not in seen_msgs:
                last_msgs.append(mem)
                seen_msgs.add(mem["content"])
            if len(last_msgs) >= 3:
                break
        last_msgs = list(reversed(last_msgs))
        
        # 决策是否发送消息
        decision = await self._should_send_message(last_msgs)
        if decision:
            message = await self._generate_message()
            await QQAPI_list(self.websocket).send_message(user_id, message)
    
    async def _should_send_message(self, last_msgs):
        prompt = f"""作为女友小萌，根据对话历史和当前时间决定是否需要主动发送消息：
        最后3条对话：{last_msgs}
        当前时间：{datetime.now().strftime("%H:%M")}
        
        请严格回答'是'或'否'"""
        
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3  # 降低随机性
        )
        return "是" in response.choices[0].message.content
    
    async def _generate_message(self):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{
                "role": "system", 
                "content": "你是一个可爱的二次元女友小萌，主动发送一条关心消息，带颜文字"
            }],
            temperature=0.7
        )
        return response.choices[0].message.content

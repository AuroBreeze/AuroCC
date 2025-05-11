from openai import OpenAI
import yaml
from api.Logger_owner import Logger
from api.memory_store import MemoryStore
import json


GP_PROMPT = """你是一个可爱的二次元女友，名字叫小清，性格活泼开朗，有一个有趣的灵魂但有时会害羞。
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
    你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]
务必进行列表的闭合

"""



class AIApi:
    def __init__(self):
        self.logger = Logger()
        try:
            with open("./_config.yml", "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error("Config file not found.")
            exit()
        
        self.client = OpenAI(api_key=self.config["basic_settings"]["API_token"],
                             base_url="https://api.deepseek.com")
        self.memory_store = MemoryStore(self.config["basic_settings"]["QQbot_admin_account"])
    
    def Get_aurocc_response(self) -> list:
        """
        获取AuroCC的回复

        Returns:
            list: _description_
        """
                # 获取最近对话上下文 (确保获取有效数据)
        try:
            memories = self.memory_store.get_memories()
            #print("获取最近对话上下文...")
            #print(memories)
            if not memories:
                # 数据库为空时初始化第一条记录
                self.memory.add_memory("system_msg", {
                    "content": "系统初始化",
                    "importance": 0
                })
                memories = self.memory_store.get_memories()
                if not memories:
                    self.logger.error("无法初始化记忆数据")
                    return
        except:
            self.logger.error("无法获取记忆数据")
            
        
        prompt = {"role":"system","content":GP_PROMPT}
        meaasge = [prompt]
        for memory in reversed(memories):
            meaasge.append(memory)
            
        self.logger.info(f"获取到记忆")
            
        response = self.client.chat.completions.create(
                model="deepseek-chat",
                temperature=0.7,
                messages=meaasge,
                max_tokens=256,
            )
        answer = response.choices[0].message.content.strip()
        
        try:
            answer = json.loads(answer)
        except:
            answer = "我无法回答你的问题(｡･ω･｡)"
            self.logger.error(f"AI回复错误: {answer}")
            self.logger.error(f"无法将AI回复解析为list数据: {answer}")
        finally:
            answer_json = {"role": "assistant", "content": answer}
            self.memory_store.add_memory("ai_msg",content=answer_json)
        return answer
    

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import json
from datetime import datetime, timedelta
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from api.memory_store import MemoryStore
import yaml
from openai import OpenAI
import random
import json
import asyncio

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

注意：和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
    回复时务必使用列表进行回复。
    示例：
    我： 你好
    你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]

"""

class Answer_api:
    def __init__(self, websocket, message:dict):
        self.Logger = Logger()
        self.message = message
        self.websocket = websocket
        self.user_id = str(message.get('message_sender_id'))
        
        self.message_buffer = {}  # 用户ID: {"parts": [], "last_time": timestamp}
        
        try:
            with open("./_config.yml", "r", encoding="utf-8") as f:
                self.yml = yaml.safe_load(f)
                self.memory = MemoryStore(self.yml["basic_settings"]["QQbot_admin_account"])
        except:
            self.Logger.error("配置文件config.yaml加载失败")
            
            
        
    async def msg_answer_api(self, is_active=False):

        msg = self.message.get("raw_message")
        if not msg:
            return
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
        #print(f"合并消息: {msg}")
        
        # 使用AI判断消息重要性(0-5级)
        importance_prompt = f"""
        你是一个可爱的二次元女友，名字叫小清，性格活泼开朗，有一个有趣的灵魂但有时会害羞。
        
        请按以下规则评估消息重要性：
        要记住一些重要的时间和事件，并考虑消息的urgencity(紧急程度)。
        消息内容：{msg}
        评估标准：
        1 - 一般
        2 - 还行
        3 - 重要
        4 - 非常重要
        5 - 极其重要
        只需返回数字1-5"""
        importance = 1
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
        finally:
            msg = msg+"当前时间为："+str(datetime.now())
            content_json = {"role": "user", "content": msg}
            self.memory.add_memory("user_msg",content=content_json,importance=importance)
        # 获取最近对话上下文 (确保获取有效数据)
        try:
            memories = self.memory.get_memories()
            #print("获取最近对话上下文...")
            #print(memories)
            if not memories:
                # 数据库为空时初始化第一条记录
                self.memory.add_memory("system_msg", {
                    "content": "系统初始化",
                    "importance": 0
                })
                memories = self.memory.get_memories()
                if not memories:
                    self.Logger.error("无法初始化记忆数据")
                    return
        except:
            self.Logger.error("无法获取记忆数据")
            
        meaasge = [{"role": "system", "content": GF_PROMPT}]
        
        for memory in reversed(memories):
            meaasge.append(memory)
            self.Logger.info(f"获取到记忆：{memory}")

        #print(meaasge)
        
        # 获取回复
        try:
            client = OpenAI(
                api_key=self.yml["basic_settings"]['API_token'],
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                temperature=0.7,
                messages=meaasge,
            )
            #print(response)
            answer = response.choices[0].message.content.strip()
            print(f"AI回复: {answer}")
        except:
            answer = "我无法回答你的问题(｡･ω･｡)"
            self.Logger.error(f"AI回复错误: {answer}")
        finally:
            answer_json = {"role": "assistant", "content": answer}
            self.memory.add_memory("ai_msg",content=answer_json)
        
        answer = json.loads(answer)
        
        try:
            for answer_part in answer:
                random_delay = random.randint(1, 3)
                await asyncio.sleep(random_delay)
                await self.msg_send_api(answer_part)
        except:
            await self.msg_send_api("消息发送失败(｡･ω･｡)")
            self.Logger.error(f"消息发送失败: {answer}")

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
        if self.message.get("raw_message") != None:
            await self.msg_answer_api()
        elif self.message.get("post_type") == "meta_event" and self.message.get("meta_event_type") == "heartbeat":
            # 检查是否需要主动聊天
            await self.check_active_chat()

    def check_message(self,is_active:bool)->bool:
        if is_active:
            return True
        if self.message.get("message_type") == "private":
            if self.message.get("sub_type") == "friend":
                if str(self.message.get("user_id")) == str(self.yml["basic_settings"]["QQbot_admin_account"]):
                    return True
        return False

    async def check_active_chat(self):
        """检查是否需要主动发起聊天"""
        # 获取最后聊天时间
        last_chat = self.memory.get_memories()
        #print(last_chat)
        if not last_chat:
            return False
        #print(11)
        import re
        timestamp = str(re.findall(r"当前时间为：(.*)", last_chat[0].get("content"))[0])
        #timestamp = last_chat[0].get("timestamp", "")
        print(timestamp)
        if not timestamp:
            return False
            
        last_time = datetime.fromisoformat(timestamp)
        
        if (datetime.now() - last_time).total_seconds() < random.randint(3*60, 5*60*60):  # 30分钟内聊过
            return False

            
        # 准备主动聊天判断数据
        context = {
            "last_chat": last_chat[0],
            "memories": self.memory.get_memories(),
            "current_time": datetime.now().isoformat()
        }
        
        # 使用严格提示词判断
        prompt = f"""请根据以下条件判断是否需要主动发起聊天：
        最后聊天时间：{last_time}
        当前时间：{datetime.now()}
        最近聊天内容：{reversed(context["memories"])}
        
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
                messages=[{"role": "system","content": GF_PROMPT},{"role": "user", "content": prompt}],
                temperature=0.1
            )
            should_chat = response.choices[0].message.content.strip().lower() == "true"
            print(f"主动聊天判断结果: {should_chat}")
            if should_chat:
                # 生成个性化开场白
                topic_prompt = f"""基于以下记忆生成一个自然的聊天开场白：
                最后聊天时间：{last_time}
                当前时间：{datetime.now()}
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
                        messages=[{"role": "user", "content": GF_PROMPT+topic_prompt}],
                        temperature=0.7
                    )
                    opener = topic_response.choices[0].message.content.strip()
                    
                    try:
                        for content_part in json.loads(opener):
                            print(f"生成的开场白: {content_part}")
                            random_delay = random.randint(1, 3)
                            await asyncio.sleep(random_delay)
                            await self.msg_send_api(content_part,is_active=True)
                    except Exception as e:
                        await self.msg_send_api("消息发送失败(｡･ω･｡)")
                        self.Logger.error(f"消息发送失败: {opener}")
                        self.Logger.error(datetime.now())
                        self.Logger.error(f"错误信息: {e}")
                        
                    finally:
                        # 记录主动聊天记录
                        content_json = {"role": "assistant", "content": opener}
                        self.memory.add_memory("active_chat",content=content_json)
                    # 发起主动聊天
                    print(f"发起主动聊天: {opener}")
                except Exception as e:
                    self.Logger.error(f"话题生成失败: {str(e)}")
                    # 使用默认开场白
                    await self.msg_answer_api("最近过得怎么样呀？(｡･ω･｡)ﾉ♡", is_active=True)
        except Exception as e:
            self.Logger.error(f"主动聊天判断失败: {str(e)}")

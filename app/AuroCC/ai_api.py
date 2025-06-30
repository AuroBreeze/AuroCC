from openai import OpenAI
from api.Logger_owner import Logger
from app.AuroCC.share_date import memory_store
from app.AuroCC.mcp_functions import weather_api
import pytz
from datetime import datetime
import random
import ast
from config import env
from config import bot_personality
from api.memory_api import memory_tools


GF_PROMPT = bot_personality.GF_PROMPT
tools = [
    {
        "type": "function",
        "function":
        {
            "name": "weather_api",
            "description": "获取我的天气情况，获取曲阜的天气信息",
            "parameters": {
                "type": "object",
                "properties": {},     # 没有参数
                "required": []        # 没有必须字段
            }
        },
    }
]


class AIApi:
    def __init__(self):
        self.logger = Logger("AIApi")

        self.client = OpenAI(api_key=env.DEEPSEEK_API_KEY,
                             base_url="https://api.deepseek.com")

        self.memory_store = memory_store  # 导入记忆数据库
        self.memory_store.load_indexes()  # 加载索引

        self.bj_tz = pytz.timezone('Asia/Shanghai')

    def Get_aurocc_response(self, importance: int) -> list:
        """
        获取AuroCC的回复,并对消息进行数据库的存储
        Args:
            importance (int): 重要性

        Returns:
            list: _description_
        """
        try:
            self.memory_store.load_indexes()  # 加载索引
            self.logger.info("加载索引成功")
            try:
                qurey_text = str(
                    #self.memory_store.get_memory_short()
                    memory_tools.MemoryStore_Tools().get_memory_short()
                    )  # 获取刚刚发送的对话内容
                if not qurey_text:  # 数据库为空时初始化第一条记录
                    self.memory_store.add_memory("system_msg", {
                        "content": "系统初始化",
                        "importance": 0
                    })
                    qurey_text = str(
                        #self.memory_store.get_memory_short()
                        memory_tools.MemoryStore_Tools().get_memory_short()
                        )
                self.logger.info(f"获取最近对话内容: {qurey_text}")
            except:
                qurey_text = ""
                self.logger.error("获取最近对话内容失败")
        except Exception as e:
            self.logger.error("无法加载索引")
            self.logger.error("错误信息: " + str(e))
            qurey_text = "" # 未定义情况的处理

        # TODO : 要动态调整top_k的数值,数据少的时候,会因为索引过少而搜索不到结果,导致报错
        memories = self.memory_store.search_memories(query_text=qurey_text, top_k=5)  # 获取对话的相关记忆
        self.logger.info(f"搜索记忆结果: {memories[:5]}")
        if memories is not None:
            for memory in memories[:10]:
                self.logger.info(
                    f"搜索记忆: {memory['content']}  相关分数： {memory['score']}")
        else:
            self.logger.error("搜索记忆无")

        memories_short = memory_tools.MemoryStore_Tools().get_memories()  # 加载最近的记忆
        if not memories_short:
            self.logger.error("无最近记忆")
            return []

        prompt = {"role": "system", "content": GF_PROMPT}
        message = [prompt]
        for memory in reversed(memories):
            message.append(memory["content"])
        try:
            for memory in reversed(memories_short[:20]):
                message.append(memory)
        except Exception as e:
            self.logger.error(f"无最近记忆")

        # 将最近用户发送的消息放到列表最下面，以便ai进行回复。
        message.append(ast.literal_eval(qurey_text))
        # print(message)
        self.logger.info("记忆组建完成")

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.7,
            messages=message,
            max_tokens=256,
            tools=tools,
            # functions=Functions_list.return_weather_api(),
            # function_call="auto",
        ) 
        if response.choices[0].finish_reason == "tool_calls":
            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "weather_api":
                message.append(response.choices[0].message) # 加入工具调用消息
                self.logger.info("调用天气API")
                weather_info = weather_api()
                content_json = {
                    "role": "tool",
                    "content": str(weather_info),
                    "tool_call_id": tool_call.id,
                    "name": "weather_api"
                }
                
                message.append(content_json)
                
                # 获取最终响应
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=message,
                    max_tokens=80
                )
        answer = response.choices[0].message.content.strip()
        self.logger.info(f"AI回复: {answer},消息类型：{type(answer)}")

        try:
            answer = ast.literal_eval(answer)
        except Exception as e:
            answer = ["我无法回答你的问题(｡･ω･｡)"]
            self.logger.error(f"AI回复错误: {answer}")
            self.logger.error(f"无法将AI回复解析为list数据: {answer}")
            self.logger.error(f"错误信息: {e}")
        finally:
            answer_json = {"role": "assistant", "content": str(answer)}
            self.memory_store.add_memory(
                "ai_msg", content=answer_json, importance=importance)  # 将AI回复存入数据库
        return answer

    def Get_message_importance_and_add_to_memory(self, msg: str) -> int:
        """
        获取消息的importance

        Args:
            msg (str): 消息

        Returns:
            int: 重要性
        """
        # 使用AI判断消息重要性(0-5级)
        importance_prompt = f"""
        {bot_personality.INFORMATION_ASSESS}
        
        请按以下规则评估消息重要性：
        要记住一些重要的时间和事件，并考虑消息的重要性
        
        消息内容：{msg}
        评估标准：
        1-5:
        1 - 一般重要
        2 - 重要
        3 - 很重
        4 - 非常重要
        5 - 极其重要
        
        只需返回数字1-5"""
        importance = 1
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": GF_PROMPT},
                          {"role": "user", "content": importance_prompt}],
                temperature=0.1
            )
            importance = int(response.choices[0].message.content.strip())
        except:
            importance = 1
        finally:
            msg = msg+"当前时间为："+str(datetime.now(self.bj_tz))
            content_json = {"role": "user", "content": msg}
            self.memory_store.add_memory(
                "user_msg", content=content_json, importance=importance)

        return int(importance)

    def Get_check_active_chat(self) -> list:
        """
        生成主动聊天的内容，并进行返回

        Returns:
            list: 主动聊天的内容
        """
        # 获取最后聊天时间
        last_chat = memory_tools.MemoryStore_Tools().get_memories()
        if not last_chat:
            return []
        timestamp = str(memory_tools.MemoryStore_Tools().get_memory_short_time())

        if not timestamp:
            return []

        last_time = datetime.fromisoformat(timestamp)
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=pytz.utc)  # 假设timestamp是UTC时间

        if (datetime.now(self.bj_tz) - last_time.astimezone(self.bj_tz)).total_seconds() < random.randint(30*60, 7*60*60):  # 30分钟内聊过
            return []

        # 准备主动聊天判断数据
        context = {
            "last_chat": last_chat[0],
            "memories": memory_tools.MemoryStore_Tools().get_memories(),
            "current_time": datetime.now(self.bj_tz).isoformat()
        }
        msg = []
        for message in reversed(context["memories"]):
            msg.append(message)
        # 使用严格提示词判断
        prompt = f"""请根据以下条件判断是否需要主动发起聊天：
        最后聊天时间：{last_time}
        当前时间：{datetime.now(self.bj_tz)}
        最近聊天内容：{msg[-30:]}

        {bot_personality.PROACTIVE_JUDGEMENT}
        
        """
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": GF_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.1
            )
            should_chat = response.choices[0].message.content.strip().lower() == "true"
            # print(f"主动聊天判断结果: {should_chat}")
            self.logger.info(f"主动聊天判断结果: {should_chat}")
            if should_chat:

                self.logger.info(f"话题基于记忆{msg[-5:]}")
                # 生成个性化开场白
                topic_prompt = f"""基于以下记忆生成一个自然的聊天开场白：
                注意：
                    要关注聊天的时间顺序。
                
                最后聊天时间：{last_time}
                当前时间：{datetime.now(self.bj_tz)}
                最近聊天记录：{msg[-30:]}

                {bot_personality.PROACTIVE_INFORMATION}
                
                """

                try:
                    topic_response = self.client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": GF_PROMPT}, {
                            "role": "user", "content": topic_prompt}],
                        temperature=1,
                        # functions=Functions_list.return_weather_api(),
                        # function_call="auto"
                        tools=tools,
                    )
                    opener = topic_response.choices[0].message.content.strip()
                    return ast.literal_eval(opener)

                except Exception as e:
                    self.logger.error(f"话题生成失败: {str(e)}")
                    # 使用默认开场白
                    # await self.msg_answer_api("最近过得怎么样呀？(｡･ω･｡)ﾉ♡", is_active=True)
                    msg = ["最近过得怎么样呀？(｡･ω･｡)ﾉ♡"]
                    return msg

            return []
        except Exception as e:
            self.logger.error(f"主动聊天判断失败: {str(e)}")
        return []

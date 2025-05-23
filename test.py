# Please install OpenAI SDK first: `pip3 install openai`

# sudo xvfb-run -a qq --no-sandbox -q 271065523 
# source .venv/bin/activate

from openai import OpenAI
from app.AuroCC.mcp_functions import weather_api
import yaml
with open("_config.yml", "r",encoding="utf-8") as f:
    config = yaml.safe_load(f)
api_key = config["basic_settings"]["API_token"]

GP_PROMPT = """
和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
回复时务必使用列表进行回复。
示例：
我： 你好
你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]
"""
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
functions = [
        {
            "name": "weather_api",
            "description": "获取我的天气情况，获取曲阜的天气信息",
            "parameters": {
                "type": "object",
                "properties": {},     # 没有参数
                "required": []        # 没有必须字段
            }
            },
]

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
# sudo xvfb-run -a qq --no-sandbox -q 3552638520 
# source .venv/bin/activate
messages=[
        {"role": "system", "content": GP_PROMPT},
        {"role": "user", "content": "今天我这边的天气怎么样？"}
        ]
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    max_tokens=80,
    tools=tools,
    # functions=functions,
    # function_call="auto",
    )
print(response)
messages.append(response.choices[0].message)
if response.choices[0].finish_reason == "tool_calls":
    tool_call = response.choices[0].message.tool_calls[0]
    if tool_call.function.name == "weather_api":
        print("调用了天气API")
        weather_info = weather_api()
        messages.append({
            "role": "tool",
            "content": str(weather_info),
            "tool_call_id": tool_call.id
        })
        
        # 获取最终响应
        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=80
        )
        print(final_response.choices[0].message.content)

print("消耗的总token数：" + str(response.usage.total_tokens))
print("生成消耗token数：" + str(response.usage.completion_tokens))
print("缓存复用token数：" + str(response.usage.prompt_tokens_details.cached_tokens))
print(f"Messages: {messages}")



# from api.memory_store import MemoryStore

# memory = MemoryStore("1732373074")
# res = memory.get_memories()
# print(res)

# 使用 pytz（兼容旧版本）
# import pytz
# from datetime import datetime

# bj_tz = pytz.timezone('Asia/Shanghai')
# now = datetime.now(bj_tz)
# print(now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))

# import json
# import ast
# i = str(['(⊙ˍ⊙) 诶？', '这是新型密码吗', '还是在测试', '我的反应呀~', '不管怎样', '收到指令！', '✧٩(ˊωˋ*)و✧'])
# print(ast.literal_eval(i)[4])

# from api.memory_store import MemoryStore

# msg = [1,2,3,4,5,6,8]
# print(msg[:5])

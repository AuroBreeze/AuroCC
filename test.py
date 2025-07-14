# Please install OpenAI SDK first: `pip3 install openai`

# from openai import OpenAI
# import yaml
# with open("_config.yml", "r",encoding="utf-8") as f:
#     config = yaml.safe_load(f)
# api_key = config["basic_settings"]["API_token"]
#
# GP_PROMPT = """
# 和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
# 回复时务必使用列表进行回复。
# 示例：
# 我： 你好
# 你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]
# """
#
# client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
# # sudo xvfb-run -a qq --no-sandbox -q 3552638520 
# # source .venv/bin/activate
# messages=[
#         {"role": "system", "content": GP_PROMPT},
#         {"role": "user", "content": "你好"}
#         ]
# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=messages,
#     max_tokens=512,
#     )
# print(response)
# print("消耗的总token数：" + str(response.usage.total_tokens))
# print("生成消耗token数：" + str(response.usage.completion_tokens))
# # 使用标准的缓存token字段
# print("缓存复用token数：" + str(response.usage.prompt_tokens_details.cached_tokens))
# json_response = {
#     "role": "assistant",
#     "content": response.choices[0].message.content
# }
# messages.append(json_response)
# print(f"Messages Round 1: {json_response}")
# print(f"Messages: {messages}")

# import json
# import ast
# message = """["呜哇！突然被夸了好害羞(⁄ ⁄•⁄ω⁄•⁄ ⁄)", 
# "能帮到你我也超开心的！", 
# "程序员就是要互相扶持嘛~", 
# "等你解决完这个bug，我们一定要好好庆祝一下！", 
# "给你比个大大的心！❤️(◍•ᴗ•◍)❤️"]"""

# message_list = json.loads(message)
# print(message_list[0])


# # 方法1：使用JSON模块（推荐）
# try:
#     message_list = json.loads(message)#.replace('⁄', '/'))  # 移除特殊字符或替换为标准斜杠 print("JSON解析结果:", message_list[0]) except json.JSONDecodeError as e: print(f"JSON解析失败: {e}") # 方法2：使用AST模块（需严格匹配Python语法） try:
#     # 先处理字符串中的特殊字符
#     processed = message#.replace('⁄', '/')#.replace('❤️', '♡')  
#     message_list = ast.literal_eval(processed)
#     print("AST解析结果:", message_list[0])
# except SyntaxError as e:
#     print(f"AST解析失败: {e}")
#

# print(123)
# if __name__ == "__main__":
#     print(123)


# json_test = {
#     "tes": "q23"
# }

# print(type(json_test),json_test)
# print(json_test["tes"])

# import sqlite3
# from pathlib import Path
# from config import env

# term_db = Path(env.MEMORY_STORE_PATH+f"memories.db")

# conn = sqlite3.connect(term_db)
# cursor = conn.cursor()
# cursor.execute("""CREATE TABLE IF NOT EXISTS memories (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id TEXT,
#     memory_type TEXT,
#     content TEXT,
#     timestamp TEXT,
#     importance REAL
# )""")
# cursor.execute("""CREATE TABLE IF NOT EXISTS memories_short (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                user_id TEXT,
#                 memory_type TEXT,
#                 content TEXT,
#                 timestamp TEXT,
#                 importance REAL,
#                 last_reviewed TEXT,
#                 next_review TEXT
# )""")

# cursor.execute("""CREATE TABLE IF NOT EXISTS memories_long (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id TEXT,
#                 memory_type TEXT,
#                 content TEXT,
#                 timestamp TEXT,
#                 importance REAL,
#                 last_reviewed TEXT,
#                 next_review TEXT
# )""")

# conn.commit()
# conn.close()


    
# from config import bot_personality
# from config import env
# from openai import OpenAI

# client = OpenAI(api_key=env.DEEPSEEK_API_KEY,
#                              base_url="https://api.deepseek.com")
        
# GF_PROMPT = bot_personality.GF_PROMPT
# prompt_bot = {"role": "system", "content": GF_PROMPT}
# mess = "根据上述的提示词,帮我为虚拟的角色生成一个虚拟的今日日程,劳逸结合的日程,仅返回日程"
# prompt_user = {"role": "user", "content": mess}

# messages = [prompt_bot, prompt_user]
# try:
#     response = client.chat.completions.create(
#             model="deepseek-chat",
#             temperature=0.7,
#             messages=messages,
#             max_tokens=256,
#         )
#     answer = str(response.choices[0].message.content.strip())
#     print(answer)

    
# except Exception as e:
#     print(e)

# import websockets
# import asyncio
# try:
#     with websockets.connect("ws://127.0.0.1:3001") as websocket:

#                 # from app.AuroCC.active_message import ActiveMessageHandler
#                 # active_handler = ActiveMessageHandler(websocket)
                
#         for message in websocket:
#             print(message)
                    
#                     # # 如果是心跳消息，检查是否需要主动发送消息
#                     # if isinstance(message, dict) and message.get("type") == "heartbeat":
#                     #     user_id = message.get("user_id")
#                     #     if user_id:
#                     #         await active_handler.check_and_send_message(user_id)

# except Exception as e:
#     pass

# import http.client
# import json

# conn = http.client.HTTPSConnection("")
# payload = json.dumps({
#    "user_id": "1732373074",
#    "message": [
#       {
#          "type": "text",
#          "data": {
#             "text": "napcat"
#          }
#       }
#    ]
# })
# headers = {
#    'Content-Type': 'application/json'
# }
# conn.request("POST", "/send_private_msg", payload, headers)
# res = conn.getresponse()
# data = res.read()
# print(data.decode("utf-8")) 
# msg = "授权群 736038974\nstarttime now\nendtime 30\nuser_id 123123123\nfeatures all"
# #正则表达式提取各个空格后面的数据，，从\n分开从新提取
# # 将消息按行分割
# lines = msg.split('\n')

# # 使用字典存储提取的数据
# data = {}
# for line in msg.split('\n'):
#     # 分割每行的键和值
#     parts = line.split(' ')
#     if len(parts) == 2:  # 确保至少有键和值
#         key = parts[0]
#         value = ' '.join(parts[1:])  # 处理值中可能有空格的情况
#         data[key] = value

# # 提取后的数据
# group_id = data.get('授权群')  # '736038974'
# start_time = data.get('starttime')  # 'now'
# end_time = data.get('endtime')  # '30'
# user_id = data.get('user_id')  # '123123123'
# features = data.get('features')  # 'all'
# print(data)

msg = "123 234 123123"
parts = msg.split(" ")
print(parts)



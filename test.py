# Please install OpenAI SDK first: `pip3 install openai`

# sudo xvfb-run -a qq --no-sandbox -q 271065523 
# source .venv/bin/activate

# from openai import OpenAI
# import yaml
# with open("_config.yml", "r",encoding="utf-8") as f:
#     config = yaml.safe_load(f)
# api_key = config["basic_settings"]["API_token"]

# GP_PROMPT = """
# 和我聊天时，学会适当断句，将长句切短一点，并使用合适的语气词和颜文字。
# 回复时务必使用列表进行回复。
# 示例：
# 我： 你好
# 你： ["你好"，“请问有什么事情吗？”，“我在玩游戏”]
# """

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
#     max_tokens=80,
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

# from api.memory_store import MemoryStore

# memory = MemoryStore("1732373074")
# res = memory.get_memories()
# print(res)

# 使用 pytz（兼容旧版本）
import pytz
from datetime import datetime

bj_tz = pytz.timezone('Asia/Shanghai')
now = datetime.now(bj_tz)
print(now.strftime('%Y-%m-%d %H:%M:%S %Z%z'))

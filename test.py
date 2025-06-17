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


json_test = {
    "tes": "q23"
}

print(type(json_test),json_test)
print(json_test["tes"])



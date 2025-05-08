# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI
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

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
# sudo xvfb-run -a qq --no-sandbox -q 3552638520 
# source .venv/bin/activate
messages=[
        {"role": "system", "content": GP_PROMPT},
        {"role": "user", "content": "你好"}
        ]
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    )

json_response = {
    "role": "assistant",
    "content": response.choices[0].message.content
}
messages.append(json_response)
print(f"Messages Round 1: {json_response}")
print(f"Messages: {messages}")
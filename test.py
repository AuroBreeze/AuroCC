# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI
import yaml
with open("_config.yml", "r",encoding="utf-8") as f:
    config = yaml.safe_load(f)
api_key = config["basic_settings"]["API_token"]

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
# sudo xvfb-run -a qq --no-sandbox -q 3552638520 
# source .venv/bin/activate
messages=[
        {"role": "system", "content": "使用中文与我对话"},
        {"role": "user", "content": "你好"}
        ]
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=False,
)

json_response = {
    "role": "assistant",
    "content": response.choices[0].message.content
}
messages.append(json_response)
print(f"Messages Round 1: {json_response}")

# Round 2
messages.append({"role": "user", "content": "我上一句话说的是什么？"})
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,

)

json_response = {
    "role": "assistant",
    "content": response.choices[0].message.content
}
messages.append(json_response)
print(f"Messages Round 2: {json_response}")

print(f"Messages: {messages}")
message_buffer = {} # 存储聊天的缓存，实现多次输入后合并为一条消息


from api.memory_store import MemoryStore
import yaml
with open('_config.yml', 'r', encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
    user_id = config["basic_settings"]["QQbot_admin_account"]

memory_store = MemoryStore(user_id)

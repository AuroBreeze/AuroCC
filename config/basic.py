# QQ setttings for development environment
QQ_BOT  = '' # QQ Bot ID QQ机器人账号
QQ_ADMIN = '' # QQ Admin ID QQ管理员账号

# ws settings for development environment
WS_URL = "ws://napcat:3001"


# KEY settings for development environment
DEEPSEEK_API_KEY = '' # DeepSeek API Key
AMAP_KEY = '' # 高德API

# memory_store_path settings for development environment
DB_PATH = './store/memory_store/' # Database path 数据库保存位置
MEMORY_STORE_PATH = './store/memory_store/' # Memory store path 聊天记录保存位置
INDEX_STORE_PATH = './store/index/' # FAISS Index store path 向量数据库索引保存位置

# model settings for development environment
# FAISS 向量数据库emmbedding模型    
MODEL_CHOOSE = 'distilbert-base-nli-stsb-mean-tokens' # Model choose 选择模型
MODEL_STORE_PATH = './local_model/' # Model store path 模型保存位置

# timezone  settings for development environment
TIMEZONE = 'Asia/Shanghai' # Timezone 时区

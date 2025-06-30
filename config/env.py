from config.basic import *
from api import Logger_owner

logs = Logger_owner.Logger(log_name='ENV')
current_env = 'dev'

try:
    import yaml
    with open("./config/_config.yml", "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        QQ_ADMIN = QQ_ADMIN if QQ_ADMIN else config['basic_settings']['QQbot_admin_account']
        QQ_BOT = QQ_BOT if QQ_BOT else config['basic_settings']['QQbot_account']
        DEEPSEEK_API_KEY = DEEPSEEK_API_KEY if DEEPSEEK_API_KEY else config['basic_settings']['API_token']
        AMAP_KEY = AMAP_KEY if AMAP_KEY else config['basic_settings']['Weather_api_key']
except Exception as e:
    logs.error(f"Failed to load config from _config.yml with Error: {e}")
    
if current_env == 'dev':
    WS_URL = "ws://127.0.0.1:3001"
elif current_env == 'prod':
    pass


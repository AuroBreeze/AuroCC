from config.basic import *
from api import Logger_owner

logs = Logger_owner.Logger(log_name='ENV').error(2)
current_env = 'dev'

try:
    import yaml
    with open("./config/_config.yml", "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        QQ_ADMIN = config['basic_settings']['QQbot_admin_account']
        QQ_BOT = config['basic_settings']['QQbot_account']
        DEEPSEEK_API_KEY = config['basic_settings']['API_token']
        AMAP_KEY = config['basic_settings']['Weather_api_key']
except Exception as e:
    logs.error(f"Failed to load config from _config.yml  wiht Error: {e}")
    #print(1) 
    
if current_env == 'dev':
    WS_URL = "ws://127.0.0.1:3001"
elif current_env == 'prod':
    pass

print(WS_URL)
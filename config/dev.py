from config.basic import *

try:
    import yaml
    with open("./config/_config.yml", "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        QQ_ADMIN = config['basic_settings']['QQbot_admin_account']
        QQ_BOT = config['basic_settings']['QQbot_account']
        DEEPSEEK_API_KEY = config['basic_settings']['API_token']
        AMAP_KEY = config['basic_settings']['Weather_api_key']
except Exception as e:
    print(e)
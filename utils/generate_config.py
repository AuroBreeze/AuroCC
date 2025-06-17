import yaml
from pathlib import Path

def create_config():
    # 创建配置目录（如果不存在）
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True)
    
    # 定义配置内容
    config = {
        'basic_settings': {
            'QQbot_admin_account': '',  # 管理员账号
            'QQbot_account': '',      # 机器人账号
            'API_token': '',  # API密钥
            'Weather_api_key': ''  # 天气API密钥
        }
    }
    
    # 写入YAML文件
    with open(config_dir / '_config.yml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, allow_unicode=True, sort_keys=False)

if __name__ == '__main__':
    create_config()
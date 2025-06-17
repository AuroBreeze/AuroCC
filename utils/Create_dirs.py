import os
from config import env
from api.Logger_owner import Logger
def create_dirs():
    Logger().info("开始创建必要的目录")
    os.makedirs(env.INDEX_STORE_PATH,exist_ok=True) # 创建索引存储目录
    os.makedirs(env.MEMORY_STORE_PATH,exist_ok=True) # 创建记忆存储目录
    os.makedirs(env.DB_PATH,exist_ok=True) # 创建数据库目录
    os.makedirs(env.MODEL_STORE_PATH,exist_ok=True) # 创建模型存储目录
    Logger().info("创建完成")
    
if __name__ == '__main__':
    create_dirs()
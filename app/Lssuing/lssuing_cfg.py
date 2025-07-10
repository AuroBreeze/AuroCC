from config import env
import os

DB_PATH = "./app/Lssuing/store/db/"# database path 数据库路径
TIMEZONE = 'Asia/Shanghai' # Timezone 时区




os.makedirs(DB_PATH, exist_ok=True) # 创建数据库目录

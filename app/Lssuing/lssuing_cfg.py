from config import env
import os

ADMIN_GROUP_ID = "" # 管理员群组ID,管理员在该群进行权限管理
DB_PATH = "./app/Lssuing/store/db/"# database path 数据库路径
TIMEZONE = 'Asia/Shanghai' # Timezone 时区

os.makedirs(DB_PATH, exist_ok=True) # 创建数据库目录

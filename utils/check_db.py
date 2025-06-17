import sqlite3
import json
from pprint import pprint
from config import env

def show_db_contents(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute("PRAGMA table_info(memories)")
    columns = [col[1] for col in cursor.fetchall()]
    print("表结构:", columns)
    
    # 获取最近10条记录
    cursor.execute("""
        SELECT id, timestamp, memory_type, 
               substr(content, 1, 1000) as content_preview,
               importance
        FROM memories 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    
    print("\n最近10条记录:")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}")
        print(f"时间: {row[1]}")
        print(f"类型: {row[2]}")
        print(f"内容预览: {row[3]}")
        print(f"重要性: {row[4]}")
        print("-" * 50)
    
    conn.close()

if __name__ == "__main__":
    show_db_contents(env.DB_PATH+f"user_memories_short_{env.QQ_ADMIN}.db")

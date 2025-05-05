import sqlite3
import json
from pathlib import Path
from datetime import datetime

class MemoryStore:
    def __init__(self, user_id):
        self.user_id = str(user_id)
        self.db_path = Path("user_memories.db")
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT,
            timestamp DATETIME,
            memory_type TEXT,
            content TEXT,
            PRIMARY KEY (user_id, timestamp, memory_type)
        )
        """)
        conn.commit()
        conn.close()
        
    def add_memory(self, memory_type, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?)",
            (self.user_id, datetime.now().isoformat(), memory_type, json.dumps(content))
        )
        conn.commit()
        conn.close()
        
    def get_memories(self, memory_type=None, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT content FROM memories WHERE user_id = ?"
        params = [self.user_id]
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return results

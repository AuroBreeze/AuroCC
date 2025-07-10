import sqlite3
import os
from . import lssuing_cfg
from api.Logger_owner import Logger
import pytz

class Store_db:
    """
    存储数据库，用来存储授权的群，功能和时间
    """
    def __init__(self):
        self.logger = Logger("Lssuing_store_db")
        self.db_path = lssuing_cfg.DB_PATH
        self.timezone = lssuing_cfg.TIMEZONE
        self.bj_tz = pytz.timezone(self.timezone)
        self.conn = sqlite3.connect(self.db_path)

    def _init_dbs(self):
        cursor = self.conn.cursor()
        # 授权群组，建群组权限表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_permissions (
            group_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,  -- 群组所有者
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 创建群组用户权限表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,  -- 被授权用户
            level INTEGER NOT NULL,  -- 权限级别(1=最高,2=第二级,3=最低)
            parent_id TEXT,         -- 上级授权人
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES group_permissions(group_id) ON DELETE CASCADE,
            UNIQUE(user_id)
        )
        """)
        
        # 群组授权管理 
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_authorizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,  -- 被授权用户
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            features TEXT NOT NULL,  -- JSON格式存储授权功能
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES group_permissions(group_id) ON DELETE CASCADE
        )
        """)
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_group 
        ON user_authorizations(group_id)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_user 
        ON user_authorizations(user_id)
        """)
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_time 
        ON user_authorizations(start_time, end_time)
        """)
        self.conn.commit()


    def create_group_permission(self, group_id: str, owner_id: str, parent_id:str ,level:int = 2)-> bool:
        """
        授权群组,并设置权限(2级权限)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO group_permissions (group_id, owner_id)
        VALUES (?, ?)
        """, (group_id, owner_id))

        cursor.execute("""
        INSERT INTO user_permissions (group_id, user_id, level, parent_id)
        VALUES (?, ?, ?, ?)
        """, (group_id, owner_id, level, parent_id))
        self.conn.commit()
        return True
    
    def add_group_authorization(self, group_id: str, user_id: str,start_time: str, end_time: str, features: str) -> bool:

        """
        群组授权管理，群组详细授权
        """
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO user_authorizations (group_id, user_id, start_time, end_time, features)
        VALUES (?, ?, ?, ?, ?)
        """, (group_id, user_id, start_time, end_time, features))
        return True
    def add_user_authorization(self, group_id: str, user_id: str, level: int, 
                             parent_id: str) -> bool:
        """
        添加用户授权
        """

        # 检查父用户权限等级
        if self.check_user_permission(group_id, parent_id, 2) == False:
            return False

        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO user_permissions (group_id, user_id, level, parent_id)
        VALUES (?, ?, ?, ?)
        """, (group_id, user_id, level, parent_id))
        return True

    def check_user_permission(self, group_id: str, user_id: str, required_level: int):
        """检查用户权限
        权限级别: 
        1=最高权限(系统管理员)
        2=付费用户(群组管理员)
        3=普通用户
        """
        cursor = self.conn.cursor()
        # 检查直接权限
        cursor.execute("""
        SELECT level FROM user_permissions 
        WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        result = cursor.fetchone()
        
        if result and result[0] <= required_level:
            return True
            
        # 检查通过上级继承的权限
        cursor.execute("""
        WITH RECURSIVE permission_tree AS (
            SELECT user_id, level, parent_id
            FROM user_permissions
            WHERE group_id = ? AND user_id = ?
            
            UNION ALL
            
            SELECT u.user_id, u.level, u.parent_id
            FROM user_permissions u
            JOIN permission_tree p ON u.user_id = p.parent_id
            WHERE u.group_id = ?
        )
        SELECT MIN(level) FROM permission_tree
        """, (group_id, user_id, group_id))
        
        min_level = cursor.fetchone()[0]
        return min_level is not None and min_level <= required_level

    def can_manage_user(self, group_id: str, manager_id: str, target_user_id: str):
        """检查用户是否有权限管理目标用户"""
        cursor = self.conn.cursor()
        
        # 获取管理者的权限级别
        cursor.execute("""
        SELECT level FROM user_permissions 
        WHERE group_id = ? AND user_id = ?
        """, (group_id, manager_id))
        manager_level = cursor.fetchone()
        
        if not manager_level:
            return False
            
        manager_level = manager_level[0]
        
        # 获取目标用户的权限级别
        cursor.execute("""
        SELECT level FROM user_permissions 
        WHERE group_id = ? AND user_id = ?
        """, (group_id, target_user_id))
        target_level = cursor.fetchone()
        
        # 如果目标用户不存在或级别更高，不能管理
        if not target_level or manager_level >= target_level[0]:
            return False
            
        # 1级可以管理2级和3级
        # 2级只能管理3级
        return (manager_level == 1 and target_level[0] in [2, 3]) or \
               (manager_level == 2 and target_level[0] == 3)
               
    def remove_user_permission(self, group_id: str, manager_id: str, target_user_id: str):
        """移除用户权限"""
        if not self.can_manage_user(group_id, manager_id, target_user_id):
            self.logger.error(f"用户 {manager_id} 无权移除 {target_user_id} 的权限")
            return False
            
        cursor = self.conn.cursor()
        try:
            # 删除用户权限记录
            cursor.execute("""
            DELETE FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, target_user_id))
            
            # 删除授权记录
            cursor.execute("""
            DELETE FROM user_authorizations 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, target_user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"移除用户权限失败: {e}")
            self.conn.rollback()
            return False

    def get_group_permission(self, group_id: str):
        """获取群组权限信息"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM group_permissions WHERE group_id = ?
        """, (group_id,))
        return cursor.fetchone()

    def list_group_users(self, group_id: str):
        """列出群组所有授权用户"""
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT p.*, a.start_time, a.end_time, a.features 
        FROM user_permissions p
        JOIN user_authorizations a ON p.group_id = a.group_id AND p.user_id = a.user_id
        WHERE p.group_id = ? AND datetime('now') BETWEEN a.start_time AND a.end_time
        """, (group_id,))
        return cursor.fetchall()

    def get_manageable_users(self, group_id: str, manager_id: str):
        """获取用户可以管理的用户列表"""
        if not self.check_user_permission(group_id, manager_id, 2):
            return []
            
        cursor = self.conn.cursor()
        
        # 获取管理者的权限级别
        cursor.execute("""
        SELECT level FROM user_permissions 
        WHERE group_id = ? AND user_id = ?
        """, (group_id, manager_id))
        manager_level = cursor.fetchone()
        
        if not manager_level:
            return []
            
        manager_level = manager_level[0]
        
        # 根据管理者级别查询可管理的用户
        if manager_level == 1:  # 系统管理员可以管理2级和3级
            cursor.execute("""
            SELECT p.user_id, p.level, a.start_time, a.end_time, a.features
            FROM user_permissions p
            JOIN user_authorizations a ON p.group_id = a.group_id AND p.user_id = a.user_id
            WHERE p.group_id = ? AND p.level IN (2, 3)
            """, (group_id,))
        else:  # 群组管理员(2级)只能管理3级
            cursor.execute("""
            SELECT p.user_id, p.level, a.start_time, a.end_time, a.features
            FROM user_permissions p
            JOIN user_authorizations a ON p.group_id = a.group_id AND p.user_id = a.user_id
            WHERE p.group_id = ? AND p.level = 3
            """, (group_id,))
            
        return cursor.fetchall()
        
    def promote_to_group_admin(self, group_id: str, admin_id: str, user_id: str):
        """将用户提升为群组管理员(2级权限)"""
        if not self.check_user_permission(group_id, admin_id, 1):
            self.logger.error(f"用户 {admin_id} 无权提升 {user_id} 为群组管理员")
            return False
            
        cursor = self.conn.cursor()
        try:
            # 更新用户权限级别为2(群组管理员)
            cursor.execute("""
            UPDATE user_permissions 
            SET level = 2, parent_id = ?
            WHERE group_id = ? AND user_id = ?
            """, (admin_id, group_id, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"提升用户权限失败: {e}")
            self.conn.rollback()
            return False

    def __str__(self):
        return "create database for admin and user"

if __name__ == '__main__':
    print(Store_db())

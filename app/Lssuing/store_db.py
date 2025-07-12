import sqlite3
import os
from . import lssuing_cfg
from api.Logger_owner import Logger
import pytz
from datetime import datetime
from config.env import QQ_ADMIN

class Store_db:
    """
    存储数据库，用来存储授权的群，功能和时间
    """
    def __init__(self):
        self.logger = Logger("Lssuing_store_db")
        self.db_path = lssuing_cfg.DB_PATH + "store_db.db"
        self.timezone = lssuing_cfg.TIMEZONE
        self.bj_tz = pytz.timezone(self.timezone)
        self.conn = None

    def _get_connection(self):
        """获取数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            # 启用外键约束
            self.conn.execute("PRAGMA foreign_keys = ON")
            self._init_dbs()
        return self.conn

    def _init_dbs(self):
        cursor = self.conn.cursor()
        # 授权群组，建群组权限表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_permissions (
            group_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,  -- 群组所有者
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id)
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
            UNIQUE (group_id, user_id)  -- 新增组合唯一约束
        )
        """)
        
        # 群组授权管理 
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_information (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL,  -- 被授权用户
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            features TEXT NOT NULL,  -- JSON格式存储授权功能
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES group_permissions(group_id) ON DELETE CASCADE,
            UNIQUE (group_id)
        )
        """)
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_group 
        ON group_information(group_id)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_user 
        ON group_information(user_id)
        """)
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_auth_time 
        ON group_information(start_time, end_time)
        """)

        self.conn.commit()

    def create_group_permission(self, group_id: str, owner_id: str, parent_id:str, level:int = 2) -> bool:
        """
        授权群权限,创建或更新群组权限,并为user用户授予2级权限
        此为1级权限用户功能

        :param group_id: 群组ID
        :param owner_id: 群组所有者ID
        :param parent_id: 上级授权人ID
        :param level: 权限级别(1=最高,2=第二级,3=最低)
        :return: 成功返回True，失败返回False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查群组权限是否存在
            cursor.execute("""
            SELECT COUNT(*) FROM group_permissions 
            WHERE group_id = ?
            """, (group_id,))
            group_exists = cursor.fetchone()[0] > 0
            
            # 创建或更新群组权限
            if group_exists:
                cursor.execute("""
                UPDATE group_permissions 
                SET owner_id = ?
                WHERE group_id = ?
                """, (owner_id, group_id))
            else:
                cursor.execute("""
                INSERT INTO group_permissions (group_id, owner_id)
                VALUES (?, ?)
                """, (group_id, owner_id))
            
            # 创建或更新用户权限
            cursor.execute("""
            INSERT OR REPLACE INTO user_permissions (group_id, user_id, level, parent_id)
            VALUES (?, ?, ?, ?)
            """, (group_id, owner_id, level, parent_id))
            
            conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"创建群组权限失败: {e}")
            return False
    
    def add_group_authorization(self, group_id: str, user_id: str, start_time: str, end_time: str, features: str) -> tuple[bool, str]:
        """
        群组授权管理，群组详细授权（存在则更新，不存在则插入）

        :param group_id: 群组ID
        :param user_id: 被授权用户ID
        :param start_time: 授权开始时间
        :param end_time: 授权结束时间
        :param features: 授权功能JSON格式字符串
        :return: 成功返回True,失败返回False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO group_information (group_id, user_id, start_time, end_time, features)
                VALUES (?, ?, ?, ?, ?)
                """, (group_id, user_id, start_time, end_time, features))
            
            conn.commit()
            return True, f"群组{group_id}授权成功,获权用户{user_id}"
        except Exception as e:
            self.logger.error(f"群组授权失败: {e}")
            return False, f"群组授权失败: {e}"
    def add_user_authorization(self, group_id: str, user_id: str, level: int, 
                             parent_id: str) -> tuple[bool, str]:
        """
        添加用户权限

        :param group_id: 群组ID
        :param user_id: 用户ID
        :param level: 权限级别(1=最高,2=第二级,3=最低)
        :param parent_id: 上级授权人ID
        :return: 成功返回True，失败返回False
        """
        try:
            if level <= 1 or level > 3:
                return False, "权限级别错误"
            # 检查父用户权限等级
            if self.check_user_permission(group_id, parent_id, 2) == False:
                msg = f"用户{user_id}没有2级权限"
                self.logger.warning(f"用户{parent_id}没有2级权限")
                return False,msg

            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 新增：验证权限等级必须比授权者低一级
            cursor.execute("SELECT level FROM user_permissions WHERE group_id=? AND user_id=?", 
                         (group_id, parent_id))
            parent_level = cursor.fetchone()[0]
            if level <= parent_level:  # 新权限等级必须大于父级
                if self.check_user_permission(group_id, parent_id, 1) == False:
                    msg = f"权限等级必须比授权者({parent_level})低一级"
                    self.logger.warning(msg)
                    return False, msg

            cursor.execute("""
            INSERT OR REPLACE INTO user_permissions (group_id, user_id, level, parent_id)
            VALUES (?, ?, ?, ?)
            """, (group_id, user_id, level, parent_id))
            conn.commit()
            return True, f"用户: {user_id} 权限添加成功, 权限等级: {level} ,上级权限人: {parent_id} "
        except Exception as e:
            self.logger.error(f"添加用户授权失败: {e}")
            return False, f"添加用户授权失败: {e}"

    def check_user_permission(self, group_id: str, user_id: str, required_level: int = 3) -> bool:
        """检查用户权限
        权限级别: 
        1=最高权限(系统管理员)
        2=付费用户(群组拥有者)
        3=管理员(群组管理员)

        :param group_id: 群组ID
        :param user_id: 用户ID
        :param required_level: 需要的权限级别
        :return: 用户权限级别，如果用户没有指定权限级别或权限不足，返回None
        """
        try:
            if str(user_id) == str(QQ_ADMIN):  # 管理员权限
                return True
            conn = self._get_connection()
            cursor = conn.cursor()
            # 检查直接权限
            
            cursor.execute("""
            SELECT level FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, user_id))
            result = cursor.fetchone()
            
            if result and result[0] <= required_level:
                return True
            else:
                self.logger.warning(f"用户 {user_id} 在群组 {group_id} 中没有足够的权限,用户的权限等级为 {result[0]}")
                return False
            
        except Exception as e:
            self.logger.error(f"检查用户权限失败: {e}")
            return False
    
    def remove_authorize_group(self,group_id: str) -> tuple[bool, str]:
        """
        删除授权群（先检查是否存在）

        :param group_id: 群号
        :return: (是否成功, 失败原因/None)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 先检查群组是否存在
            cursor.execute("""
            SELECT COUNT(*) FROM group_permissions 
            WHERE group_id = ?
            """, (group_id,))
            
            if cursor.fetchone()[0] == 0:
                self.logger.warning(f"群组 {group_id} 不存在于群组授权中")
                return False, f"群组 {group_id} 不存在于群组授权中"
                
            # 存在则删除
            cursor.execute("""
            DELETE FROM group_permissions
            WHERE group_id = ?
            """, (group_id,))

            conn.commit()
            self.logger.info(f"删除授权群 {group_id} 成功")
            return True, None
        except Exception as e:
            self.logger.error(f"删除授权群 {group_id} 失败: {str(e)}")
            return False, f"删除授权群 {group_id} 失败: {str(e)}"

    def can_manage_user(self, group_id: str, manager_id: str, target_user_id: str) -> bool:
        """
        检查用户是否有权限管理目标用户
         
        :param group_id: 群组ID
        :param manager_id: 管理者ID
        :param target_user_id: 目标用户ID
        :return: 如果用户有权限管理目标用户，返回True，否则返回False
        
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取管理者的权限级别
            cursor.execute("""
            SELECT level FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, manager_id))
            manager_level = cursor.fetchone()
            
            if not manager_level:
                self.logger.debug(f"用户 {manager_id} 不存在")
                return False
                
            manager_level = manager_level[0]
            
            # 获取目标用户的权限级别
            cursor.execute("""
            SELECT level FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, target_user_id))
            target_level = cursor.fetchone()

            # 如果目标用户没有权限，则返回False
            if target_level is None:
                self.logger.debug(f"用户{target_user_id}没有任何权限")
                return False
    
            # 如果目标用户不存在或级别更高，不能管理
            if manager_level >= target_level[0]:
                self.logger.debug(f"执行用户为 {manager_id}，目标用户为 {target_user_id}，执行用户权限级别为 {manager_level}，目标用户权限级别为 {target_level[0]}，不能管理")
                return False
                
            # 1级可以管理2级和3级
            # 2级只能管理3级
            return (manager_level == 1 and target_level[0] in [2, 3]) or \
                   (manager_level == 2 and target_level[0] == 3)
        except Exception as e:
            self.logger.error(f"检查管理权限失败: {e}")
            return False
               
    def remove_user_permission(self, group_id: str, manager_id: str, target_user_id: str):
        """
        移除用户权限
        
        :param group_id: 群组ID
        :param manager_id: 管理者ID
        :param target_user_id: 目标用户ID
        :return: (是否成功, 错误信息)
        """
        try:
            if not self.can_manage_user(group_id, manager_id, target_user_id):
                msg = f"用户 {manager_id} 无权移除 {target_user_id} 的权限"
                self.logger.warning(msg)
                return False, msg
                
            conn = self._get_connection()
            cursor = conn.cursor()
            # 删除用户权限记录
            cursor.execute("""
            DELETE FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, target_user_id))
            
            # 删除授权记录
            cursor.execute("""
            DELETE FROM group_information 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, target_user_id))
            
            conn.commit()
            return True, ""
        except Exception as e:
            self.logger.error(f"移除用户权限失败: {e}")
            return False, f"移除用户权限失败: {e}"
        
    def get_user_ascription(self, user_id: str) -> tuple[list, str]:
        """
        获取用户归属的群组

        :param user_id: 用户ID
        :return: (群组列表, 错误信息)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
            SELECT group_id FROM user_permissions 
            WHERE user_id = ?
            """, (user_id,))
            
            rows = cursor.fetchall()
            if not rows:
                self.logger.debug(f"用户 {user_id} 没有归属的群组")
                return [], f"用户 {user_id} 没有归属的群组"
                
            return [row[0] for row in rows], ""
        except Exception as e:
            self.logger.error(f"获取用户归属的群组失败: {e}")
            return [], f"获取用户归属的群组失败: {e}"

    def get_group_information(self, group_id: str, user_id: str) -> tuple[dict, str]:
        """
        获取群组信息,用户仅能查找属于自己归属的群组
        :return: (权限信息, 错误信息) 如果出错则权限信息为None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取用户归属的群组
            cursor.execute("""
            SELECT group_id FROM user_permissions WHERE user_id = ?
            """, (user_id,))
            group_list = [row[0] for row in cursor.fetchall()]
            
            if group_id not in group_list and user_id != QQ_ADMIN:
                msg = f"用户{user_id}不属于群组{group_id}"
                self.logger.warning(msg)
                return None, msg

            # 使用更高效的查询方式
            cursor.execute("""
            SELECT id, group_id, user_id, start_time, end_time, features, create_time 
            FROM group_information 
            WHERE group_id = ? 
            LIMIT 1
            """, (group_id,))
            
            result = cursor.fetchone()
            if not result:
                self.logger.warning(f"群组{group_id}不存在")
                return None, f"群组{group_id}不存在"
                
            return result, None
        except sqlite3.OperationalError as e:
            self.logger.error(f"数据库操作失败: {e}")
            return None, f"数据库操作失败: {e}"
        except Exception as e:
            self.logger.error(f"获取群组信息失败: {e}")
            return None, f"获取群组信息失败: {e}"

    def list_group_users(self, group_id: str) -> tuple[list, str]:
        """列出群组所有授权用户
        :return: (用户列表, 错误信息) 如果出错则用户列表为空
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.*, a.start_time, a.end_time, a.features 
            FROM user_permissions p
            JOIN group_information a ON p.group_id = a.group_id AND p.user_id = a.user_id
            WHERE p.group_id = ? AND datetime('now') BETWEEN a.start_time AND a.end_time
            """, (group_id,))
            return cursor.fetchall(), ""
        except Exception as e:
            self.logger.error(f"列出群组用户失败: {e}")
            return [], f"列出群组用户失败: {e}"

    def get_manageable_users(self, group_id: str, manager_id: str) -> tuple[list, str]:
        """获取用户可以管理的用户列表
        :return: (用户列表, 错误信息) 如果出错则用户列表为空
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if not self.check_user_permission(group_id, manager_id, 2):
                return [], "权限不足"
            
            # 获取管理者的权限级别
            cursor.execute("""
            SELECT level FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, manager_id))
            manager_level = cursor.fetchone()
            
            if not manager_level:
                return [], "管理者权限不存在"
                
            manager_level = manager_level[0]
            
            # 根据管理者级别查询可管理的用户
            if manager_level == 1:  # 系统管理员可以管理2级和3级
                cursor.execute("""
                SELECT p.user_id, p.level, a.start_time, a.end_time, a.features
                FROM user_permissions p
                JOIN group_information a ON p.group_id = a.group_id AND p.user_id = a.user_id
                WHERE p.group_id = ? AND p.level IN (2, 3)
                """, (group_id,))
            else:  # 群组管理员(2级)只能管理3级
                cursor.execute("""
                SELECT p.user_id, p.level, a.start_time, a.end_time, a.features
                FROM user_permissions p
                JOIN group_information a ON p.group_id = a.group_id AND p.user_id = a.user_id
                WHERE p.group_id = ? AND p.level = 3
                """, (group_id,))
                
            return cursor.fetchall(), ""
        except Exception as e:
            self.logger.error(f"获取可管理用户失败: {e}")
            return [], f"获取可管理用户失败: {e}"
        
    def get_user_permission_level(self, group_id: str, user_id: str) -> tuple[int, str]:
        """
        获取用户在群组中的权限等级
        返回: (权限等级, 错误信息) 如果出错则等级为-1
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
            SELECT level FROM user_permissions 
            WHERE group_id = ? AND user_id = ?
            """, (group_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return 4, f"用户{user_id}在群组{group_id}中没有权限记录"
                
            return result[0], None
        except Exception as e:
            self.logger.error(f"查询用户权限等级失败: {e}")
            return -1, f"查询用户权限等级失败: {e}"
    
    def check_group_permission(self, group_id: str) -> tuple[bool, str]:
        """检查群组是否被授权
        :return: (是否存在, 错误信息)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 先检查是否存在
            cursor.execute("""
            SELECT * FROM group_permissions WHERE group_id = ?
            """, (group_id,))
            result = cursor.fetchone()
            if not result:
                return False, f"群组{group_id}没有任何授权记录"

            # 再检查是否在被授权的时间段
            cursor.execute("""
            SELECT * FROM group_information WHERE group_id = ? AND start_time <= ? AND end_time >= ?
            """, (group_id, datetime.now(self.bj_tz), datetime.now(self.bj_tz)))
            result = cursor.fetchone()
            if not result:
                return False, f"群组{group_id}没有授权,授权时间段为{result[2]}至{result[3]}"
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"查询群组授权状态失败: {e}")
            return False, f"查询群组授权状态失败: {e}"

    def __str__(self):
        return "create database for admin and user"

if __name__ == '__main__':
    print(Store_db())

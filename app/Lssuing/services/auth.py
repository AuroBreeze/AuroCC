from api.Logger_owner import Logger
from ..store_db import Store_db
from .auth_interface import IAuthManager

logger = Logger("Lssuing_auth")

class AuthManager(IAuthManager):
    """权限管理实现类"""
    
    def __init__(self, db: Store_db):
        self.db = db
        
    def check_permission(self, group_id: str, user_id: str, required_level: int) -> bool:
        """
        检查用户权限

        :param group_id: 群组ID
        :param user_id: 用户ID
        :param required_level: 需要的权限级别(1=最高,2=第二级,3=最低)
        :return: 是否有权限
        """
        return self.db.check_user_permission(group_id, user_id, required_level)
        
    def get_permission_level(self, group_id: str, user_id: str) -> tuple[int, str]:
        """
        获取用户权限级别

        :param group_id: 群组ID
        :param user_id: 用户ID
        :return: (权限级别, 错误信息)
        """
        return self.db.get_user_permission_level(group_id, user_id)
        
    def can_manage_user(self, group_id: str, manager_id: str, target_user_id: str) -> bool:
        """
        检查用户是否有权限管理目标用户

        :param group_id: 群组ID
        :param manager_id: 管理者ID
        :param target_user_id: 目标用户ID
        :return: 如果用户有权限管理目标用户，返回True，否则返回False
        """
        return self.db.can_manage_user(group_id, manager_id, target_user_id)
    
    def raise_user_permission(self,group_id: str, user_id: str, parent_id: str,level:int = 3) -> tuple[bool, str]:
        """
        提升用户权限

        :param group_id: 群组ID
        :param user_id: 用户ID
        :param parent_id: 父级用户ID
        :param level: 权限级别(1=最高,2=第二级,3=最低)
        :return: (是否成功提升权限, 错误信息)
        """
        return self.db.add_user_authorization(group_id, user_id, level, parent_id)

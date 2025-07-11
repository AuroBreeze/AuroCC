from abc import ABC, abstractmethod
from typing import Tuple

class IAuthManager(ABC):
    """权限管理接口"""
    
    @abstractmethod
    def check_permission(self, group_id: str, user_id: str, required_level: int) -> bool:
        """检查用户权限"""
        pass
        
    @abstractmethod
    def get_permission_level(self, group_id: str, user_id: str) -> Tuple[int, str]:
        """获取用户权限级别"""
        pass
        
    @abstractmethod 
    def can_manage_user(self, group_id: str, manager_id: str, target_user_id: str) -> bool:
        """检查用户是否有权限管理目标用户"""
        pass
        
    @abstractmethod
    def raise_user_permission(self, group_id: str, user_id: str, parent_id: str, level: int = 3) -> Tuple[bool, str]:
        """提升用户权限"""
        pass
    
    @abstractmethod
    def remove_user_permission(self, group_id: str, manager_id: str, target_user_id: str) -> Tuple[bool, str]:
        """移除用户权限"""
        pass
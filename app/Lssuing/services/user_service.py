from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from config import env
from ..store_db import Store_db
from .auth import AuthManager
from .. import lssuing_cfg

class UserService_API:
    """
    群组用户权限服务层,封装群组用户权限相关功能
    """
    def __init__(self, db: Store_db, websocket, message):
        self.logger = Logger("Lssuing_group_service")
        self.auth = AuthManager(db)
        self.service = UserService(db)
        self.websocket = websocket
        self.message = message
    async def handle_event(self) -> None:
        """
        统一处理各种事件
        """
        if self.message.get("message_type") != "group":
            return
        
        # 改变用户群组权限
        judge,msg = await self.service.raise_user_permission(self.message)
        if msg is not None:
            await self.service.send_group_message(self.websocket, self.message.get("group_id"), msg)

        # 移除用户群组权限
        judge,msg = await self.service.remove_user_permission(self.message)
        if msg is not None:
            await self.service.send_group_message(self.websocket, self.message.get("group_id"), msg)

class UserService:
    """
    用户权限管理
    """
    def __init__(self, db: Store_db):
        self.logger = Logger("Lssuing_user_service")
        self.db = db
        self.auth = AuthManager(db)
    async def raise_user_permission(self,message) -> tuple[bool, str]:
        """改变用户群组权限"""
        msg = str(message.get("raw_message"))
        if not msg.startswith("raise "):
            self.logger.debug("无效的权限提高命令格式")
            return False, None
        
        group_id = message.get("group_id")
        user_id = str(message.get("user_id"))
        
        # 检查用户权限(包含管理员检查)
        if str(user_id) != str(env.QQ_ADMIN):  # 管理员直接通过
            if not self.auth.check_permission(group_id, user_id, 1):
                level, msg = self.auth.get_permission_level(group_id, user_id)
                return False, msg
        
        parts = msg.split(" ")
        target_group_id = parts[1]
        target_user = parts[2]
        level = int(parts[3])

        try:
            judge,msg = self.auth.raise_user_permission(target_group_id,target_user,user_id,level)
            if not judge:
                return False, msg
            else:
                return True,msg
        except Exception as e:
            return False, f"权限提高过程中发生错误: {str(e)}"
    async def remove_user_permission(self,message):
        """取消用户权限"""
        msg = str(message.get("raw_message"))
        if not msg.startswith("remove_user "): # remove_user <target_group_id> <target_user_id>
            self.logger.debug("无效的移除权限命令格式")
            return False, None
        
        group_id = message.get("group_id")
        executor_id = str(message.get("user_id"))
        
        # 检查用户权限(包含管理员检查)
        if str(executor_id) != str(env.QQ_ADMIN):  # 管理员直接通过
            if not self.auth.check_permission(group_id, executor_id, 1):
                level, msg = self.auth.get_permission_level(group_id, executor_id)
                return False, msg
        
        part = msg.split(" ")
        target_group_id = part[1]
        target_user_id = part[2]

        try:
            judge,msg = self.auth.remove_user_permission(target_group_id,executor_id,target_user_id)
            if not judge:
                return False, msg
            else:
                return True,f"已取消群组 {target_group_id} 的用户 {target_user_id} 的权限"
        except Exception as e:
            return False, f"取消权限过程中发生错误: {str(e)}"

    

    async def send_group_message(self, websocket, group_id, message):
        """发送群消息"""
        await QQAPI_list(websocket).send_group_message(group_id, message)

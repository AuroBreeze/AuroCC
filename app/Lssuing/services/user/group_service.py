from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from config import env
from ..sql.store_db import Store_db
from ..auth import AuthManager
from ... import lssuing_cfg

class GroupService_user_API:
    """群组服务层，封装所有admin权限群组相关业务逻辑"""
    def __init__(self,websocket, message):
        self.logger = Logger("Lssuing_group_service")
        self.db = Store_db()
        self.auth = AuthManager(self.db)
        self.service = GroupService(self.db)
        self.websocket = websocket
        self.message = message
    async def handle_event(self) -> None:
        """
        统一处理各种事件
        """
        if self.message.get("message_type") != "group":
            return
                # 获取群组信息
        judge, msg = await self.service.get_group_information(self.message)
        if msg is not None:
            await self.service.send_group_message(self.websocket, self.message.get("group_id"), msg)


class GroupService:
    """2,3级权限，群组服务层，封装所有群组相关业务逻辑"""
    
    def __init__(self, db: Store_db):
        self.logger = Logger("Lssuing_group_service")
        self.db = db
        self.auth = AuthManager(db)
        self.bj_tz = pytz.timezone(lssuing_cfg.TIMEZONE)
    async def get_group_information(self, message) -> tuple[bool, str]:
        """
        获取群授权信息
        """
        msg = str(message.get("raw_message"))
        if not msg.startswith("get_group_information "): # get_group_information <target_group_id>
            self.logger.debug("无效的获取群权限命令格式")
            return False, None
        
        group_id = message.get("group_id")
        user_id = str(message.get("user_id"))
        
        # 检查用户权限
        check_judge, check_msg = self.auth.permission_evaluation_and_assessment(group_id, user_id, 2)
        if not check_judge:
            return False, check_msg
        
        
        part = msg.split(" ")
        target_group_id = part[1]

        info,msg = self.db.get_group_information(target_group_id, user_id)
        if info: # (3, '736038975', '1732373074', '2025-07-11 21:14:11', '2025-07-21 21:14:11', 'all', '2025-07-11 13:14:11')
            return True, f"群组: {target_group_id}\n管理员: {info[2]}\n创建时间: {info[3]}\n到期时间: {info[4]}\n群组权限: {info[5]}"
        else:
            return False, msg

    async def send_group_message(self, websocket, group_id, message):
        """发送群消息"""
        await QQAPI_list(websocket).send_group_message(group_id, message)

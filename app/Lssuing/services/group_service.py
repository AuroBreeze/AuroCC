from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from api.Botapi import QQAPI_list
from config import env
from ..store_db import Store_db
from ..auth import AuthManager
from .. import lssuing_cfg

class GroupService:
    """1级权限，群组服务层，封装所有群组相关业务逻辑"""
    
    def __init__(self, db: Store_db):
        self.logger = Logger("Lssuing_group_service")
        self.db = db
        self.auth = AuthManager(db)
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        
    async def authorize_group(self, message) -> tuple[bool, str]:
        """处理群组授权"""
        msg = str(message.get("raw_message"))
        if not msg.startswith("subscribe_group "):
            self.logger.debug("无效的群组授权格式")
            return False, None
        
        group_id = message.get("group_id")
        user_id = str(message.get("user_id"))
        
        # 检查用户权限
        if not self.auth.check_permission(group_id, user_id, 1):
            level, msg = self.auth.get_permission_level(group_id, user_id)
            return False, f"用户{user_id}权限不足"
        
        # 解析授权数据
        data = {}
        for line in msg.split("\n"):
            parts = line.strip().split(" ")
            if len(parts) != 2:
                continue
            data[parts[0]] = parts[1]
        
        # 验证必要参数
        required_fields = ['subscribe_group', 'starttime', 'endtime', 'user_id', 'features']
        if not all(field in data for field in required_fields):
            return False, "缺少必要的授权参数"
        
        try:
            if data['starttime'] == 'now':
                start_time = datetime.now(tz=self.bj_tz).strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time = data['starttime']
                
            end_time = datetime.now(tz=self.bj_tz) + timedelta(days=int(data['endtime']))
            
            # 创建群组权限
            if not self.db.create_group_permission(data["subscribe_group"], 
                                                 data["user_id"], 
                                                 user_id):
                self.logger.error("群组授权失败")
                return False, "群组授权失败"
            
            # 添加群组授权
            return self.db.add_group_authorization(
                data['subscribe_group'], 
                data['user_id'], 
                start_time, 
                end_time.strftime('%Y-%m-%d %H:%M:%S'), 
                data['features']
            )
            
        except ValueError as e:
            return False, f"参数格式错误: {str(e)}"
        except Exception as e:
            return False, f"授权过程中发生错误: {str(e)}"

    async def remove_authorization(self, message) -> tuple[bool, str]:
        """删除群组授权"""
        msg = str(message.get("raw_message"))
        if not msg.startswith("unsubscribe_group "):
            self.logger.debug("无效的取消授权命令格式")
            return False, None
        
        group_id = message.get("group_id")
        user_id = str(message.get("user_id"))
        
        # 检查用户权限
        if not self.auth.check_permission(group_id, user_id, 1):
            level, msg = self.auth.get_permission_level(group_id, user_id)
            return False, f"用户{user_id}权限不足"
        
        target_group = msg.split(" ")[1]

        try:
            judge,msg = self.db.remove_authorize_group(group_id=target_group)
            if judge:
                return True, msg
            else:
                return False, f"取消群授权失败: {msg}"
        except Exception as e:
            return False, f"取消授权过程中发生错误: {str(e)}"

    async def raise_user_permission(self,message) -> tuple[bool, str]:
        """提升用户权限"""
        msg = str(message.get("raw_message"))
        if not msg.startswith("raise "):
            self.logger.debug("无效的权限提高命令格式")
            return False, None
        
        group_id = message.get("group_id")
        user_id = str(message.get("user_id"))
        
        # 检查用户权限
        if not self.auth.check_permission(group_id, user_id, 1):
            level, msg = self.auth.get_permission_level(group_id, user_id)
            return False, f"用户{user_id}权限不足,用户权限为 {level}"
        
        parts = msg.split(" ")
        target_group_id = parts[1]
        target_user = parts[2]
        level = int(parts[3])

        try:
            judge,msg = self.auth.raise_user_permission(target_group_id,target_user,user_id,level)
            if not judge:
                return False, f"用户{user_id}无权限提升用户{target_user}的权限"
            else:
                return True,msg
        except Exception as e:
            return False, f"权限提高过程中发生错误: {str(e)}"

    async def send_group_message(self, websocket, group_id, message):
        """发送群消息"""
        await QQAPI_list(websocket).send_group_message(group_id, message)

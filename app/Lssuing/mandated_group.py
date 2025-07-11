from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
from .store_db import *
class Mandated_group():
    def __init__(self,websocket, message):
        self.logger = Logger("Lssuing_mandated_group")
        self.bj_tz = pytz.timezone(env.TIMEZONE)

        self.websocket = websocket
        self.message = message
    async def handle_event(self):
        await Authorize_group(self.websocket, self.message).handle_event()

class Authorize_group():
    def __init__(self, websocket, message):
        self.logger = Logger("Lssuing_authorize_group")
        self.bj_tz = pytz.timezone(env.TIMEZONE)

        self.websocket = websocket
        self.message = message

    async def handle_event(self):
        await Manage_group_authorization(self.websocket, self.message).handle_event()

class Manage_group_authorization():
    def __init__(self, websocket, message):
        self.Logger = Logger("Lssuing_manage_group_authorization")
        self.message = message
        self.websocket = websocket

    async def handle_event(self) -> tuple[bool, str]:
        if self.message.get("message_type") != "group":
            return

        judge,msg = await self.authorize_group()
        if msg != None:
            await QQAPI_list(self.websocket).send_group_message(self.message.get("group_id"),msg)
        
        judge,msg = await self.remove_authorize_group()
        if msg != None:
            await QQAPI_list(self.websocket).send_group_message(self.message.get("group_id"),msg)

        judge,msg = await self.raise_user_permission()
        if msg != None:
            await QQAPI_list(self.websocket).send_group_message(self.message.get("group_id"),msg)


    async def authorize_group(self) -> tuple[bool, str]:
        """
        处理消息,对群组授权,并写入数据库
        """
        msg = str(self.message.get("raw_message"))
        if not msg.startswith("subscribe_group "):
            # subscribe_group <group_id>
            # user_id <user_id>
            # starttime now/<start_time>
            # endtime <days>
            # features <features>
            self.Logger.debug("无效的群组授权格式")
            return False, None
        
        group_id = self.message.get("group_id")
        user = str(self.message.get("user_id"))
        
        # 创建单个数据库实例
        db = Store_db()
        
        # 检查用户权限
        if not db.check_user_permission(group_id, user, 1):
            level, msg = db.get_user_permission_level(group_id, user)
            return False, msg
        
        # 解析授权数据
        data = {}
        for line in msg.split("\n"):
            parts = line.strip().split(" ")
            if len(parts) != 2:
                continue
            key = parts[0]
            value = parts[1]
            data[key] = value
        
        # 验证必要参数
        required_fields = ['subscribe_group', 'starttime', 'endtime', 'user_id', 'features']
        if not all(field in data for field in required_fields):
            return False, "缺少必要的授权参数"
        
        # 处理时间参数
        try:
            if data['starttime'] == 'now':
                start_time = datetime.now(tz=pytz.timezone(lssuing_cfg.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time = data['starttime']
                
            end_time = datetime.now(tz=pytz.timezone(lssuing_cfg.TIMEZONE)) + timedelta(days=int(data['endtime']))
            
            judge = db.create_group_permission(data["subscribe_group"],owner_id=data["user_id"],parent_id=user)
            
            if not judge:
                self.logger.error(f"群组授权失败")
                return False,"群组授权失败"
            
            judge, msg = db.add_group_authorization(
                data['subscribe_group'], 
                data['user_id'], 
                start_time, 
                end_time.strftime('%Y-%m-%d %H:%M:%S'), 
                data['features']
            )
            return judge, msg
            
        except ValueError as e:
            return False, f"参数格式错误: {str(e)}"
        except Exception as e:
            return False, f"授权过程中发生错误: {str(e)}"

    async def remove_authorize_group(self) -> tuple[bool, str]:
        """
        删除群组授权
        """
        msg = str(self.message.get("raw_message"))
        if not msg.startswith("unsubscribe_group "): # unsubscribe_group <group_id>
            self.Logger.debug("无效的取消授权命令格式")
            return False, None
        
        group_id = self.message.get("group_id")
        user = str(self.message.get("user_id"))
        
        # 创建单个数据库实例
        db = Store_db()
        
        # 检查用户权限
        if not db.check_user_permission(group_id, user, 1):
            level, msg = db.get_user_permission_level(group_id, user)
            return False, msg
        
        group_id = msg.split(" ")[1]

        judge,msg = db.remove_authorize_group(group_id=group_id)
        if judge:
            return True, f"已取消群组 {group_id} 的授权"
        else:
            return False, f"取消授权失败: {msg}"
    async def raise_user_permission(self) -> tuple[bool, str]:
        """
        提升特定用户权限
        """

        msg = str(self.message.get("raw_message"))
        if not msg.startswith("raise "):  # raise <group_id> <user_id> <level>
            self.Logger.debug("无效的权限提高命令格式")
            return False, None
        
        group_id = self.message.get("group_id")
        user = str(self.message.get("user_id"))
        
        # 创建单个数据库实例
        db = Store_db()
        
        # 检查用户权限
        if not db.check_user_permission(group_id, user, 1):
            level, msg = db.get_user_permission_level(group_id, user)
            return False, msg
        
        part = msg.split(" ")
        group_id = part[1]
        user_id = part[2]
        level = int(part[3])

        judge,msg = db.add_user_authorization(group_id, user_id, level, parent_id=user)
        if judge:
            return True, f"已提升用户 {user_id} 的权限为 {level}"
        else:
            return False, f"提升权限失败: {msg}"



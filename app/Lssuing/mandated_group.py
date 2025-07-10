from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
import json
import asyncio
import time
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
        await self.message_handler()

    async def message_handler(self):
        if self.message.get("message_type") != "group":
            return
        group_id = self.message.get("group_id")

        judge,msg = await self.authorize_group()
        await QQAPI_list(self.websocket).send_group_message(group_id,msg)


    async def authorize_group(self) -> tuple[bool, str]:
        """
        处理消息,对群组授权,并写入数据库
        """
        msg = str(self.message.get("raw_message"))
        if not msg.startswith("授权群 "):
            return False, "无效的授权命令格式"
        
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
        required_fields = ['授权群', 'starttime', 'endtime', 'user_id', 'features']
        if not all(field in data for field in required_fields):
            return False, "缺少必要的授权参数"
        
        # 处理时间参数
        try:
            if data['starttime'] == 'now':
                start_time = datetime.now(tz=pytz.timezone(lssuing_cfg.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time = data['starttime']
                
            end_time = datetime.now(tz=pytz.timezone(lssuing_cfg.TIMEZONE)) + timedelta(days=int(data['endtime']))
            
            judge = db.create_group_permission(data["授权群"],owner_id=data["user_id"],parent_id=user)
            
            if not judge:
                self.logger.error(f"群组授权失败")
                return False,"群组授权失败"
            
            judge, msg = db.add_group_authorization(
                data['授权群'], 
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

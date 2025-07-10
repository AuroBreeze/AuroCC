from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
import json
import asyncio
import time
from . import store_db
class Mandated_group():
    def __init__(self,websocket, message):
        self.logger = Logger("Lssuing_mandated_group")
        self.bj_tz = pytz.timezone(env.TIMEZONE)

        self.websocket = websocket
        self.message = message
    

    async def handle_event(self):
        await self.message_handler()

    async def message_handler(self):
        if self.message.get("message_type") != "group":
            return
        msg = self.message.get("raw_message")
        if msg.startswith("授权群 "):
            group_id = str(msg[3:].strip())
            if store_db.Store_db().create_group_permission(group_id, self.message.get("self_id"),self.message.get("self_id"),2):
                await QQAPI_list(self.websocket).send_group_message(self.message.get("group_id"),f"群{group_id}授权成功")
            else:
                self.logger.error("授权失败")
        if msg.startswith("权限授权 "):
            user_id = str(msg[4:].strip())
            if store_db.Store_db().add_user_authorization("736038975", user_id, 3, "2712065523")[0]:
                await QQAPI_list(self.websocket).send_group_message("736038975",f"用户{user_id}授权成功")
            else:
                await QQAPI_list(self.websocket).send_group_message("736038975",f"用户{user_id}授权失败")
                self.logger.error("授权失败")
            

    async def authorize_group(self, group_id: str, user_id: str, level: int, parent_id: str) -> bool:
        
        store_db.Store_db().create_group_permission(group_id, user_id, level, parent_id)



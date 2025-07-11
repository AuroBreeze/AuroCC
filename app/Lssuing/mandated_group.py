from api.Logger_owner import Logger
from .services.group_service import GroupService
from .store_db import Store_db

class Mandated_group():
    def __init__(self, websocket, message):
        self.logger = Logger("Lssuing_mandated_group")
        self.websocket = websocket
        self.message = message
        self.group_service = GroupService(Store_db())
        
    async def handle_event(self):
        await Authorize_group(self.websocket, self.message, self.group_service).handle_event()

class Authorize_group():
    def __init__(self, websocket, message, group_service):
        self.logger = Logger("Lssuing_authorize_group")
        self.websocket = websocket
        self.message = message
        self.group_service = group_service

    async def handle_event(self):
        await Manage_group_authorization(self.websocket, self.message, self.group_service).handle_event()

class Manage_group_authorization():
    def __init__(self, websocket, message, group_service):
        self.Logger = Logger("Lssuing_manage_group_authorization")
        self.message = message
        self.websocket = websocket
        self.group_service = group_service

    async def handle_event(self) -> tuple[bool, str]:
        if self.message.get("message_type") != "group":
            return

        judge, msg = await self.group_service.authorize_group(self.message)
        if msg is not None:
            await self.group_service.send_group_message(self.websocket, self.message.get("group_id"), msg)
        
        judge, msg = await self.group_service.remove_authorization(self.message)
        if msg is not None:
            await self.group_service.send_group_message(self.websocket, self.message.get("group_id"), msg)

        judge, msg = await self.group_service.raise_user_permission(self.message)
        if msg is not None:
            await self.group_service.send_group_message(self.websocket, self.message.get("group_id"), msg)

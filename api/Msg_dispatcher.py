import json
from app.AuroCC.msg_answer import Answer_api

class Main_dispatcher_and_run:
    """
    插件功能器,功能接口,用于注册
    """
    def __init__(self):
        self.msg_dispatcher = Msg_dispatcher()
    async def handle_event(self, websocket, message): # 消息处理
        await self.msg_dispatcher.handle_event(websocket, message)
        
class Msg_dispatcher: 
    """
    原始消息分发处理器
    """
    async def handle_event(self, websocket, message): # 事件处理器(功能注册处)
        await self.AuroCC(websocket, message)
    async def AuroCC(self, websocket, message):
        try:
            if isinstance(message, str):
                message = json.loads(message)
            await Answer_api(websocket, message).handle_event()
        except Exception as e:
            import traceback
            traceback.print_exc()


import json
from app.AuroCC.msg_answer import Answer_api

class Msg_dispatcher:
    def __init__(self):
        pass
    async def AuroCC_answer(self, websocket, message):
        try:
            if isinstance(message, str):
                message = json.loads(message)
            await Answer_api(websocket, message).handle_event()
        except Exception as e:
            import traceback
            traceback.print_exc()

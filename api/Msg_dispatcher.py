import json
from app.AuroCC.msg_answer import Answer_api
from app.Learn_clock.clock_main import Clock_learn


class Msg_dispatcher:
    def __init__(self):
        pass

    async def AuroCC(self, websocket, message):
        try:
            if isinstance(message, str):
                message = json.loads(message)
            await Answer_api(websocket, message).handle_event()
        except Exception as e:
            import traceback
            traceback.print_exc()
    async def Learn_clock(self, websocket, message):
        try:
            if isinstance(message, str):
                message = json.loads(message)
            await Clock_learn(websocket, message).handle_clock()

        except Exception as e:
            import traceback
            traceback.print_exc()

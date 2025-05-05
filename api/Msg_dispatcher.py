from app import AuroCC

class Msg_dispatcher:
    def __init__(self):
        pass
    async def AuroCC_answer(self, websocket,message):
        await AuroCC.Answer_api(websocket,message).handle_event()
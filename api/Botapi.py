import asyncio
import json
from api.Logger_owner import Logger

class QQAPI_list:
    def __init__(self,websocket):
        self.websocket = websocket
        self.Logger = Logger("BotAPI")
    async def send_message(self,user_id:str,message): #发送私聊消息
        """_summary_
        {
            "user_id": "123456",
            "message": [
                {
                "type": "text",
                "data": {
                    "text": "napcat"
                    }
                }
            ]
        }
        """
        json_message = {
            "action": "send_private_msg",
            "params":{
                "user_id": str(user_id),
                "message": [{
                    "type": "text",
                    "data": {
                        "text": message
                    }
                    }],
            }
        }
        await self.websocket.send(json.dumps(json_message))
        self.Logger.info("发送消息:%s,接收者:%s"%(message,user_id))
        await asyncio.sleep(3)



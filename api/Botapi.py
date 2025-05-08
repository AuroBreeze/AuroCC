import asyncio
import json
from api.Logger_owner import Logger

class QQAPI_list:
    def __init__(self,websocket):
        self.websocket = websocket
        self.Logger = Logger()
    async def send_message(self,user_id,message): #发送私聊消息
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
                "user_id": user_id,
                "message": [{
                    "type": "text",
                    "data": {
                        "text": message
                    }
                    }],
            }
        }
        print(1)

        await self.websocket.send(json.dumps(json_message))
        print(2)
        self.Logger.info("发送消息:%s,接收者:%d"%(message,user_id))
        await asyncio.sleep(3)



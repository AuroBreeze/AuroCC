from random import randint
import aiohttp
import json

from api.Logger_owner import Logger
from api.Botapi import QQAPI_list


class Answer_api:
    def __init__(self,websocket,message ):

        self.Logger = Logger()

        self.message = message
        self.websocket = websocket
    async def msg_answer_api(self):
        msg = self.Processed_data["message_content"]
        url = f"http://api.qingyunke.com/api.php?key=free&appid=0&msg={msg}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.text()
                result_dict = json.loads(result)
                answer = result_dict["content"]
                await self.msg_send_api(answer)

    async def msg_send_api(self,answer):
        if self.Processed_data["message_group"] == None:
            # 私聊消息
            user_id = self.Processed_data['message_sender_id']
            await QQAPI_list(self.websocket).send_message(user_id, answer)
            pass
        else:
            # 群聊消息
            group_id = self.Processed_data['message_group']
            await QQAPI_list(self.websocket).send_group_message(group_id, answer)



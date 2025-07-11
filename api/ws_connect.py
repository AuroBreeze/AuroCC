import websockets
from api.Logger_owner import Logger # 美化日志输出
from api.Share_date import Raw_data # 导入原始数据队列
import asyncio
from api.Msg_dispatcher import Main_dispatcher_and_run
from config.env import WS_URL

class Websocket_receiver:
    def __init__(self):
        self.logger = Logger("Websocket_receiver")  # 实例化日志类
        self.url = WS_URL  # 使用Docker服务名称代替localhost

    async def msg_raw_receiver(self):
        self.logger.info("Starting Websocket Receiver")
        self.logger.info("Websocket URL: %s"% self.url)

        try:
            async with websockets.connect(self.url) as websocket:
                self.logger.info("Websocket Connected: %s" % "QQbot_server_started")

                # from app.AuroCC.active_message import ActiveMessageHandler
                # active_handler = ActiveMessageHandler(websocket)
                
                async for message in websocket:
                    self.logger.info("Message Received: %s" % message)
                    await Raw_data.put(message)
                    await Main_dispatcher_and_run().handle_event(websocket, message)
                    
                    # await Msg_dispatcher().AuroCC_answer(websocket, message)
                    # await Msg_dispatcher().Learn_clock(websocket, message)
                    # await Msg_dispatcher().Lssuing(websocket, message)
                    
                    # # 如果是心跳消息，检查是否需要主动发送消息
                    # if isinstance(message, dict) and message.get("type") == "heartbeat":
                    #     user_id = message.get("user_id")
                    #     if user_id:
                    #         await active_handler.check_and_send_message(user_id)

        except Exception as e:
            self.logger.error("Websocket Receiver Error: %s" % e)
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error("Websocket Connection Closed Error: %s" % e)
        except:
            self.logger.error("Websocket Receiver Error: %s" % "Unknown Error or closed()")

    async def initialize(self):
        await self.msg_raw_receiver()
    async def start_receiver(self):
        await self.msg_raw_receiver()
if __name__ == '__main__':
    asyncio.run(Websocket_receiver().start_receiver())

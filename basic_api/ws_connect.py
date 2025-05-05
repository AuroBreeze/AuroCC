import websockets
from basic_api.Logger_owner import Logger # 美化日志输出
from basic_api.Share_date import Raw_data # 导入原始数据队列
from basic_api.Msg_dispatcher import Msg_dispatcher # 导入消息处理类
import asyncio

class Websocket_receiver:

    def __init__(self):
        self.logger = Logger()  # 实例化日志类
        self.url = "ws://localhost:3001"  # 连接地址

    async def msg_raw_receiver(self):
        self.logger.info("Starting Websocket Receiver")
        self.logger.info("Websocket URL: %s"% self.url)

        try:
            async with websockets.connect(self.url) as websocket:
                self.logger.info("Websocket Connected: %s" % "QQbot_server_started")

                async for message in websocket:
                    self.logger.info("Message Received: %s" % message)
                    await Raw_data.put(message)  # 将接收到的数据,放入原始队列
                    
                    # 开启消息处理任务
                    #Msg_processor_task = asyncio.create_task(Msg_dispatcher(websocket).dispatch_task_main())


        except Exception as e:
            self.logger.error("Websocket Receiver Error: %s" % e)
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error("Websocket Connection Closed Error: %s" % e)
        except:
            self.logger.error("Websocket Receiver Error: %s" % "Unknown Error or closed()")

    async def start_receiver(self):
        await self.msg_raw_receiver()
if __name__ == '__main__':
    asyncio.run(Websocket_receiver().start_receiver())
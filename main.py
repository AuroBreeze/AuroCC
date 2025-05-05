from basic_api.ws_connect import Websocket_receiver
import asyncio

async def main():
    ws_receiver = Websocket_receiver()
    await ws_receiver.start_receiver()

if __name__ == '__main__':
    asyncio.run(main())
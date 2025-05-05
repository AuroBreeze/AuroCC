import asyncio
import json
from basic_api.Logger_owner import Logger

class QQAPI_list:
    def __init__(self,websocket):
        self.websocket = websocket
        self.Logger = Logger()


    async def send_message(self,user_id,message,auto_escape=True): #发送私聊消息
        message = {
            "action": "send_private_msg",
            "params":{
                "user_id": user_id,
                "message": message,
                "auto_escape": auto_escape #消息内容是否作为纯文本发送（即不解析 CQ 码），只在 message 字段是字符串时有效
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("发送消息:%s,接收者:%d"%(message,user_id))
        await asyncio.sleep(3)


    async def send_group_message(self,group_id,message,auto_escape=False): #发送群消息
        message = {
            "action": "send_group_msg",
            "params":{
                "group_id": group_id,
                "message": message,
                "auto_escape": auto_escape #消息内容是否作为纯文本发送（即不解析 CQ 码），只在 message 字段是字符串时有效
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("Sent %s to %d"%(message,group_id))
        await asyncio.sleep(3)

    async def delete_message(self,message_id):#删除消息
        message = {
            "action": "delete_msg",
            "params":{
                "message_id": message_id
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("撤回消息:%d"%(message_id))
        await asyncio.sleep(3)

    async def get_friends_list(self):#获取好友列表 #后期做个人信息统计时再去制作
        message = {
            "action": "get_friend_list"
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("请求好友列表")
        await asyncio.sleep(3)

    async def get_group_list(self,group_id):#获取群列表 #后期做群信息统计时再去制作
        message = {
            "action": "get_group_list"
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("请求群列表")
        await asyncio.sleep(3)

    async def set_friend_list(self,flag,approve=True,remark=""):#处理加好友请求
        message = {
            "action": "set_friend_add_request",
            "params":{
                "flag": flag,
                "approve": approve,
                "remark": remark
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("处理加好友请求")
        await asyncio.sleep(3)

    async def get_group_member_list(self,group_id): #获取群成员列表
        message = {
            "action": "get_group_member_list",
            "params":{
                "group_id": group_id
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("请求群成员列表")
        await asyncio.sleep(3)

    async def set_group_add_request(self,flag,sub_type,approve=True,reason=""):#处理加群请求
        message = {
            "action": "set_group_add_request",
            "params":{
                "flag": flag,
                "sub_type": sub_type,
                "approve": approve,
                "reason": reason
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("处理加群请求")
        await asyncio.sleep(3)

    async def set_group_kick(self,group_id,user_id,reject_add_request=False):#处理群组踢人
        message = {
            "action": "set_group_kick",
            "params":{
                "group_id": group_id,
                "user_id": user_id,
                "reject_add_request": reject_add_request
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("群组:%d,处理踢人:%d" % (group_id,user_id))
        await asyncio.sleep(3)

    async def set_group_ban(self,group_id,user_id,duration=60):#处理群组禁言 禁言单位为秒
        message = {
            "action": "set_group_ban",
            "params":{
                "group_id": group_id,
                "user_id": user_id,
                "duration": duration
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("群组:%d,被处理人:%d,处理禁言:%d秒" % (group_id,user_id,duration))
        await asyncio.sleep(3)

    async def set_group_whole_ban(self,group_id,enable=True):#处理全员禁言
        message = {
            "action": "set_group_whole_ban",
            "params":{
                "group_id": group_id,
                "enable": enable
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("群组:%d,全员禁言设置" % group_id)
        await asyncio.sleep(3)

    async def set_group_name(self,group_id,group_name):#修改群名
        message = {
            "action": "set_group_name",
            "params":{
                "group_id": group_id,
                "group_name": group_name
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("群组:%d,修改群名:%s")
        await asyncio.sleep(3)

    async def upload_group_file(self,group_id,file_path,name):#上传群文件 暂不能使用
        message = {
            "action": "upload_group_file",
            "params":{
                "group_id": group_id,
                "file": file_path,
                "name": name
            }
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("群组:%d,上传文件:%s" % (group_id,file_path))
        await asyncio.sleep(3)

    async def clean_cache(self): #清理缓存

        message = {
            "action": "clean_cache"
        }
        await self.websocket.send(json.dumps(message))
        self.Logger.info("Cleaned cache")
        await asyncio.sleep(3)


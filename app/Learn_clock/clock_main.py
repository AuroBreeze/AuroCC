from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
import json

class Clock_learn():
    def __init__(self, websocket, message:dict):
        self.logger = Logger("Clock_learn")
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.user_id = env.QQ_ADMIN
        self.message = message
        self.websocket = websocket
        self.clock_records = {}  # 存储打卡记录 {user_id: {task_name: {"start": datetime, "end": datetime}}}
    
    async def handle_clock(self):
        if self.message.get("message_type") != "group":
            return
        msg = self.message.get("raw_message", "").strip()
        if not msg:
            return
        
        # 处理开始打卡
        if msg == "开始":
            await self.send_message("打卡格式不正确，请使用：开始 [任务名称]\n例如：开始 单词")
            return
            
        if msg.startswith("开始"):
            if len(msg) <= 3 or not msg[3:].strip():
                await self.send_message("请指定打卡任务名称，格式为：开始 [任务名称]\n例如：开始 单词")
                return
                
            task_name = msg[3:].strip()
            
            if self.user_id not in self.clock_records:
                self.clock_records[self.user_id] = {}
            
            if task_name in self.clock_records[self.user_id]:
                await self.send_message(f"您已经在进行'{task_name}'打卡了，请先结束当前打卡")
            else:
                self.clock_records[self.user_id][task_name] = {
                    "start": datetime.now(self.bj_tz),
                    "end": None
                }
                start_time = datetime.now(self.bj_tz)
                sender_name = self.message.get("sender", {}).get("nickname", "用户")
                await self.send_message(
                    f"⏰ 打卡开始通知\n"
                    f"📌 项目: {task_name}\n"
                    f"🕒 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"👤 发起人: {sender_name}\n"
                    f"🔚 完成后请发送: 结束 {task_name}"
                )
        
        # 处理结束打卡
        elif msg == "结束":
            await self.send_message("打卡格式不正确，请使用：结束 [任务名称]\n例如：结束 单词")
            return
            
        elif msg.startswith("结束"):
            if len(msg) <= 3 or not msg[3:].strip():
                await self.send_message("请指定要结束的打卡任务名称，格式为：结束 [任务名称]\n例如：结束 单词")
                return
                
            task_name = msg[3:].strip()
            
            if self.user_id not in self.clock_records or task_name not in self.clock_records[self.user_id]:
                await self.send_message(f"⚠️ 没有找到'{task_name}'的打卡记录\n请确认任务名称是否正确")
                return
            
            record = self.clock_records[self.user_id][task_name]
            if record["end"]:
                await self.send_message(f"'{task_name}'打卡已经结束过了")
                return
            
            record["end"] = datetime.now(self.bj_tz)
            duration = record["end"] - record["start"]
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await self.send_message(
                f"🎉 '{task_name}'打卡完成！\n"
                f"⏱️ 开始时间: {record['start'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⏱️ 结束时间: {record['end'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⏳ 总时长: {int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
            )
            
            # 计算当天该任务总时长
            total_duration = timedelta()
            for task, records in self.clock_records.get(self.user_id, {}).items():
                if task == task_name and records["end"]:
                    total_duration += records["end"] - records["start"]
            
            total_hours, total_remainder = divmod(total_duration.total_seconds(), 3600)
            total_minutes, total_seconds = divmod(total_remainder, 60)
            
            await self.send_message(
                f"📊 今日'{task_name}'累计时长: "
                f"{int(total_hours)}小时{int(total_minutes)}分钟{int(total_seconds)}秒"
            )
    
    async def send_message(self, message):
        if self.message.get("message_type") == "group":
            await QQAPI_list(self.websocket).send_group_message(
                self.message["group_id"], 
                message
            )
        else:
            await QQAPI_list(self.websocket).send_message(
                self.message["user_id"], 
                message
            )

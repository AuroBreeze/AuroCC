from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
import json
import threading
import schedule
import asyncio
import time

class Clock_learn():
    def __init__(self, websocket, message:dict):
        self.logger = Logger("Clock_learn")
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.user_id = env.QQ_ADMIN
        self.message = message
        self.websocket = websocket
        self.clock_records = {}  # 存储打卡记录 {user_id: {task_name: [{"start": datetime, "end": datetime}]}}
        
        # 启动定时任务线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
    def _run_scheduler(self):
        """运行定时任务"""
        schedule.every().day.at("01:00").do(self._reset_clock_records)
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    def _reset_clock_records(self):
        """每天凌晨1点重置打卡记录"""
        self.logger.info("正在重置所有打卡记录...")
        reset_time = datetime.now(self.bj_tz)
        self.clock_records = {}
        self.logger.info("打卡记录已重置")
        
        # 发送重置通知到所有群组
        if hasattr(self, 'websocket'):
            try:
                group_ids = ["123456", "654321"]  # 这里需要替换为实际的群组ID列表
                for group_id in group_ids:
                    asyncio.run_coroutine_threadsafe(
                        QQAPI_list(self.websocket).send_group_message(
                            group_id,
                            f"⏰ 每日打卡记录已重置\n🕒 重置时间: {reset_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        ),
                        asyncio.get_event_loop()
                    )
            except Exception as e:
                self.logger.error(f"发送重置通知失败: {e}")
    
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
            
            if self.user_id not in self.clock_records:
                self.clock_records[self.user_id] = {}
            if task_name not in self.clock_records[self.user_id]:
                self.clock_records[self.user_id][task_name] = []
            
            # 检查是否有未结束的打卡
            if any(record["end"] is None for record in self.clock_records[self.user_id][task_name]):
                await self.send_message(f"您有未结束的'{task_name}'打卡，请先结束当前打卡")
            else:
                self.clock_records[self.user_id][task_name].append({
                    "start": datetime.now(self.bj_tz),
                    "end": None
                })
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
            
            records = self.clock_records[self.user_id][task_name]
            # 找到最后一个未结束的记录
            active_record = None
            for record in reversed(records):
                if record["end"] is None:
                    active_record = record
                    break
            
            if not active_record:
                await self.send_message(f"没有找到未结束的'{task_name}'打卡记录")
                return
            
            active_record["end"] = datetime.now(self.bj_tz)
            duration = active_record["end"] - active_record["start"]
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await self.send_message(
                f"🎉 '{task_name}'打卡完成！\n"
                f"⏱️ 开始时间: {active_record['start'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⏱️ 结束时间: {active_record['end'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⏳ 本次时长: {int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
            )
            
            # 计算当天该任务总时长和打卡次数
            total_duration = timedelta()
            completed_count = 0
            for record in records:
                if record["end"]:
                    total_duration += record["end"] - record["start"]
                    completed_count += 1
            
            total_hours, total_remainder = divmod(total_duration.total_seconds(), 3600)
            total_minutes, total_seconds = divmod(total_remainder, 60)
            
            await self.send_message(
                f"📊 今日'{task_name}'统计:\n"
                f"📌 打卡次数: {completed_count}次\n"
                f"⏳ 累计时长: {int(total_hours)}小时{int(total_minutes)}分钟{int(total_seconds)}秒"
            )
            
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

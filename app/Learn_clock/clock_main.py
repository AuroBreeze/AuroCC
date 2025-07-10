from datetime import datetime, timedelta
import pytz
from api.Logger_owner import Logger
from config import env
from api.Botapi import QQAPI_list
from . import share_date
import json
import asyncio
import time

class Clock_learn():
    def __init__(self, websocket, message:dict):
        self.logger = Logger("Clock_learn")
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.user_id = None
        self.message = message
        self.websocket = websocket
        self.logger.debug(f"初始化Clock_learn, 当前打卡记录: {json.dumps(share_date.clock_records, default=str)}")
        
    def _check_reset_time(self):
        """检查是否到达重置时间(凌晨1点)"""
        now = datetime.now(self.bj_tz)
        if now.hour == 1 and now.minute == 0:  # 凌晨1点
            self.logger.info("已到达重置时间，正在重置打卡记录...")
            self._reset_clock_records()
            
    def _reset_clock_records(self):
        """每天凌晨1点重置打卡记录"""
        self.logger.info("正在重置所有打卡记录...")
        reset_time = datetime.now(self.bj_tz)
        share_date.clock_records = {}
        self.logger.info("打卡记录已重置")
        self.logger.debug(f"重置后打卡记录: {json.dumps(share_date.clock_records, default=str)}")
        
        # 发送重置通知到所有群组
        if hasattr(self, 'websocket'):
            try:
                group_ids = ["299355209"]  # 这里需要替换为实际的群组ID列表
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

        self.user_id = self.message.get("user_id")
        # 调试日志
        # self.logger.error(f"当前用户ID: {self.user_id}")
        # self.logger.error(f"当前打卡记录: {json.dumps(share_date.clock_records, default=str)}")
        
        # 处理开始打卡
        if msg == "开始":
            await self.send_message("打卡格式不正确，请使用：开始 [任务名称]\n例如：开始 单词")
            return
            
        if msg.startswith("开始 "):
            if len(msg) <= 3 or not msg[3:].strip():
                await self.send_message("请指定打卡任务名称，格式为：开始 [任务名称]\n例如：开始 单词")
                return
                
            task_name = msg[3:].strip()
            
            if self.user_id not in share_date.clock_records:
                share_date.clock_records[self.user_id] = {}
            if task_name not in share_date.clock_records[self.user_id]:
                share_date.clock_records[self.user_id][task_name] = []
            
            # print(share_date.clock_records)
            
            # 检查是否有未结束的打卡
            if any(record["end"] is None for record in share_date.clock_records[self.user_id][task_name]):
                await self.send_message(f"您有未结束的'{task_name}'打卡，请先结束当前打卡")
            else:
                share_date.clock_records[self.user_id][task_name].append({
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
            if self.user_id not in share_date.clock_records:
                await self.send_message("没有找到任何未结束的打卡记录")
                return
                
            # 查找所有未结束的打卡
            active_records = []
            for name, records in share_date.clock_records[self.user_id].items():
                for record in reversed(records):
                    if record["end"] is None:
                        active_records.append(name)
                        break
            
            if not active_records:
                await self.send_message("没有找到任何未结束的打卡记录")
            else:
                task_list = "\n".join([f"- {name}" for name in active_records])
                await self.send_message(
                    f"您有以下未结束的打卡任务:\n"
                    f"{task_list}\n"
                    f"请使用: 结束 [任务名称] 来结束指定打卡"
                )
            return
            
        elif msg == "重置":
            # 只有管理员可以重置
            if not share_date.is_admin(self.user_id):
                await self.send_message("⚠️ 您没有权限执行此操作")
                return
            
            self._reset_clock_records()
            self.send_message("✅ 打卡记录已手动重置")
            return
            
        elif msg.startswith("添加管理员 "):
            if not share_date.is_admin(self.user_id):
                await self.send_message("⚠️ 您没有权限执行此操作")
                return
                
            target_id = msg[5:].strip()
            if not target_id.isdigit():
                await self.send_message("⚠️ 请输入有效的QQ号")
                return
                
            if share_date.add_admin(target_id):
                await self.send_message(f"✅ 已添加 {target_id} 为管理员")
            else:
                await self.send_message(f"⚠️ {target_id} 已经是管理员")
            return
            
        elif msg.startswith("移除管理员 "):
            if not share_date.is_admin(self.user_id):
                await self.send_message("⚠️ 您没有权限执行此操作")
                return
                
            target_id = msg[5:].strip()
            if not target_id.isdigit():
                await self.send_message("⚠️ 请输入有效的QQ号")
                return
                
            if share_date.remove_admin(target_id):
                await self.send_message(f"✅ 已移除 {target_id} 的管理员权限")
            else:
                await self.send_message(f"⚠️ {target_id} 不是管理员")
            return
            
        elif msg == "打卡查询":
            if self.user_id not in share_date.clock_records or not share_date.clock_records[self.user_id]:
                await self.send_message("今天还没有任何打卡记录")
                return
                
            response = "📊 今日打卡统计:\n"
            total_tasks = 0
            total_duration_all = timedelta()
            
            for task_name, records in share_date.clock_records[self.user_id].items():
                total_tasks += 1
                task_duration = timedelta()
                response += f"\n📌 项目: {task_name}\n"
                
                for i, record in enumerate(records, 1):
                    if record["end"]:
                        duration = record["end"] - record["start"]
                        task_duration += duration
                        hours, remainder = divmod(duration.total_seconds(), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        response += (
                            f"  {i}. ⏱️ {record['start'].strftime('%H:%M:%S')} - "
                            f"{record['end'].strftime('%H:%M:%S')} "
                            f"({int(hours)}时{int(minutes)}分{int(seconds)}秒)\n"
                        )
                
                total_hours, total_remainder = divmod(task_duration.total_seconds(), 3600)
                total_minutes, total_seconds = divmod(total_remainder, 60)
                response += (
                    f"  🔢 次数: {len(records)}次\n"
                    f"  ⏳ 累计: {int(total_hours)}时{int(total_minutes)}分{int(total_seconds)}秒\n"
                )
                total_duration_all += task_duration
            
            total_h, total_r = divmod(total_duration_all.total_seconds(), 3600)
            total_m, total_s = divmod(total_r, 60)
            response += (
                f"\n📈 今日总计:\n"
                f"  📌 项目数: {total_tasks}个\n"
                f"  ⏳ 总时长: {int(total_h)}时{int(total_m)}分{int(total_s)}秒"
            )
            
            await self.send_message(response)
            
        elif msg == "帮助" or msg == "菜单":
            help_msg = """📋 打卡系统命令菜单

👤 普通用户命令:
• 开始 [任务名称] - 开始新的打卡任务
  例: 开始 单词
• 结束 [任务名称] - 结束指定打卡任务
  例: 结束 单词
• 打卡查询 - 查看今日打卡统计
• 帮助/菜单 - 显示本帮助菜单

👑 管理员命令:
• 重置 - 手动重置所有打卡记录
• 添加管理员 [QQ号] - 添加管理员
  例: 添加管理员 123456
• 移除管理员 [QQ号] - 移除管理员
  例: 移除管理员 123456

📝 注意:
1. 方括号[]表示必填参数
2. 不要输入方括号本身
3. 命令与参数之间用空格分隔"""
            await self.send_message(help_msg)
            return
            
        elif msg.startswith("结束 "):
            if len(msg) <= 3 or not msg[3:].strip():
                await self.send_message("请指定要结束的打卡任务名称，格式为：结束 [任务名称]\n例如：结束 单词")
                return
                
            task_name = msg[3:].strip()
            
            if self.user_id not in share_date.clock_records:
                await self.send_message(f"⚠️ 没有找到任何打卡记录")
                return
            
            # 如果指定了任务名称
            if task_name:
                if task_name not in share_date.clock_records[self.user_id]:
                    await self.send_message(f"⚠️ 没有找到'{task_name}'的打卡记录\n请确认任务名称是否正确")
                    return
                
                records = share_date.clock_records[self.user_id][task_name]
                # 找到最后一个未结束的记录
                active_record = None
                for record in reversed(records):
                    if record["end"] is None:
                        active_record = record
                        break
                
                if not active_record:
                    await self.send_message(f"没有找到未结束的'{task_name}'打卡记录")
                    return
            else:
                # 如果没有指定任务名称，查找所有未结束的打卡
                active_records = []
                for name, records in share_date.clock_records[self.user_id].items():
                    for record in reversed(records):
                        if record["end"] is None:
                            active_records.append((name, record))
                            break
                
                if not active_records:
                    await self.send_message("没有找到任何未结束的打卡记录")
                    return
                elif len(active_records) > 1:
                    task_list = "\n".join([f"- {name}" for name, _ in active_records])
                    await self.send_message(
                        f"⚠️ 您有多个未结束的打卡任务，请指定要结束的任务名称:\n"
                        f"{task_list}\n"
                        f"格式: 结束 [任务名称]"
                    )
                    return
                
                task_name, active_record = active_records[0]
            
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

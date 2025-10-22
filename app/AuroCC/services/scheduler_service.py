from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime
import pytz
from config import env
from app.AuroCC.services.schedule_service import ScheduleService


class SchedulerService:
    """
    OS风格的简单优先级调度器：
    - 依据当前时间匹配今日日程中的当前活动
    - 与聊天优先级(默认3)进行比较，形成调度上下文
    - 提供可注入到提示词的上下文字符串
    """

    def __init__(self, schedule_service: Optional[ScheduleService] = None) -> None:
        self.tz = pytz.timezone(env.TIMEZONE)
        self.schedule_service = schedule_service or ScheduleService()

    def _today_str(self) -> str:
        return datetime.now(self.tz).strftime("%Y-%m-%d")

    @staticmethod
    def _hm_to_minutes(hm: str) -> Optional[int]:
        try:
            h, m = hm.split(":")
            return int(h) * 60 + int(m)
        except Exception:
            return None

    def _is_now_in_range(self, start_hm: str, end_hm: str, now_min: int) -> bool:
        """
        处理跨天：若 end < start，则认为跨午夜，区间为 [start, 1440) U [0, end]
        """
        s = self._hm_to_minutes(start_hm)
        e = self._hm_to_minutes(end_hm)
        if s is None or e is None:
            return False
        if s <= e:
            return s <= now_min < e
        # wrap around midnight
        return now_min >= s or now_min < e

    def get_current_item(self) -> Optional[Dict[str, Any]]:
        today = self._today_str()
        items = self.schedule_service.list_items_by_date(today)
        # list_items_by_date 返回列: id, idx, start, end, state, importance, done, completed_at, schedule_id
        now = datetime.now(self.tz)
        now_min = now.hour * 60 + now.minute
        for row in items:
            # 返回列: id, idx, start, end, state, importance, progress, done, completed_at, schedule_id
            _id, _idx, start, end, state, importance, progress, done, _completed_at, _schedule_id = row
            if self._is_now_in_range(str(start), str(end), now_min):
                return {
                    "id": _id,
                    "idx": _idx,
                    "start": start,
                    "end": end,
                    "state": state,
                    "importance": int(importance or 3),
                    "progress": int(progress or 0),
                    "done": bool(done),
                    "schedule_id": _schedule_id,
                }
        return None

    def get_priority_decision(self, chat_priority: int = 3) -> Dict[str, Any]:
        cur = self.get_current_item()
        if not cur:
            return {
                "chat_priority": chat_priority,
                "active_item": None,
                "active_priority": None,
                "decision": "chat_allowed",
                "reason": "no_active_item",
            }
        active_pri = int(cur.get("importance", 3))
        decision = "chat_allowed"
        # 简单优先级：活动优先级高至少1级时，建议温和聊天或与活动相关的陪伴
        if active_pri >= chat_priority + 1:
            decision = "chat_soft"  # 放低打扰性，更多辅助/提醒
        return {
            "chat_priority": chat_priority,
            "active_item": cur,
            "active_priority": active_pri,
            "decision": decision,
            "reason": "compare_active_vs_chat",
        }

    def build_prompt_context(self, chat_priority: int = 3) -> str:
        now = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M")
        pd = self.get_priority_decision(chat_priority)
        if not pd.get("active_item"):
            return (
                f"[调度器]\n当前时间：{now}\n"
                f"今日当前无匹配日程项。聊天优先级={chat_priority}，决策=chat_allowed。\n"
            )
        it = pd["active_item"]
        return (
            f"[调度器]\n当前时间：{now}\n"
            f"她当前日程：{it['start']}-{it['end']} {it['state']}\n"
            f"对象活动重要性={it['importance']}；聊天优先级={chat_priority}；决策={pd['decision']}。\n"
            f"策略：若决策为chat_soft，请以不打断对象当前活动为前提，给出贴合对象活动的关怀、提醒或轻量互动。\n"
        )

    def build_action_prompt_context(self, action_name: str, action_priority: int) -> str:
        """
        将一个拟进行的动作（如“主动聊天”）以任务形式纳入调度比较，返回可注入提示词的上下文。
        """
        now = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M")
        pd = self.get_priority_decision(chat_priority=action_priority)
        if not pd.get("active_item"):
            return (
                f"[调度器]\n当前时间：{now}\n"
                f"计划动作：{action_name}(priority={action_priority})\n"
                f"今日无匹配日程项，决策=allow_action。\n"
                f"策略：可直接执行计划动作。\n"
            )
        it = pd["active_item"]
        decision = pd.get("decision")
        tip = (
            "以不打断当前活动为前提进行轻量执行"
            if decision == "chat_soft" else "可正常执行计划动作"
        )
        return (
            f"[调度器]\n当前时间：{now}\n"
            f"对象当前日程：{it['start']}-{it['end']} {it['state']} (importance={it['importance']})\n"
            f"计划动作：{action_name}(priority={action_priority})；决策={decision}。\n"
            f"策略：{tip}。\n"
        )

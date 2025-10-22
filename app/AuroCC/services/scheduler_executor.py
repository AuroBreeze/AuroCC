from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import pytz

from config import env
from app.AuroCC.services.schedule_service import ScheduleService
from app.AuroCC.services.scheduler_service import SchedulerService
from api.Logger_owner import Logger


class SchedulerExecutor:
    """
    优先循环调度器（Priority Round-Robin）：
    - 周期性 tick()
    - 按 importance 分组，从高到低轮转选择可执行项（未完成、progress<100）
    - 对当前时间命中的项优先推进；若无命中，则在可执行列表中按优先级轮询推进
    - 推进行为：更新 progress（示例：+10），当 progress>=100 标记完成
    - 可选：在推进时调用 AIApi 生成拟人化提醒/陪伴语
    """

    def __init__(self, schedule_service: ScheduleService, scheduler_service: SchedulerService) -> None:
        self.logger = Logger("SchedulerExecutor")
        self.tz = pytz.timezone(env.TIMEZONE)
        self.schedule_service = schedule_service
        self.scheduler_service = scheduler_service
        # 简单的内存去重控制节流
        self._last_tick = None
        self._rr_cursor_by_pri: Dict[int, int] = {}  # priority -> cursor idx

    def _today_str(self) -> str:
        return datetime.now(self.tz).strftime('%Y-%m-%d')

    async def tick(self) -> None:
        # 节流：每30秒最多执行一次
        now = datetime.now(self.tz)
        if self._last_tick and (now - self._last_tick).total_seconds() < 30:
            return
        self._last_tick = now

        # 1) 优先当前时间命中的项
        cur = self.scheduler_service.get_current_item()
        if cur and not cur.get("done") and int(cur.get("progress", 0)) < 100:
            await self._advance_item(cur)
            return

        # 2) 无命中则执行“优先循环”
        items = self.schedule_service.store.list_runnable_items_by_date(self._today_str())
        if not items:
            return
        # items: (id, idx, start, end, state, importance, progress, done, completed_at, schedule_id)
        # 分组
        by_pri: Dict[int, List[tuple]] = {}
        for row in items:
            pri = int(row[5] or 2)
            by_pri.setdefault(pri, []).append(row)
        for pri in sorted(by_pri.keys(), reverse=True):
            lst = by_pri[pri]
            if not lst:
                continue
            cursor = self._rr_cursor_by_pri.get(pri, 0) % len(lst)
            chosen = lst[cursor]
            self._rr_cursor_by_pri[pri] = (cursor + 1) % len(lst)
            await self._advance_row_tuple(chosen)
            break  # 本轮推进一个即可

    async def _advance_row_tuple(self, row: tuple) -> None:
        _id, _idx, start, end, state, importance, progress, done, _completed_at, _schedule_id = row
        if done:
            return
        await self._advance_item({
            "id": _id,
            "idx": _idx,
            "start": start,
            "end": end,
            "state": state,
            "importance": int(importance or 2),
            "progress": int(progress or 0),
            "done": bool(done),
            "schedule_id": _schedule_id,
        })

    async def _advance_item(self, item: Dict[str, Any]) -> None:
        try:
            # 由AI决定推进幅度与事件
            from app.AuroCC.ai_api import AIApi  # 延迟导入以避免循环依赖
            ai = AIApi()
            decision = ai.Decide_schedule_progress(item)
            delta = int(decision.get("progress_delta", 10))
            event = str(decision.get("event", "none")).lower()
            msg = decision.get("assistant_message", "")

            base = int(item.get("progress", 0))
            target = base
            if event == "complete":
                target = 100
            else:
                target = max(0, min(100, base + delta))

            self.schedule_service.store.update_item_progress(int(item["id"]), target)

            decision_ctx = self.scheduler_service.build_action_prompt_context("日程推进", action_priority=int(item.get("importance", 2)))
            self.logger.info(
                f"AI推进[{item['state']} idx={item['idx']}] 进度 {base}% -> {target}% (delta={delta}, event={event})\n{decision_ctx}"
            )
            if msg:
                self.logger.info(f"AI建议话术：{msg}")
        except Exception as e:
            self.logger.error(f"推进日程失败: {e}")

from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any
from api.memory_api.daily_schedule_store import DailyScheduleStore


class ScheduleService:
    def __init__(self, store: Optional[DailyScheduleStore] = None) -> None:
        self.store = store or DailyScheduleStore()

    # 原子化创建：主表 + 子项 + 统计
    def create_today_schedule(self, content_json: str, items: List[Dict[str, Any]]) -> int:
        return self.store.create_schedule_with_items(content_json, items)

    # 标记完成/撤销，并同步主表统计
    def mark_item_done(self, item_id: int, done: bool = True) -> Tuple[int, int, float]:
        self.store.mark_item_done(item_id, done)
        # 获取该 item 所属 schedule_id
        rows = self.store.conn.execute(
            "SELECT schedule_id FROM daily_schedule_item WHERE id = ?",
            (int(item_id),),
        ).fetchone()
        if not rows:
            return 0, 0, 0.0
        schedule_id = rows[0]
        return self.store.recalc_schedule_stats(int(schedule_id))

    # 只读：获取指定日期统计
    def get_stats_by_date(self, date_str: str) -> Tuple[int, int, float]:
        return self.store.get_stats_by_date(date_str)

    # 只读：列出某日子项
    def list_items_by_date(self, date_str: str):
        return self.store.list_items_by_date(date_str)

    # 删除整个日程（含子项）
    def delete_schedule(self, schedule_id: int) -> int:
        return self.store.delete_schedule(schedule_id)

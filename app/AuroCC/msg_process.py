from datetime import datetime
import json
import pytz
from app.AuroCC.share_date import memory_store,daily_schedule_store
from api.Logger_owner import Logger
from config import env
from config import bot_personality
from openai import OpenAI
from api.memory_api import memory_tools
import re
from app.AuroCC.services.schedule_service import ScheduleService


class TimingProcess:
    def __init__(self, user_id):
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        self.memory_store = memory_store
        self.schedule_store = daily_schedule_store
        self.schedule_service = ScheduleService(self.schedule_store)

        self.client = OpenAI(api_key=env.DEEPSEEK_API_KEY,
                             base_url="https://api.deepseek.com")
        
        self.logger = Logger("TimingProcess")
        try:
            self.Ensure_today_schedule()
        except Exception as e:
            self.logger.error(e)
    
    def Get_daily_schedule(self):
        self.logger.info("开始获取日程")

        # 上下文：长期/短期记忆与历史日程
        try:
            mt = memory_tools.MemoryStore_Tools()
            memories_dict = mt.get_memories()
            short_mems = memories_dict.get("short", [])
            long_mems = memories_dict.get("long", [])
        except Exception as e:
            self.logger.error(f"获取记忆失败: {e}")
            short_mems, long_mems = [], []

        # 取部分样本以控制长度
        SHORT_MAX, LONG_MAX = 10, 8
        short_ctx = short_mems[:SHORT_MAX]
        long_ctx = long_mems[:LONG_MAX]

        # 历史日程（最近3条）
        try:
            history_rows = self.schedule_store.get_all_daily_schedule(limit=3)
            history_schedules = []
            for rid, content, status, *rest in history_rows:
                try:
                    history_schedules.append({
                        "id": rid,
                        "content": json.loads(content),
                        "status": status
                    })
                except Exception:
                    history_schedules.append({
                        "id": rid,
                        "content": content,
                        "status": status
                    })
        except Exception as e:
            self.logger.error(f"读取历史日程失败: {e}")
            history_schedules = []

        GF_PROMPT = bot_personality.GF_PROMPT
        PERSONALITY = bot_personality.PERSONALITY
        prompt_bot = {"role": "system", "content": GF_PROMPT}
        mess = (
            "你是一个日程规划助手。请结合以下信息，生成更拟人的今日日程：\n"
            f"这是你需要生成的人的身份：{PERSONALITY}"
            f"长期记忆(节选): {json.dumps(long_ctx, ensure_ascii=False)}\n"
            f"短期记忆(节选): {json.dumps(short_ctx, ensure_ascii=False)}\n"
            f"历史日程(最近3条): {json.dumps(history_schedules, ensure_ascii=False)}\n\n"
            "请输出严格的 JSON，字段与格式必须完全一致：\n"
            "{\n  \"schedule\": [\n    {\"start\": \"07:00\", \"end\": \"09:00\", \"state\": \"示例活动\", \"importance\": 2, \"done\": false}\n  ]\n}\n"
            "要求：\n"
            "- 仅返回 JSON 本体，不要任何额外文本、注释或反引号。\n"
            "- 重要性是要和聊天的重要性进行比较"
            "- 每一项必须包含 start/end/state/importance/done，时间为HH:MM 24小时制；importance为1-5整数，默认3；done为布尔值。\n"
            "- 结合长期/短期记忆与历史日程中的未完成与偏好，合理安排时间段，使日程更贴合习惯与目标。\n"
        )
        prompt_user = {"role": "user", "content": mess}

        messages = [prompt_bot, prompt_user]
        
        def _try_repair_json(text: str):
            # 去掉代码块围栏
            t = text.strip()
            if t.startswith('```'):
                t = re.sub(r"^```[a-zA-Z]*\n?|```$", "", t).strip()
            # 提取主体：优先 {..}，否则尝试 [...]
            if '{' in t and '}' in t:
                t = t[t.find('{'): (t.rfind('}')+1) if '}' in t else len(t)]
            elif '[' in t and ']' in t:
                arr = t[t.find('['): (t.rfind(']')+1) if ']' in t else len(t)]
                t = '{"schedule": ' + arr + '}'
            # 去掉对象/数组末尾多余逗号或不完整键值尾巴
            t = re.sub(r",\s*(\]|\}|$)", r"\1", t)
            # 若出现明显被截断的最后一项，尝试裁掉末尾残缺到最近的 '},' 或 ']' 之前
            if t.count('{') > 0 and t.count('}') == 0:
                # 没有任何闭合花括号，尝试截断到最后一个 '}' 或 '},' 的位置（若都没有则保留到最后一个 '{' 之前）
                cut = max(t.rfind('},'), t.rfind('}'))
                if cut > 0:
                    t = t[:cut+1]
            # 平衡括号数量
            def balance_brackets(s: str) -> str:
                open_curly = s.count('{'); close_curly = s.count('}')
                open_sq = s.count('['); close_sq = s.count(']')
                if close_sq < open_sq: s += ']' * (open_sq - close_sq)
                if close_curly < open_curly: s += '}' * (open_curly - close_curly)
                return s
            t = balance_brackets(t)
            # 候选列表按顺序尝试
            candidates = [t]
            # 替换全角/智能引号
            t1 = t.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
            if t1 != t:
                candidates.append(t1)
            # 将单引号键/值替换为双引号（保守）
            candidates.append(re.sub(r"'([^']*)'", r'"\\1"', t1))
            # Python常量转JSON
            for i in range(len(candidates)):
                c = candidates[i]
                c = c.replace('True', 'true').replace('False', 'false').replace('None', 'null')
                # 去掉对象/数组末尾多余逗号
                c = re.sub(r",\s*(\}|\])", r"\1", c)
                # 若最外层缺 key 包裹，仅是数组，进行包裹
                c_strip = c.strip()
                if c_strip.startswith('[') and c_strip.endswith(']'):
                    c = '{"schedule": ' + c_strip + '}'
                # 再次平衡括号
                c = balance_brackets(c)
                candidates[i] = c
            # 逐个尝试解析
            for c in candidates:
                try:
                    obj = json.loads(c)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    continue
            return None
        try:
            response = self.client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.7,
            messages=messages,
            max_tokens=512,
        )
            answer_text = str(response.choices[0].message.content.strip())
            self.logger.info(f"TimingProcess:Get_daily_schedule: {answer_text}")
            try:
                obj = _try_repair_json(answer_text)
                if obj is None:
                    raise ValueError("无法修复为有效JSON")
                
                assert isinstance(obj, dict) and "schedule" in obj and isinstance(obj["schedule"], list)
                # 归一与校验：确保 importance(1-5) 与 done 字段
                normalized = []
                for it in obj["schedule"]:
                    assert isinstance(it.get("start"), str) and isinstance(it.get("end"), str) and isinstance(it.get("state"), str)
                    done_val = it.get("done")
                    if not isinstance(done_val, bool):
                        done_val = False
                    # importance 1-5，默认3
                    imp = it.get("importance", 3)
                    try:
                        imp = int(imp)
                    except Exception:
                        imp = 3
                    if imp < 1: imp = 1
                    if imp > 5: imp = 5
                    normalized.append({
                        "start": it["start"],
                        "end": it["end"],
                        "state": it["state"],
                        "importance": imp,
                        "done": done_val,
                    })
                obj["schedule"] = normalized
                payload = json.dumps(obj, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"日程解析失败，使用默认模板: {e}")
                # 默认模板（含 done 字段）
                obj = {
                    "schedule": [
                        {"start": "07:00", "end": "09:00", "state": "morning", "importance": 2, "done": False},
                        {"start": "09:00", "end": "11:00", "state": "study", "importance": 2, "done": False},
                        {"start": "12:00", "end": "13:00", "state": "rest", "importance": 2, "done": False},
                        {"start": "14:00", "end": "17:00", "state": "active", "importance": 2, "done": False},
                        {"start": "22:00", "end": "23:00", "state": "sleepy", "importance": 2, "done": False},
                        {"start": "23:00", "end": "07:00", "state": "sleep", "importance": 2, "done": False},
                    ]
                }
                payload = json.dumps(obj, ensure_ascii=False)

            self.logger.info("虚拟日程创建成功")
            try:
                items = obj.get("schedule", []) if isinstance(obj, dict) else []
                schedule_id = self.schedule_service.create_today_schedule(payload, items)
                self.logger.info(f"日程已保存（原子化），ID={schedule_id}")
            except Exception as e:
                self.logger.error(f"保存日程失败: {e}")
            return payload
        except Exception as e:
            self.logger.error(e)

        pass

    def Ensure_today_schedule(self):
        try:
            if not self.schedule_store.has_schedule_for_today():
                return self.Get_daily_schedule()
            row = self.schedule_store.get_today_schedule()
            if row and len(row) >= 2 and row[1]:
                return row[1]
            return self.Get_daily_schedule()
        except Exception as e:
            self.logger.error(e)
            return self.Get_daily_schedule()

    def Save_indexs_and_rebuild_indexs(self):
        self.memory_store.rebuild_all_indexes()
        self.memory_store.save_indexes()
        self.logger.info("保存索引成功")
    
    def Clear_memories_short(self):
        self.memory_store.clear_memories_short()
        self.logger.info("清理短期数据库成功")

class MsgProcessScheduler:
    def __init__(self, user_id):
        self.msg_process = TimingProcess(user_id)
        self.bj_tz = pytz.timezone(env.TIMEZONE)
        
    def Start_scheduler(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 22 and now.minute==10:
            self.msg_process.Clear_memories_short()

    def Save_and_rebuild_indexs(self):
        now = datetime.now(self.bj_tz)
        
        if now.hour == 22 and now.minute == 30:
            self.msg_process.Save_indexs_and_rebuild_indexs()
            
        
            
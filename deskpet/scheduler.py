"""提醒调度纯逻辑：无 DB、无 Qt，便于单测。"""

from __future__ import annotations

from datetime import datetime, timedelta

REPEATS = ("once", "daily", "weekdays")


def effective_due(reminder: dict) -> datetime:
    """返回实际触发时间；临时延后优先于原计划时间。"""
    value = reminder.get("snoozed_until") or reminder["due_at"]
    return datetime.fromisoformat(value)


def due_reminders(reminders: list[dict], now: datetime) -> list[dict]:
    """返回此刻应当弹出的提醒：启用、本周期未弹过、due_at <= now。"""
    out = []
    for r in reminders:
        if not r.get("enabled"):
            continue
        if r.get("notified"):
            continue
        try:
            due = effective_due(r)
        except (KeyError, ValueError, TypeError):
            continue  # 脏数据直接跳过
        if due <= now:
            out.append(r)
    return out


def next_after_trigger(reminder: dict, now: datetime):
    """计算本次弹出后的计划时间，延后不会改变重复提醒的固定时刻。"""
    repeat = reminder.get("repeat", "once")
    if repeat == "once" or repeat not in REPEATS:
        return None
    scheduled = datetime.fromisoformat(reminder["due_at"])
    if reminder.get("snoozed_until") and scheduled > now:
        return scheduled
    return next_due(scheduled, repeat, now)


def next_due(due_at: datetime, repeat: str, now: datetime):
    """计算下一次触发时间。

    - once → None（调用方据此停用）
    - daily → 明天同时刻；若已落后多轮，直接推进到 now 之后的第一轮
    - weekdays → 同 daily，但跳过周六/周日
    """
    if repeat == "once" or repeat not in REPEATS:
        return None
    step = timedelta(days=1)
    nxt = due_at + step
    while nxt <= now:
        nxt += step
    if repeat == "weekdays":
        while nxt.weekday() >= 5:  # 5=周六 6=周日
            nxt += step
    return nxt

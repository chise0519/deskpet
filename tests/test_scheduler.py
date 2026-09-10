from datetime import datetime

from deskpet import scheduler


def R(id=1, due="2026-09-09T09:00:00", repeat="once", notified=0, enabled=1):
    return {"id": id, "content": "x", "due_at": due, "repeat": repeat,
            "notified": notified, "enabled": enabled}


NOW = datetime(2026, 9, 9, 9, 30)  # 周三


def test_due_filters():
    rs = [
        R(id=1, due="2026-09-09T09:00:00"),                # 到期 ✓
        R(id=2, due="2026-09-09T10:00:00"),                # 未到
        R(id=3, due="2026-09-09T09:00:00", notified=1),    # 本周期已弹过
        R(id=4, due="2026-09-09T09:00:00", enabled=0),     # 停用
        {"id": 5, "due_at": "bad", "enabled": 1, "notified": 0, "repeat": "once"},
    ]
    assert [r["id"] for r in scheduler.due_reminders(rs, NOW)] == [1]


def test_next_due_once_is_none():
    assert scheduler.next_due(NOW, "once", NOW) is None


def test_next_due_daily_tomorrow():
    due = datetime(2026, 9, 9, 9, 0)
    now = datetime(2026, 9, 9, 9, 0, 30)
    assert scheduler.next_due(due, "daily", now) == datetime(2026, 9, 10, 9, 0)


def test_next_due_daily_skips_passed_today():
    """昨天 9 点的每日提醒，今天 15 点才开机 → 直接推到明天，不当场轰炸。"""
    due = datetime(2026, 9, 8, 9, 0)
    now = datetime(2026, 9, 9, 15, 0)
    assert scheduler.next_due(due, "daily", now) == datetime(2026, 9, 10, 9, 0)


def test_next_due_daily_multi_day_behind():
    due = datetime(2026, 9, 1, 9, 0)
    now = datetime(2026, 9, 9, 15, 0)
    assert scheduler.next_due(due, "daily", now) == datetime(2026, 9, 10, 9, 0)


def test_next_due_weekdays_friday_to_monday():
    due = datetime(2026, 9, 11, 18, 0)  # 周五
    now = datetime(2026, 9, 11, 18, 0, 30)
    assert scheduler.next_due(due, "weekdays", now) == datetime(2026, 9, 14, 18, 0)


def test_next_due_weekdays_midweek():
    due = datetime(2026, 9, 9, 9, 0)  # 周三
    now = datetime(2026, 9, 9, 9, 0, 30)
    assert scheduler.next_due(due, "weekdays", now) == datetime(2026, 9, 10, 9, 0)

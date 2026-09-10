import sqlite3

import pytest

from deskpet import storage


@pytest.fixture()
def db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    conn.row_factory = sqlite3.Row
    storage.init_db(conn)
    storage.use_conn(conn)
    yield conn
    conn.close()
    storage.use_conn(None)


def test_note_add_and_list(db):
    nid = storage.add_note("写周报")
    assert isinstance(nid, int)
    storage.add_note("修 bug", created_at="2026-09-08T10:00:00")
    assert len(storage.list_notes()) == 2


def test_note_day_filter(db):
    storage.add_note("今天的", created_at="2026-09-09T08:00:00")
    storage.add_note("昨天的", created_at="2026-09-08T10:00:00")
    day = storage.list_notes(day="2026-09-09")
    assert len(day) == 1 and day[0]["content"] == "今天的"


def test_note_toggle_and_delete(db):
    nid = storage.add_note("开会")
    n = storage.toggle_note(nid)
    assert n["done"] == 1 and n["done_at"]
    n = storage.toggle_note(nid)
    assert n["done"] == 0 and n["done_at"] is None
    storage.delete_note(nid)
    assert storage.list_notes() == []


def test_reminder_add_update(db):
    rid = storage.add_reminder("站会", "2026-09-10T09:30:00", repeat="daily")
    r = storage.list_reminders()[0]
    assert r["repeat"] == "daily" and r["enabled"] == 1 and r["notified"] == 0
    storage.update_reminder(rid, content="晨会")
    assert storage.list_reminders()[0]["content"] == "晨会"
    with pytest.raises(KeyError):
        storage.update_reminder(rid, id=99)


def test_mark_notified_once_disables(db):
    rid = storage.add_reminder("取快递", "2026-09-09T18:00:00")
    storage.mark_notified(rid, "2026-09-09T18:00:10", None)
    r = storage.list_reminders()[0]
    assert r["notified"] == 1 and r["enabled"] == 0
    assert r["last_notified_at"] == "2026-09-09T18:00:10"


def test_mark_notified_repeat_advances(db):
    rid = storage.add_reminder("喝水", "2026-09-09T10:00:00", repeat="daily")
    storage.mark_notified(rid, "2026-09-09T10:00:05", "2026-09-10T10:00:00")
    r = storage.list_reminders()[0]
    assert r["notified"] == 0 and r["enabled"] == 1
    assert r["due_at"] == "2026-09-10T10:00:00"


def test_reminders_notified_on(db):
    rid = storage.add_reminder("复盘", "2026-09-09T17:00:00")
    storage.mark_notified(rid, "2026-09-09T17:00:02", None)
    assert len(storage.reminders_notified_on("2026-09-09")) == 1
    assert storage.reminders_notified_on("2026-09-08") == []

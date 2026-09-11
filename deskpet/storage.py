"""SQLite 存储层：notes / reminders 的 CRUD。

单连接 + RLock，GUI 线程直接调用；测试可 use_conn() 注入临时库。
时间一律存 ISO8601 本地时间字符串（秒精度）。
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Iterable, Optional, Union

from . import config

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None

When = Union[str, datetime, None]


def now_iso(dt: Optional[datetime] = None) -> str:
    return (dt or datetime.now()).isoformat(timespec="seconds")


def _norm(v):
    return now_iso(v) if isinstance(v, datetime) else v


def init_db(conn: sqlite3.Connection) -> None:
    with _lock, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              done INTEGER NOT NULL DEFAULT 0,
              done_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reminders(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              content TEXT NOT NULL,
              due_at TEXT NOT NULL,
              repeat TEXT NOT NULL DEFAULT 'once',
              notified INTEGER NOT NULL DEFAULT 0,
              last_notified_at TEXT,
              enabled INTEGER NOT NULL DEFAULT 1
            );
            """
        )


def get_conn(db_file=None) -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(
                str(db_file or config.db_path()), check_same_thread=False
            )
            _conn.row_factory = sqlite3.Row
            init_db(_conn)
        return _conn


def use_conn(conn: Optional[sqlite3.Connection]) -> None:
    """测试用：注入/清空连接。"""
    global _conn
    with _lock:
        _conn = conn


def _rows(sql: str, args: Iterable = ()) -> list[dict]:
    conn = get_conn()
    with _lock:
        cur = conn.execute(sql, tuple(args))
        return [dict(r) for r in cur.fetchall()]


def _exec(sql: str, args: Iterable = ()) -> int:
    conn = get_conn()
    with _lock, conn:
        cur = conn.execute(sql, tuple(args))
        return cur.lastrowid if cur.lastrowid else cur.rowcount


# ---------------- notes ----------------

def add_note(content: str, created_at: When = None) -> int:
    return _exec(
        "INSERT INTO notes(content, created_at) VALUES(?,?)",
        (content.strip(), _norm(created_at) or now_iso()),
    )


def list_notes(day: Optional[str] = None) -> list[dict]:
    """day='YYYY-MM-DD' 时只返回当天创建的；按时间升序。"""
    if day:
        return _rows(
            "SELECT * FROM notes WHERE substr(created_at,1,10)=? ORDER BY created_at, id",
            (day,),
        )
    return _rows("SELECT * FROM notes ORDER BY created_at, id")


def toggle_note(note_id: int, when: When = None) -> dict:
    rows = _rows("SELECT * FROM notes WHERE id=?", (note_id,))
    if not rows:
        raise KeyError(note_id)
    if rows[0]["done"]:
        _exec("UPDATE notes SET done=0, done_at=NULL WHERE id=?", (note_id,))
    else:
        _exec(
            "UPDATE notes SET done=1, done_at=? WHERE id=?",
            (_norm(when) or now_iso(), note_id),
        )
    return _rows("SELECT * FROM notes WHERE id=?", (note_id,))[0]


def delete_note(note_id: int) -> None:
    _exec("DELETE FROM notes WHERE id=?", (note_id,))


def update_note(note_id: int, content: str) -> dict:
    """改速记内容；空内容拒绝，不存在的 id 抛 KeyError。"""
    text = content.strip()
    if not text:
        raise ValueError("速记内容不能为空")
    if not _rows("SELECT id FROM notes WHERE id=?", (note_id,)):
        raise KeyError(note_id)
    _exec("UPDATE notes SET content=? WHERE id=?", (text, note_id))
    return _rows("SELECT * FROM notes WHERE id=?", (note_id,))[0]


# ---------------- reminders ----------------

def add_reminder(content: str, due_at: When, repeat: str = "once") -> int:
    return _exec(
        "INSERT INTO reminders(content, due_at, repeat) VALUES(?,?,?)",
        (content.strip(), _norm(due_at) or now_iso(), repeat),
    )


def list_reminders() -> list[dict]:
    return _rows("SELECT * FROM reminders ORDER BY due_at, id")


_ALLOWED = {"content", "due_at", "repeat", "enabled", "notified", "last_notified_at"}


def update_reminder(reminder_id: int, **fields) -> None:
    sets, args = [], []
    for k, v in fields.items():
        if k not in _ALLOWED:
            raise KeyError(f"字段不允许更新: {k}")
        sets.append(f"{k}=?")
        args.append(_norm(v))
    if not sets:
        return
    args.append(reminder_id)
    _exec(f"UPDATE reminders SET {','.join(sets)} WHERE id=?", args)


def delete_reminder(reminder_id: int) -> None:
    _exec("DELETE FROM reminders WHERE id=?", (reminder_id,))


def mark_notified(reminder_id: int, when: When, next_due_at: When = None) -> None:
    """提醒触发后立即调用（防止轮询重复弹窗）。

    next_due_at=None → 一次性提醒，直接停用；
    否则推进到下一周期，notified 归零等待下次触发。
    """
    when_s = _norm(when) or now_iso()
    if next_due_at is None:
        _exec(
            "UPDATE reminders SET notified=1, last_notified_at=?, enabled=0 WHERE id=?",
            (when_s, reminder_id),
        )
    else:
        _exec(
            "UPDATE reminders SET notified=0, due_at=?, last_notified_at=? WHERE id=?",
            (_norm(next_due_at), when_s, reminder_id),
        )


def reminders_notified_on(day: str) -> list[dict]:
    """当天实际弹过的提醒（日报用），按触发时间升序。"""
    return _rows(
        "SELECT * FROM reminders WHERE substr(last_notified_at,1,10)=? "
        "ORDER BY last_notified_at, id",
        (day,),
    )

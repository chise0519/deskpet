"""真桌面 E2E 自检：在真实桌面会话里启动全部组件，逐状态截图后自动退出。

运行（前台，约 9 秒，会在屏幕上短暂出现窗口）:
    .venv\\Scripts\\python.exe tests\\e2e_desktop.py
"""
import ctypes
import sys
import time
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setStyle("Fusion")

import sqlite3
from deskpet import config, report, scheduler, storage
from deskpet.alert_card import AlertCard
from deskpet.pet_widget import PetWidget
from deskpet.quick_note import QuickNotePanel
from deskpet.reminder_dialog import ReminderPanel
from deskpet.report_window import ReportWindow

# 临时库，不污染真实数据
tmpdb = ROOT / "preview" / "e2e.db"
if tmpdb.exists():
    tmpdb.unlink()
conn = sqlite3.connect(str(tmpdb))
conn.row_factory = sqlite3.Row
storage.init_db(conn)
storage.use_conn(conn)

out = ROOT / "preview"
out.mkdir(exist_ok=True)

pet = PetWidget()
note = QuickNotePanel()
remp = ReminderPanel()
rwin = ReportWindow()
card = AlertCard()

# 造点数据
storage.add_note("E2E 验证：悬浮窗渲染")
n2 = storage.add_note("E2E 验证：日报生成")
storage.toggle_note(n2)
storage.add_reminder("E2E 测试提醒", datetime.now() + timedelta(minutes=30), "daily")

steps = []


def shot(name):
    steps.append(name)
    pet.grab().save(str(out / f"real_{name}.png"))
    print("shot:", name, flush=True)


def seq():
    # 1 时钟
    pet.pet_mode = False
    pet.show()
    QTimer.singleShot(600, lambda: (shot("1_clock"), None))
    # 2 企鹅 idle
    QTimer.singleShot(1600, lambda: (setattr(pet, "pet_mode", True),
                                     setattr(pet, "anim", "idle"),
                                     pet.update(), shot("2_idle")))
    # 3 happy
    QTimer.singleShot(2600, lambda: (setattr(pet, "anim", "happy"),
                                     setattr(pet, "_happy_until", pet.frame + 10),
                                     pet.update(), shot("3_happy")))
    # 4 alert 举牌
    QTimer.singleShot(3600, lambda: (pet.set_alert("E2E 测试提醒"), shot("4_alert")))
    # 5 速记面板
    QTimer.singleShot(4600, lambda: (note.show_near(pet.mapToGlobal(
        pet.rect().topLeft())), note.grab().save(str(out / "real_5_note.png")),
        print("shot: 5_note", flush=True)))
    # 6 提醒面板
    QTimer.singleShot(5800, lambda: (remp.show_near(pet.mapToGlobal(
        pet.rect().topLeft())), remp.grab().save(str(out / "real_6_reminder.png")),
        print("shot: 6_reminder", flush=True)))
    # 7 提醒卡片
    QTimer.singleShot(7000, lambda: (card.popup(
        {"id": 1, "content": "E2E 测试提醒"},
        pet.mapToGlobal(pet.rect().topLeft())),
        card.grab().save(str(out / "real_7_card.png")),
        print("shot: 7_card", flush=True)))
    # 8 日报窗口
    QTimer.singleShot(8200, lambda: (rwin.show_and_generate(),
        rwin.grab().save(str(out / "real_8_report.png")),
        print("shot: 8_report", flush=True)))
    # 收尾：验证窗口句柄可见 + 退出
    QTimer.singleShot(9500, finish)


def finish():
    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    found = []

    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value == "DeskPet":
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            found.append((bool(user32.IsWindowVisible(hwnd)),
                          (r.left, r.top, r.right, r.bottom)))
        return True

    EnumWindows(WNDENUMPROC(cb), 0)
    print("WINDOW ENUM:", found, flush=True)
    print("E2E_OK steps=", steps, flush=True)
    app.quit()


QTimer.singleShot(300, seq)
sys.exit(app.exec())

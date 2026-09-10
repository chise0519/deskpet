"""离屏冒烟测试：渲染各状态截图 + 走一遍核心流程，不依赖真实桌面。"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from deskpet import config, report, scheduler, storage
from deskpet.alert_card import AlertCard
from deskpet.pet_widget import PetWidget
from deskpet.quick_note import QuickNotePanel
from deskpet.reminder_dialog import ReminderPanel
from deskpet.report_window import ReportWindow

# 用临时 DB
tmpdb = Path(os.environ.get("TEMP", ".")) / "deskpet_smoke.db"
if tmpdb.exists():
    tmpdb.unlink()
conn = sqlite3.connect(str(tmpdb))
conn.row_factory = sqlite3.Row
storage.init_db(conn)
storage.use_conn(conn)

out = Path(__file__).resolve().parent.parent / "preview"
out.mkdir(exist_ok=True)

# 1) 时钟形态
pet = PetWidget()
pet.pet_mode = False
pet.grab().save(str(out / "1_clock.png"))

# 2) 企鹅 idle
pet.pet_mode = True
pet.anim = "idle"
pet.frame = 10
pet.grab().save(str(out / "2_penguin_idle.png"))

# 3) 企鹅 happy（跳跃挥手帧）
pet.anim = "happy"
pet._happy_until = pet.frame + 10
pet.frame += 4
pet.grab().save(str(out / "3_penguin_happy.png"))

# 4) alert 举牌
pet.anim = "alert"
pet.grab().save(str(out / "4_penguin_alert.png"))

# 5) 数据流：记 3 条速记，勾掉 1 条，建提醒并触发调度
n1 = storage.add_note("评审 PR #42")
n2 = storage.add_note("给客户回邮件")
n3 = storage.add_note("更新部署文档")
storage.toggle_note(n1)
rid = storage.add_reminder("15:00 站会", datetime.now() - timedelta(minutes=1), repeat="daily")

due = scheduler.due_reminders(storage.list_reminders(), datetime.now())
assert len(due) == 1 and due[0]["id"] == rid, "调度应命中过期提醒"
nxt = scheduler.next_due(datetime.fromisoformat(due[0]["due_at"]), "daily", datetime.now())
storage.mark_notified(rid, datetime.now(), nxt)
assert scheduler.due_reminders(storage.list_reminders(), datetime.now()) == [], "不应重复触发"

# 6) 日报
notes = storage.list_notes(day=datetime.now().strftime("%Y-%m-%d"))
rems = storage.reminders_notified_on(datetime.now().strftime("%Y-%m-%d"))
md = report.build_report(datetime.now(), notes, rems)
path = report.save_report(md, datetime.now(), out)
print("=== 日报预览 ===")
print(md)
assert path.exists()

# 7) 面板都能实例化并渲染
panel = QuickNotePanel(); panel.reload(); panel.grab().save(str(out / "5_note_panel.png"))
rpanel = ReminderPanel(); rpanel.reload(); rpanel.grab().save(str(out / "6_reminder_panel.png"))
card = AlertCard(); card.body.setText("15:00 站会"); card.grab().save(str(out / "7_alert_card.png"))
rwin = ReportWindow(); rwin.generate(); rwin.grab().save(str(out / "8_report_window.png"))

print("SMOKE_OK  截图输出目录:", out)

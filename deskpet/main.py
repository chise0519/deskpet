"""DeskPet 入口：单实例 + 托盘 + 提醒轮询 + 组装所有窗口。

运行: python -m deskpet.main   或双击 run.bat
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMenu, QMessageBox, QSystemTrayIcon,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from . import autostart, config, scheduler, storage
from .alert_card import AlertCard
from .pet_widget import PetWidget, W, H
from .quick_note import QuickNotePanel
from .reminder_dialog import ReminderPanel
from .report_window import ReportWindow
from .settings_window import SettingsWindow

SINGLE_INSTANCE_KEY = "***"
POLL_MS = 15_000


def make_icon() -> QIcon:
    """品牌图标：与日报窗口左上角同一个（icons.app_icon，多尺寸）。"""
    from .icons import app_icon

    return app_icon()


class DeskPetApp:
    def __init__(self, app: QApplication):
        self.app = app
        app.setQuitOnLastWindowClosed(False)  # 面板全关了也要活着
        app.setApplicationName(config.APP_NAME)
        icon = make_icon()
        app.setWindowIcon(icon)

        storage.get_conn()  # 初始化 DB

        self.pet = PetWidget()
        self.note_panel = QuickNotePanel()
        self.reminder_panel = ReminderPanel()
        self.report_win = ReportWindow()
        self.alert_card = AlertCard()
        self.settings_win = SettingsWindow()

        # 信号接线
        self.pet.request_note.connect(self.open_note)
        self.pet.request_reminder.connect(self.open_reminder)
        self.pet.request_report.connect(self.open_report)
        self.pet.request_settings.connect(self.open_settings)
        self.pet.request_quit.connect(self.quit)
        self.settings_win.changed.connect(self._apply_poll_interval)
        self.alert_card.done.connect(self._alert_done)
        self.alert_card.snooze.connect(self._alert_snooze)
        self.alert_card.ignore.connect(self._alert_ignore)

        # 提醒轮询
        self.poll = QTimer()
        self.poll.timeout.connect(self.poll_reminders)
        self._apply_poll_interval()

        # 托盘
        self.tray = QSystemTrayIcon(icon, app)
        self.tray.setToolTip(f"DeskPet {config.VERSION} · 桌面速记小企鹅")
        from .icons import icon as ui_icon

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#23262f;color:#dfe3ea;border:1px solid #3b3f4d;"
            "font-size:12px;padding:6px;}"
            "QMenu::item{padding:6px 26px 6px 10px;border-radius:6px;}"
            "QMenu::item:selected{background:#3a5a86;}"
            "QMenu::icon{margin:0 8px 0 4px;}"
            "QMenu::separator{height:1px;background:#3b3f4d;margin:5px 8px;}"
        )
        for ic_name, text, slot in [
            ("note", "速记", self.open_note),
            ("bell", "提醒管理", self.open_reminder),
            ("doc", "写日报", self.open_report),
            ("eye", "显示/隐藏企鹅", self.toggle_pet),
            ("gear", "设置", self.open_settings),
        ]:
            act = QAction(ui_icon(ic_name), text, menu)
            act.triggered.connect(slot)
            menu.addAction(act)
        menu.addSeparator()
        self.autostart_act = QAction("开机自启", menu)
        self.autostart_act.setCheckable(True)
        self.autostart_act.setChecked(autostart.is_enabled())
        self.autostart_act.toggled.connect(
            lambda on: autostart.set_enabled(on)
        )
        menu.addAction(self.autostart_act)
        quit_act = QAction("退出", menu)
        quit_act.triggered.connect(self.quit)
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

        self.pet.show()
        QTimer.singleShot(300, self._startup_check)

    # ---------------- 面板开关 ----------------

    def open_note(self):
        self.note_panel.show_near(self.pet.mapToGlobal(self.pet.rect().topLeft()))

    def open_reminder(self):
        self.reminder_panel.show_near(self.pet.mapToGlobal(self.pet.rect().topLeft()))

    def open_report(self):
        self.report_win.show_and_generate()

    def open_settings(self):
        self.settings_win.show_settings()

    def _apply_poll_interval(self):
        sec = int(config.load_config().get("poll_sec", 15))
        self.poll.start(max(5, min(300, sec)) * 1000)

    def toggle_pet(self):
        self.pet.setVisible(not self.pet.isVisible())

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 单击
            self.open_note()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_report()

    # ---------------- 提醒 ----------------

    def poll_reminders(self):
        now = datetime.now()
        due = scheduler.due_reminders(storage.list_reminders(), now)
        if not due:
            return
        r = due[0]  # 一次只弹一条，下一条 15s 后自然再来
        rep = r.get("repeat", "once")
        nxt = scheduler.next_due(
            datetime.fromisoformat(r["due_at"]), rep, now
        )
        storage.mark_notified(r["id"], now, nxt)  # 先落库防重复弹
        self.pet.set_alert(r["content"])
        due_s = datetime.fromisoformat(r["due_at"]).strftime("%H:%M")
        anchor = self.pet.mapToGlobal(self.pet.rect().topLeft())
        anchor.setX(anchor.x() + W // 2)
        rep_cn = {"daily": "每天", "weekdays": "工作日"}.get(rep, "仅一次")
        self.alert_card.popup(
            r, anchor, when_text=f"计划 {due_s} · {rep_cn}",
        )
        if config.load_config().get("sys_notify", True):
            self.tray.showMessage(
                "⏰ DeskPet 提醒", r["content"],
                QSystemTrayIcon.MessageIcon.Information, 5000,
            )

    def _alert_done(self, rem_id: int):
        self.pet.clear_alert()
        # 若有同名未完成速记则顺手勾掉
        rows = storage.list_notes(day=datetime.now().strftime("%Y-%m-%d"))
        rem = next((x for x in storage.list_reminders() if x["id"] == rem_id), None)
        if rem:
            for n in rows:
                if not n["done"] and n["content"] == rem["content"]:
                    storage.toggle_note(n["id"])
                    break

    def _alert_snooze(self, rem_id: int):
        self.pet.clear_alert()
        r = next((x for x in storage.list_reminders() if x["id"] == rem_id), None)
        if r:
            storage.update_reminder(
                rem_id,
                due_at=datetime.now() + timedelta(minutes=5),
                notified=0, enabled=1,
            )

    def _alert_ignore(self, _rem_id: int):
        self.pet.clear_alert()

    def _startup_check(self):
        """启动时补查错过的提醒：只汇总提示一次，不连环轰炸；
        重复提醒静默推进到下一周期。"""
        now = datetime.now()
        missed = scheduler.due_reminders(storage.list_reminders(), now)
        if not missed:
            return
        names = []
        for r in missed:
            nxt = scheduler.next_due(
                datetime.fromisoformat(r["due_at"]), r.get("repeat", "once"), now
            )
            if nxt is not None:
                storage.mark_notified(r["id"], now, nxt)  # 重复项推进
            else:
                names.append(r["content"])  # 一次性过期项
        if names:
            text = "\n".join(f"· {n}" for n in names[:8])
            more = f"\n…等 {len(names)} 条" if len(names) > 8 else ""
            self.tray.showMessage(
                "⏰ 离线期间错过的提醒", text + more,
                QSystemTrayIcon.MessageIcon.Warning, 8000,
            )

    # ---------------- 退出 ----------------

    def quit(self):
        self.poll.stop()
        self.tray.hide()
        self.pet.bubble.close()
        self.app.quit()


def already_running() -> bool:
    """单实例：已有实例则发消息让它弹速记面板，返回 True。"""
    sock = QLocalSocket()
    sock.connectToServer(SINGLE_INSTANCE_KEY)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if already_running():
        return 0

    server = QLocalServer()
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    server.listen(SINGLE_INSTANCE_KEY)

    deskpet = DeskPetApp(app)

    def on_conn():
        conn = server.nextPendingConnection()
        if conn:
            conn.readyRead.connect(lambda: deskpet.open_note())

    server.newConnection.connect(on_conn)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

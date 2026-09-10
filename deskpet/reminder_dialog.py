"""提醒管理面板。"""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QDate, QDateTime, QTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from . import storage
from .quick_note import PANEL_CSS

REPEAT_LABEL = {"once": "仅一次", "daily": "每天", "weekdays": "工作日"}
REPEAT_KEYS = list(REPEAT_LABEL.keys())

EXTRA_CSS = """
QComboBox, QDateTimeEdit {
    background: #1b1d25; color: #eceff4; border: 1px solid #3b3f4d;
    border-radius: 6px; padding: 4px 7px; font-size: 12px;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #23262f; color: #eceff4; selection-background-color: #3a5a86;
}
QDateTimeEdit::drop-down { border: none; width: 18px; }
QCalendarWidget QWidget { background: #23262f; color: #eceff4; }
QPushButton.mini {
    background: #33384a; color: #dfe3ea; border: none; border-radius: 6px;
    padding: 5px 10px; font-size: 12px;
}
QPushButton.mini:hover { background: #424a60; }
QPushButton.mini.danger:hover { background: #7a3d43; }
QLabel.rem { color: #dfe3ea; font-size: 12px; }
QLabel.remsub { color: #7f8798; font-size: 10px; }
"""


class ReminderRow(QWidget):
    toggled = Signal(int, bool)
    removed = Signal(int)

    def __init__(self, rem: dict, parent=None):
        super().__init__(parent)
        self.rem_id = rem["id"]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 3, 4, 3)
        lay.setSpacing(1)

        top = QHBoxLayout()
        self.box = QCheckBox(rem["content"])
        self.box.setChecked(bool(rem["enabled"]))
        self.box.toggled.connect(lambda on: self.toggled.emit(self.rem_id, on))
        top.addWidget(self.box, 1)

        try:
            due = datetime.fromisoformat(rem["due_at"])
            late = due < datetime.now() and not rem["enabled"]
            due_s = due.strftime("%m-%d %H:%M") + ("（已过）" if late else "")
        except ValueError:
            due_s = rem["due_at"]
        sub = QLabel(f"{REPEAT_LABEL.get(rem['repeat'], rem['repeat'])} · 下次 {due_s}")
        sub.setObjectName("remsub")
        top.addWidget(sub)

        btn = QPushButton("删")
        btn.setFixedSize(22, 20)
        btn.setStyleSheet(
            "QPushButton{background:transparent;color:#6f7889;border:none;"
            "font-size:11px;}QPushButton:hover{color:#e06c75;}"
        )
        btn.clicked.connect(lambda: self.removed.emit(self.rem_id))
        top.addWidget(btn)

        lay.addLayout(top)


class ReminderPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notePanel")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(PANEL_CSS + EXTRA_CSS)
        self.setFixedWidth(330)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(7)

        hdr = QHBoxLayout()
        t = QLabel("提醒")
        t.setObjectName("hdr")
        hdr.addWidget(t)
        hdr.addStretch(1)
        close = QPushButton("×")
        close.setFixedSize(20, 20)
        close.setStyleSheet(
            "QPushButton{background:transparent;color:#8b93a3;border:none;"
            "font-size:16px;}QPushButton:hover{color:#e06c75;}"
        )
        close.clicked.connect(self.hide)
        hdr.addWidget(close)
        root.addLayout(hdr)

        # 新建表单
        form = QFormLayout()
        form.setSpacing(5)
        self.content = QLineEdit()
        self.content.setPlaceholderText("提醒内容…")
        self.content.returnPressed.connect(self._add)
        form.addRow("内容", self.content)

        self.dt = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.dt.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt.setCalendarPopup(True)
        self.dt.setMinimumDate(QDate.currentDate().addYears(-1))
        form.addRow("时间", self.dt)

        self.repeat = QComboBox()
        for k in REPEAT_KEYS:
            self.repeat.addItem(REPEAT_LABEL[k], k)
        form.addRow("重复", self.repeat)
        root.addLayout(form)

        btns = QHBoxLayout()
        quick = QPushButton("+1小时")
        quick.setProperty("class", "mini")
        quick.setStyleSheet(
            "background:#33384a;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:4px 9px;font-size:11px;"
        )
        quick.clicked.connect(lambda: self._bump(3600))
        btns.addWidget(quick)
        tomorrow = QPushButton("明早9点")
        tomorrow.setStyleSheet(quick.styleSheet())
        tomorrow.clicked.connect(self._tomorrow9)
        btns.addWidget(tomorrow)
        btns.addStretch(1)
        add = QPushButton("添加提醒")
        add.setObjectName("addBtn")
        add.clicked.connect(self._add)
        btns.addWidget(add)
        root.addLayout(btns)

        self.list = QListWidget()
        self.list.setMinimumHeight(80)
        self.list.setMaximumHeight(200)
        root.addWidget(self.list)

        self.stat = QLabel("")
        self.stat.setObjectName("stat")
        root.addWidget(self.stat)

    # ---------------- 数据 ----------------

    def reload(self):
        self.list.clear()
        rems = storage.list_reminders()
        for r in rems:
            row = ReminderRow(r)
            row.toggled.connect(self._toggle)
            row.removed.connect(self._delete)
            item = QListWidgetItem(self.list)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        active = sum(1 for r in rems if r["enabled"])
        self.stat.setText(f"共 {len(rems)} 条 · 启用 {active} 条")

    def _add(self):
        text = self.content.text().strip()
        if not text:
            return
        due = self.dt.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        storage.add_reminder(text, due, self.repeat.currentData())
        self.content.clear()
        self.reload()

    def _bump(self, secs: int):
        self.dt.setDateTime(QDateTime.currentDateTime().addSecs(secs))

    def _tomorrow9(self):
        d = QDate.currentDate().addDays(1)
        self.dt.setDateTime(QDateTime(d, QTime(9, 0)))

    def _toggle(self, rem_id: int, on: bool):
        storage.update_reminder(rem_id, enabled=int(on))
        self.reload()

    def _delete(self, rem_id: int):
        storage.delete_reminder(rem_id)
        self.reload()

    def show_near(self, global_pos):
        self.reload()
        self.adjustSize()
        geo = (self.screen() or self.windowHandle().screen()).availableGeometry()
        x = global_pos.x() - self.width() - 10
        if x < geo.left():
            x = global_pos.x() + 90
        y = max(geo.top(), min(global_pos.y() - 40, geo.bottom() - self.height()))
        self.move(min(x, geo.right() - self.width()), y)
        self.show()
        self.content.setFocus()

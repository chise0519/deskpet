"""提醒到点弹窗：宠物旁边的小卡片，可完成 / 稍后5分钟 / 忽略。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

CSS = """
#alertCard {
    background: rgba(43, 34, 30, 244);
    border: 1.5px solid #b07a4a;
    border-radius: 12px;
}
QLabel#title { color: #f0b070; font-size: 12px; font-weight: bold; }
QLabel#body  { color: #f5ede2; font-size: 14px; }
QLabel#when  { color: #a08a70; font-size: 10px; }
QPushButton {
    border: none; border-radius: 7px; padding: 5px 12px; font-size: 12px;
}
QPushButton#done { background: #4a9d6a; color: white; }
QPushButton#done:hover { background: #59b37c; }
QPushButton#snooze { background: #b08840; color: white; }
QPushButton#snooze:hover { background: #c79a4d; }
QPushButton#ignore { background: #4a4a55; color: #cfd2da; }
QPushButton#ignore:hover { background: #5c5c68; }
"""


class AlertCard(QWidget):
    done = Signal(int)     # reminder_id → 记完成（并勾掉同名速记可选）
    snooze = Signal(int)   # reminder_id → 推迟 5 分钟
    ignore = Signal(int)   # reminder_id → 本周期忽略

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alertCard")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(CSS)
        self.setFixedWidth(280)
        self.rem_id = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 11, 14, 11)
        root.setSpacing(5)

        t = QLabel("提醒时间到")
        t.setObjectName("title")
        bell = QLabel()
        from .icons import icon as ui_icon
        bell.setPixmap(ui_icon("bell", 16).pixmap(16, 16))
        row0 = QHBoxLayout()
        row0.setSpacing(6)
        row0.addWidget(bell)
        row0.addWidget(t)
        row0.addStretch(1)
        root.addLayout(row0)

        self.body = QLabel("")
        self.body.setObjectName("body")
        self.body.setWordWrap(True)
        f = QFont("Microsoft YaHei UI", 11)
        self.body.setFont(f)
        root.addWidget(self.body)

        self.when = QLabel("")
        self.when.setObjectName("when")
        root.addWidget(self.when)

        btns = QHBoxLayout()
        btns.addStretch(1)
        b_done = QPushButton("完成")
        b_done.setObjectName("done")
        b_done.clicked.connect(lambda: self._fire(self.done))
        btns.addWidget(b_done)
        b_snz = QPushButton("5分钟后")
        b_snz.setObjectName("snooze")
        b_snz.clicked.connect(lambda: self._fire(self.snooze))
        btns.addWidget(b_snz)
        b_ign = QPushButton("忽略")
        b_ign.setObjectName("ignore")
        b_ign.clicked.connect(lambda: self._fire(self.ignore))
        btns.addWidget(b_ign)
        root.addLayout(btns)

    def _fire(self, sig):
        sig.emit(self.rem_id)
        self.hide()

    def popup(self, rem: dict, anchor_point, when_text: str = ""):
        self.rem_id = rem["id"]
        self.body.setText(rem["content"])
        self.when.setText(when_text)
        self.adjustSize()
        geo = self.screen().availableGeometry() if self.screen() else None
        x = anchor_point.x() - self.width() // 2
        y = anchor_point.y() - self.height() - 12
        if geo:
            x = max(geo.left(), min(x, geo.right() - self.width()))
            y = max(geo.top(), y)
        self.move(x, y)
        self.show()
        self.raise_()
        QApplication.beep()

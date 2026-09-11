"""速记面板：多行输入（回车保存/Shift+回车换行），列表可勾选完成、
右键编辑或删除。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor, QFont
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from . import storage

PANEL_CSS = """
#notePanel {
    background: rgba(28, 30, 38, 236);
    border: 1px solid #3b3f4d;
    border-radius: 12px;
}
QLineEdit {
    background: #1b1d25; color: #eceff4;
    border: 1px solid #3b3f4d; border-radius: 8px;
    padding: 6px 9px; font-size: 13px;
}
QLineEdit:focus { border-color: #6f9bd8; }
QPlainTextEdit {
    background: #1b1d25; color: #eceff4;
    border: 1px solid #3b3f4d; border-radius: 8px;
    padding: 6px 9px; font-size: 13px;
}
QPlainTextEdit:focus { border-color: #6f9bd8; }
QPushButton#addBtn {
    background: #4a7fc1; color: white; border: none;
    border-radius: 8px; padding: 6px 14px; font-size: 13px;
}
QPushButton#addBtn:hover { background: #5a92d8; }
QListWidget {
    background: transparent; border: none; color: #dfe3ea; font-size: 13px;
    outline: none;
}
QListWidget::item { padding: 2px 0; }
QListWidget::item:hover { background: rgba(255,255,255,14); border-radius: 6px; }
QCheckBox { color: #dfe3ea; spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #5a6070; background: #1b1d25; }
QCheckBox::indicator:checked { background: #4a9d6a; border-color: #4a9d6a; }
QLabel#hdr { color: #9aa3b2; font-size: 11px; }
QLabel#stat { color: #6f7889; font-size: 11px; }
QMenu { background: #23262f; color: #dfe3ea; border: 1px solid #3b3f4d; }
QMenu::item:selected { background: #3a5a86; }
"""


class NoteRow(QWidget):
    toggled = Signal(int, bool)
    removed = Signal(int)
    edit_requested = Signal(int, str)   # (id, 当前内容) → 回填到上方编辑框

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note_id = note["id"]
        self._content = note["content"]
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 1, 4, 1)
        self.box = QCheckBox(note["content"])
        self.box.setChecked(bool(note["done"]))
        self.box.setToolTip("双击或右键可编辑")
        if note["done"]:
            f = self.box.font()
            f.setStrikeOut(True)
            self.box.setFont(f)
            self.box.setStyleSheet("color:#7d8797;")
        self.box.toggled.connect(lambda on: self.toggled.emit(self.note_id, on))
        lay.addWidget(self.box, 1)

    def mouseDoubleClickEvent(self, ev):
        self.edit_requested.emit(self.note_id, self._content)
        ev.accept()

    def contextMenuEvent(self, ev):
        menu = QMenu(self)
        act_edit = QAction("编辑这条", menu)
        act_edit.triggered.connect(
            lambda: self.edit_requested.emit(self.note_id, self._content))
        menu.addAction(act_edit)
        act = QAction("删除这条", menu)
        act.triggered.connect(lambda: self.removed.emit(self.note_id))
        menu.addAction(act)
        menu.exec(QCursor.pos())
        ev.accept()


class QuickNotePanel(QWidget):
    """无边框小面板，挂在企鹅旁边。"""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notePanel")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(PANEL_CSS)
        self.setFixedWidth(340)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(7)

        hdr = QHBoxLayout()
        t = QLabel("速记 · 今天")
        t.setObjectName("hdr")
        hdr.addWidget(t)
        hdr.addStretch(1)
        close = QPushButton("×")
        close.setFixedSize(20, 20)
        close.setStyleSheet(
            "QPushButton{background:transparent;color:#8b93a3;border:none;"
            "font-size:16px;} QPushButton:hover{color:#e06c75;}"
        )
        close.clicked.connect(self.hide)
        hdr.addWidget(close)
        root.addLayout(hdr)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("记点什么…\n回车保存，Shift+回车换行")
        self.edit.setFixedHeight(58)
        self.edit.installEventFilter(self)
        row.addWidget(self.edit, 1)
        col = QVBoxLayout()
        col.setSpacing(6)
        self.add_btn = QPushButton("添加")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.clicked.connect(self._save)
        col.addWidget(self.add_btn)
        col.addStretch(1)
        row.addLayout(col)
        root.addLayout(row)

        self.list = QListWidget()
        self.list.setMinimumHeight(120)
        self.list.setMaximumHeight(280)
        root.addWidget(self.list)

        self.stat = QLabel("")
        self.stat.setObjectName("stat")
        root.addWidget(self.stat)
        self._editing_id = None

    def eventFilter(self, obj, ev):
        """输入框：回车=保存（Shift+回车=换行）；编辑态 Esc=取消。"""
        if obj is self.edit and ev.type() == ev.Type.KeyPress:
            if ev.key() == Qt.Key_Escape and self._editing_id is not None:
                self._cancel_edit()
                return True
            if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
                    ev.modifiers() & Qt.ShiftModifier):
                self._save()
                return True
        return super().eventFilter(obj, ev)

    # ---------------- 数据 ----------------

    def reload(self):
        from datetime import date

        self.list.clear()
        notes = storage.list_notes(day=date.today().isoformat())
        for n in notes:
            row = NoteRow(n)
            row.toggled.connect(self._toggle)
            row.removed.connect(self._delete)
            row.edit_requested.connect(self._start_edit)
            item = QListWidgetItem(self.list)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        done = sum(1 for n in notes if n["done"])
        self.stat.setText(f"共 {len(notes)} 条 · 已完成 {done} 条")

    def _save(self):
        """新增或保存修改，统一入口（按钮/回车共用）。"""
        text = self.edit.toPlainText().strip()
        if not text:
            return
        if self._editing_id is not None:
            try:
                storage.update_note(self._editing_id, text)
            except (ValueError, KeyError):
                return
            self._cancel_edit(refresh=False)
        else:
            storage.add_note(text)
        self.edit.clear()
        self.reload()

    def _start_edit(self, note_id: int, content: str):
        """把选中条目回填到上方编辑框，进入编辑态。"""
        self._editing_id = note_id
        self.edit.setPlainText(content)
        self.edit.setFocus()
        self.edit.moveCursor(self.edit.textCursor().MoveOperation.End)
        self.add_btn.setText("保存修改")
        self.stat.setText("编辑中：改完点「保存修改」或回车，Esc 取消")

    def _cancel_edit(self, refresh: bool = True):
        self._editing_id = None
        self.edit.clear()
        self.add_btn.setText("添加")
        if refresh:
            self.reload()

    def _toggle(self, note_id: int, _on: bool):
        storage.toggle_note(note_id)
        self.reload()

    def _delete(self, note_id: int):
        if self._editing_id == note_id:
            self._cancel_edit(refresh=False)
        storage.delete_note(note_id)
        self.reload()

    # ---------------- 交互 ----------------

    def show_near(self, global_pos):
        """在企鹅左侧弹出；屏幕放不下则换到右侧。"""
        self.reload()
        self.adjustSize()
        screen = self.screen() or self.windowHandle().screen()
        geo = screen.availableGeometry()
        x = global_pos.x() - self.width() - 10
        if x < geo.left():
            x = global_pos.x() + 90
        y = max(geo.top(), min(global_pos.y() - 40, geo.bottom() - self.height()))
        self.move(min(x, geo.right() - self.width()), y)
        self.show()
        self.edit.setFocus()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
            self.closed.emit()
        else:
            super().keyPressEvent(ev)

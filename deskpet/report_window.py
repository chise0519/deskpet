"""日报窗口：预生成 Markdown → 可编辑 → 保存文件。"""
from __future__ import annotations

import os
import subprocess
from datetime import date, datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from . import config, llm, report, storage

CSS = """
#reportWin { background: #1e2028; }
QLabel#hdr { color: #e6e9ef; font-size: 14px; font-weight: bold; }
QLabel#sub { color: #8b93a3; font-size: 11px; }
QTextEdit {
    background: #17181e; color: #dfe3ea;
    border: 1px solid #343a48; border-radius: 8px; padding: 8px;
    font-family: 'Consolas', 'Microsoft YaHei UI';
    font-size: 13px;
}
QPushButton {
    background: #33384a; color: #dfe3ea; border: none;
    border-radius: 7px; padding: 6px 14px; font-size: 12px;
}
QPushButton:hover { background: #424a60; }
QPushButton#save { background: #4a7fc1; }
QPushButton#save:hover { background: #5a92d8; }
QPushButton#polish { background: #6a4fa3; }
QPushButton#polish:hover { background: #7d5fbe; }
QPushButton:disabled { background: #2a2d38; color: #6f7889; }
"""


class PolishWorker(QThread):
    """后台调 LLM，避免卡 UI。"""

    ok = Signal(str)
    err = Signal(str)

    def __init__(self, markdown: str, parent=None):
        super().__init__(parent)
        self.markdown = markdown

    def run(self):
        try:
            self.ok.emit(llm.polish_report(self.markdown))
        except llm.LLMError as e:
            self.err.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.err.emit(f"润色失败：{e}")


class ReportWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reportWin")
        self.setWindowTitle("DeskPet · 日报")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setStyleSheet(CSS)
        from .icons import app_icon
        self.setWindowIcon(app_icon())
        self.resize(560, 520)
        self._day = date.today()
        self._last_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        from .icons import app_icon
        doc_ic = QLabel()
        doc_ic.setPixmap(app_icon((16,)).pixmap(16, 16))
        hdr.addWidget(doc_ic)
        t = QLabel("今日日报")
        t.setObjectName("hdr")
        hdr.addWidget(t)
        hdr.addStretch(1)
        regen = QPushButton("重新生成")
        regen.clicked.connect(self.generate)
        hdr.addWidget(regen)
        root.addLayout(hdr)

        self.sub = QLabel("")
        self.sub.setObjectName("sub")
        root.addWidget(self.sub)

        self.editor = QTextEdit()
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        self.editor.setFont(f)
        root.addWidget(self.editor, 1)

        btns = QHBoxLayout()
        self.path_lbl = QLabel("")
        self.path_lbl.setObjectName("sub")
        self.path_lbl.setWordWrap(True)
        btns.addWidget(self.path_lbl, 1)
        b_open = QPushButton("打开目录")
        b_open.clicked.connect(self._open_dir)
        btns.addWidget(b_open)
        b_saveas = QPushButton("另存为…")
        b_saveas.clicked.connect(self._save_as)
        btns.addWidget(b_saveas)
        self.b_polish = QPushButton("一键润色")
        self.b_polish.setObjectName("polish")
        from .icons import icon as _ic
        self.b_polish.setIcon(_ic("spark", 14))
        self.b_polish.clicked.connect(self._polish)
        btns.addWidget(self.b_polish)
        b_save = QPushButton("保存日报")
        b_save.setObjectName("save")
        b_save.setIcon(_ic("doc", 14))
        b_save.clicked.connect(self._save)
        btns.addWidget(b_save)
        root.addLayout(btns)

    def generate(self):
        day_s = self._day.isoformat()
        notes = storage.list_notes(day=day_s)
        rems = storage.reminders_notified_on(day_s)
        md = report.build_report(self._day, notes, rems)
        self.editor.setPlainText(md)
        done = sum(1 for n in notes if n["done"])
        self.sub.setText(
            f"{day_s} · 速记 {len(notes)} 条（完成 {done}）· 提醒触发 {len(rems)} 次"
        )

    def _save(self):
        path = report.save_report(
            self.editor.toPlainText(), self._day, config.reports_dir()
        )
        self._last_path = path
        self.path_lbl.setText(f"已保存：{path}")

    # ---------------- AI 润色 ----------------

    def _polish(self):
        md = self.editor.toPlainText()
        if not md.strip():
            QMessageBox.information(self, "DeskPet", "日报内容为空，先写点东西。")
            return
        self._pre_polish = md
        self.b_polish.setEnabled(False)
        self.b_polish.setText("润色中…")
        self.path_lbl.setText("正在调用模型润色，请稍候…")
        self._worker = PolishWorker(md, self)
        self._worker.ok.connect(self._polish_ok)
        self._worker.err.connect(self._polish_err)
        self._worker.start()

    def _polish_ok(self, polished: str):
        self.b_polish.setEnabled(True)
        self.b_polish.setText("一键润色")
        self.editor.setPlainText(polished)
        mode = config.load_config().get("polish_save", "new")
        try:
            if mode == "overwrite":
                path = report.save_report(
                    polished, self._day, config.reports_dir())
                note = f"润色完成并已覆盖：{path.name}"
            else:
                path = report.save_report(
                    polished, self._day, config.reports_dir(),
                    suffix=".polished")
                note = f"润色完成，另存为：{path.name}（原文未动）"
        except OSError as e:
            self.path_lbl.setText(f"润色完成但保存失败：{e}")
            return
        self._last_path = path
        self.path_lbl.setText(note)

    def _polish_err(self, msg: str):
        self.b_polish.setEnabled(True)
        self.b_polish.setText("一键润色")
        self.path_lbl.setText("润色失败")
        QMessageBox.warning(self, "AI 润色失败", msg)

    def _save_as(self):
        default = str(config.reports_dir() / f"{self._day.isoformat()}.md")
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", default, "Markdown (*.md);;所有文件 (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.editor.toPlainText())
            self._last_path = path
            self.path_lbl.setText(f"已保存：{path}")

    def _open_dir(self):
        d = config.reports_dir()
        if os.name == "nt":
            subprocess.Popen(["explorer", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])

    def show_and_generate(self):
        self._day = date.today()
        self.generate()
        self.show()
        self.raise_()
        self.activateWindow()

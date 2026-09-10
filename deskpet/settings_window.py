"""设置窗口：日报目录 + 时钟/互动/提醒/系统各项偏好。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
    QWidget,
)

from . import autostart, config, llm
from .quick_note import PANEL_CSS

EXTRA_CSS = """
QGroupBox {
    color: #9aa3b2; font-size: 11px; border: 1px solid #343a48;
    border-radius: 8px; margin-top: 12px; padding-top: 6px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLineEdit, QSpinBox {
    background: #1b1d25; color: #eceff4; border: 1px solid #3b3f4d;
    border-radius: 6px; padding: 5px 8px; font-size: 12px;
}
QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
QCheckBox { color: #dfe3ea; spacing: 7px; font-size: 12px; }
QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #5a6070; background: #1b1d25; }
QCheckBox::indicator:checked { background: #4a9d6a; border-color: #4a9d6a; }
QPushButton.mini {
    background: #33384a; color: #dfe3ea; border: none; border-radius: 6px;
    padding: 5px 10px; font-size: 12px;
}
QPushButton.mini:hover { background: #424a60; }
QLabel.hint { color: #6f7889; font-size: 10px; }
"""


class ConnTestWorker(QThread):
    """后台跑连接自检，避免卡设置窗口。"""

    done = Signal(bool, str)

    def __init__(self, base_url, api_key, model, timeout, parent=None):
        super().__init__(parent)
        self.args = (base_url, api_key, model, timeout)

    def run(self):
        ok, msg = llm.test_connection(*self.args)
        self.done.emit(ok, msg)


class DiscoverWorker(QThread):
    """后台自动发现可用模型服务。"""

    done = Signal(list)

    def __init__(self, extra, parent=None):
        super().__init__(parent)
        self.extra = extra

    def run(self):
        try:
            self.done.emit(llm.discover(self.extra))
        except Exception:  # noqa: BLE001
            self.done.emit([])


class ModelsWorker(QThread):
    """后台拉某个端点的模型列表（切服务商/填完 Key 时用）。"""

    done = Signal(list)

    def __init__(self, base_url, api_key, parent=None):
        super().__init__(parent)
        self.args = (base_url, api_key)

    def run(self):
        try:
            self.done.emit(llm.list_models(*self.args, timeout=5))
        except llm.LLMError:
            self.done.emit([])


class SettingsWindow(QWidget):
    """改完即存（config.save_config），无"确定/取消"心智负担。"""

    changed = Signal()  # 通知主程序热更新（轮询间隔等）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notePanel")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(PANEL_CSS + EXTRA_CSS)
        self.setWindowTitle("DeskPet 设置")
        self.setFixedWidth(400)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(6)

        hdr = QHBoxLayout()
        t = QLabel("设置")
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

        # ---- 日报 ----
        g = QGroupBox("日报")
        fl = QFormLayout(g)
        fl.setSpacing(5)
        row = QHBoxLayout()
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("留空 = 默认目录")
        row.addWidget(self.dir_edit, 1)
        b_browse = QPushButton("浏览…")
        b_browse.setProperty("class", "mini")
        b_browse.setStyleSheet(
            "background:#33384a;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:5px 10px;font-size:12px;"
        )
        b_browse.clicked.connect(self._browse_dir)
        row.addWidget(b_browse)
        b_open = QPushButton("打开")
        b_open.setStyleSheet(b_browse.styleSheet())
        b_open.clicked.connect(self._open_dir)
        row.addWidget(b_open)
        fl.addRow("存放目录", row)
        self.dir_hint = QLabel("")
        self.dir_hint.setStyleSheet("color:#6f7889;font-size:10px;")
        fl.addRow("", self.dir_hint)
        root.addWidget(g)

        # ---- 时钟 ----
        g = QGroupBox("时钟")
        v = QVBoxLayout(g)
        v.setSpacing(4)
        self.cb_sec = QCheckBox("显示秒")
        self.cb_sec.toggled.connect(lambda on: self._set("show_seconds", on))
        v.addWidget(self.cb_sec)
        self.cb_date = QCheckBox("显示日期和星期")
        self.cb_date.toggled.connect(lambda on: self._set("show_date", on))
        v.addWidget(self.cb_date)
        self.cb_12 = QCheckBox("12 小时制")
        self.cb_12.toggled.connect(lambda on: self._set("hour12", on))
        v.addWidget(self.cb_12)
        root.addWidget(g)

        # ---- 互动与提醒 ----
        g = QGroupBox("互动与提醒")
        v = QVBoxLayout(g)
        v.setSpacing(4)
        self.cb_bubble = QCheckBox("点击企鹅时弹气泡语录")
        self.cb_bubble.toggled.connect(lambda on: self._set("bubble_on", on))
        v.addWidget(self.cb_bubble)
        self.cb_beep = QCheckBox("提醒到点 beep 提示音")
        self.cb_beep.toggled.connect(lambda on: self._set("beep_on", on))
        v.addWidget(self.cb_beep)
        self.cb_notify = QCheckBox("提醒到点发系统通知（托盘气泡）")
        self.cb_notify.toggled.connect(lambda on: self._set("sys_notify", on))
        v.addWidget(self.cb_notify)
        row = QHBoxLayout()
        row.addWidget(QLabel("提醒轮询间隔"))
        self.spin_poll = QSpinBox()
        self.spin_poll.setRange(5, 300)
        self.spin_poll.setSuffix(" 秒")
        self.spin_poll.valueChanged.connect(
            lambda v: (self._set("poll_sec", v), self.changed.emit()))
        row.addWidget(self.spin_poll)
        row.addStretch(1)
        v.addLayout(row)
        root.addWidget(g)

        # ---- AI 润色 ----
        g = QGroupBox("AI 润色（一键润色日报）")
        v = QVBoxLayout(g)
        v.setSpacing(5)
        row = QHBoxLayout()
        row.addWidget(QLabel("服务商"))
        self.cmb_prov = QComboBox()
        for key, meta in llm.PROVIDERS.items():
            self.cmb_prov.addItem(meta["label"], key)
        self.cmb_prov.currentIndexChanged.connect(self._on_provider)
        row.addWidget(self.cmb_prov, 1)
        v.addLayout(row)
        fl = QFormLayout()
        fl.setSpacing(5)
        self.llm_url = QLineEdit()
        self.llm_url.setPlaceholderText("OpenAI 兼容 Base URL")
        fl.addRow("Base URL", self.llm_url)
        self.llm_model = QComboBox()
        self.llm_model.setEditable(True)
        self.llm_model.lineEdit().setPlaceholderText("选一个或手输模型名")
        fl.addRow("模型", self.llm_model)
        self.llm_key = QLineEdit()
        self.llm_key.setEchoMode(QLineEdit.Password)
        self.llm_key.setPlaceholderText("本地服务可留空")
        fl.addRow("API Key", self.llm_key)
        row = QHBoxLayout()
        row.addWidget(QLabel("超时"))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 600)
        self.spin_timeout.setSuffix(" 秒")
        row.addWidget(self.spin_timeout)
        row.addStretch(1)
        fl.addRow("", row)
        v.addLayout(fl)
        row = QHBoxLayout()
        row.addWidget(QLabel("润色后"))
        self.cmb_save = QComboBox()
        self.cmb_save.addItem("另存为 .polished.md（保留原文）", "new")
        self.cmb_save.addItem("覆盖原日报文件", "overwrite")
        row.addWidget(self.cmb_save, 1)
        v.addLayout(row)
        row = QHBoxLayout()
        self.b_discover = QPushButton("自动发现")
        self.b_discover.setStyleSheet(
            "background:#3a5a6b;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:5px 12px;font-size:12px;"
        )
        self.b_discover.clicked.connect(self._discover)
        row.addWidget(self.b_discover)
        self.b_test = QPushButton("测试连接")
        self.b_test.setStyleSheet(
            "background:#3a6b4f;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:5px 12px;font-size:12px;"
        )
        self.b_test.clicked.connect(self._test_conn)
        row.addWidget(self.b_test)
        row.addStretch(1)
        v.addLayout(row)
        self.test_lbl = QLabel("点“自动发现”扫描本地模型服务；点“测试连接”自检当前填写值。")
        self.test_lbl.setStyleSheet("color:#6f7889;font-size:10px;")
        self.test_lbl.setWordWrap(True)
        v.addWidget(self.test_lbl)
        hint = QLabel("Key 仅存本机 config.json；切换服务商自动填默认地址/模型，可改。")
        hint.setStyleSheet("color:#6f7889;font-size:10px;")
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.llm_url.editingFinished.connect(
            lambda: (self._set("llm_base_url", self.llm_url.text().strip()),
                     self._refresh_models()))
        self.llm_model.lineEdit().editingFinished.connect(
            lambda: self._set("llm_model", self.llm_model.currentText().strip()))
        self.llm_model.currentIndexChanged.connect(
            lambda _i: self._set("llm_model", self.llm_model.currentText().strip()))
        self.llm_key.editingFinished.connect(
            lambda: (self._set("llm_api_key", self.llm_key.text()),
                     self._refresh_models()))
        self.spin_timeout.valueChanged.connect(
            lambda v: self._set("llm_timeout", v))
        self.cmb_save.currentIndexChanged.connect(
            lambda _i: self._set("polish_save", self.cmb_save.currentData()))
        root.addWidget(g)

        # ---- 系统 ----
        g = QGroupBox("系统")
        v = QVBoxLayout(g)
        v.setSpacing(4)
        self.cb_auto = QCheckBox("开机自启")
        self.cb_auto.toggled.connect(lambda on: autostart.set_enabled(on))
        v.addWidget(self.cb_auto)
        row = QHBoxLayout()
        b_reset = QPushButton("重置企鹅位置到屏幕右下角")
        b_reset.setStyleSheet(
            "background:#33384a;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:5px 10px;font-size:12px;"
        )
        b_reset.clicked.connect(self._reset_pos)
        row.addWidget(b_reset)
        row.addStretch(1)
        v.addLayout(row)
        root.addWidget(g)

        root.addStretch(1)
        self.load()

    # ---------------- 读写 ----------------

    def load(self):
        cfg = config.load_config()
        self._loading = True
        self.dir_edit.setText(cfg.get("reports_dir") or "")
        self.dir_hint.setText(
            f"当前生效：{config.reports_dir()}"
        )
        self.cb_sec.setChecked(bool(cfg.get("show_seconds", True)))
        self.cb_date.setChecked(bool(cfg.get("show_date", True)))
        self.cb_12.setChecked(bool(cfg.get("hour12", False)))
        self.cb_bubble.setChecked(bool(cfg.get("bubble_on", True)))
        self.cb_beep.setChecked(bool(cfg.get("beep_on", True)))
        self.cb_notify.setChecked(bool(cfg.get("sys_notify", True)))
        self.spin_poll.setValue(int(cfg.get("poll_sec", 15)))
        idx = self.cmb_prov.findData(cfg.get("llm_provider", "qwen"))
        self.cmb_prov.setCurrentIndex(max(0, idx))
        self.llm_url.setText(cfg.get("llm_base_url") or "")
        self._set_model_text(cfg.get("llm_model") or "")
        self.llm_key.setText(cfg.get("llm_api_key") or "")
        self.spin_timeout.setValue(int(cfg.get("llm_timeout", 60)))
        idx = self.cmb_save.findData(cfg.get("polish_save", "new"))
        self.cmb_save.setCurrentIndex(max(0, idx))
        self.cb_auto.setChecked(autostart.is_enabled())
        self._loading = False

    def _on_provider(self, _idx):
        if getattr(self, "_loading", False):
            return
        key = self.cmb_prov.currentData()
        meta = llm.PROVIDERS.get(key, {})
        self._set("llm_provider", key)
        hint = llm.env_key_hint(key)
        if hint and not self.llm_key.text():
            self.llm_key.setText(hint)
            self._set("llm_api_key", hint)
        if meta.get("base_url"):
            self.llm_url.setText(meta["base_url"])
            self._set_model_text(meta["model"])
            self._set("llm_base_url", meta["base_url"])
            self._set("llm_model", meta["model"])
        self._refresh_models()

    def _set_model_text(self, text: str):
        """设置模型框文本（不触发保存信号）。"""
        i = self.llm_model.findText(text)
        if i >= 0:
            self.llm_model.setCurrentIndex(i)
        else:
            self.llm_model.setCurrentIndex(-1)
            self.llm_model.setEditText(text)

    # ---------------- 自动发现 ----------------

    def _discover(self):
        self.b_discover.setEnabled(False)
        self.b_discover.setText("扫描中…")
        self.test_lbl.setStyleSheet("color:#8b93a3;font-size:10px;")
        self.test_lbl.setText("正在扫描本地模型服务与已配置端点…")
        extra = []
        prov = self.cmb_prov.currentData()
        meta = llm.PROVIDERS.get(prov, {})
        key = self.llm_key.text()
        if meta.get("base_url") and key:
            extra.append((meta["label"], meta["base_url"], key))
        cur = self.llm_url.text().strip()
        if cur and cur not in [b for _, b in llm.LOCAL_ENDPOINTS]:
            extra.append(("当前填写", cur, key))
        self._disc_worker = DiscoverWorker(extra, self)
        self._disc_worker.done.connect(self._discover_done)
        self._disc_worker.start()

    def _discover_done(self, found: list):
        self.b_discover.setEnabled(True)
        self.b_discover.setText("自动发现")
        if not found:
            self.test_lbl.setStyleSheet("color:#e06c75;font-size:10px;")
            self.test_lbl.setText(
                "未发现可用模型服务。本地可装 Ollama/llama-server；"
                "云端请先填 API Key 再点自动发现，或直接手填 Base URL/模型。")
            return
        self._found = found
        self.test_lbl.setStyleSheet("color:#7ee0a3;font-size:10px;")
        self.test_lbl.setText(
            "发现 " + "；".join(
                f"{f['source']}（{len(f['models'])} 个模型）" for f in found)
            + " —— 已填入第一个，可改。")
        first = found[0]
        self.llm_url.setText(first["base_url"])
        if first["api_key"]:
            self.llm_key.setText(first["api_key"])
        self._set("llm_base_url", first["base_url"])
        self._set("llm_api_key", first["api_key"])
        self._fill_models(first["models"])

    def _fill_models(self, models: list):
        cur = self.llm_model.currentText().strip()
        self.llm_model.blockSignals(True)
        self.llm_model.clear()
        self.llm_model.addItems(models)
        self.llm_model.blockSignals(False)
        if cur and cur in models:
            self._set_model_text(cur)
        elif models:
            self._set_model_text(models[0])
            self._set("llm_model", models[0])

    def _refresh_models(self):
        base = self.llm_url.text().strip()
        if not base:
            return
        self._models_worker = ModelsWorker(base, self.llm_key.text(), self)
        self._models_worker.done.connect(self._fill_models)
        self._models_worker.start()

    def _set(self, key, value):
        if getattr(self, "_loading", False):
            return
        cfg = config.load_config()
        cfg[key] = value
        config.save_config(cfg)

    # ---------------- 目录 ----------------

    def _browse_dir(self):
        cur = self.dir_edit.text() or str(config.reports_dir())
        d = QFileDialog.getExistingDirectory(self, "选择日报存放目录", cur)
        if not d:
            return
        self.dir_edit.setText(d)
        self._set("reports_dir", d)
        self.dir_hint.setText(f"当前生效：{config.reports_dir()}")

    def _open_dir(self):
        import os
        import subprocess

        d = config.reports_dir()
        if os.name == "nt":
            subprocess.Popen(["explorer", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])

    # ---------------- 连接自检 ----------------

    def _test_conn(self):
        self.b_test.setEnabled(False)
        self.b_test.setText("检测中…")
        self.test_lbl.setStyleSheet("color:#8b93a3;font-size:10px;")
        self.test_lbl.setText("正在连接，请稍候…")
        self._test_worker = ConnTestWorker(
            self.llm_url.text().strip(),
            self.llm_key.text(),
            self.llm_model.currentText().strip(),
            self.spin_timeout.value(),
            self,
        )
        self._test_worker.done.connect(self._test_done)
        self._test_worker.start()

    def _test_done(self, ok: bool, msg: str):
        self.b_test.setEnabled(True)
        self.b_test.setText("测试连接")
        if ok:
            self.test_lbl.setStyleSheet("color:#7ee0a3;font-size:10px;")
        else:
            self.test_lbl.setStyleSheet("color:#e06c75;font-size:10px;")
        self.test_lbl.setText(msg)

    def _reset_pos(self):
        cfg = config.load_config()
        cfg["pos_x"] = None
        cfg["pos_y"] = None
        config.save_config(cfg)
        QMessageBox.information(
            self, "DeskPet", "已重置，下次显示企鹅时回到屏幕右下角。"
        )

    def show_settings(self):
        self.load()
        self.show()
        self.raise_()
        self.activateWindow()

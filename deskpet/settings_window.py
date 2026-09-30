"""设置窗口：日报目录 + 时钟/互动/提醒/系统各项偏好。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import autostart, config, llm, skills
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
QComboBox {
    background: #1b1d25; color: #eceff4; border: 1px solid #3b3f4d;
    border-radius: 6px; padding: 5px 8px; font-size: 12px;
}
QComboBox::drop-down { border-left: 1px solid #3b3f4d; width: 26px; }
QComboBox QAbstractItemView {
    background: #23262f; color: #eceff4; selection-background-color: #3a5a86;
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

COMBO_POPUP_CSS = """
QListView {
    background-color: #23262f;
    color: #eceff4;
    border: 1px solid #454b5b;
    outline: 0;
    selection-background-color: #3a5a86;
    selection-color: #ffffff;
}
QListView::item { min-height: 24px; padding: 4px 8px; }
QListView::item:hover { background-color: #303849; color: #ffffff; }
QListView::item:selected { background-color: #3a5a86; color: #ffffff; }
"""


def apply_combo_popup_theme(combo: QComboBox) -> None:
    """给独立弹出的下拉列表显式应用暗色主题与调色板。"""
    view = combo.view()
    view.setStyleSheet(COMBO_POPUP_CSS)
    palette = view.palette()
    palette.setColor(QPalette.Base, QColor("#23262f"))
    palette.setColor(QPalette.Window, QColor("#23262f"))
    palette.setColor(QPalette.Text, QColor("#eceff4"))
    palette.setColor(QPalette.WindowText, QColor("#eceff4"))
    palette.setColor(QPalette.Highlight, QColor("#3a5a86"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    view.setPalette(palette)


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
        self.resize(430, 720)
        self.setMinimumWidth(420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll.viewport().setStyleSheet("background:transparent;")
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(6)
        scroll.setWidget(body)
        outer.addWidget(scroll)

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
        self.dir_edit.editingFinished.connect(self._apply_reports_dir)
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
        self.spin_poll.valueChanged.connect(lambda v: self._set("poll_sec", v))
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
        apply_combo_popup_theme(self.cmb_prov)
        self.cmb_prov.currentIndexChanged.connect(self._on_provider)
        row.addWidget(self.cmb_prov, 1)
        v.addLayout(row)
        fl = QFormLayout()
        fl.setSpacing(5)
        self.llm_url = QLineEdit()
        self.llm_url.setPlaceholderText("OpenAI 兼容 Base URL")
        fl.addRow("Base URL", self.llm_url)
        self.llm_model = QComboBox()
        self.llm_model.setEditable(False)
        self.llm_model.setMaxVisibleItems(12)
        apply_combo_popup_theme(self.llm_model)
        self.llm_model.setPlaceholderText("自动发现后选择模型")
        fl.addRow("模型选择", self.llm_model)
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
        apply_combo_popup_theme(self.cmb_save)
        row.addWidget(self.cmb_save, 1)
        v.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("润色技能"))
        self.cmb_skill = QComboBox()
        apply_combo_popup_theme(self.cmb_skill)
        self.cmb_skill.currentIndexChanged.connect(self._on_skill)
        row.addWidget(self.cmb_skill, 1)
        b_add = QPushButton("添加…")
        b_add.setStyleSheet(
            "background:#33384a;color:#dfe3ea;border:none;border-radius:6px;"
            "padding:5px 10px;font-size:12px;"
        )
        b_add.clicked.connect(self._add_skill)
        row.addWidget(b_add)
        b_del = QPushButton("删除")
        b_del.setStyleSheet(b_add.styleSheet())
        b_del.clicked.connect(self._del_skill)
        row.addWidget(b_del)
        v.addLayout(row)
        self.skill_hint = QLabel("")
        self.skill_hint.setStyleSheet("color:#6f7889;font-size:10px;")
        self.skill_hint.setWordWrap(True)
        v.addWidget(self.skill_hint)
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
        self.test_lbl = QLabel(
            "点“自动发现”扫描模型服务；发现后从“模型选择”下拉框切换模型。"
        )
        self.test_lbl.setStyleSheet("color:#6f7889;font-size:10px;")
        self.test_lbl.setWordWrap(True)
        v.addWidget(self.test_lbl)
        hint = QLabel("Key 仅存本机 config.json；切换服务商自动填默认地址/模型，可改。")
        hint.setStyleSheet("color:#6f7889;font-size:10px;")
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.llm_url.editingFinished.connect(lambda: (self._save_form(), self._refresh_models()))
        self.llm_model.currentIndexChanged.connect(lambda _i: self._save_form())
        self.llm_key.editingFinished.connect(lambda: (self._save_form(), self._refresh_models()))
        self.spin_timeout.valueChanged.connect(lambda v: self._set("llm_timeout", v))
        self.cmb_save.currentIndexChanged.connect(
            lambda _i: self._set("polish_save", self.cmb_save.currentData())
        )
        root.addWidget(g)

        # ---- 系统 ----
        g = QGroupBox("系统")
        v = QVBoxLayout(g)
        v.setSpacing(4)
        self.cb_auto = QCheckBox("开机自启")
        self.cb_auto.toggled.connect(self._toggle_autostart)
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
        self.dir_hint.setText(f"当前生效：{config.reports_dir()}")
        self.cb_sec.setChecked(bool(cfg.get("show_seconds", True)))
        self.cb_date.setChecked(bool(cfg.get("show_date", True)))
        self.cb_12.setChecked(bool(cfg.get("hour12", False)))
        self.cb_bubble.setChecked(bool(cfg.get("bubble_on", True)))
        self.cb_beep.setChecked(bool(cfg.get("beep_on", True)))
        self.cb_notify.setChecked(bool(cfg.get("sys_notify", True)))
        self.spin_poll.setValue(int(cfg.get("poll_sec", 15)))
        idx = self.cmb_prov.findData(cfg.get("llm_provider", "qwen"))
        self.cmb_prov.setCurrentIndex(max(0, idx))
        prov = self.cmb_prov.currentData()
        self._form_provider = prov
        self._load_profile_to_form(prov)
        self.spin_timeout.setValue(int(cfg.get("llm_timeout", 60)))
        idx = self.cmb_save.findData(cfg.get("polish_save", "new"))
        self.cmb_save.setCurrentIndex(max(0, idx))
        self._reload_skills()
        self.cb_auto.setChecked(autostart.is_enabled())
        self._loading = False

    def _on_provider(self, _idx):
        if getattr(self, "_loading", False):
            return
        new = self.cmb_prov.currentData()
        old = getattr(self, "_form_provider", None)
        if old and old != new:
            # 表单里还是旧服务商的值，先归档再换
            self._save_form()
        self._set("llm_provider", new)
        self._form_provider = new
        self._load_profile_to_form(new)
        self._refresh_models()

    # ---------------- 按服务商存档 ----------------

    def _save_form(self):
        """把表单当前值存入"表单正在显示的服务商"的档案并落盘。"""
        prov = getattr(self, "_form_provider", None) or self.cmb_prov.currentData()
        cfg = config.load_config()
        config.set_llm_profile(
            cfg,
            prov,
            {
                "base_url": self.llm_url.text().strip(),
                "model": self.llm_model.currentText().strip(),
                "api_key": self.llm_key.text(),
            },
        )
        config.save_config(cfg)

    def _load_profile_to_form(self, provider: str):
        """把某服务商档案读回表单；空档案用预设地址/环境变量 Key 兜底（不落盘）。"""
        cfg = config.load_config()
        prof = config.get_llm_profile(cfg, provider)
        base, model, key = prof["base_url"], prof["model"], prof["api_key"]
        meta = llm.PROVIDERS.get(provider, {})
        if not base and meta.get("base_url"):
            base, model = meta["base_url"], meta.get("model", "")
        if not key:
            key = llm.env_key_hint(provider)
        self.llm_url.blockSignals(True)
        self.llm_key.blockSignals(True)
        self.llm_model.blockSignals(True)
        self.llm_url.setText(base)
        self.llm_key.setText(key)
        self._set_model_text(model)
        self.llm_url.blockSignals(False)
        self.llm_key.blockSignals(False)
        self.llm_model.blockSignals(False)

    def _set_model_text(self, text: str):
        """设置模型框文本（不触发保存信号）。"""
        i = self.llm_model.findText(text)
        if i < 0 and text:
            self.llm_model.addItem(text)
            i = self.llm_model.count() - 1
        if i < 0:
            self.llm_model.setCurrentIndex(-1)
        else:
            self.llm_model.setCurrentIndex(i)

    # ---------------- 自动发现 ----------------

    def _discover(self):
        self.b_discover.setEnabled(False)
        self.b_discover.setText("扫描中…")
        self.test_lbl.setStyleSheet("color:#8b93a3;font-size:10px;")
        self.test_lbl.setText("正在扫描本地模型服务与已配置端点…")
        extra = []
        key = self.llm_key.text()
        cur = self.llm_url.text().strip()
        if cur:
            extra.append(("当前配置", cur, key))
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
                "云端请先填 API Key 再点自动发现，或直接手填 Base URL/模型。"
            )
            return
        self._found = found
        current_url = llm.normalize_base_url(self.llm_url.text())
        preferred = next(
            (
                index
                for index, entry in enumerate(found)
                if llm.normalize_base_url(entry["base_url"]) == current_url
            ),
            0,
        )
        labels = [
            f"{entry['source']} · {entry['base_url']} · {len(entry['models'])} 个模型"
            for entry in found
        ]
        chosen = preferred
        if len(found) > 1:
            label, accepted = QInputDialog.getItem(
                self,
                "选择模型服务",
                "发现多个可用服务，请选择要使用的一个：",
                labels,
                preferred,
                False,
            )
            if not accepted:
                self.test_lbl.setStyleSheet("color:#8b93a3;font-size:10px;")
                self.test_lbl.setText(f"发现 {len(found)} 个可用服务；已取消选择，配置未更改。")
                return
            chosen = labels.index(label)
        self._apply_discovered(found[chosen], len(found))

    def _apply_discovered(self, entry: dict, total: int):
        """应用用户选择的发现结果；本地服务放进“自定义”档案。"""
        if entry.get("local") and self.cmb_prov.currentData() != "custom":
            index = self.cmb_prov.findData("custom")
            if index >= 0:
                self.cmb_prov.setCurrentIndex(index)

        self.llm_url.setText(entry["base_url"])
        # 本地端点通常免 Key，必须清掉表单里可能残留的云端 Key。
        self.llm_key.setText(entry.get("api_key", "") if not entry.get("local") else "")
        self._fill_models(entry["models"])
        self._save_form()
        self.test_lbl.setStyleSheet("color:#7ee0a3;font-size:10px;")
        self.test_lbl.setText(
            f"共发现 {total} 个服务；已选择 {entry['source']}，"
            f"加载 {len(entry['models'])} 个模型。"
        )

    def _fill_models(self, models: list):
        if not models:
            return  # 拉取失败/为空时不动用户已填的模型名
        cur = self.llm_model.currentText().strip()
        self.llm_model.blockSignals(True)
        self.llm_model.clear()
        self.llm_model.addItems(models)
        self.llm_model.blockSignals(False)
        if cur and cur in models:
            self._set_model_text(cur)
        elif models:
            self._set_model_text(models[0])
            self._save_form()

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
        self.changed.emit()

    # ---------------- 目录 ----------------

    def _browse_dir(self):
        cur = self.dir_edit.text() or str(config.reports_dir())
        d = QFileDialog.getExistingDirectory(self, "选择日报存放目录", cur)
        if not d:
            return
        self.dir_edit.setText(d)
        self._set("reports_dir", d)
        self.dir_hint.setText(f"当前生效：{config.reports_dir()}")

    def _apply_reports_dir(self):
        if getattr(self, "_loading", False):
            return
        value = self.dir_edit.text().strip()
        if value:
            path = Path(value).expanduser()
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(self, "目录不可用", f"无法使用该目录：{exc}")
                return
            value = str(path.resolve())
            self.dir_edit.setText(value)
        else:
            value = None
        self._set("reports_dir", value)
        self.dir_hint.setText(f"当前生效：{config.reports_dir()}")

    def _open_dir(self):
        import os
        import subprocess

        d = config.reports_dir()
        if os.name == "nt":
            subprocess.Popen(["explorer", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])

    # ---------------- 润色技能 ----------------

    def _reload_skills(self):
        cur = config.load_config().get("polish_skill", "") or ""
        self.cmb_skill.blockSignals(True)
        self.cmb_skill.clear()
        self.cmb_skill.addItem("内置润色提示", "")
        for s in skills.list_skills():
            self.cmb_skill.addItem(s["name"], s["name"])
        i = self.cmb_skill.findData(cur)
        self.cmb_skill.setCurrentIndex(max(0, i))
        self.cmb_skill.blockSignals(False)
        self._update_skill_hint()

    def _update_skill_hint(self):
        name = self.cmb_skill.currentData()
        if not name:
            self.skill_hint.setText("未选技能：润色用内置提示词。")
            return
        sk = skills.get_skill(name)
        desc = sk["description"] if sk else ""
        self.skill_hint.setText(f"{desc}" if desc else f"技能：{name}")

    def _on_skill(self, _i):
        if getattr(self, "_loading", False):
            return
        self._set("polish_skill", self.cmb_skill.currentData() or "")
        self._update_skill_hint()

    def _add_skill(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择技能文件（.md）", str(Path.home()), "Markdown (*.md);;所有文件 (*)"
        )
        if not path:
            return
        try:
            s = skills.add_skill(path)
        except (OSError, UnicodeDecodeError) as e:
            QMessageBox.warning(self, "添加技能失败", f"读取文件出错：{e}")
            return
        self._reload_skills()
        i = self.cmb_skill.findData(s["name"])
        if i >= 0:
            self.cmb_skill.setCurrentIndex(i)
            self._on_skill(i)
        QMessageBox.information(self, "DeskPet", f"已添加技能「{s['name']}」并选中。")

    def _del_skill(self):
        name = self.cmb_skill.currentData()
        if not name:
            QMessageBox.information(self, "DeskPet", "内置提示不可删除。")
            return
        if skills.remove_skill(name):
            cfg = config.load_config()
            if cfg.get("polish_skill") == name:
                cfg["polish_skill"] = ""
                config.save_config(cfg)
            self._reload_skills()

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
        cfg["screen_name"] = ""
        cfg["pos_rel_x"] = None
        cfg["pos_rel_y"] = None
        config.save_config(cfg)
        QMessageBox.information(self, "DeskPet", "已重置，下次显示企鹅时回到屏幕右下角。")

    def _toggle_autostart(self, on: bool):
        if getattr(self, "_loading", False):
            return
        if autostart.set_enabled(on):
            return
        self.cb_auto.blockSignals(True)
        self.cb_auto.setChecked(not on)
        self.cb_auto.blockSignals(False)
        QMessageBox.warning(self, "开机自启", "无法更新开机自启设置，请检查目录权限。")

    def show_settings(self):
        self.load()
        self.show()
        self.raise_()
        self.activateWindow()

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from deskpet.settings_window import SettingsWindow


def test_discovered_models_populate_visible_dropdown(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKPET_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = SettingsWindow()

    entry = {
            "source": "llama-server",
            "base_url": "http://127.0.0.1:8080/v1",
            "api_key": "",
            "models": ["model-a", "model-b"],
            "local": True,
        }
    window._apply_discovered(entry, [entry])

    assert window.cmb_prov.currentData() == "custom"
    assert [window.llm_model.itemText(i) for i in range(window.llm_model.count())] == [
        "model-a",
        "model-b",
    ]
    assert window.llm_model.isEditable() is False
    assert window.llm_model.styleSheet() == window.cmb_prov.styleSheet()
    window.llm_model.setCurrentIndex(1)
    assert window.llm_model.currentText() == "model-b"
    window.close()
    app.processEvents()


def test_discovery_uses_current_service_without_popup(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKPET_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = SettingsWindow()
    window.llm_url.setText("https://current.example/v1")

    window._discover_done(
        [
            {
                "source": "llama-server",
                "base_url": "http://127.0.0.1:8080/v1",
                "api_key": "",
                "models": ["local-model"],
                "local": True,
            },
            {
                "source": "当前配置",
                "base_url": "https://current.example/v1",
                "api_key": "key",
                "models": ["cloud-a", "cloud-b"],
                "local": False,
            },
        ]
    )

    assert window.llm_url.text() == "https://current.example/v1"
    assert [window.llm_model.itemText(i) for i in range(window.llm_model.count())] == [
        "cloud-a",
        "cloud-b",
    ]
    assert "llama-server（1 个模型）" in window.test_lbl.text()
    assert "当前配置（2 个模型）" in window.test_lbl.text()
    window.close()
    app.processEvents()


def test_all_combo_popups_use_dark_theme(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKPET_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = SettingsWindow()

    for combo in (window.cmb_prov, window.llm_model, window.cmb_save, window.cmb_skill):
        palette = combo.view().palette()
        assert palette.color(QPalette.Base).name() == "#23262f"
        assert palette.color(QPalette.Text).name() == "#eceff4"
        assert palette.color(QPalette.Highlight).name() == "#3a5a86"
        assert "background-color: #23262f" in combo.view().styleSheet()

    window.close()
    app.processEvents()

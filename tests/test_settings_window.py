from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from deskpet.settings_window import SettingsWindow


def test_discovered_models_populate_visible_dropdown(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKPET_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    window = SettingsWindow()

    window._apply_discovered(
        {
            "source": "llama-server",
            "base_url": "http://127.0.0.1:8080/v1",
            "api_key": "",
            "models": ["model-a", "model-b"],
            "local": True,
        },
        1,
    )

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

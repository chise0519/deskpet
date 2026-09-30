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
    assert window.b_model_dropdown.isEnabled()
    window.llm_model.setCurrentIndex(1)
    assert window.llm_model.currentText() == "model-b"
    window.close()
    app.processEvents()

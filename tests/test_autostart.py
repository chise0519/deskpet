import sys

from deskpet import autostart


def test_linux_autostart_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert autostart.is_enabled() is False
    assert autostart.set_enabled(True) is True
    path = tmp_path / "autostart" / autostart.AUTOSTART_FILE
    text = path.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Exec=" in text
    assert "deskpet" in text
    assert autostart.is_enabled() is True
    assert autostart.set_enabled(False) is True
    assert not path.exists()

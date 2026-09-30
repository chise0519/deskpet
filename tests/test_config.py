import os

from deskpet import config


def test_private_atomic_config(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKPET_HOME", str(tmp_path))
    monkeypatch.setattr(config, "_layout_ready_for", None)
    config.save_config({"llm_profiles": {"custom": {"api_key": "secret"}}})
    path = tmp_path / "config.json"
    assert path.exists()
    assert config.load_config()["llm_profiles"]["custom"]["api_key"] == "secret"
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
        assert tmp_path.stat().st_mode & 0o777 == 0o700
    assert list(tmp_path.glob(".config.*.tmp")) == []


def test_xdg_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("DESKPET_HOME", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setattr(config, "_layout_ready_for", None)
    assert config.config_dir() == tmp_path / "config" / "deskpet"
    assert config.data_dir() == tmp_path / "data" / "deskpet"
    assert config.cache_dir() == tmp_path / "cache" / "deskpet"

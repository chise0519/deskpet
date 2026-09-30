"""全局配置：跨平台路径、安全持久化、常量与企鹅语录。"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path

APP_NAME = "DeskPet"
APP_ID = "io.github.chise0519.deskpet"
VERSION = "1.1.0"

_log = logging.getLogger(__name__)
_layout_lock = threading.Lock()
_layout_ready_for: tuple[str, str, str] | None = None


def _override_root() -> Path | None:
    """测试/便携运行时可用 DESKPET_HOME 把全部数据放进一个目录。"""
    value = os.environ.get("DESKPET_HOME")
    if value:
        return Path(value).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    return None


def _raw_config_dir() -> Path:
    override = _override_root()
    if override:
        return override
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "deskpet"


def _raw_data_dir() -> Path:
    override = _override_root()
    if override:
        return override
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "deskpet"


def _raw_cache_dir() -> Path:
    override = _override_root()
    if override:
        return override / "cache"
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "deskpet"


def _secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        try:
            path.chmod(0o700)
        except OSError:
            _log.warning("无法收紧目录权限：%s", path, exc_info=True)


def _copy_if_missing(src: Path, dst: Path) -> None:
    if not src.exists() or dst.exists():
        return
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _ensure_layout() -> None:
    """创建私有目录，并从旧 Linux 目录复制一次数据（旧目录保留作回滚）。"""
    global _layout_ready_for
    cfg_dir, app_dir, cache = _raw_config_dir(), _raw_data_dir(), _raw_cache_dir()
    key = (str(cfg_dir), str(app_dir), str(cache))
    if _layout_ready_for == key:
        return
    with _layout_lock:
        if _layout_ready_for == key:
            return
        for path in {cfg_dir, app_dir, cache}:
            _secure_dir(path)

        if os.name != "nt" and _override_root() is None:
            legacy = Path.home() / ".deskpet" / APP_NAME
            if legacy.exists():
                try:
                    _copy_if_missing(legacy / "config.json", cfg_dir / "config.json")
                    _copy_if_missing(legacy / "deskpet.db", app_dir / "deskpet.db")
                    _copy_if_missing(legacy / "reports", app_dir / "reports")
                    _copy_if_missing(legacy / "skills", app_dir / "skills")
                except OSError:
                    _log.exception("从旧目录迁移 DeskPet 数据失败：%s", legacy)

        for sensitive in (cfg_dir / "config.json", app_dir / "deskpet.db"):
            if sensitive.exists() and os.name != "nt":
                try:
                    sensitive.chmod(0o600)
                except OSError:
                    _log.warning("无法收紧文件权限：%s", sensitive, exc_info=True)
        _layout_ready_for = key


def config_dir() -> Path:
    _ensure_layout()
    return _raw_config_dir()


def data_dir() -> Path:
    """数据库、技能和日报目录；Linux 遵循 XDG_DATA_HOME。"""
    _ensure_layout()
    return _raw_data_dir()


def cache_dir() -> Path:
    _ensure_layout()
    return _raw_cache_dir()


def config_path() -> Path:
    return config_dir() / "config.json"


def db_path() -> Path:
    return data_dir() / "deskpet.db"


def reports_dir() -> Path:
    """日报目录：设置里可自定义，未设置时用默认目录。"""
    custom = load_config().get("reports_dir")
    p = Path(custom) if custom else data_dir() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


_DEFAULTS = {
    "pos_x": None,
    "pos_y": None,
    "reports_dir": None,
    "show_seconds": True,
    "show_date": True,
    "hour12": False,
    "bubble_on": True,
    "beep_on": True,
    "sys_notify": True,
    "poll_sec": 15,
    "llm_provider": "qwen",
    "llm_timeout": 60,
    "polish_save": "new",  # new=另存.polished.md / overwrite=覆盖原文件
    "polish_skill": "",  # 空=内置润色提示；否则为技能名
    "screen_name": "",
    "pos_rel_x": None,
    "pos_rel_y": None,
}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    f = config_path()
    if f.exists():
        try:
            cfg.update(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            _log.exception("读取配置失败，将使用安全默认值：%s", f)
    # 迁移：老版本只有一套 llm_* 字段，按当前服务商归档为 llm_profiles
    if not isinstance(cfg.get("llm_profiles"), dict):
        cfg["llm_profiles"] = {
            cfg.get("llm_provider", "qwen"): {
                "base_url": cfg.get("llm_base_url", "") or "",
                "model": cfg.get("llm_model", "") or "",
                "api_key": cfg.get("llm_api_key", "") or "",
            }
        }
    # 敏感信息只保留在新 profiles 结构，避免旧字段留下重复 Key。
    for old_key in ("llm_base_url", "llm_model", "llm_api_key"):
        cfg.pop(old_key, None)
    return cfg


def get_llm_profile(cfg: dict, provider: str) -> dict:
    """取某服务商的配置档案 {base_url, model, api_key}。

    无 llm_profiles 的字典（单测直传的老式扁平配置）回退到扁平字段。
    """
    profiles = cfg.get("llm_profiles")
    if not isinstance(profiles, dict):
        return {
            "base_url": cfg.get("llm_base_url", "") or "",
            "model": cfg.get("llm_model", "") or "",
            "api_key": cfg.get("llm_api_key", "") or "",
        }
    prof = dict(profiles.get(provider, {}))
    for k in ("base_url", "model", "api_key"):
        prof.setdefault(k, "")
    return prof


def set_llm_profile(cfg: dict, provider: str, values: dict) -> dict:
    """把某服务商的档案写回 cfg（不落盘，调用方自行 save_config）。"""
    profiles = cfg.setdefault("llm_profiles", {})
    profiles[provider] = {k: (values.get(k, "") or "") for k in ("base_url", "model", "api_key")}
    return cfg


def save_config(cfg: dict) -> None:
    """以 0600 权限原子写入配置；失败会抛错并写日志，不再静默丢设置。"""
    f = config_path()
    payload = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
    fd = -1
    temp_name = ""
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=f.parent)
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, f)
        temp_name = ""
        if os.name != "nt":
            f.chmod(0o600)
    except OSError:
        _log.exception("保存配置失败：%s", f)
        raise
    finally:
        if fd >= 0:
            os.close(fd)
        if temp_name:
            try:
                Path(temp_name).unlink()
            except OSError:
                pass


# 点击企鹅时的随机气泡语录
QUOTES = [
    "嘎嘎！有何吩咐",
    "今天也要加油鸭！",
    "摸鱼被我发现了",
    "喝水时间到~",
    "站起来动一动",
    "有事记得记下来",
    "专注 25 分钟试试",
    "你最棒了，嘎！",
    "别忘了看提醒哦",
    "休息一下眼睛吧",
    "日报别忘了写~",
    "嘎？点我干啥",
]

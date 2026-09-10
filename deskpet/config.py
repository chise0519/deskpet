"""全局配置：路径、常量、企鹅语录。"""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "DeskPet"
VERSION = "1.0.0"


def data_dir() -> Path:
    """运行时数据目录：%APPDATA%/DeskPet"""
    base = os.environ.get("APPDATA") or str(Path.home() / ".deskpet")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


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
    "reports_dir": None,      # None = 默认 %APPDATA%/DeskPet/reports
    "show_seconds": True,
    "show_date": True,
    "hour12": False,
    "bubble_on": True,
    "beep_on": True,
    "sys_notify": True,
    "poll_sec": 15,
    "llm_provider": "qwen",
    "llm_base_url": "",
    "llm_model": "",
    "llm_api_key": "",
    "llm_timeout": 60,
    "polish_save": "new",   # new=另存.polished.md / overwrite=覆盖原文件
    "polish_skill": "",     # 空=内置润色提示；否则为技能名
}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    f = data_dir() / "config.json"
    if f.exists():
        try:
            cfg.update(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    # 迁移：老版本只有一套 llm_* 字段，按当前服务商归档为 llm_profiles
    if not isinstance(cfg.get("llm_profiles"), dict):
        cfg["llm_profiles"] = {
            cfg.get("llm_provider", "qwen"): {
                "base_url": cfg.get("llm_base_url", "") or "",
                "model": cfg.get("llm_model", "") or "",
                "api_key": cfg.get("llm_api_key", "") or "",
            }
        }
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
    profiles[provider] = {
        k: (values.get(k, "") or "") for k in ("base_url", "model", "api_key")
    }
    return cfg


def save_config(cfg: dict) -> None:
    f = data_dir() / "config.json"
    try:
        f.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
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

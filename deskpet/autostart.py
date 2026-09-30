"""跨平台开机自启：Windows 注册表 / Linux XDG Autostart。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import APP_ID, APP_NAME

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_FILE = f"{APP_ID}.desktop"


def _command() -> str:
    root = Path(__file__).resolve().parent.parent
    if getattr(sys, "frozen", False):  # PyInstaller 打包后
        return f'"{sys.executable}"'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    return f'"{exe}" "{root / "run_deskpet.py"}"'


def _linux_args() -> list[str]:
    root = Path(__file__).resolve().parent.parent
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    console_script = Path(sys.executable).with_name("deskpet")
    if console_script.is_file():
        return [str(console_script.resolve())]
    return [str(Path(sys.executable).resolve()), str(root / "run_deskpet.py")]


def _linux_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / AUTOSTART_FILE


def _desktop_exec(args: list[str]) -> str:
    def quote(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped = escaped.replace("`", "\\`").replace("$", "\\$")
        return f'"{escaped}"'

    return " ".join(quote(arg) for arg in args)


def _linux_content() -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            f"Name={APP_NAME}",
            "Comment=Desktop pet, quick notes and reminders",
            f"Exec={_desktop_exec(_linux_args())}",
            f"Icon={APP_ID}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "StartupNotify=false",
            "",
        ]
    )


def is_enabled() -> bool:
    if sys.platform.startswith("linux"):
        path = _linux_path()
        if not path.is_file():
            return False
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return False
        return "Hidden=true" not in text and "X-GNOME-Autostart-enabled=false" not in text
    if sys.platform != "win32":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except OSError:
        return False


def set_enabled(on: bool) -> bool:
    if sys.platform.startswith("linux"):
        path = _linux_path()
        try:
            if on:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                path.parent.chmod(0o700)
                tmp = path.with_suffix(".desktop.tmp")
                tmp.write_text(_linux_content(), encoding="utf-8")
                tmp.chmod(0o600)
                os.replace(tmp, path)
            else:
                path.unlink(missing_ok=True)
            return True
        except OSError:
            return False
    if sys.platform != "win32":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False

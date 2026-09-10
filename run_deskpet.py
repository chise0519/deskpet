#!/usr/bin/env python
"""DeskPet 启动脚本（供 run.bat / 开机自启调用）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deskpet.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

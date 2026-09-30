"""使用操作系统字体，避免依赖 Windows 专用字体。"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase


def general(point_size: int, weight=QFont.Normal) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


def fixed(point_size: int, weight=QFont.Normal) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setPointSize(point_size)
    font.setWeight(weight)
    font.setStyleHint(QFont.Monospace)
    return font

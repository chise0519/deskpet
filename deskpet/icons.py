"""现代线性图标：QPainter 代码绘制（Feather 风格描边），无图片素材，与深色 UI 统一。

用法: from .icons import icon;  menu.addAction(icon("note"), "速记", ...)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_CACHE: dict = {}

COLORS = {
    "note": "#8ab4f8",   # 速记：笔
    "bell": "#f2c14e",   # 提醒：铃
    "doc": "#7ee0a3",    # 日报：文档
    "quit": "#e06c75",   # 退出：电源
    "eye": "#b39ddb",    # 显示/隐藏：眼睛
    "gear": "#9fb3c8",   # 设置：齿轮
    "spark": "#c792ea",  # 润色：星光
}


def _canvas():
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    return pm, p


def _pen(p, color, w=3.2):
    p.setPen(QPen(QColor(color), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)


def _draw_note(p, c):
    """钢笔尖 + 下划线"""
    _pen(p, c)
    path = QPainterPath()
    path.moveTo(30, 8)
    path.lineTo(40, 18)
    path.lineTo(16, 42)
    path.lineTo(6, 44)
    path.lineTo(8, 34)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(26, 44, 44, 44)


def _draw_bell(p, c):
    """铃铛 + 铃舌"""
    _pen(p, c)
    path = QPainterPath()
    path.moveTo(36, 16)
    path.arcTo(12, 4, 24, 24, 0, 180)      # 顶部圆拱
    path.cubicTo(12, 26, 9, 31, 6, 34)
    path.lineTo(42, 34)
    path.cubicTo(39, 31, 36, 26, 36, 16)
    p.drawPath(path)
    tongue = QPainterPath()
    tongue.moveTo(19, 39)
    tongue.arcTo(18, 36, 12, 10, 180, 180)  # 下半弧
    p.drawPath(tongue)


def _draw_doc(p, c):
    """折角文档 + 两行文字"""
    _pen(p, c)
    path = QPainterPath()
    path.moveTo(28, 6)
    path.lineTo(14, 6)
    path.quadTo(10, 6, 10, 10)
    path.lineTo(10, 38)
    path.quadTo(10, 42, 14, 42)
    path.lineTo(34, 42)
    path.quadTo(38, 42, 38, 38)
    path.lineTo(38, 16)
    path.closeSubpath()
    p.drawPath(path)
    fold = QPainterPath()
    fold.moveTo(28, 6)
    fold.lineTo(28, 16)
    fold.lineTo(38, 16)
    p.drawPath(fold)
    p.drawLine(17, 25, 31, 25)
    p.drawLine(17, 32, 27, 32)


def _draw_quit(p, c):
    """电源符号：顶部留口的圆 + 竖线。

    Qt 角度=度，0°在3点方向、逆时针为正；顶部=90°，
    故从 125° 起扫 290°，缺口落在顶部中央。
    """
    _pen(p, c)
    path = QPainterPath()
    path.arcTo(10, 10, 28, 28, 125, 290)
    p.drawPath(path)
    p.drawLine(24, 4, 24, 20)


def _draw_eye(p, c):
    """眼睛 + 瞳孔"""
    _pen(p, c)
    path = QPainterPath()
    path.moveTo(4, 24)
    path.cubicTo(12, 10, 36, 10, 44, 24)
    path.cubicTo(36, 38, 12, 38, 4, 24)
    path.closeSubpath()
    p.drawPath(path)
    p.drawEllipse(QPointF(24, 24), 6, 6)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(c))
    p.drawEllipse(QPointF(24, 24), 2.6, 2.6)


def _draw_gear(p, c):
    """齿轮：外圈8齿 + 中心圆孔"""
    import math as _m

    _pen(p, c)
    p.drawEllipse(QPointF(24, 24), 7, 7)
    p.drawEllipse(QPointF(24, 24), 2.6, 2.6)
    for i in range(8):
        a = _m.radians(i * 45)
        x1, y1 = 24 + 12 * _m.cos(a), 24 + 12 * _m.sin(a)
        x2, y2 = 24 + 18 * _m.cos(a), 24 + 18 * _m.sin(a)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _draw_spark(p, c):
    """星光：四角星 + 小星点"""
    _pen(p, c)
    path = QPainterPath()
    path.moveTo(24, 6)
    path.lineTo(28, 20)
    path.lineTo(42, 24)
    path.lineTo(28, 28)
    path.lineTo(24, 42)
    path.lineTo(20, 28)
    path.lineTo(6, 24)
    path.lineTo(20, 20)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(37, 8), QPointF(37, 14))
    p.drawLine(QPointF(34, 11), QPointF(40, 11))


_DRAWERS = {
    "note": _draw_note,
    "bell": _draw_bell,
    "doc": _draw_doc,
    "quit": _draw_quit,
    "eye": _draw_eye,
    "gear": _draw_gear,
    "spark": _draw_spark,
}


def icon(name: str, size: int = 18) -> QIcon:
    key = (name, size)
    if key in _CACHE:
        return _CACHE[key]
    pm, p = _canvas()
    _DRAWERS[name](p, COLORS.get(name, "#c9d1e0"))
    p.end()
    big = pm.scaled(size * 2, size * 2, Qt.KeepAspectRatio,
                    Qt.SmoothTransformation)
    ic = QIcon(big)
    _CACHE[key] = ic
    return ic

"""多显示器定位工具：始终以全局锚点或保存位置选择目标屏幕。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QSize
from PySide6.QtGui import QGuiApplication, QScreen


def as_point(value) -> QPoint:
    if isinstance(value, QPoint):
        return value
    if isinstance(value, QPointF):
        return value.toPoint()
    return QPoint(int(value.x()), int(value.y()))


def screen_named(name: str | None) -> QScreen | None:
    if not name:
        return None
    return next((screen for screen in QGuiApplication.screens() if screen.name() == name), None)


def screen_at(value) -> QScreen:
    point = as_point(value)
    screen = QGuiApplication.screenAt(point)
    if screen is not None:
        return screen

    def distance(candidate: QScreen) -> int:
        geo = candidate.availableGeometry()
        dx = max(geo.left() - point.x(), 0, point.x() - geo.right())
        dy = max(geo.top() - point.y(), 0, point.y() - geo.bottom())
        return dx * dx + dy * dy

    screens = QGuiApplication.screens()
    if screens:
        return min(screens, key=distance)
    return QGuiApplication.primaryScreen()


def clamp_top_left(value, size: QSize, screen: QScreen | None = None) -> QPoint:
    point = as_point(value)
    screen = screen or screen_at(
        QPoint(point.x() + size.width() // 2, point.y() + size.height() // 2)
    )
    geo = screen.availableGeometry()
    max_x = max(geo.left(), geo.right() - size.width() + 1)
    max_y = max(geo.top(), geo.bottom() - size.height() + 1)
    return QPoint(
        max(geo.left(), min(point.x(), max_x)),
        max(geo.top(), min(point.y(), max_y)),
    )


def restore_top_left(
    cfg: dict, size: QSize, margin_x: int = 60, margin_y: int = 30
) -> tuple[QPoint, QScreen]:
    """恢复窗口位置；优先跟随同名显示器和屏内相对坐标。"""
    x, y = cfg.get("pos_x"), cfg.get("pos_y")
    named = screen_named(cfg.get("screen_name"))
    rel_x, rel_y = cfg.get("pos_rel_x"), cfg.get("pos_rel_y")

    if named is not None and rel_x is not None and rel_y is not None:
        geo = named.availableGeometry()
        span_x = max(0, geo.width() - size.width())
        span_y = max(0, geo.height() - size.height())
        point = QPoint(
            geo.left() + round(max(0.0, min(1.0, float(rel_x))) * span_x),
            geo.top() + round(max(0.0, min(1.0, float(rel_y))) * span_y),
        )
        return clamp_top_left(point, size, named), named

    if x is not None and y is not None:
        point = QPoint(int(x), int(y))
        target = screen_at(QPoint(point.x() + size.width() // 2, point.y() + size.height() // 2))
        return clamp_top_left(point, size, target), target

    target = QGuiApplication.primaryScreen() or screen_at(QPoint(0, 0))
    geo = target.availableGeometry()
    point = QPoint(
        geo.right() - size.width() - margin_x + 1, geo.bottom() - size.height() - margin_y + 1
    )
    return clamp_top_left(point, size, target), target


def relative_position(top_left: QPoint, size: QSize, screen: QScreen) -> tuple[float, float]:
    geo: QRect = screen.availableGeometry()
    span_x = max(1, geo.width() - size.width())
    span_y = max(1, geo.height() - size.height())
    return (
        max(0.0, min(1.0, (top_left.x() - geo.left()) / span_x)),
        max(0.0, min(1.0, (top_left.y() - geo.top()) / span_y)),
    )

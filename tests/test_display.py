from PySide6.QtCore import QPoint, QRect, QSize

from deskpet import display


class FakeScreen:
    def __init__(self, rect):
        self.rect = rect

    def availableGeometry(self):
        return self.rect


def test_clamp_handles_offset_monitor():
    screen = FakeScreen(QRect(1920, 0, 1920, 1080))
    assert display.clamp_top_left(QPoint(4000, -20), QSize(140, 150), screen) == QPoint(3700, 0)


def test_relative_position_on_second_monitor():
    screen = FakeScreen(QRect(1920, 0, 1920, 1080))
    x, y = display.relative_position(QPoint(2810, 465), QSize(140, 150), screen)
    assert x == 0.5
    assert y == 0.5

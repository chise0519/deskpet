"""核心悬浮窗 PetWidget：

- 无鼠标时 = 时钟（HH:MM 大字 + 秒 + 日期，半透明圆角底板，QPainter 自绘）
- 鼠标悬停 = 程序绘制的企鹅桌宠（idle/happy/drag/alert 四种动画状态）
- 左键拖动移动、单击反应+气泡、双击开速记、右键菜单

企鹅为 QPainter 逐帧绘制，不依赖图片素材；后期可换 GIF/序列帧。
"""
from __future__ import annotations

import math
import random
from datetime import datetime

from PySide6.QtCore import (
    QPointF, QRectF, Qt, QTimer, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QFont, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QMenu, QWidget

from . import config

W, H = 140, 150          # 窗口尺寸
FPS = 25                 # 宠物动画帧率
LEAVE_DELAY_MS = 400     # 鼠标移开后回时钟的防抖

CLOCK_BG = QColor(24, 26, 33, 190)
CLOCK_BORDER = QColor(70, 78, 96, 200)
CLOCK_FG = QColor(235, 240, 248)
CLOCK_SEC = QColor(140, 190, 250)
CLOCK_DATE = QColor(155, 163, 178)

PENGY_BODY = QColor(38, 42, 56)
PENGY_BELLY = QColor(245, 246, 250)
PENGY_BEAK = QColor(245, 166, 66)
PENGY_FEET = QColor(240, 150, 50)
PENGY_CHEEK = QColor(255, 150, 160, 120)


class Bubble(QWidget):
    """宠物头顶的气泡语录。"""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._text = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def say(self, text: str, anchor: QPointF, ms: int = 2600):
        self._text = text
        fm_w = max(120, min(260, 16 + 13 * len(text)))
        self.setFixedSize(fm_w, 52)
        x = int(anchor.x() - self.width() / 2)
        y = int(anchor.y() - self.height() - 6)
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start(ms)
        self.update()

    def paintEvent(self, _ev):
        if not self._text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -9)
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), 10, 10)
        # 小尾巴
        tail_x = self.width() / 2
        path.moveTo(tail_x - 7, r.bottom() - 1)
        path.lineTo(tail_x, r.bottom() + 7)
        path.lineTo(tail_x + 7, r.bottom() - 1)
        p.setPen(QPen(QColor(70, 78, 96, 220), 1))
        p.setBrush(QColor(32, 35, 44, 240))
        p.drawPath(path.simplified())
        p.setPen(QColor(235, 240, 248))
        f = QFont("Microsoft YaHei UI", 10)
        p.setFont(f)
        p.drawText(r, Qt.AlignCenter, self._text)


class PetWidget(QWidget):
    # 供 main.py 连接的信号
    request_note = Signal()      # 双击 → 速记
    request_reminder = Signal()  # 菜单 → 提醒
    request_report = Signal()    # 菜单 → 日报
    request_quit = Signal()

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(W, H)
        self.setWindowTitle("DeskPet")

        # ---- 状态 ----
        self.pet_mode = False          # False=时钟 True=企鹅
        self.anim = "idle"             # idle/happy/drag/alert
        self.frame = 0
        self._drag_offset = None
        self._press_pos = None
        self._moved = False
        self._alert_text = ""
        self._happy_until = 0          # frame 计数
        self._blink_frames = set()     # 随机眨眼帧

        self.bubble = Bubble()

        # ---- 定时器 ----
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._on_clock_tick)
        self.clock_timer.start(500)

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(1000 // FPS)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start()

        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self._leave_confirmed)

        self._schedule_blink()
        self._restore_pos()
        self.update()

    # ================= 时钟 =================

    def _on_clock_tick(self):
        if not self.pet_mode:
            self.update()

    def _draw_clock(self, p: QPainter):
        p.setRenderHint(QPainter.Antialiasing)
        board = QRectF(8, 18, W - 16, H - 46)
        path = QPainterPath()
        path.addRoundedRect(board, 18, 18)
        p.setPen(QPen(CLOCK_BORDER, 1.2))
        p.setBrush(QBrush(CLOCK_BG))
        p.drawPath(path)

        now = datetime.now()
        hm = now.strftime("%H:%M")
        # 大数字 HH:MM（居左）+ 秒（右侧小字），超宽自动缩字号
        big_pt, sec_pt = 30, 15
        f_big = QFont("Consolas", big_pt, QFont.Bold)
        f_sec = QFont("Consolas", sec_pt, QFont.Bold)
        from PySide6.QtGui import QFontMetrics
        while big_pt > 20:
            big_w = QFontMetrics(f_big).horizontalAdvance(hm)
            sec_w = QFontMetrics(f_sec).horizontalAdvance(":SS")
            if big_w + sec_w <= board.width() - 14:
                break
            big_pt -= 2
            sec_pt -= 1
            f_big = QFont("Consolas", big_pt, QFont.Bold)
            f_sec = QFont("Consolas", sec_pt, QFont.Bold)
        p.setFont(f_big)
        left = board.center().x() - (big_w + sec_w) / 2
        p.setPen(CLOCK_FG)
        p.drawText(QPointF(left, board.top() + 52), hm)
        p.setFont(f_sec)
        p.setPen(CLOCK_SEC)
        p.drawText(QPointF(left + big_w + 2, board.top() + 52), now.strftime(":%S"))
        # 日期 + 星期
        wk = "一二三四五六日"[now.weekday()]
        f3 = QFont("Microsoft YaHei UI", 9)
        p.setFont(f3)
        p.setPen(CLOCK_DATE)
        p.drawText(QRectF(board.left(), board.bottom() - 26, board.width(), 18),
                   Qt.AlignCenter, now.strftime(f"%m月%d日 周{wk}"))
        # 呼吸小圆点（活着的感觉）
        alpha = int(90 + 90 * math.sin(now.timestamp() * 2))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(120, 200, 150, alpha))
        p.drawEllipse(QPointF(board.right() - 14, board.top() + 14), 3.2, 3.2)

    # ================= 企鹅 =================

    def _on_anim_tick(self):
        self.frame += 1
        if self.anim == "happy" and self.frame > self._happy_until:
            self.anim = "idle"
            self._schedule_blink()
        if self.frame in self._blink_frames:
            pass  # blink 由 _blink_frames 判断
        if self.pet_mode or self.anim == "alert":
            self.update()

    def _schedule_blink(self):
        self._blink_frames = {self.frame + random.randint(20, 70)}

    def _is_blinking(self) -> bool:
        return (self.frame % 75) > 71  # 每 ~3s 眨一次

    def _draw_penguin(self, p: QPainter):
        p.setRenderHint(QPainter.Antialiasing)
        f = self.frame
        # 呼吸起伏
        bob = math.sin(f * 0.18) * 3
        jump = 0.0
        lean = 0.0
        wing_l = wing_r = 0.0  # 翅膀角度（度，负=抬起）

        if self.anim == "idle":
            pass
        elif self.anim == "happy":
            t = (self._happy_until - f) / 12.0
            jump = -abs(math.sin(t * 2.4)) * 16
            wing_l = -50 - 25 * math.sin(f * 0.9)
            wing_r = 50 + 25 * math.sin(f * 0.9)
        elif self.anim == "drag":
            lean = math.sin(f * 0.3) * 6
            bob = 6 + math.sin(f * 0.3) * 2
            wing_l, wing_r = -18, 18
        elif self.anim == "alert":
            bob = math.sin(f * 0.45) * 2
            wing_r = -75 + math.sin(f * 0.5) * 8   # 右翅举牌

        cx = W / 2
        base_y = H - 22 + bob + jump

        p.save()
        p.translate(cx, base_y)
        p.rotate(lean)
        p.translate(-cx, -base_y)

        # 影子
        p.setPen(Qt.NoPen)
        sh_a = int(60 - jump)
        p.setBrush(QColor(0, 0, 0, max(sh_a, 15)))
        p.drawEllipse(QPointF(cx, H - 14), 34 - jump * 0.4, 7)

        # 脚
        p.setBrush(PENGY_FEET)
        wig = math.sin(f * 0.18) * 2 if self.anim == "idle" else 0
        p.drawEllipse(QPointF(cx - 15 + wig, base_y + 2), 13, 6)
        p.drawEllipse(QPointF(cx + 15 - wig, base_y + 2), 13, 6)

        # 身体（黑）
        body = QRectF(cx - 38, base_y - 96, 76, 100)
        p.setBrush(PENGY_BODY)
        p.drawRoundedRect(body, 36, 36)

        # 肚皮（白）
        belly = QRectF(cx - 27, base_y - 78, 54, 80)
        p.setBrush(PENGY_BELLY)
        p.drawRoundedRect(belly, 26, 26)

        # 翅膀
        self._draw_wing(p, cx - 36, base_y - 62, wing_l, left=True)
        self._draw_wing(p, cx + 36, base_y - 62, wing_r, left=False)

        # 眼睛
        eye_y = base_y - 62
        blinking = self._is_blinking() and self.anim != "happy"
        for ex in (cx - 13, cx + 13):
            if blinking:
                p.setPen(QPen(QColor(20, 22, 30), 2.4, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(ex - 5, eye_y), QPointF(ex + 5, eye_y))
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(250, 250, 252))
                p.drawEllipse(QPointF(ex, eye_y), 7.5, 9)
                # 瞳孔看向鼠标（gp 与 eye 均为窗口坐标，y 向下）
                gp = self.mapFromGlobal(QCursor.pos())
                px = ex + max(-2.6, min(2.6, (gp.x() - ex) * 0.03))
                py = eye_y + max(-2.6, min(2.6, (gp.y() - eye_y) * 0.03))
                p.setBrush(QColor(25, 28, 38))
                p.drawEllipse(QPointF(px, py), 3.6, 4.6)
                p.setBrush(QColor(255, 255, 255))
                p.drawEllipse(QPointF(px - 1.2, py - 1.8), 1.3, 1.3)

        # 腮红
        p.setPen(Qt.NoPen)
        p.setBrush(PENGY_CHEEK)
        p.drawEllipse(QPointF(cx - 22, eye_y + 11), 6, 3.6)
        p.drawEllipse(QPointF(cx + 22, eye_y + 11), 6, 3.6)

        # 嘴
        beak_y = eye_y + 12
        p.setBrush(PENGY_BEAK)
        mouth_open = self.anim == "happy" and (f % 10) < 5
        if mouth_open:
            path = QPainterPath()
            path.moveTo(cx - 8, beak_y)
            path.quadTo(cx, beak_y + 14, cx + 8, beak_y)
            path.closeSubpath()
            p.drawPath(path)
        else:
            path = QPainterPath()
            path.moveTo(cx - 8, beak_y - 2)
            path.quadTo(cx, beak_y + 8, cx + 8, beak_y - 2)
            path.quadTo(cx, beak_y + 2, cx - 8, beak_y - 2)
            p.drawPath(path)

        p.restore()

        # 提醒状态：举的牌子
        if self.anim == "alert":
            self._draw_alert_sign(p, cx + 44, base_y - 96, f)

    def _draw_wing(self, p: QPainter, x: float, y: float, angle: float, left: bool):
        p.save()
        p.translate(x, y)
        p.rotate(angle)
        p.setPen(Qt.NoPen)
        p.setBrush(PENGY_BODY)
        r = QRectF(-7, -6, 14, 46)
        p.drawRoundedRect(r, 7, 7)
        p.restore()

    def _draw_alert_sign(self, p: QPainter, x: float, y: float, f: int):
        p.save()
        p.translate(x, y)
        p.rotate(6 + math.sin(f * 0.4) * 4)
        r = QRectF(-16, -22, 32, 26)
        p.setPen(QPen(QColor(200, 90, 80), 1.4))
        p.setBrush(QColor(250, 240, 235))
        p.drawRoundedRect(r, 6, 6)
        p.setPen(QColor(200, 70, 60))
        p.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        p.drawText(r, Qt.AlignCenter, "❗")
        p.restore()

    # ================= 事件 =================

    def enterEvent(self, ev):
        self.leave_timer.stop()
        if not self.pet_mode and self.anim != "alert":
            self.pet_mode = True
            self.anim = "idle"
            self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        if self._drag_offset is None:
            self.leave_timer.start(LEAVE_DELAY_MS)
        super().leaveEvent(ev)

    def _leave_confirmed(self):
        if self.anim != "alert" and self._drag_offset is None:
            self.pet_mode = False
            self.anim = "idle"
            self.update()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._press_pos = ev.globalPosition().toPoint()
            self._drag_offset = ev.globalPosition().toPoint() - self.pos()
            self._moved = False
            if self.pet_mode:
                self.anim = "drag"
                self.update()
        elif ev.button() == Qt.RightButton:
            self._show_menu(ev.globalPosition().toPoint())

    def mouseMoveEvent(self, ev):
        if self._drag_offset is not None:
            gp = ev.globalPosition().toPoint()
            if (gp - self._press_pos).manhattanLength() > 4:
                self._moved = True
            self.move(gp - self._drag_offset)

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        self._drag_offset = None
        if not self._moved:
            # 单击 → 开心反应 + 气泡
            self._react()
        elif self.pet_mode:
            self.anim = "idle"
            self.update()
        self._save_pos()

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.request_note.emit()

    def _react(self):
        self.pet_mode = True
        self.anim = "happy"
        self._happy_until = self.frame + 14
        self.update()
        anchor = self.mapToGlobal(QPointF(W / 2, 14))
        self.bubble.say(random.choice(config.QUOTES), anchor)

    def _show_menu(self, pos):
        from .icons import icon

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#23262f;color:#dfe3ea;border:1px solid #3b3f4d;"
            "font-size:12px;padding:6px;}"
            "QMenu::item{padding:6px 26px 6px 10px;border-radius:6px;}"
            "QMenu::item:selected{background:#3a5a86;}"
            "QMenu::icon{margin:0 8px 0 4px;}"
            "QMenu::separator{height:1px;background:#3b3f4d;margin:5px 8px;}"
        )
        menu.addAction(icon("note"), "速记", self.request_note.emit)
        menu.addAction(icon("bell"), "提醒", self.request_reminder.emit)
        menu.addAction(icon("doc"), "写日报", self.request_report.emit)
        menu.addSeparator()
        menu.addAction(icon("quit"), "退出", self.request_quit.emit)
        menu.exec(pos)

    # ================= 对外接口 =================

    def set_alert(self, text: str):
        """提醒到点：切 ALERT 状态并举牌。"""
        self._alert_text = text
        self.pet_mode = True
        self.anim = "alert"
        self.leave_timer.stop()
        self.update()
        anchor = self.mapToGlobal(QPointF(W / 2, 14))
        self.bubble.say(f"提醒：{text}", anchor, ms=6000)

    def clear_alert(self):
        if self.anim == "alert":
            self._alert_text = ""
            self.anim = "idle"
            if not self.underMouse():
                self.leave_timer.start(LEAVE_DELAY_MS)
            self.update()

    def global_center_top(self) -> QPointF:
        return self.mapToGlobal(QPointF(W / 2, 8))

    # ================= 位置持久化 =================

    def _save_pos(self):
        cfg = config.load_config()
        cfg["pos_x"] = self.x()
        cfg["pos_y"] = self.y()
        config.save_config(cfg)

    def _restore_pos(self):
        cfg = config.load_config()
        screen = self.screen()
        geo = screen.availableGeometry() if screen else QRectF(0, 0, 1920, 1080)
        x, y = cfg.get("pos_x"), cfg.get("pos_y")
        if x is None or y is None:
            x = geo.right() - W - 60
            y = geo.bottom() - H - 30
        # 夹回屏幕内（防止拔显示器后丢窗外）
        x = max(geo.left(), min(x, geo.right() - W))
        y = max(geo.top(), min(y, geo.bottom() - H))
        self.move(int(x), int(y))

    def paintEvent(self, _ev):
        p = QPainter(self)
        if self.pet_mode or self.anim == "alert":
            self._draw_penguin(p)
        else:
            self._draw_clock(p)

    def closeEvent(self, ev):
        self.bubble.close()
        super().closeEvent(ev)

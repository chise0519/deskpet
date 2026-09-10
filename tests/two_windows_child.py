"""子进程：同时开一个普通不透明窗 + 一个透明悬浮窗，供父进程截屏对比。"""
import sys
from PySide6.QtCore import QTimer, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)

a = QLabel("OPAQUE WINDOW")
a.setStyleSheet("background: rgb(220,40,40); color: white; font-size: 20px;")
a.setGeometry(400, 400, 300, 200)
a.show()


class Trans(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(800, 400, 140, 150)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(8, 8, 124, 134), 18, 18)
        p.setPen(QPen(QColor(70, 78, 96, 200), 1.2))
        p.setBrush(QColor(24, 26, 33, 190))
        p.drawPath(path)
        p.setPen(QColor(235, 240, 248))
        p.drawText(self.rect(), Qt.AlignCenter, "TRANS")


b = Trans()
b.show()
print("both shown", flush=True)
QTimer.singleShot(15000, app.quit)
sys.exit(app.exec())

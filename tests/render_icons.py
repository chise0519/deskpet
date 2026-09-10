"""渲染图标条 + 右键菜单截图，验证新图标视觉。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QWidget

app = QApplication(sys.argv)

from deskpet.icons import icon

names = ["note", "bell", "doc", "quit", "eye"]
strip = QPixmap(len(names) * 56 + 16, 72)
strip.fill(QColor(35, 38, 47))
p = QPainter(strip)
for i, n in enumerate(names):
    ic = icon(n, 22)
    ic.paint(p, 12 + i * 56, 24, 24, 24)
p.end()
out = ROOT / "preview"
strip.save(str(out / "icons_strip.png"))

# 右键菜单样式（离屏 grab）
w = QWidget()
menu = QMenu()
menu.setStyleSheet(
    "QMenu{background:#23262f;color:#dfe3ea;border:1px solid #3b3f4d;"
    "font-size:12px;padding:6px;}"
    "QMenu::item{padding:6px 26px 6px 10px;border-radius:6px;}"
    "QMenu::item:selected{background:#3a5a86;}"
    "QMenu::icon{margin:0 8px 0 4px;}"
    "QMenu::separator{height:1px;background:#3b3f4d;margin:5px 8px;}"
)
menu.addAction(icon("note"), "速记")
menu.addAction(icon("bell"), "提醒")
menu.addAction(icon("doc"), "写日报")
menu.addSeparator()
menu.addAction(icon("quit"), "退出")
menu.move(0, 0)
menu.show()
app.processEvents()
menu.grab().save(str(out / "menu_new.png"))
print("ICONS_OK")

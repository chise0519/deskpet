"""用 Qt(DXGI) 抓真实桌面，确认运行中的 DeskPet 可见。"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
img = app.primaryScreen().grabWindow(0).toImage()
dpr = app.primaryScreen().devicePixelRatio()
out = Path(__file__).resolve().parent.parent / "preview"
# 窗口逻辑位置约 (2379,829) 140x150 → 物理坐标
img.copy(int(2359 * dpr), int(809 * dpr), int(180 * dpr), int(190 * dpr)).save(
    str(out / "live_widget.png"))
img.scaled(img.width() // 2, img.height() // 2).save(str(out / "live_full.png"))
print("saved, dpr =", dpr)

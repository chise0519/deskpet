"""父进程 v2：DPR 换算后探针。"""
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

child = subprocess.Popen(
    [sys.executable, str(Path(__file__).resolve().parent / "two_windows_child.py")],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
time.sleep(5)

img = app.primaryScreen().grabWindow(0).toImage()
dpr = app.primaryScreen().devicePixelRatio()
print("img:", img.width(), img.height(), "dpr:", dpr)
out = Path(__file__).resolve().parent.parent / "preview"
# 逻辑 (380,380)-(980,600) → 物理 *dpr
img.copy(int(380 * dpr), int(380 * dpr), int(620 * dpr), int(230 * dpr)).save(
    str(out / "cmp_two.png"))


def px(lx, ly):
    c = img.pixelColor(int(lx * dpr), int(ly * dpr))
    return (c.red(), c.green(), c.blue())


print("opaque center (550,500):", px(550, 500))
print("trans  center (870,475):", px(870, 475))
print("trans  board  (820,430):", px(820, 430))
print("outside      (1000,475):", px(1000, 475))
child.terminate()
child.wait(timeout=5)

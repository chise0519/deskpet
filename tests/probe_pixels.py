from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
import sys

app = QApplication(sys.argv)
img = QImage(r"C:\Users\lenovo\DeskPet\preview\virtual2.png")
print("img size:", img.width(), img.height())
# 窗口 rect = (2379,829)-(2519,979)
for (x, y) in [(2450, 900), (2400, 850), (2500, 960), (2379, 829)]:
    c = img.pixelColor(x, y)
    print((x, y), c.red(), c.green(), c.blue(), c.alpha())

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
import sys

app = QApplication(sys.argv)
img = QImage(r"C:\Users\lenovo\DeskPet\preview\virtual2.png")
img.copy(2359, 809, 180, 190).scaled(360, 380).save(
    r"C:\Users\lenovo\DeskPet\preview\exact_widget.png")
print("saved")

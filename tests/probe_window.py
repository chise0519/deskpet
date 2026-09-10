import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

hwnd = None


def cb(h, _):
    global hwnd
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, buf, 256)
    if buf.value == "DeskPet" and user32.IsWindowVisible(h):
        hwnd = h
    return True


user32.EnumWindows(WNDENUMPROC(cb), 0)
print("hwnd:", hwnd)

GWL_EXSTYLE = -20
ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
flags = []
if ex & 0x80000:
    flags.append("LAYERED")
if ex & 0x80:
    flags.append("TOOL")
if ex & 0x8:
    flags.append("TOPMOST")
if ex & 0x20:
    flags.append("TRANSPARENT")
print("exstyle: 0x%x" % ex, flags)

hdc = user32.GetDC(hwnd)
r = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
w, h = r.right - r.left, r.bottom - r.top
mem = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mem, bmp)
ok = user32.PrintWindow(hwnd, mem, 2)
print("PrintWindow ok:", ok, "size:", w, h)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


bmi = BITMAPINFOHEADER()
bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.biWidth = w
bmi.biHeight = -h
bmi.biPlanes = 1
bmi.biBitCount = 32
bmi.biCompression = 0
buf = (ctypes.c_ubyte * (w * h * 4))()
gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)


def px(x, y):
    i = (y * w + x) * 4
    return tuple(buf[i:i + 4])  # BGRA


print("center:", px(w // 2, h // 2))
print("corner:", px(2, 2))
print("inner-top-left:", px(20, 20))
gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem)
user32.ReleaseDC(hwnd, hdc)

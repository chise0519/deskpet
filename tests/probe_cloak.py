import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
dwm = ctypes.windll.dwmapi
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

rows = []


def cb(h, _):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, buf, 256)
    if buf.value in ("DeskPet", "QtWinTest"):
        cloaked = wintypes.DWORD(0)
        dwm.DwmGetWindowAttribute(h, 14, ctypes.byref(cloaked), 4)  # DWMWA_CLOAKED
        r = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        rows.append((buf.value, pid.value, bool(user32.IsWindowVisible(h)),
                     cloaked.value, (r.left, r.top, r.right, r.bottom)))
    return True


user32.EnumWindows(WNDENUMPROC(cb), 0)
for row in rows:
    print(row)
if not rows:
    print("NO DeskPet WINDOW FOUND")

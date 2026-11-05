# All the raw Windows calls live here so the rest of the app can stay plain python.
import ctypes, os
from ctypes import wintypes as w

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
shcore = ctypes.WinDLL('shcore')

CURSOR_SHOWING = 1
CURSOR_SUPPRESSED = 2  # touch/pen input is hiding the cursor

class CURSORINFO(ctypes.Structure):
    _fields_ = [('cbSize', w.DWORD), ('flags', w.DWORD), ('hCursor', w.HANDLE), ('ptScreenPos', w.POINT)]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [('cbSize', w.DWORD), ('rcMonitor', w.RECT), ('rcWork', w.RECT), ('dwFlags', w.DWORD), ('szDevice', w.WCHAR*32)]

user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext.restype = w.BOOL
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
user32.GetForegroundWindow.restype = w.HWND
user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.GetMonitorInfoW.argtypes = [w.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
MONITORENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HMONITOR, w.HDC, ctypes.POINTER(w.RECT), w.LPARAM)
user32.EnumDisplayMonitors.argtypes = [w.HDC, ctypes.POINTER(w.RECT), MONITORENUMPROC, w.LPARAM]
shcore.GetDpiForMonitor.argtypes = [w.HMONITOR, ctypes.c_int, ctypes.POINTER(w.UINT), ctypes.POINTER(w.UINT)]
kernel32.OpenProcess.restype = w.HANDLE
kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
kernel32.CloseHandle.argtypes = [w.HANDLE]
kernel32.GetCurrentPackageFamilyName.argtypes = [ctypes.POINTER(ctypes.c_uint32), w.LPWSTR]
kernel32.GetCurrentPackageFamilyName.restype = ctypes.c_long
kernel32.GetCurrentThreadId.restype = w.DWORD
# WinEvent hook bits, used to hear about foreground window changes without polling
WINEVENTPROC = ctypes.WINFUNCTYPE(None, w.HANDLE, w.DWORD, w.HWND, w.LONG, w.LONG, w.DWORD, w.DWORD)
user32.SetWinEventHook.restype = w.HANDLE
user32.SetWinEventHook.argtypes = [w.DWORD, w.DWORD, w.HMODULE, WINEVENTPROC, w.DWORD, w.DWORD, w.DWORD]
user32.UnhookWinEvent.argtypes = [w.HANDLE]
user32.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
user32.GetMessageW.restype = w.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(w.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user32.PostThreadMessageW.argtypes = [w.DWORD, w.UINT, w.WPARAM, w.LPARAM]
EVENT_SYSTEM_FOREGROUND = 3
WM_QUIT = 0x12
shell32 = ctypes.WinDLL('shell32')
shell32.SHQueryUserNotificationState.argtypes = [ctypes.POINTER(ctypes.c_int)]
shell32.SHQueryUserNotificationState.restype = ctypes.c_long
user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
user32.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
user32.MonitorFromWindow.argtypes = [w.HWND, w.DWORD]
user32.MonitorFromWindow.restype = w.HMONITOR
user32.GetWindowLongPtrW.argtypes = [w.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [w.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SystemParametersInfoW.argtypes = [w.UINT, w.UINT, ctypes.c_void_p, w.UINT]
SHELL_CLASSES = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'}  # the desktop itself is "full screen" too

def set_dpi_aware():
    # -4 = PER_MONITOR_AWARE_V2, so every coordinate we get is real pixels on every monitor (no 150% fudging)
    # has to run before Qt starts, Qt asks for the same thing anyway
    return bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))

def cursor_info():
    # GetCursorInfo gives position + whether the cursor is actually showing + which cursor image it is
    # returns None when windows says no (happens on the lock screen / UAC prompt)
    ci = CURSORINFO(cbSize=ctypes.sizeof(CURSORINFO))
    if not user32.GetCursorInfo(ctypes.byref(ci)): return None
    return ci.ptScreenPos.x, ci.ptScreenPos.y, ci.flags, ci.hCursor or 0

def cursor_pos():
    p = w.POINT()
    if not user32.GetCursorPos(ctypes.byref(p)): return None
    return p.x, p.y

def foreground_window():
    return user32.GetForegroundWindow() or 0

def window_exe(hwnd):
    # window -> process id -> exe path. only keep the file name, never the window title
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value: return ''
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # 0x1000 = PROCESS_QUERY_LIMITED_INFORMATION, works on admin windows too
    if not h: return '?'
    try:
        buf = ctypes.create_unicode_buffer(1024); n = w.DWORD(1024)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)): return '?'
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(h)

def monitors():
    # every monitor with its full rect, work area (minus taskbar) and dpi. 96 dpi = 100% scale
    out = []
    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFOEXW(cbSize=ctypes.sizeof(MONITORINFOEXW))
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        dx, dy = w.UINT(), w.UINT()
        if shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy)) != 0: dx.value = 96  # 0 = effective dpi
        r, wk = mi.rcMonitor, mi.rcWork
        out.append({'device': mi.szDevice, 'primary': bool(mi.dwFlags & 1),
            'rect': [r.left, r.top, r.right, r.bottom], 'work': [wk.left, wk.top, wk.right, wk.bottom],
            'dpi': dx.value, 'scale': round(dx.value/96, 3)})
        return True
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    return out

def virtual_screen():
    # the box around all monitors together. 76-79 are SM_X/Y/CX/CYVIRTUALSCREEN
    x, y, cx, cy = (user32.GetSystemMetrics(i) for i in (76, 77, 78, 79))
    return [x, y, x+cx, y+cy]

def animations_enabled():
    # the "Animation effects" switch in Windows settings (SPI_GETCLIENTAREAANIMATION = 0x1042)
    on = w.BOOL(1)
    if not user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0): return True
    return bool(on.value)

def notification_state():
    # windows' own idea of "don't bother the user right now". 0 if the call fails
    st = ctypes.c_int(0)
    if shell32.SHQueryUserNotificationState(ctypes.byref(st)) != 0: return 0
    return st.value

def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def window_rect(hwnd):
    r = w.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)): return None
    return [r.left, r.top, r.right, r.bottom]

def monitor_rect(hwnd):
    mi = MONITORINFOEXW(cbSize=ctypes.sizeof(MONITORINFOEXW))
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi)): return None  # 2 = nearest monitor
    r = mi.rcMonitor
    return [r.left, r.top, r.right, r.bottom]

def covers_monitor(win, mon, tol=2):
    # a borderless full screen window sits exactly on its monitor. maximized windows hang ~8px over the sides so they don't count
    return all(abs(a - b) <= tol for a, b in zip(win, mon))

def fullscreen_busy(hwnd):
    # notification state 1 = locked/screensaver, 2 = something full screen, 3 = d3d exclusive full screen, 4 = presenting
    if notification_state() in (1, 2, 3, 4): return True
    if not hwnd or window_class(hwnd) in SHELL_CLASSES: return False
    r, m = window_rect(hwnd), monitor_rect(hwnd)
    return bool(r and m and covers_monitor(r, m))

def make_click_through(hwnd):
    # belt and braces on top of Qt's window flags: clicks fall straight through, never takes focus, not in alt-tab
    # WS_EX_TRANSPARENT 0x20, WS_EX_LAYERED 0x80000, WS_EX_NOACTIVATE 0x8000000, WS_EX_TOOLWINDOW 0x80
    ex = user32.GetWindowLongPtrW(hwnd, -20) & 0xFFFFFFFF  # -20 = GWL_EXSTYLE
    want = ex | 0x20 | 0x80000 | 0x8000000 | 0x80
    if want != ex: user32.SetWindowLongPtrW(hwnd, -20, want)
    return ex, want

def package_family():
    # Microsoft Store python runs as a packaged app, which matters because windows quietly redirects its AppData writes
    # error 122 (buffer too small) on the size check means we are packaged, anything else means we aren't
    n = ctypes.c_uint32(0)
    if kernel32.GetCurrentPackageFamilyName(ctypes.byref(n), None) != 122: return None
    buf = ctypes.create_unicode_buffer(n.value)
    if kernel32.GetCurrentPackageFamilyName(ctypes.byref(n), buf) != 0: return None
    return buf.value

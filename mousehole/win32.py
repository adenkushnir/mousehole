# all the raw windows calls live here so the rest of the app can stay plain python
import ctypes, os
from ctypes import wintypes as w

user32 = ctypes.WinDLL('user32', use_last_error=True)  # windows, cursor, monitors, input
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)  # processes and threads
shcore = ctypes.WinDLL('shcore')  # per monitor dpi

CURSOR_SHOWING = 1  # GetCursorInfo flag: the cursor is being drawn
CURSOR_SUPPRESSED = 2  # GetCursorInfo flag: touch or pen input is hiding the cursor

# what GetCursorInfo fills in: size, flags, which cursor image, where it is
class CURSORINFO(ctypes.Structure):
    _fields_ = [('cbSize', w.DWORD), ('flags', w.DWORD), ('hCursor', w.HANDLE), ('ptScreenPos', w.POINT)]

# what GetMonitorInfoW fills in: full rect, work area without the taskbar, primary flag, device name
class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [('cbSize', w.DWORD), ('rcMonitor', w.RECT), ('rcWork', w.RECT), ('dwFlags', w.DWORD), ('szDevice', w.WCHAR*32)]

# argument and return types for every call we make, so 64-bit handles don't get chopped to 32 bits
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext.restype = w.BOOL
user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
user32.GetForegroundWindow.restype = w.HWND
user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.GetMonitorInfoW.argtypes = [w.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
MONITORENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HMONITOR, w.HDC, ctypes.POINTER(w.RECT), w.LPARAM)  # callback shape for EnumDisplayMonitors
user32.EnumDisplayMonitors.argtypes = [w.HDC, ctypes.POINTER(w.RECT), MONITORENUMPROC, w.LPARAM]
shcore.GetDpiForMonitor.argtypes = [w.HMONITOR, ctypes.c_int, ctypes.POINTER(w.UINT), ctypes.POINTER(w.UINT)]
kernel32.OpenProcess.restype = w.HANDLE
kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
kernel32.CloseHandle.argtypes = [w.HANDLE]
kernel32.GetCurrentPackageFamilyName.argtypes = [ctypes.POINTER(ctypes.c_uint32), w.LPWSTR]
kernel32.GetCurrentPackageFamilyName.restype = ctypes.c_long
kernel32.GetCurrentThreadId.restype = w.DWORD
WINEVENTPROC = ctypes.WINFUNCTYPE(None, w.HANDLE, w.DWORD, w.HWND, w.LONG, w.LONG, w.DWORD, w.DWORD)  # callback shape for SetWinEventHook
# winevent hook and message loop calls, used to hear about foreground window changes without polling
user32.SetWinEventHook.restype = w.HANDLE
user32.SetWinEventHook.argtypes = [w.DWORD, w.DWORD, w.HMODULE, WINEVENTPROC, w.DWORD, w.DWORD, w.DWORD]
user32.UnhookWinEvent.argtypes = [w.HANDLE]
user32.GetMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT]
user32.GetMessageW.restype = w.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(w.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user32.PostThreadMessageW.argtypes = [w.DWORD, w.UINT, w.WPARAM, w.LPARAM]
EVENT_SYSTEM_FOREGROUND = 3  # winevent id for "a different window came to the front"
WM_QUIT = 0x12  # message that ends a GetMessage loop
shell32 = ctypes.WinDLL('shell32')  # notification state (full screen, presenting, locked)
# full screen check and window style calls
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
SHELL_CLASSES = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'}  # desktop and taskbar windows, they cover the screen but aren't "full screen apps"

# what Process32FirstW/NextW fill in for each running process. we only use the id and the exe name
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ProcessID', w.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', w.DWORD), ('cntThreads', w.DWORD), ('th32ParentProcessID', w.DWORD), ('pcPriClassBase', w.LONG),
        ('dwFlags', w.DWORD), ('szExeFile', w.WCHAR*260)]
# process list calls, used to see if powertoys is running
kernel32.CreateToolhelp32Snapshot.restype = w.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
kernel32.Process32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.ProcessIdToSessionId.argtypes = [w.DWORD, ctypes.POINTER(w.DWORD)]
INVALID_HANDLE = ctypes.c_void_p(-1).value  # what CreateToolhelp32Snapshot gives back when it fails

# switch to per monitor dpi v2 (-4) so every coordinate is real pixels on every monitor. has to run before qt starts
def set_dpi_aware():
    return bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))

# cursor position, flags (showing or not) and which cursor image. None when windows says no (lock screen, uac prompt)
def cursor_info():
    ci = CURSORINFO(cbSize=ctypes.sizeof(CURSORINFO))
    if not user32.GetCursorInfo(ctypes.byref(ci)): return None
    return ci.ptScreenPos.x, ci.ptScreenPos.y, ci.flags, ci.hCursor or 0

# just the cursor position in real pixels, None if windows says no
def cursor_pos():
    p = w.POINT()
    if not user32.GetCursorPos(ctypes.byref(p)): return None
    return p.x, p.y

# handle of the window in front, 0 if there isn't one
def foreground_window():
    return user32.GetForegroundWindow() or 0

# the exe file name behind a window (never the title). '' for no process, '?' if windows won't say
def window_exe(hwnd):
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value: return ''
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # 0x1000 = query limited info, works on admin windows too
    if not h: return '?'
    try:
        buf = ctypes.create_unicode_buffer(1024); n = w.DWORD(1024)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)): return '?'
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(h)

# every monitor with its full rect, work area, dpi and scale (96 dpi = 100%)
def monitors():
    out = []
    # called by windows once per monitor, adds that monitor to out
    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFOEXW(cbSize=ctypes.sizeof(MONITORINFOEXW))
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        dx, dy = w.UINT(), w.UINT()
        if shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy)) != 0: dx.value = 96  # 0 = effective dpi, fall back to 100%
        r, wk = mi.rcMonitor, mi.rcWork
        out.append({'device': mi.szDevice, 'primary': bool(mi.dwFlags & 1),
            'rect': [r.left, r.top, r.right, r.bottom], 'work': [wk.left, wk.top, wk.right, wk.bottom],
            'dpi': dx.value, 'scale': round(dx.value/96, 3)})
        return True
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    return out

# the box around all monitors together as [left, top, right, bottom]
def virtual_screen():
    x, y, cx, cy = (user32.GetSystemMetrics(i) for i in (76, 77, 78, 79))  # loops over the 4 metric ids: virtual x, y, width, height
    return [x, y, x+cx, y+cy]

# the "animation effects" switch in windows settings (SPI_GETCLIENTAREAANIMATION = 0x1042), True if we can't tell
def animations_enabled():
    on = w.BOOL(1)
    if not user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0): return True
    return bool(on.value)

# windows' own "don't bother the user" state (full screen, presenting, locked). 0 if the call fails
def notification_state():
    st = ctypes.c_int(0)
    if shell32.SHQueryUserNotificationState(ctypes.byref(st)) != 0: return 0
    return st.value

# the window's class name, used to spot the desktop and taskbar
def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

# the window's rect as [left, top, right, bottom], None if windows says no
def window_rect(hwnd):
    r = w.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)): return None
    return [r.left, r.top, r.right, r.bottom]

# rect of the monitor the window is mostly on, None if windows says no
def monitor_rect(hwnd):
    mi = MONITORINFOEXW(cbSize=ctypes.sizeof(MONITORINFOEXW))
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi)): return None  # 2 = nearest monitor
    r = mi.rcMonitor
    return [r.left, r.top, r.right, r.bottom]

# does the window sit exactly on its monitor? maximized windows hang ~8px over the sides so they don't count
def covers_monitor(win, mon, tol=2):
    return all(abs(a - b) <= tol for a, b in zip(win, mon))  # loops over the 4 sides of the window and monitor rects

# is something full screen right now? windows' state first (1 locked, 2 full screen, 3 d3d full screen, 4 presenting), then the window itself
def fullscreen_busy(hwnd):
    if notification_state() in (1, 2, 3, 4): return True
    if not hwnd or window_class(hwnd) in SHELL_CLASSES: return False
    r, m = window_rect(hwnd), monitor_rect(hwnd)
    return bool(r and m and covers_monitor(r, m))

# make a window click-through, never focused and out of alt-tab, on top of qt's own flags.
# WS_EX_TRANSPARENT 0x20, WS_EX_LAYERED 0x80000, WS_EX_NOACTIVATE 0x8000000, WS_EX_TOOLWINDOW 0x80
def make_click_through(hwnd):
    ex = user32.GetWindowLongPtrW(hwnd, -20) & 0xFFFFFFFF  # -20 = the extended style
    want = ex | 0x20 | 0x80000 | 0x8000000 | 0x80
    if want != ex: user32.SetWindowLongPtrW(hwnd, -20, want)
    return ex, want

# the store package name when running under microsoft store python (it redirects appdata), None otherwise.
# error 122 (buffer too small) on the size check means we are packaged
def package_family():
    n = ctypes.c_uint32(0)
    if kernel32.GetCurrentPackageFamilyName(ctypes.byref(n), None) != 122: return None
    buf = ctypes.create_unicode_buffer(n.value)
    if kernel32.GetCurrentPackageFamilyName(ctypes.byref(n), buf) != 0: return None
    return buf.value

# which windows session a process is in, None if windows won't say
def session_of(pid):
    sid = w.DWORD()
    return sid.value if kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid)) else None

# lowercase exe names of every process running in our own windows session, so another signed-in user's don't count
def process_names():
    snap = kernel32.CreateToolhelp32Snapshot(2, 0)  # 2 = every process
    if snap in (None, INVALID_HANDLE): return set()
    mine, names = session_of(os.getpid()), set()
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:  # loops over every process in the snapshot
            if session_of(entry.th32ProcessID) == mine: names.add(entry.szExeFile.lower())  # skip other users' processes
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return names

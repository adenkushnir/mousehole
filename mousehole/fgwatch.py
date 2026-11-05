# Tells us whenever the foreground window changes, through a WinEvent hook so there's no polling.
import ctypes, threading, time
from ctypes import wintypes
from . import win32
from .win32 import user32, kernel32

class ForegroundWatch:
    def __init__(self, q):
        self.q = q
        self.tid = None
        self.thread = None

    def start(self):
        ready = threading.Event()
        def run():
            self.tid = kernel32.GetCurrentThreadId()
            put, now = self.q.put, time.perf_counter_ns
            # out-of-context hook (flag 0): windows calls this back through this thread's message loop below
            proc = win32.WINEVENTPROC(lambda hk, ev, hwnd, obj, child, thread, ms: put(('fg', now(), hwnd or 0)))
            hk = user32.SetWinEventHook(win32.EVENT_SYSTEM_FOREGROUND, win32.EVENT_SYSTEM_FOREGROUND, None, proc, 0, 0, 0)
            ready.set()
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if hk: user32.UnhookWinEvent(hk)
        self.thread = threading.Thread(target=run, name='mh-fg', daemon=True)
        self.thread.start()
        ready.wait(2)

    def stop(self):
        if self.tid: user32.PostThreadMessageW(self.tid, win32.WM_QUIT, 0, 0)  # ends the GetMessage loop
        if self.thread: self.thread.join(1)
        self.tid = self.thread = None

# tells us whenever the window in front changes, through a winevent hook so there's no polling
import ctypes, threading, time
from ctypes import wintypes
from . import win32
from .win32 import user32, kernel32

# runs the winevent hook on its own thread and puts ('fg', time, window) on the queue for every change
class ForegroundWatch:
    # q is where the changes go
    def __init__(self, q):
        self.q = q
        self.tid = None
        self.thread = None

    # start the hook thread and wait until it's listening
    def start(self):
        ready = threading.Event()
        # the hook thread: set the hook, then pump messages so windows can call us back
        def run():
            self.tid = kernel32.GetCurrentThreadId()
            put, now = self.q.put, time.perf_counter_ns
            proc = win32.WINEVENTPROC(lambda hk, ev, hwnd, obj, child, thread, ms: put(('fg', now(), hwnd or 0)))  # called by windows on each change
            hk = user32.SetWinEventHook(win32.EVENT_SYSTEM_FOREGROUND, win32.EVENT_SYSTEM_FOREGROUND, None, proc, 0, 0, 0)  # flag 0 = call back on this thread
            ready.set()
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:  # loops over this thread's window messages until stop() posts WM_QUIT
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if hk: user32.UnhookWinEvent(hk)
        self.thread = threading.Thread(target=run, name='mh-fg', daemon=True)
        self.thread.start()
        ready.wait(2)

    # end the message loop and wait for the thread
    def stop(self):
        if self.tid: user32.PostThreadMessageW(self.tid, win32.WM_QUIT, 0, 0)
        if self.thread: self.thread.join(1)
        self.tid = self.thread = None

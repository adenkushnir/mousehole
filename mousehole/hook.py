# Low level mouse hook. Windows silently drops hooks that answer slowly, so the callback only drops a tuple in a queue.
import time
from pynput import mouse

LLMHF_INJECTED = 0x01  # event came from SendInput etc, not a real mouse
LLMHF_LOWER_IL_INJECTED = 0x02  # ...and the sender ran at a lower integrity level than us

def decode_flags(flags):
    return bool(flags & LLMHF_INJECTED), bool(flags & LLMHF_LOWER_IL_INJECTED)

class MouseHook:
    def __init__(self, q):
        self.q = q
        self.listener = None

    def start(self):
        put, now = self.q.put, time.perf_counter_ns
        def f(msg, data):
            # data is the MSLLHOOKSTRUCT windows hands the hook. copy the numbers out and get out of the way
            put(('hook', now(), msg, data.pt.x, data.pt.y, data.flags, data.dwExtraInfo or 0, data.mouseData, data.time))
            return False  # tells pynput to skip its own callbacks, windows still gets the event as normal
        self.listener = mouse.Listener(win32_event_filter=f)
        self.listener.start()
        self.listener.wait()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

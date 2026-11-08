# low level mouse hook. windows quietly drops hooks that answer slowly, so the callback only drops a tuple in a queue
import time
from pynput import mouse

LLMHF_INJECTED = 0x01  # hook flag: the event came from software (SendInput etc), not a real mouse
LLMHF_LOWER_IL_INJECTED = 0x02  # hook flag: and the sender ran at a lower integrity level than us

# the two injected flags as (injected, lower_il_injected)
def decode_flags(flags):
    return bool(flags & LLMHF_INJECTED), bool(flags & LLMHF_LOWER_IL_INJECTED)

# the hook itself, putting ('hook', time, msg, x, y, flags, extra, mouse_data, hook_time) on the queue for every event
class MouseHook:
    # q is where the events go
    def __init__(self, q):
        self.q = q
        self.listener = None

    # install the hook and wait until it's live
    def start(self):
        put, now = self.q.put, time.perf_counter_ns
        # called by windows for every mouse event. copy the numbers out of the struct and get out of the way
        def f(msg, data):
            put(('hook', now(), msg, data.pt.x, data.pt.y, data.flags, data.dwExtraInfo or 0, data.mouseData, data.time))
            return False  # tells pynput to skip its own callbacks, windows still gets the event as normal
        self.listener = mouse.Listener(win32_event_filter=f)
        self.listener.start()
        self.listener.wait()

    # remove the hook
    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

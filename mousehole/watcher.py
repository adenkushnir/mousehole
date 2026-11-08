# wires the detector to the live mouse hook, foreground changes and a bit of cursor polling, all on one worker thread
import logging, platform, queue, threading, time
from . import edges, mwb_settings, win32
from .detector import HELPER, Detector
from .fgwatch import ForegroundWatch
from .hook import MouseHook

log = logging.getLogger('mousehole')  # shared app log
WATCH_MS = 150  # after input near an edge, poll the cursor this long. that's when mwb parks it
POLL_MS = 10  # how often to poll the cursor while watching
DOG_S = 2  # how often the watchdog looks around when nothing is happening
RESTART_GAP_S = 30  # never re-hook more often than this

# the time in ms on the same clock the hook uses
def now_ms():
    return time.perf_counter_ns() / 1e6

NEAR_EVERY_MS = 100  # tell the gui about "near an edge" at most this often

# runs the detector live and calls back on switches and when the cursor nears an edge
class Watcher:
    # callbacks, an optional edge override and the approach distance. nothing starts until start()
    def __init__(self, on_switch=None, sides=None, on_near=None, approach_px=0):
        self.on_switch, self.on_near, self.approach_px = on_switch, on_near, approach_px
        self.override = sides  # None means go by the powertoys layout
        self.q = queue.SimpleQueue()
        self.stop_ev = threading.Event()
        self.thread = None
        self.user_hwnd = 0  # last window in front that isn't mwb's helper, for the full screen check

    # read the layout and screens, then start the hook, the foreground watch and the worker
    def start(self):
        self.machine = platform.node()
        self.layout_sides = edges.switch_sides(self.machine, mwb_settings.read())
        self.sides = self.override or self.layout_sides
        box = win32.virtual_screen()
        self.user_hwnd = win32.foreground_window()
        fg = win32.window_exe(self.user_hwnd)
        self.monitors = win32.monitors()
        self.det = Detector(box, self.sides, edges.park_spots(box, self.monitors), start=win32.cursor_pos(), fg=fg)
        self.hook = MouseHook(self.q)
        self.hook.start()
        self.fgw = ForegroundWatch(self.q)
        self.fgw.start()
        self.stop_ev.clear()
        self.thread = threading.Thread(target=self._run, name='mh-detect', daemon=True)
        self.thread.start()
        log.info('watching for switches on %s: screen %s, switching edges %s, cursor %s', self.machine, box, self.sides, self.det.state)

    # new edge override from the settings window. swapping the tuple in one go is safe with the worker reading it
    def set_sides(self, sides):
        self.override = sides
        self.sides = sides or self.layout_sides
        self.det.sides = tuple(self.sides)
        log.info('switching edges now %s', self.sides)

    # which switching edge's approach zone this point is in, if any. the zone is in logical px so scale it for the monitor
    def near_side(self, x, y):
        if not self.approach_px or self.det.near_park((x, y)): return None
        m = edges.monitor_at((x, y), self.monitors)
        zone = self.approach_px * (m['scale'] if m else 1) * 1.2  # a bit extra so the gui is ready before it matters
        return edges.side_of(x, self.det.box, zone, self.det.sides)

    # stop the worker, the hook and the foreground watch
    def stop(self):
        self.stop_ev.set()
        self.q.put(('stop',))  # wakes the worker if it's sitting in the 2s wait
        if self.thread: self.thread.join(1)
        self.hook.stop()
        self.fgw.stop()

    # the worker: feeds the detector, polls the cursor near edges, and keeps an eye on the hook and the screens
    def _run(self):
        watch_until = last_poll = last_near = 0
        heard = 0  # hook events since the last watchdog look
        dog_at, dog_pos, restarted = time.monotonic() + DOG_S, win32.cursor_pos(), 0
        while not self.stop_ev.is_set():  # loops over incoming events until stop() is called
            watching = now_ms() < watch_until
            try: it = self.q.get(timeout=POLL_MS / 1000 if watching else DOG_S)
            except queue.Empty: it = None
            if it and it[0] == 'hook':
                t, x, y = it[1] / 1e6, it[3], it[4]
                heard += 1
                self._emit(self.det.hook(t, x, y))
                if self.det.state == 'home' and self.det.side((x, y)): watch_until = t + WATCH_MS  # near an edge: poll, mwb parks the cursor with no hook events
                if self.det.pending: watch_until = max(watch_until, t + 60)  # an arrival is waiting on a cursor sample
                if self.on_near and self.det.state == 'home' and t - last_near >= NEAR_EVERY_MS:
                    s = self.near_side(x, y)
                    if s:
                        last_near = t
                        try: self.on_near(s)
                        except Exception: log.exception('near callback failed')
            elif it and it[0] == 'fg':
                exe = win32.window_exe(it[2]) if it[2] else ''
                if it[2] and HELPER not in exe.lower(): self.user_hwnd = it[2]
                self._emit(self.det.foreground(it[1] / 1e6, exe, win32.cursor_pos()))
            if watching and now_ms() - last_poll >= POLL_MS:
                p = win32.cursor_pos()
                if p: self._emit(self.det.cursor(now_ms(), *p))
                last_poll = now_ms()
            if time.monotonic() >= dog_at:
                p = win32.cursor_pos()
                moved = p and dog_pos and abs(p[0] - dog_pos[0]) + abs(p[1] - dog_pos[1]) > 100
                dead = not (self.hook.listener and self.hook.listener.running)
                # windows quietly unhooks slow hooks. cursor moved but we heard nothing means hook again
                # (an admin window in front also makes us deaf, hence 30s between tries)
                if (dead or (moved and not heard and not self.det.near_park(p))) and time.monotonic() - restarted > RESTART_GAP_S:
                    log.warning('mouse hook looks %s, hooking again', 'stopped' if dead else 'deaf (cursor moved, no events)')
                    self.hook.stop()
                    self.hook = MouseHook(self.q)
                    self.hook.start()
                    restarted = time.monotonic()
                # screens change (monitor plugged in, laptop rotated), keep the detector's screen up to date
                box = win32.virtual_screen()
                if tuple(box) != self.det.box:
                    self.monitors = win32.monitors()
                    self.det.set_screen(box, parks=edges.park_spots(box, self.monitors))
                    log.info('screen changed to %s', box)
                heard, dog_pos, dog_at = 0, p, time.monotonic() + DOG_S

    # log a switch and pass it to the callback
    def _emit(self, sw):
        if not sw: return
        log.info('%s at %s [%s]', sw.describe(), sw.pt, sw.via)
        if self.on_switch:
            try: self.on_switch(sw)
            except Exception: log.exception('switch callback failed')

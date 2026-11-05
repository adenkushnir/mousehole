# Diagnostic recorder: dumps every mouse hook event plus the cursor state to a csv so we can see what MWB really does on a switch.
import csv, json, logging, os, platform, queue, sys, threading, time
from datetime import datetime, timezone
from . import __version__, mwb_settings, paths, win32
from .hook import MouseHook, decode_flags

MSG_NAMES = {0x200: 'move', 0x201: 'ldown', 0x202: 'lup', 0x204: 'rdown', 0x205: 'rup', 0x207: 'mdown', 0x208: 'mup',
    0x20A: 'wheel', 0x20B: 'xdown', 0x20C: 'xup', 0x20E: 'hwheel'}
COLS = ['t_ms', 'wall_utc', 'source', 'msg', 'x', 'y', 'flags_hex', 'injected', 'lower_il_injected', 'extra_info',
    'mouse_data', 'cursor_showing', 'cursor_suppressed', 'cursor_handle', 'fg_exe', 'hook_time']
POLL_S = 0.01
BEAT_NS = 1_000_000_000  # write a poll row at least once a second even if nothing moved
log = logging.getLogger('mousehole')

def wall_str(ns):
    return datetime.fromtimestamp(ns // 1_000_000 / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def format_row(it, t0, wall0):
    # turns a queue item into a csv row. kept separate so the tests can poke at it without a real hook
    kind, t = it[0], it[1]
    head = [f'{(t - t0) / 1e6:.1f}', wall_str(wall0 + t - t0), kind]
    if kind == 'hook':
        _, _, msg, x, y, flags, extra, mdata, htime = it
        inj, low = decode_flags(flags)
        return head + [MSG_NAMES.get(msg, hex(msg)), x, y, f'0x{flags:x}', int(inj), int(low), f'0x{extra:x}', mdata, '', '', '', '', htime]
    if kind == 'poll':
        what, ci = it[2], it[3]
        if not ci: return head + ['no_info'] + [''] * 12
        x, y, fl, hc = ci
        return head + [what, x, y, '', '', '', '', '', int(bool(fl & win32.CURSOR_SHOWING)), int(bool(fl & win32.CURSOR_SUPPRESSED)), f'0x{hc:x}', '', '']
    return head + [''] * 11 + [it[2], '']  # fg change

class Recorder:
    def __init__(self, out_dir=None):
        self.out_dir = out_dir or paths.recordings_dir()
        self.running = False
        self.csv_path = self.json_path = None

    def start(self):
        machine = platform.node() or os.environ.get('COMPUTERNAME', 'pc')
        base = os.path.join(self.out_dir, f"{machine}_{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        self.csv_path, self.json_path = base + '.csv', base + '.json'
        self.q = queue.SimpleQueue()
        self.t0, self.wall0 = time.perf_counter_ns(), time.time_ns()
        self.counts = {'hook': 0, 'injected': 0, 'lower_il': 0, 'poll': 0, 'fg': 0}
        self.info = {'app': 'mousehole', 'version': __version__, 'machine': machine, 'windows': platform.version(),
            'python': platform.python_version(), 'frozen': bool(getattr(sys, 'frozen', False)),
            'started_utc': wall_str(self.wall0), 'csv': os.path.basename(self.csv_path), 'poll_ms': POLL_S * 1000,
            'heartbeat_ms': BEAT_NS // 1_000_000, 'monitors': win32.monitors(), 'virtual_screen': win32.virtual_screen(),
            'mwb': mwb_settings.read()}
        self._save_info()
        self.stop_ev = threading.Event()
        self.writer = threading.Thread(target=self._write, name='mh-writer', daemon=True)
        self.poller = threading.Thread(target=self._poll, name='mh-poll', daemon=True)
        self.writer.start()
        self.poller.start()
        self.hook = MouseHook(self.q)
        self.hook.start()
        self.running = True
        log.info('recording started %s', self.csv_path)

    def stop(self):
        if not self.running: return
        self.running = False
        self.hook.stop()
        self.stop_ev.set()
        self.poller.join(2)
        self.q.put(None)  # tells the writer it's done
        self.writer.join(5)
        end = time.time_ns()
        self.info.update(ended_utc=wall_str(end), seconds=round((end - self.wall0) / 1e9, 1), counts=self.counts)
        self._save_info()
        log.info('recording saved %s %s', self.csv_path, self.counts)

    def _save_info(self):
        with open(self.json_path, 'w', encoding='utf-8') as f: json.dump(self.info, f, indent=1)

    def _poll(self):
        # every 10ms: where's the cursor, is it showing, which cursor image. only queue it when something changed
        put, now = self.q.put, time.perf_counter_ns
        last = None; last_put = 0; last_hwnd = None; last_exe = None
        nxt = time.perf_counter()
        while not self.stop_ev.is_set():
            t = now()
            ci = win32.cursor_info()
            if ci != last or t - last_put >= BEAT_NS:
                put(('poll', t, 'change' if ci != last else 'beat', ci))
                last, last_put = ci, t
            hwnd = win32.foreground_window()
            if hwnd != last_hwnd:
                # only look the exe up when the foreground window changes, OpenProcess every 10ms would be silly
                last_hwnd = hwnd
                exe = win32.window_exe(hwnd) if hwnd else ''
                if exe != last_exe:
                    put(('fg', t, exe))
                    last_exe = exe
            nxt += POLL_S
            d = nxt - time.perf_counter()
            if d > 0: time.sleep(d)  # python 3.11+ sleeps with a high res timer on windows so 10ms is actually 10ms
            else: nxt = time.perf_counter()  # fell behind, don't try to catch up

    def _write(self):
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            wr = csv.writer(f)
            wr.writerow(COLS)
            flushed = time.monotonic()
            while True:
                try: it = self.q.get(timeout=0.25)
                except queue.Empty: it = ()
                if it is None: break
                if it:
                    wr.writerow(format_row(it, self.t0, self.wall0))
                    self.counts[it[0]] += 1
                    if it[0] == 'hook':
                        inj, low = decode_flags(it[5])
                        self.counts['injected'] += inj
                        self.counts['lower_il'] += low
                if time.monotonic() - flushed > 1:
                    f.flush()
                    flushed = time.monotonic()

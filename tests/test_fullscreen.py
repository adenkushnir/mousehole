# the "skip while something is full screen" check, with fake window and monitor rects
from mousehole import win32

MON = [0, 0, 2400, 1600]  # a laptop monitor's rect

# a window sitting exactly on the monitor, or a pixel off, is full screen
def test_borderless_full_screen_counts():
    assert win32.covers_monitor([0, 0, 2400, 1600], MON)
    assert win32.covers_monitor([-1, 0, 2401, 1600], MON)

# maximized windows overhang the sides by ~8px, with or without the taskbar showing
def test_maximized_window_does_not_count():
    assert not win32.covers_monitor([-8, -8, 2408, 1536], MON)
    assert not win32.covers_monitor([-8, -8, 2408, 1608], MON)

# normal windows and mwb's tiny helper window aren't full screen
def test_normal_windows_do_not_count():
    assert not win32.covers_monitor([100, 100, 900, 700], MON)
    assert not win32.covers_monitor([1197, 1, 1201, 5], MON)

# full screen on a second monitor counts, a window on the other monitor doesn't
def test_second_monitor():
    assert win32.covers_monitor([2400, 0, 6240, 2160], [2400, 0, 6240, 2160])
    assert not win32.covers_monitor([0, 0, 2400, 1600], [2400, 0, 6240, 2160])

# swap the windows calls for fakes: notification state, window class, window rect and the monitor
def fake(monkeypatch, state=5, cls='Chrome_WidgetWin_1', rect=MON):
    monkeypatch.setattr(win32, 'notification_state', lambda: state)
    monkeypatch.setattr(win32, 'window_class', lambda h: cls)
    monkeypatch.setattr(win32, 'window_rect', lambda h: rect)
    monkeypatch.setattr(win32, 'monitor_rect', lambda h: MON)

# a window filling the monitor is busy, a normal one isn't, and no window isn't
def test_fullscreen_busy(monkeypatch):
    fake(monkeypatch)
    assert win32.fullscreen_busy(123)
    fake(monkeypatch, rect=[100, 100, 900, 700])
    assert not win32.fullscreen_busy(123)
    assert not win32.fullscreen_busy(0)

# the desktop covers the screen but doesn't count as a full screen app
def test_desktop_itself_is_not_full_screen(monkeypatch):
    fake(monkeypatch, cls='Progman')
    assert not win32.fullscreen_busy(123)
    fake(monkeypatch, cls='WorkerW')
    assert not win32.fullscreen_busy(123)

# when windows itself says locked, full screen, d3d full screen or presenting, it's busy whatever the window
def test_windows_says_busy(monkeypatch):
    for st in (1, 2, 3, 4):  # loops over the 4 busy states: locked, full screen app, d3d exclusive, presenting
        fake(monkeypatch, state=st, rect=[100, 100, 900, 700])
        assert win32.fullscreen_busy(123)
    fake(monkeypatch, state=5, rect=[100, 100, 900, 700])  # 5 = normal
    assert not win32.fullscreen_busy(123)

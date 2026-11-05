# The "skip while something is full screen" check, with fake window and monitor rects.
from mousehole import win32

MON = [0, 0, 2400, 1600]

def test_borderless_full_screen_counts():
    assert win32.covers_monitor([0, 0, 2400, 1600], MON)
    assert win32.covers_monitor([-1, 0, 2401, 1600], MON)  # a pixel either way is still full screen

def test_maximized_window_does_not_count():
    assert not win32.covers_monitor([-8, -8, 2408, 1536], MON)  # overhangs the sides, stops at the taskbar
    assert not win32.covers_monitor([-8, -8, 2408, 1608], MON)  # even with an auto-hide taskbar

def test_normal_windows_do_not_count():
    assert not win32.covers_monitor([100, 100, 900, 700], MON)
    assert not win32.covers_monitor([1197, 1, 1201, 5], MON)  # MWB's tiny helper window

def test_second_monitor():
    assert win32.covers_monitor([2400, 0, 6240, 2160], [2400, 0, 6240, 2160])
    assert not win32.covers_monitor([0, 0, 2400, 1600], [2400, 0, 6240, 2160])

def fake(monkeypatch, state=5, cls='Chrome_WidgetWin_1', rect=MON):
    monkeypatch.setattr(win32, 'notification_state', lambda: state)
    monkeypatch.setattr(win32, 'window_class', lambda h: cls)
    monkeypatch.setattr(win32, 'window_rect', lambda h: rect)
    monkeypatch.setattr(win32, 'monitor_rect', lambda h: MON)

def test_fullscreen_busy(monkeypatch):
    fake(monkeypatch)
    assert win32.fullscreen_busy(123)
    fake(monkeypatch, rect=[100, 100, 900, 700])
    assert not win32.fullscreen_busy(123)
    assert not win32.fullscreen_busy(0)

def test_desktop_itself_is_not_full_screen(monkeypatch):
    fake(monkeypatch, cls='Progman')
    assert not win32.fullscreen_busy(123)
    fake(monkeypatch, cls='WorkerW')
    assert not win32.fullscreen_busy(123)

def test_windows_says_busy(monkeypatch):
    for st in (1, 2, 3, 4):  # locked, full screen app, d3d exclusive, presenting
        fake(monkeypatch, state=st, rect=[100, 100, 900, 700])
        assert win32.fullscreen_busy(123)
    fake(monkeypatch, state=5, rect=[100, 100, 900, 700])  # 5 = normal
    assert not win32.fullscreen_busy(123)

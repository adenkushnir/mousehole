# the recorder's csv rows line up with the header for every kind of event, and MOUSEHOLE_HOME keeps tests out of appdata
import os
from mousehole import paths
from mousehole.recorder import COLS, format_row

T0, WALL0 = 1_000_000_000, 1_700_000_000_000_000_000  # a pretend session start: clock time and wall time in ns

# format one queue item and hand it back as {column: value}, checking it has one value per column
def row(it):
    r = format_row(it, T0, WALL0)
    assert len(r) == len(COLS)
    return dict(zip(COLS, r))

# a hook event fills in the message, spot, flags, extra info and hook time
def test_hook_row():
    r = row(('hook', T0 + 12_345_678, 0x200, 2399, 800, 0x01, 0xABC, 0, 555))
    assert r['t_ms'] == '12.3' and r['source'] == 'hook' and r['msg'] == 'move'
    assert (r['x'], r['y']) == (2399, 800)
    assert r['injected'] == 1 and r['lower_il_injected'] == 0
    assert r['flags_hex'] == '0x1' and r['extra_info'] == '0xabc' and r['hook_time'] == 555

# a message number we don't know is kept as hex
def test_unknown_msg_kept_as_hex():
    assert row(('hook', T0, 0x2FF, 0, 0, 0, 0, 0, 0))['msg'] == '0x2ff'

# cursor samples fill in showing, suppressed and the cursor image, or say no_info
def test_poll_rows():
    r = row(('poll', T0, 'change', (10, 20, 1, 0x10005)))
    assert r['cursor_showing'] == 1 and r['cursor_suppressed'] == 0 and r['cursor_handle'] == '0x10005'
    hidden = row(('poll', T0, 'beat', (10, 20, 0, 0)))
    assert hidden['msg'] == 'beat' and hidden['cursor_showing'] == 0
    assert row(('poll', T0, 'change', None))['msg'] == 'no_info'

# a foreground change fills in the exe name
def test_fg_row():
    r = row(('fg', T0, 'explorer.exe'))
    assert r['source'] == 'fg' and r['fg_exe'] == 'explorer.exe'

# the wall clock column is utc with milliseconds
def test_wall_clock():
    assert row(('fg', T0 + 1_500_000, 'x.exe'))['wall_utc'] == '2023-11-14T22:13:20.001Z'

# MOUSEHOLE_HOME moves the folder, recordings included
def test_home_override(tmp_path, monkeypatch):
    monkeypatch.setenv('MOUSEHOLE_HOME', str(tmp_path / 'mh'))
    assert paths.home() == str(tmp_path / 'mh')
    assert os.path.isdir(paths.recordings_dir()) and paths.recordings_dir().startswith(str(tmp_path))

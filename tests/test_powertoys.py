# starting powertoys: finding the exe, spotting it running, and what ensure does in each case. never starts the real thing
import json
import pytest
from mousehole import powertoys, settings, win32

# every test here gets its own empty mousehole folder, so the real settings are never touched
@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('MOUSEHOLE_HOME', str(tmp_path))
    return tmp_path

# the first install spot that has the exe wins, none means None
def test_find_exe(tmp_path):
    there = tmp_path / 'b' / 'PowerToys.exe'
    there.parent.mkdir()
    there.write_bytes(b'')
    assert powertoys.find_exe([str(tmp_path / 'a' / 'PowerToys.exe'), str(there)]) == str(there)
    assert powertoys.find_exe([str(tmp_path / 'a' / 'PowerToys.exe')]) is None

# running means powertoys.exe is in the list, whatever the case
def test_is_running():
    assert powertoys.is_running({'explorer.exe', 'powertoys.exe'})
    assert not powertoys.is_running({'explorer.exe', 'powertoys.settings.exe'})

# the real process list works and has this python in it
def test_process_names_has_us():
    names = win32.process_names()
    assert any(n.startswith('python') for n in names)

# already running: nothing gets started
def test_ensure_running_starts_nothing():
    started = []
    assert powertoys.ensure(lambda: True, lambda: 'x.exe', started.append) == 'running' and started == []

# not running: starts the exe it found
def test_ensure_starts_it():
    started = []
    assert powertoys.ensure(lambda: False, lambda: r'C:\PT\PowerToys.exe', started.append) == 'started'
    assert started == [r'C:\PT\PowerToys.exe']

# not installed, or windows refuses to start it
def test_ensure_missing_or_failed():
    # stands in for a start that windows refuses
    def refuse(exe):
        raise OSError('nope')
    assert powertoys.ensure(lambda: False, lambda: None, refuse) == 'missing'
    assert powertoys.ensure(lambda: False, lambda: 'x.exe', refuse) == 'failed'

# every outcome that needs saying has a note, and only missing or failed count as a problem
def test_notes():
    assert powertoys.NOTES['started'][1] is False and powertoys.NOTES['missing'][1] and powertoys.NOTES['failed'][1]
    assert 'running' not in powertoys.NOTES

# the setting is on by default and junk in the file leaves it on
def test_setting_default_and_junk(home):
    assert settings.load()['start_powertoys'] is True
    (home / 'settings.json').write_text(json.dumps({'start_powertoys': 'no'}), encoding='utf-8')
    assert settings.load()['start_powertoys'] is True
    (home / 'settings.json').write_text(json.dumps({'start_powertoys': False}), encoding='utf-8')
    assert settings.load()['start_powertoys'] is False

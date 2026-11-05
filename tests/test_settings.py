# Settings load/save: defaults, round trip, and junk in the file never breaking anything.
import json
import pytest
from mousehole import settings

@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('MOUSEHOLE_HOME', str(tmp_path))
    return tmp_path

def test_defaults_when_no_file():
    assert settings.load() == settings.DEFAULTS

def test_round_trip(home):
    s = settings.load()
    s.update(portal_size=1.5, exit_color='#123ABC', edge_side='right', animations=False, halo_fade_ms=900)
    settings.save(s)
    assert settings.load() == s
    assert not (home / 'settings.json.tmp').exists()

def test_broken_file_gives_defaults(home):
    (home / 'settings.json').write_text('{nope', encoding='utf-8')
    assert settings.load() == settings.DEFAULTS
    (home / 'settings.json').write_text('[1, 2]', encoding='utf-8')
    assert settings.load() == settings.DEFAULTS

def test_bad_values_are_ignored_or_clamped(home):
    (home / 'settings.json').write_text(json.dumps({'portal_size': 99, 'speed': -3, 'halo_size': 40.7, 'glow': 'lots',
        'animations': 'yes', 'exit_color': 'orange', 'entry_color': '#00ff00', 'edge_side': 'top', 'passphrase': 'x'}), encoding='utf-8')
    s = settings.load()
    assert s['portal_size'] == 2.0 and s['speed'] == 0.5 and s['halo_size'] == 40
    assert s['glow'] == 1.0 and s['animations'] is True and s['exit_color'] == '#FF8A1F'
    assert s['entry_color'] == '#00ff00' and s['edge_side'] == 'auto' and 'passphrase' not in s

def test_sides_map():
    assert settings.SIDES['auto'] is None and settings.SIDES['both'] == ('left', 'right') and settings.SIDES['left'] == ('left',)

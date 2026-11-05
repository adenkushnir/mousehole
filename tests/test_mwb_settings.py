# Makes sure the PowerToys settings reader only hands back allowed keys and never the security key.
import json
from mousehole import mwb_settings

FAKE = {'properties': {'SecurityKey': 'supersecret123', 'MachinePool': {'value': 'A:1,B:2'}, 'Name2IP': {'value': 'A 10.0.0.2'},
    'MachineMatrixString': ['A', 'B', '', ''], 'MatrixOneRow': {'value': True}, 'WrapMouse': {'value': True},
    'HideMouseAtScreenEdge': {'value': False}, 'EasyMouse': {'value': 1}, 'TCPPort': {'value': 15100}}, 'name': 'MouseWithoutBorders'}

def write(tmp_path, data):
    p = tmp_path / 'settings.json'
    p.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding='utf-8')
    return str(p)

def test_only_allowed_keys(tmp_path):
    got = mwb_settings.read(write(tmp_path, FAKE))
    assert set(got) <= set(mwb_settings.ALLOWED)
    assert 'SecurityKey' not in got and 'MachinePool' not in got and 'Name2IP' not in got
    assert 'supersecret123' not in json.dumps(got)

def test_values_unwrapped(tmp_path):
    got = mwb_settings.read(write(tmp_path, FAKE))
    assert got['MachineMatrixString'] == ['A', 'B', '', '']
    assert got['WrapMouse'] is True and got['HideMouseAtScreenEdge'] is False and got['EasyMouse'] == 1

def test_missing_or_broken_file(tmp_path):
    assert mwb_settings.read(str(tmp_path / 'nope.json')) == {}
    assert mwb_settings.read(write(tmp_path, '{not json')) == {}
    assert mwb_settings.read(write(tmp_path, '[1, 2]')) == {}

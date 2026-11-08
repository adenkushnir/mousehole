# reads the few powertoys mouse without borders settings we care about. read only, and the security key never leaves the file
import json, os

ALLOWED = ['MachineMatrixString', 'MatrixOneRow', 'WrapMouse', 'HideMouseAtScreenEdge', 'DrawMouseCursor', 'EasyMouse',
    'DisableEasyMouseWhenForegroundWindowIsFullscreen', 'BlockMouseAtScreenCorners', 'MoveMouseRelatively', 'UseService',
    'HotKeySwitchMachine']  # the only keys we ever read out. SecurityKey, MachinePool, Name2IP etc stay put

# where powertoys keeps the mouse without borders settings
def settings_path():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'PowerToys', 'MouseWithoutBorders', 'settings.json')

# the allowed settings as a plain dict, {} if the file is missing or broken
def read(path=None):
    try:
        with open(path or settings_path(), encoding='utf-8') as f: props = json.load(f).get('properties', {})
    except (OSError, ValueError, AttributeError):
        return {}
    out = {}
    for k in ALLOWED:  # loops over the allowed key names and copies each one that's in the file
        if k not in props: continue
        v = props[k]
        if isinstance(v, dict) and list(v) == ['value']: v = v['value']  # most come wrapped like {"value": true}
        out[k] = v
    return out

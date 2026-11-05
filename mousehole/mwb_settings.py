# Reads the few PowerToys Mouse Without Borders settings we care about. Read only, and the security key is never pulled out.
import json, os

# only these keys ever leave the file. SecurityKey, MachinePool, Name2IP etc stay put
ALLOWED = ['MachineMatrixString', 'MatrixOneRow', 'WrapMouse', 'HideMouseAtScreenEdge', 'DrawMouseCursor', 'EasyMouse',
    'DisableEasyMouseWhenForegroundWindowIsFullscreen', 'BlockMouseAtScreenCorners', 'MoveMouseRelatively', 'UseService',
    'HotKeySwitchMachine']

def settings_path():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'PowerToys', 'MouseWithoutBorders', 'settings.json')

def read(path=None):
    try:
        with open(path or settings_path(), encoding='utf-8') as f: props = json.load(f).get('properties', {})
    except (OSError, ValueError, AttributeError):
        return {}
    out = {}
    for k in ALLOWED:
        if k not in props: continue
        v = props[k]
        # most of them come wrapped like {"value": true}
        if isinstance(v, dict) and list(v) == ['value']: v = v['value']
        out[k] = v
    return out

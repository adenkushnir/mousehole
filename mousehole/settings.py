# Settings, kept as json next to the log. Anything missing, broken or out of range quietly falls back to the defaults.
import json, os, re
from . import paths

DEFAULTS = {'animations': True, 'portal_size': 1.0, 'speed': 1.0, 'glow': 1.0, 'halo_size': 32, 'halo_fade_ms': 750,
    'exit_color': '#FF8A1F', 'entry_color': '#2E9BFF', 'edge_side': 'auto', 'approach_px': 200}
RANGES = {'portal_size': (0.5, 2.0), 'speed': (0.5, 2.0), 'glow': (0.0, 2.0), 'halo_size': (16, 64), 'halo_fade_ms': (300, 1500),
    'approach_px': (0, 400)}  # 0 = approach effect off
SIDES = {'auto': None, 'left': ('left',), 'right': ('right',), 'both': ('left', 'right')}

def path():
    return os.path.join(paths.home(), 'settings.json')

def clean(raw):
    s = dict(DEFAULTS)
    if not isinstance(raw, dict): return s
    for k, v in raw.items():
        if k not in DEFAULTS: continue
        d = DEFAULTS[k]
        if isinstance(d, bool):
            if isinstance(v, bool): s[k] = v
        elif isinstance(d, (int, float)):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                lo, hi = RANGES[k]
                s[k] = type(d)(min(hi, max(lo, v)))
        elif k == 'edge_side':
            if v in SIDES: s[k] = v
        elif k.endswith('_color'):
            if isinstance(v, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', v): s[k] = v
    return s

def load():
    try:
        with open(path(), encoding='utf-8') as f: return clean(json.load(f))
    except (OSError, ValueError):
        return dict(DEFAULTS)

def save(s):
    # write to a temp file then swap it in, so a crash mid-write can't leave half a file
    p = path()
    with open(p + '.tmp', 'w', encoding='utf-8') as f: json.dump(clean(s), f, indent=1)
    os.replace(p + '.tmp', p)

# Runs a saved recording back through the detector and lists what it would have spotted. Handy for tuning the rules.
import csv, json, os
from . import edges
from .detector import Detector

def replay(csv_path):
    with open(os.path.splitext(csv_path)[0] + '.json', encoding='utf-8') as f: info = json.load(f)
    box = info['virtual_screen']
    sides = edges.switch_sides(info.get('machine', ''), info.get('mwb', {}))
    parks = edges.park_spots(box, info.get('monitors', []))
    det, last, out = None, None, []
    with open(csv_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            t, src = float(r['t_ms']), r['source']
            xy = (int(r['x']), int(r['y'])) if r['x'] else None
            if det is None: det = Detector(box, sides, parks, start=xy)
            sw = None
            if src == 'hook': sw = det.hook(t, *xy)
            elif src == 'poll' and xy:
                sw = det.cursor(t, *xy)
                last = xy
            elif src == 'fg': sw = det.foreground(t, r['fg_exe'], last)
            if sw: out.append(sw)
    return info, out

def main(paths):
    for p in paths:
        info, found = replay(p)
        print(f"== {os.path.basename(p)}  ({info.get('machine')}, screen {info['virtual_screen']})")
        counts = {}
        for sw in found:
            print(f'{sw.t:10.1f}  {sw.describe():40} at {sw.pt}  [{sw.via}]')
            k = f'{sw.what} {sw.how}'
            counts[k] = counts.get(k, 0) + 1
        print('  ', ', '.join(f'{v} {k}' for k, v in sorted(counts.items())) or 'nothing found')
    return 0

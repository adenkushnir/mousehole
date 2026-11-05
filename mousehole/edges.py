# Edge geometry: which screen edges lead to another PC, where a point sits along an edge, and mapping that between screens.

def switch_sides(machine, mwb):
    # which outer edges send the cursor to another PC, worked out from the PowerToys layout
    # falls back to both sides when we can't tell (2x2 grid, this PC not in the list, no settings)
    names = [n for n in (mwb.get('MachineMatrixString') or []) if n]
    low = [n.lower() for n in names]  # PowerToys isn't consistent about case (MyLaptop vs MYLAPTOP)
    if not mwb.get('MatrixOneRow', True) or (machine or '').lower() not in low or len(names) < 2:
        return ('left', 'right')
    i, n, wrap = low.index(machine.lower()), len(names), bool(mwb.get('WrapMouse'))
    sides = []
    if i > 0 or wrap: sides.append('left')
    if i < n - 1 or wrap: sides.append('right')
    return tuple(sides)

def side_of(x, box, zone, sides=('left', 'right')):
    L, T, R, B = box
    if 'left' in sides and x <= L + zone: return 'left'
    if 'right' in sides and x >= R - 1 - zone: return 'right'
    return None

def edge_frac(y, box):
    # 0 = top of the screen, 1 = bottom. MWB keeps this the same when the cursor crosses over
    L, T, R, B = box
    return min(1.0, max(0.0, (y - T) / max(1, B - 1 - T)))

def edge_point(side, frac, box):
    # the other way round, a spot on one edge of a screen from a 0..1 fraction
    L, T, R, B = box
    return (L if side == 'left' else R - 1, round(T + frac * (B - 1 - T)))

def park_spots(box, monitors=()):
    # MWB parks the cursor at the top centre when it leaves. with one monitor that's the same spot either way,
    # with more we don't know yet if it's the whole desktop or the primary monitor, so watch both
    L, T, R, B = box
    spots = [((L + R) // 2, T)]
    for m in monitors:
        if m.get('primary'):
            ml, mt, mr, mb = m['rect']
            if ((ml + mr) // 2, mt) not in spots: spots.append(((ml + mr) // 2, mt))
    return spots

def monitor_at(pt, monitors):
    # the monitor a point is on, or the closest one (hook points can be a few px off screen)
    def dist(m):
        l, t, r, b = m['rect']
        return max(l - pt[0], 0, pt[0] - (r - 1)) + max(t - pt[1], 0, pt[1] - (b - 1))
    return min(monitors, key=dist) if monitors else None

def to_logical(pt, mon_rect, scale, logical_origin):
    # our coordinates are real pixels (we're per-monitor dpi aware), Qt draws each screen in logical pixels
    return (logical_origin[0] + (pt[0] - mon_rect[0]) / scale, logical_origin[1] + (pt[1] - mon_rect[1]) / scale)

def to_pixels(logical_size, scale):
    # e.g. the 56px tall portal is 84 real pixels on a 150% screen
    return logical_size * scale

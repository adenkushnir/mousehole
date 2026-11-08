# edge geometry: which screen edges lead to another pc, where a point sits along an edge, and mapping that between screens

# which outer edges send the cursor to another pc, worked out from the powertoys layout.
# falls back to both sides when we can't tell (2x2 grid, this pc not in the list, no settings)
def switch_sides(machine, mwb):
    names = [n for n in (mwb.get('MachineMatrixString') or []) if n]  # the layout's pc names, skipping empty slots
    low = [n.lower() for n in names]  # each name in lowercase, powertoys isn't consistent about case
    if not mwb.get('MatrixOneRow', True) or (machine or '').lower() not in low or len(names) < 2:
        return ('left', 'right')
    i, n, wrap = low.index(machine.lower()), len(names), bool(mwb.get('WrapMouse'))
    sides = []
    if i > 0 or wrap: sides.append('left')
    if i < n - 1 or wrap: sides.append('right')
    return tuple(sides)

# which switching edge x is within zone px of, if any
def side_of(x, box, zone, sides=('left', 'right')):
    L, T, R, B = box
    if 'left' in sides and x <= L + zone: return 'left'
    if 'right' in sides and x >= R - 1 - zone: return 'right'
    return None

# how far down the screen y is, 0 top to 1 bottom. mwb keeps this the same when the cursor crosses over
def edge_frac(y, box):
    L, T, R, B = box
    return min(1.0, max(0.0, (y - T) / max(1, B - 1 - T)))

# the other way round: a spot on one edge of a screen from a 0 to 1 fraction
def edge_point(side, frac, box):
    L, T, R, B = box
    return (L if side == 'left' else R - 1, round(T + frac * (B - 1 - T)))

# where mwb parks the cursor when it leaves: top centre. with more than one monitor we don't know if that's the
# whole desktop or the primary monitor, so watch both
def park_spots(box, monitors=()):
    L, T, R, B = box
    spots = [((L + R) // 2, T)]
    for m in monitors:  # loops over the monitors to add the primary one's top centre
        if m.get('primary'):
            ml, mt, mr, mb = m['rect']
            if ((ml + mr) // 2, mt) not in spots: spots.append(((ml + mr) // 2, mt))
    return spots

# the monitor a point is on, or the closest one (hook points can be a few px off screen)
def monitor_at(pt, monitors):
    # how far the point is outside this monitor, 0 if it's on it
    def dist(m):
        l, t, r, b = m['rect']
        return max(l - pt[0], 0, pt[0] - (r - 1)) + max(t - pt[1], 0, pt[1] - (b - 1))
    return min(monitors, key=dist) if monitors else None

# real pixels (we're per monitor dpi aware) to qt's logical pixels for that screen
def to_logical(pt, mon_rect, scale, logical_origin):
    return (logical_origin[0] + (pt[0] - mon_rect[0]) / scale, logical_origin[1] + (pt[1] - mon_rect[1]) / scale)

# logical size to real pixels, e.g. the 56px portal is 84 real pixels at 150%
def to_pixels(logical_size, scale):
    return logical_size * scale

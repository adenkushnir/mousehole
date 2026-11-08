# edge maths: which edges switch, mapping a spot between screens of different sizes and dpi, and pixel conversions
from mousehole import edges

LAP = (0, 0, 2400, 1600)  # laptop screen
DESK = (0, 0, 3840, 2160)  # desktop screen

# a fake powertoys layout with these pc names, padded to 4 slots
def layout(names, wrap=True, one_row=True):
    return {'MachineMatrixString': names + [''] * (4 - len(names)), 'WrapMouse': wrap, 'MatrixOneRow': one_row}

# two pcs: wrap on means both edges, wrap off means only the edge facing the other pc
def test_switch_sides_two_pcs():
    assert edges.switch_sides('MyLaptop', layout(['MyLaptop', 'DESKTOP-ABC123'])) == ('left', 'right')
    assert edges.switch_sides('MyLaptop', layout(['MyLaptop', 'DESKTOP-ABC123'], wrap=False)) == ('right',)
    assert edges.switch_sides('DESKTOP-ABC123', layout(['MyLaptop', 'DESKTOP-ABC123'], wrap=False)) == ('left',)

# the desktop's copy of the layout spells the laptop in capitals, still matches
def test_switch_sides_ignores_case():
    assert edges.switch_sides('MyLaptop', layout(['MYLAPTOP', 'DESKTOP-ABC123'], wrap=False)) == ('right',)

# three pcs: the middle one switches both ways, the end one only one way
def test_switch_sides_middle_of_three():
    assert edges.switch_sides('b', layout(['a', 'b', 'c'], wrap=False)) == ('left', 'right')
    assert edges.switch_sides('c', layout(['a', 'b', 'c'], wrap=False)) == ('left',)

# anything we can't read the layout from gives both edges
def test_switch_sides_falls_back_to_both():
    assert edges.switch_sides('nobody', layout(['a', 'b'], wrap=False)) == ('left', 'right')
    assert edges.switch_sides('a', layout(['a', 'b'], wrap=False, one_row=False)) == ('left', 'right')
    assert edges.switch_sides('a', {}) == ('left', 'right')
    assert edges.switch_sides('a', layout(['a'], wrap=False)) == ('left', 'right')

# which edge a point is near, including points past the edge and edges that don't switch
def test_side_of():
    assert edges.side_of(0, LAP, 60) == 'left' and edges.side_of(2399, LAP, 60) == 'right'
    assert edges.side_of(2389, LAP, 60) == 'right' and edges.side_of(1200, LAP, 60) is None
    assert edges.side_of(-3, DESK, 60) == 'left'
    assert edges.side_of(1, LAP, 60, ('right',)) is None

# the recordings: left the laptop at y=1003, mwb put the cursor on the desktop at y=1354, and 1467 came back as 1085
def test_map_laptop_to_desktop_matches_what_mwb_did():
    f = edges.edge_frac(1003, LAP)
    assert edges.edge_point('left', f, DESK) == (0, 1354)
    x, y = edges.edge_point('right', edges.edge_frac(1467, DESK), LAP)
    assert x == 2399 and abs(y - 1085) <= 1

# the very top and bottom map to the very top and bottom
def test_map_keeps_ends():
    assert edges.edge_point('right', edges.edge_frac(0, LAP), DESK) == (3839, 0)
    assert edges.edge_point('left', edges.edge_frac(1599, LAP), DESK) == (0, 2159)

# points above or below the screen clamp to 0 and 1
def test_edge_frac_clamps():
    assert edges.edge_frac(-14, LAP) == 0.0 and edges.edge_frac(5000, LAP) == 1.0

# a desktop that doesn't start at 0,0 (monitor left of the primary)
def test_offset_screens():
    box = (-1920, -200, 1920, 1880)
    f = edges.edge_frac(840, box)
    assert abs(f - 0.5) < 0.001
    assert edges.edge_point('left', f, box) == (-1920, 840)

# real pixels to qt's logical pixels on a 150% screen
def test_to_logical_150_percent():
    x, y = edges.to_logical((2397, 1003), (0, 0, 2400, 1600), 1.5, (0, 0))
    assert abs(x - 1598) < 0.01 and abs(y - 668.67) < 0.01

# a 100% monitor right of a 150% laptop: real x starts at 2400, qt puts it at logical x 1600
def test_to_logical_second_monitor_100_percent():
    assert edges.to_logical((2700, 150), (2400, 0, 4320, 1080), 1.0, (1600, 0)) == (1900, 150)

# logical sizes to real pixels at a few scales
def test_to_pixels():
    assert edges.to_pixels(56, 1.5) == 84 and edges.to_pixels(24, 1.0) == 24 and edges.to_pixels(32, 1.25) == 40

# the monitor a point is on, the nearest one for points just off screen, None with no monitors
def test_monitor_at():
    mons = [{'rect': [0, 0, 2400, 1600]}, {'rect': [2400, 0, 6240, 2160]}]
    assert edges.monitor_at((100, 100), mons) is mons[0]
    assert edges.monitor_at((3000, 2000), mons) is mons[1]
    assert edges.monitor_at((-3, 1354), mons) is mons[0]
    assert edges.monitor_at((1, 1), []) is None

# one park spot with one monitor, two when the primary isn't the whole desktop
def test_park_spots():
    assert edges.park_spots(LAP, [{'rect': [0, 0, 2400, 1600], 'primary': True}]) == [(1200, 0)]
    two = [{'rect': [0, 0, 2400, 1600], 'primary': False}, {'rect': [2400, 0, 6240, 2160], 'primary': True}]
    assert edges.park_spots((0, 0, 6240, 2160), two) == [(3120, 0), (4320, 0)]

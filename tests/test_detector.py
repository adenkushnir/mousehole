# detector rules, fed with little event sequences shaped like what the recordings showed
from mousehole.detector import Detector

LAP = (0, 0, 2400, 1600)  # laptop screen, mwb parks at (1200, 0..4)
DESK = (0, 0, 3840, 2160)  # desktop screen, parks at (1920, 4)

# feed events to the detector and collect the switches. ('h', t, x, y) hook, ('c', t, x, y) cursor sample, ('f', t, exe, (x, y)) foreground change
def run(det, events):
    out = []
    for e in events:  # loops over each event in order and passes it to the matching detector call
        if e[0] == 'h': sw = det.hook(e[1], e[2], e[3])
        elif e[0] == 'c': sw = det.cursor(e[1], e[2], e[3])
        else: sw = det.foreground(e[1], e[2], e[3])
        if sw: out.append(sw)
    return out

# move to the right edge and get parked, a normal edge departure
def depart_right(det, t=0):
    return run(det, [('h', t, 2300, 1000), ('h', t + 5, 2350, 1002), ('h', t + 10, 2397, 1003), ('c', t + 12, 1200, 4)])

# touching the edge then getting parked is an edge departure at the right height
def test_edge_departure_via_park():
    sw = depart_right(Detector(LAP, start=(1200, 800)))
    assert len(sw) == 1 and (sw[0].what, sw[0].how, sw[0].side) == ('depart', 'edge', 'right')
    assert sw[0].pt == (2397, 1003) and abs(sw[0].frac - 0.627) < 0.001

# an arrival only counts once a cursor sample backs it up, and keeps the hook event's time and spot
def test_arrival_after_away():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 5000, 2398, 1085)]) == []
    sw = run(d, [('c', 5016, 2396, 1085)])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'right')]  # what, how and side of each switch
    assert sw[0].pt == (2398, 1085) and sw[0].t == 5000 and d.state == 'home'

# mwb parks, bounces the cursor back to the edge for ~10ms, then parks again: still away
def test_bounce_right_after_leaving_is_not_an_arrival():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 20, 2411, 639), ('c', 22, 2399, 641), ('c', 32, 1200, 4)]) == []
    assert d.state == 'away'

# wiggles around the park spot on the controlling pc don't count, a real arrival at the edge does
def test_wiggles_on_controlling_pc_are_ignored():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 500, 1157, 21), ('h', 510, 1223, 2), ('h', 520, 1200, -14), ('h', 530, 1202, 4)]) == []
    sw = run(d, [('h', 900, 1, 925), ('c', 920, 1, 925)])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'left')]  # what, how and side of each switch

# fast flicks landed 150px+ from the park spot in the live log, but the real cursor stayed pinned there
def test_big_wiggles_need_the_real_cursor_to_move():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 500, 1042, 52), ('c', 520, 1200, 4), ('h', 600, 1355, 38), ('c', 620, 1201, 3), ('h', 700, 1043, -27), ('c', 718, 1200, 4)]) == []
    assert d.state == 'away'
    sw = run(d, [('h', 3000, 2398, 900), ('c', 3016, 2398, 900)])
    assert [(s.what, s.how) for s in sw] == [('arrive', 'edge')]  # what and how of each switch

# mwb can swallow the final nudge, so resting on the edge a while ago still counts as an edge. 20px short doesn't
def test_paused_on_the_edge_then_left_still_counts_as_edge():
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2300, 1133), ('h', 20, 2398, 1133)])
    sw = run(d, [('f', 1500, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    assert [(s.what, s.how, s.side, s.pt) for s in sw] == [('depart', 'edge', 'right', (2398, 1133))]  # what, how, side and spot of each switch
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2300, 1133), ('h', 20, 2379, 1133)])
    sw = run(d, [('f', 1500, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut')]  # what and how of each switch

# leaving from mid-screen and arriving at the centre is a shortcut both ways
def test_shortcut_switch_has_no_edge():
    d = Detector(LAP, start=(1200, 800))
    sw = run(d, [('h', 0, 1227, 1082), ('c', 5, 1227, 1082), ('c', 15, 1200, 4), ('h', 7000, 1199, 799), ('c', 7016, 1199, 799)])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut'), ('arrive', 'shortcut')]  # what and how of each switch

# sitting near the edge for 5 seconds without crossing does nothing
def test_hugging_the_edge_does_nothing():
    d = Detector(DESK, start=(1000, 1000))
    ev = []
    for i in range(500):  # loops over 500 steps of 10ms, wobbling 6-37px from the left edge
        x = 6 + i % 32
        ev += [('h', i * 10, x, 1633), ('c', i * 10 + 5, x, 1633)]
    assert run(d, ev) == []
    assert d.state == 'home'

# walking the cursor up into the park spot by hand isn't a departure
def test_moving_into_the_park_spot_by_hand_does_nothing():
    d = Detector(LAP, start=(1200, 300))
    ev = []
    for i, y in enumerate(range(300, 0, -4)):  # loops over heights from 300 up to the top, 4px at a time
        ev += [('h', i * 10, 1200, y), ('c', i * 10 + 5, 1200, y)]
    assert run(d, ev) == []

# a fast flick that stops 9px short of the edge still counts as an edge
def test_fast_flick_short_of_the_edge_still_counts():
    sw = run(Detector(LAP, start=(1200, 800)), [('h', 0, 2281, 1074), ('h', 8, 2389, 1074), ('c', 10, 1200, 4)])
    assert [(s.how, s.side) for s in sw] == [('edge', 'right')]  # how and side of each switch

# admin window in front: no hook events and no parking, the helper taking focus and the cursor spot still give it away
def test_admin_window_in_front_hook_blind():
    d = Detector(DESK, start=(659, 1611), fg='taskmgr.exe')
    sw = run(d, [('f', 1000, 'PowerToys.MouseWithoutBordersHelper.exe', (12, 808))])
    assert [(s.what, s.how, s.side) for s in sw] == [('depart', 'edge', 'left')]  # what, how and side of each switch
    sw = run(d, [('h', 2400, 1, 376), ('f', 2410, 'Taskmgr.exe', (22, 382))])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'left')]  # what, how and side of each switch

# the helper letting go of focus counts as an arrival even with no hook events
def test_focus_leaving_helper_is_a_fallback_arrival():
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2397, 1003), ('f', 3, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    sw = run(d, [('f', 400, 'Code.exe', (2398, 1085))])
    assert [(s.what, s.how, s.via) for s in sw] == [('arrive', 'edge', 'focus')]  # what, how and signal of each switch

# focus flickering helper, app, helper while leaving is still one departure
def test_focus_flicker_while_leaving_does_one_departure():
    d = Detector(LAP, start=(1200, 800))
    helper = 'PowerToys.MouseWithoutBordersHelper.exe'
    sw = run(d, [('h', 0, 2397, 1003), ('c', 5, 1200, 4), ('f', 6, helper, (1200, 4)), ('f', 15, 'Code.exe', (1200, 4)), ('f', 25, helper, (1200, 4))])
    assert len(sw) == 1 and d.state == 'away'

# with wrap off the laptop's left edge goes nowhere, so leaving from it counts as a shortcut
def test_edge_that_leads_nowhere_is_not_an_edge_switch():
    sw = run(Detector(LAP, ('right',), start=(1200, 800)), [('h', 0, 1, 936), ('c', 5, 1200, 4)])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut')]  # what and how of each switch

# the pc with the real mouse: hook points run past the edge, then wiggle at the park spot while away
def test_controlling_pc_side():
    d = Detector(DESK, start=(1000, 1400))
    sw = run(d, [('h', 0, 40, 1354), ('h', 4, -3, 1354), ('c', 6, 1920, 4), ('h', 50, 1923, 4), ('h', 60, 1936, 4), ('h', 3500, 1, 1344), ('c', 3516, 1, 1344)])
    assert [(s.what, s.how, s.side) for s in sw] == [('depart', 'edge', 'left'), ('arrive', 'edge', 'left')]  # what, how and side of each switch

# starting with the cursor parked or the helper in front means it's on the other pc
def test_starts_away_if_cursor_is_parked():
    assert Detector(LAP, start=(1200, 4)).state == 'away'
    assert Detector(LAP, start=(500, 500), fg='PowerToys.MouseWithoutBordersHelper.exe').state == 'away'
    assert Detector(LAP, start=(500, 500)).state == 'home'

# a park right after arriving is too soon to be a real departure
def test_no_departure_straight_after_arriving():
    d = Detector(LAP, start=(1200, 4))
    assert len(run(d, [('h', 0, 2398, 1000), ('c', 16, 2398, 1000)])) == 1
    assert run(d, [('h', 26, 2397, 1000), ('c', 36, 1200, 4)]) == []

# arriving on an edge and going straight back out through it is an edge both ways
def test_going_straight_back_out_is_still_an_edge():
    d = Detector(LAP, start=(1200, 4))
    sw = run(d, [('h', 0, 2398, 1177), ('c', 16, 2398, 1177), ('h', 200, 2398, 1170), ('h', 400, 2398, 1164), ('f', 402, 'PowerToys.MouseWithoutBordersHelper.exe', (2398, 1164))])
    assert [(s.what, s.how) for s in sw] == [('arrive', 'edge'), ('depart', 'edge')]  # what and how of each switch

# the plain words shown in the log and the detections window
def test_describe():
    sw = depart_right(Detector(LAP, start=(1200, 800)))[0]
    assert sw.describe() == 'left via the right edge, 63% down'

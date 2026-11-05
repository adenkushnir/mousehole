# Detector rules, fed with little event sequences shaped like what the M1 recordings showed.
from mousehole.detector import Detector

LAP = (0, 0, 2400, 1600)  # laptop, MWB parks at (1200, 0..4)
DESK = (0, 0, 3840, 2160)  # desktop, parks at (1920, 4)

def run(det, events):
    # events: ('h', t, x, y) hook, ('c', t, x, y) cursor sample, ('f', t, exe, (x, y)) foreground change
    out = []
    for e in events:
        if e[0] == 'h': sw = det.hook(e[1], e[2], e[3])
        elif e[0] == 'c': sw = det.cursor(e[1], e[2], e[3])
        else: sw = det.foreground(e[1], e[2], e[3])
        if sw: out.append(sw)
    return out

def depart_right(det, t=0):
    return run(det, [('h', t, 2300, 1000), ('h', t + 5, 2350, 1002), ('h', t + 10, 2397, 1003), ('c', t + 12, 1200, 4)])

def test_edge_departure_via_park():
    sw = depart_right(Detector(LAP, start=(1200, 800)))
    assert len(sw) == 1 and (sw[0].what, sw[0].how, sw[0].side) == ('depart', 'edge', 'right')
    assert sw[0].pt == (2397, 1003) and abs(sw[0].frac - 0.627) < 0.001

def test_arrival_after_away():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 5000, 2398, 1085)]) == []  # not until the real cursor backs it up
    sw = run(d, [('c', 5016, 2396, 1085)])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'right')]
    assert sw[0].pt == (2398, 1085) and sw[0].t == 5000 and d.state == 'home'

def test_bounce_right_after_leaving_is_not_an_arrival():
    # MWB parks, bounces the cursor back to the edge for ~10ms, then parks again
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 20, 2411, 639), ('c', 22, 2399, 641), ('c', 32, 1200, 4)]) == []
    assert d.state == 'away'

def test_wiggles_on_controlling_pc_are_ignored():
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 500, 1157, 21), ('h', 510, 1223, 2), ('h', 520, 1200, -14), ('h', 530, 1202, 4)]) == []
    sw = run(d, [('h', 900, 1, 925), ('c', 920, 1, 925)])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'left')]

def test_big_wiggles_need_the_real_cursor_to_move():
    # from the live log: fast flicks on the controlling PC landed 150px+ from the park spot, but the cursor stayed pinned
    d = Detector(LAP, start=(1200, 800))
    depart_right(d)
    assert run(d, [('h', 500, 1042, 52), ('c', 520, 1200, 4), ('h', 600, 1355, 38), ('c', 620, 1201, 3), ('h', 700, 1043, -27), ('c', 718, 1200, 4)]) == []
    assert d.state == 'away'
    sw = run(d, [('h', 3000, 2398, 900), ('c', 3016, 2398, 900)])
    assert [(s.what, s.how) for s in sw] == [('arrive', 'edge')]

def test_paused_on_the_edge_then_left_still_counts_as_edge():
    # MWB's hook can swallow the final nudge, so the last thing we saw was the cursor sitting on the edge a while ago
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2300, 1133), ('h', 20, 2398, 1133)])
    sw = run(d, [('f', 1500, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    assert [(s.what, s.how, s.side, s.pt) for s in sw] == [('depart', 'edge', 'right', (2398, 1133))]
    # but stopping 20px short and switching later is a shortcut
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2300, 1133), ('h', 20, 2379, 1133)])
    sw = run(d, [('f', 1500, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut')]

def test_shortcut_switch_has_no_edge():
    d = Detector(LAP, start=(1200, 800))
    sw = run(d, [('h', 0, 1227, 1082), ('c', 5, 1227, 1082), ('c', 15, 1200, 4), ('h', 7000, 1199, 799), ('c', 7016, 1199, 799)])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut'), ('arrive', 'shortcut')]

def test_hugging_the_edge_does_nothing():
    d = Detector(DESK, start=(1000, 1000))
    ev = []
    for i in range(500):  # 5 seconds sitting 6-37px from the left edge
        x = 6 + i % 32
        ev += [('h', i * 10, x, 1633), ('c', i * 10 + 5, x, 1633)]
    assert run(d, ev) == []
    assert d.state == 'home'

def test_moving_into_the_park_spot_by_hand_does_nothing():
    d = Detector(LAP, start=(1200, 300))
    ev = []
    for i, y in enumerate(range(300, 0, -4)):
        ev += [('h', i * 10, 1200, y), ('c', i * 10 + 5, 1200, y)]
    assert run(d, ev) == []

def test_fast_flick_short_of_the_edge_still_counts():
    sw = run(Detector(LAP, start=(1200, 800)), [('h', 0, 2281, 1074), ('h', 8, 2389, 1074), ('c', 10, 1200, 4)])
    assert [(s.how, s.side) for s in sw] == [('edge', 'right')]

def test_admin_window_in_front_hook_blind():
    # no hook events at all, just the helper grabbing focus while the cursor sits by the edge (it doesn't get parked)
    d = Detector(DESK, start=(659, 1611), fg='taskmgr.exe')
    sw = run(d, [('f', 1000, 'PowerToys.MouseWithoutBordersHelper.exe', (12, 808))])
    assert [(s.what, s.how, s.side) for s in sw] == [('depart', 'edge', 'left')]
    sw = run(d, [('h', 2400, 1, 376), ('f', 2410, 'Taskmgr.exe', (22, 382))])
    assert [(s.what, s.how, s.side) for s in sw] == [('arrive', 'edge', 'left')]

def test_focus_leaving_helper_is_a_fallback_arrival():
    d = Detector(LAP, start=(1200, 800))
    run(d, [('h', 0, 2397, 1003), ('f', 3, 'PowerToys.MouseWithoutBordersHelper.exe', (1200, 4))])
    sw = run(d, [('f', 400, 'Code.exe', (2398, 1085))])
    assert [(s.what, s.how, s.via) for s in sw] == [('arrive', 'edge', 'focus')]

def test_focus_flicker_while_leaving_does_one_departure():
    d = Detector(LAP, start=(1200, 800))
    helper = 'PowerToys.MouseWithoutBordersHelper.exe'
    sw = run(d, [('h', 0, 2397, 1003), ('c', 5, 1200, 4), ('f', 6, helper, (1200, 4)), ('f', 15, 'Code.exe', (1200, 4)), ('f', 25, helper, (1200, 4))])
    assert len(sw) == 1 and d.state == 'away'

def test_edge_that_leads_nowhere_is_not_an_edge_switch():
    # wrap off: the laptop's left edge doesn't go anywhere
    sw = run(Detector(LAP, ('right',), start=(1200, 800)), [('h', 0, 1, 936), ('c', 5, 1200, 4)])
    assert [(s.what, s.how) for s in sw] == [('depart', 'shortcut')]

def test_controlling_pc_side():
    # desktop with the real mouse: hook points run past the edge (negative x), then wiggle at the park spot while away
    d = Detector(DESK, start=(1000, 1400))
    sw = run(d, [('h', 0, 40, 1354), ('h', 4, -3, 1354), ('c', 6, 1920, 4), ('h', 50, 1923, 4), ('h', 60, 1936, 4), ('h', 3500, 1, 1344), ('c', 3516, 1, 1344)])
    assert [(s.what, s.how, s.side) for s in sw] == [('depart', 'edge', 'left'), ('arrive', 'edge', 'left')]

def test_starts_away_if_cursor_is_parked():
    assert Detector(LAP, start=(1200, 4)).state == 'away'
    assert Detector(LAP, start=(500, 500), fg='PowerToys.MouseWithoutBordersHelper.exe').state == 'away'
    assert Detector(LAP, start=(500, 500)).state == 'home'

def test_no_departure_straight_after_arriving():
    d = Detector(LAP, start=(1200, 4))
    assert len(run(d, [('h', 0, 2398, 1000), ('c', 16, 2398, 1000)])) == 1  # arrived
    assert run(d, [('h', 26, 2397, 1000), ('c', 36, 1200, 4)]) == []

def test_going_straight_back_out_is_still_an_edge():
    d = Detector(LAP, start=(1200, 4))
    sw = run(d, [('h', 0, 2398, 1177), ('c', 16, 2398, 1177), ('h', 200, 2398, 1170), ('h', 400, 2398, 1164), ('f', 402, 'PowerToys.MouseWithoutBordersHelper.exe', (2398, 1164))])
    assert [(s.what, s.how) for s in sw] == [('arrive', 'edge'), ('depart', 'edge')]

def test_describe():
    sw = depart_right(Detector(LAP, start=(1200, 800)))[0]
    assert sw.describe() == 'left via the right edge, 63% down'

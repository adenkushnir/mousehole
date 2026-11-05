# The approach effect: portal grows while you head for the edge, fades when you stop or back off, ignores drifting and scrollbars.
from mousehole import anim
from mousehole.detector import Detector
from mousehole.watcher import Watcher

def run(steps, zone=200, start=0):
    # steps: distances to the edge, one per 16ms frame, or (distance, mouse_moved). returns intensities
    a, out = anim.Approach(zone), []
    for k, s in enumerate(steps):
        d, moved = s if isinstance(s, tuple) else (s, True)
        out.append(a.update(start + k * 16, d, moved))
    return a, out

IDLE = anim.APPROACH_IDLE_MS // 16
FADE = anim.APPROACH_FADE_MS // 16 + 2

def head_in(frm=300, to=0, speed=1000):
    n = int((frm - to) / speed * 1000 / 16)
    return [frm - (frm - to) * k / n for k in range(n + 1)]

def test_grows_while_heading_for_the_edge():
    _, i = run(head_in(300, 5))
    assert i[0] == 0 and i[-1] > 0.85
    assert all(b >= a - 1e-9 for a, b in zip(i, i[1:]))  # only ever grows on the way in

def test_nothing_outside_the_zone():
    _, i = run(head_in(800, 260))
    assert max(i) == 0

def test_stays_when_you_stop():
    a, i = run(head_in(300, 20) + [(20, False)] * 125)  # stop 20px short and sit there for 2 seconds
    assert i[-1] == i[len(head_in(300, 20)) + 20] > 0.75
    assert not a.done(len(i) * 16)

def test_left_alone_it_fades_after_a_while():
    a, i = run(head_in(300, 20) + [(20, False)] * (IDLE + FADE + 5))
    assert i[len(head_in(300, 20)) + IDLE - 5] > 0.75  # still there just before the idle timeout
    assert i[-1] == 0 and a.done(len(i) * 16)

def test_moving_along_the_edge_keeps_it():
    _, i = run(head_in(300, 20) + [(20, True)] * (IDLE + 40))  # sliding up and down a scrollbar
    assert i[-1] > 0.75

def test_backing_off_shrinks_then_goes():
    stop = len(head_in(300, 30))
    a, i = run(head_in(300, 30) + [30 + k * 16 for k in range(25)] + [430] * FADE)  # back off at 1000px/s and out of the zone
    back = i[stop:]
    assert all(b <= x + 1e-9 for x, b in zip(back, back[1:]))  # only ever shrinks on the way out
    assert i[-1] == 0 and a.done(len(i) * 16)

def test_comes_back_when_you_head_in_again():
    left_alone = head_in(300, 20) + [(20, False)] * (IDLE + FADE + 5)
    again = [20 + 60 - k * 16 for k in range(5)]  # nudge back out a little and head in again
    _, i = run(left_alone + [80] + again)
    assert i[len(left_alone)] == 0 and i[-1] > 0.3

def test_slow_drift_does_nothing():
    _, i = run([150 - k * 0.8 for k in range(150)])  # 50px/s
    assert max(i) == 0

def test_scrollbar_drag_does_nothing():
    _, i = run([12] * 120)  # sitting at the same distance while dragging up and down
    assert max(i) == 0

def test_zone_off():
    _, i = run(head_in(300, 0), zone=0)
    assert max(i) == 0

def test_fast_flick_still_shows_something():
    _, i = run(head_in(250, 0, speed=4000))  # crosses the whole zone in ~60ms
    assert i[-1] > 0.2

def test_prox_curve():
    assert anim.approach_prox(0, 200) == 1 and anim.approach_prox(200, 200) == 0 and anim.approach_prox(500, 200) == 0
    assert anim.approach_prox(100, 200) < 0.5  # most of the growing is in the last stretch

def test_specks_run_from_cursor_into_portal():
    cur, centre = (20.0, 50.0), (200.0, 58.0)
    for k in range(anim.SPECKS):
        x, y, r, a = anim.speck(k, anim.SPECKS, 0.37, cur, centre, 1.0)
        assert 0 <= a <= 1 and 0 < r <= 1.7
        assert cur[0] - 30 < x < centre[0] + 30
    assert anim.speck(0, anim.SPECKS, 0, cur, centre, 1.0)[3] == 0  # just born, invisible
    assert all(anim.speck(k, anim.SPECKS, 0.4, cur, centre, 0.0)[3] == 0 for k in range(anim.SPECKS))

def test_handover_without_a_second_pop():
    hold = anim.EXIT_HOLD_MS
    assert anim.portal_scale(0, hold, s0=1.0) == 1.0
    assert max(anim.portal_scale(t, hold, s0=1.0) for t in range(0, hold)) == 1.0  # already open, no overshoot
    assert anim.portal_scale(0, hold, s0=0.4) == 0.4 and anim.portal_scale(anim.OPEN_MS + 1, hold, s0=0.4) == 1.0
    assert anim.portal_scale(hold + anim.CLOSE_MS, hold, s0=1.0) == 0

def test_watcher_near_zone_scales_with_dpi():
    w = Watcher(approach_px=200)
    w.det = Detector((0, 0, 2400, 1600), ('left', 'right'), start=(1200, 800))
    w.monitors = [{'rect': [0, 0, 2400, 1600], 'scale': 1.5}]
    assert w.near_side(2399 - 300, 800) == 'right'  # 200 logical = 300 real px at 150%
    assert w.near_side(1500, 800) is None
    assert w.near_side(100, 800) == 'left'
    assert w.near_side(1200, 4) is None  # the park spot never counts
    w.det.sides = ('right',)
    assert w.near_side(100, 800) is None
    w.approach_px = 0
    assert w.near_side(2399, 800) is None

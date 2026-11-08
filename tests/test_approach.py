# the approach effect: the portal grows as you head for the edge, stays while you're near, ignores drifting and scrollbars
from mousehole import anim
from mousehole.detector import Detector
from mousehole.watcher import Watcher

# feed distances to the edge one 16ms frame at a time, or (distance, mouse_moved). gives back the approach and every strength
def run(steps, zone=200, start=0):
    a, out = anim.Approach(zone), []
    for k, s in enumerate(steps):  # loops over each frame's distance in order
        d, moved = s if isinstance(s, tuple) else (s, True)
        out.append(a.update(start + k * 16, d, moved))
    return a, out

IDLE = anim.APPROACH_IDLE_MS // 16  # frames until the still-mouse timeout
FADE = anim.APPROACH_FADE_MS // 16 + 2  # frames to fade out, plus a little

# distances for heading from frm to to at speed px/s, one per frame
def head_in(frm=300, to=0, speed=1000):
    n = int((frm - to) / speed * 1000 / 16)
    return [frm - (frm - to) * k / n for k in range(n + 1)]  # one distance per frame

# heading for the edge grows it and it never shrinks on the way in
def test_grows_while_heading_for_the_edge():
    _, i = run(head_in(300, 5))
    assert i[0] == 0 and i[-1] > 0.85
    assert all(b >= a - 1e-9 for a, b in zip(i, i[1:]))  # checks each frame against the one before

# moving around outside the zone shows nothing
def test_nothing_outside_the_zone():
    _, i = run(head_in(800, 260))
    assert max(i) == 0

# stopping 20px short keeps it showing for 2 seconds
def test_stays_when_you_stop():
    a, i = run(head_in(300, 20) + [(20, False)] * 125)
    assert i[-1] == i[len(head_in(300, 20)) + 20] > 0.75
    assert not a.done(len(i) * 16)

# left completely still, it's still there just before the timeout and gone after it
def test_left_alone_it_fades_after_a_while():
    a, i = run(head_in(300, 20) + [(20, False)] * (IDLE + FADE + 5))
    assert i[len(head_in(300, 20)) + IDLE - 5] > 0.75
    assert i[-1] == 0 and a.done(len(i) * 16)

# sliding up and down a scrollbar counts as moving, so it stays past the timeout
def test_moving_along_the_edge_keeps_it():
    _, i = run(head_in(300, 20) + [(20, True)] * (IDLE + 40))
    assert i[-1] > 0.75

# backing off at 1000px/s only ever shrinks it, and it's gone once out of the zone
def test_backing_off_shrinks_then_goes():
    stop = len(head_in(300, 30))
    a, i = run(head_in(300, 30) + [30 + k * 16 for k in range(25)] + [430] * FADE)  # one distance per frame backing off
    back = i[stop:]
    assert all(b <= x + 1e-9 for x, b in zip(back, back[1:]))  # checks each frame against the one before
    assert i[-1] == 0 and a.done(len(i) * 16)

# after the timeout, nudging out a little and heading back in brings it back
def test_comes_back_when_you_head_in_again():
    left_alone = head_in(300, 20) + [(20, False)] * (IDLE + FADE + 5)
    again = [20 + 60 - k * 16 for k in range(5)]  # one distance per frame heading back in
    _, i = run(left_alone + [80] + again)
    assert i[len(left_alone)] == 0 and i[-1] > 0.3

# drifting towards the edge at 50px/s isn't enough
def test_slow_drift_does_nothing():
    _, i = run([150 - k * 0.8 for k in range(150)])  # one distance per frame drifting in
    assert max(i) == 0

# staying the same distance away (dragging a scrollbar) never brings it up
def test_scrollbar_drag_does_nothing():
    _, i = run([12] * 120)
    assert max(i) == 0

# approach distance 0 means off
def test_zone_off():
    _, i = run(head_in(300, 0), zone=0)
    assert max(i) == 0

# crossing the whole zone in ~60ms still shows a bit of portal
def test_fast_flick_still_shows_something():
    _, i = run(head_in(250, 0, speed=4000))
    assert i[-1] > 0.2

# 1 at the edge, 0 at the zone's outside, and most of the growing near the edge
def test_prox_curve():
    assert anim.approach_prox(0, 200) == 1 and anim.approach_prox(200, 200) == 0 and anim.approach_prox(500, 200) == 0
    assert anim.approach_prox(100, 200) < 0.5

# specks stay between the cursor and the portal, start invisible, and vanish when the strength is 0
def test_specks_run_from_cursor_into_portal():
    cur, centre = (20.0, 50.0), (200.0, 58.0)
    for k in range(anim.SPECKS):  # loops over every speck and checks where it is
        x, y, r, a = anim.speck(k, anim.SPECKS, 0.37, cur, centre, 1.0)
        assert 0 <= a <= 1 and 0 < r <= 1.7
        assert cur[0] - 30 < x < centre[0] + 30
    assert anim.speck(0, anim.SPECKS, 0, cur, centre, 1.0)[3] == 0
    assert all(anim.speck(k, anim.SPECKS, 0.4, cur, centre, 0.0)[3] == 0 for k in range(anim.SPECKS))  # checks every speck is invisible

# a handed-over portal starts where the approach left it and doesn't pop a second time
def test_handover_without_a_second_pop():
    hold = anim.EXIT_HOLD_MS
    assert anim.portal_scale(0, hold, s0=1.0) == 1.0
    assert max(anim.portal_scale(t, hold, s0=1.0) for t in range(0, hold)) == 1.0  # size at every ms while open
    assert anim.portal_scale(0, hold, s0=0.4) == 0.4 and anim.portal_scale(anim.OPEN_MS + 1, hold, s0=0.4) == 1.0
    assert anim.portal_scale(hold + anim.CLOSE_MS, hold, s0=1.0) == 0

# the watcher's approach zone is in logical px, so 200 means 300 real px at 150%
def test_watcher_near_zone_scales_with_dpi():
    w = Watcher(approach_px=200)
    w.det = Detector((0, 0, 2400, 1600), ('left', 'right'), start=(1200, 800))
    w.monitors = [{'rect': [0, 0, 2400, 1600], 'scale': 1.5}]
    assert w.near_side(2399 - 300, 800) == 'right'
    assert w.near_side(1500, 800) is None
    assert w.near_side(100, 800) == 'left'
    assert w.near_side(1200, 4) is None
    w.det.sides = ('right',)
    assert w.near_side(100, 800) is None
    w.approach_px = 0
    assert w.near_side(2399, 800) is None

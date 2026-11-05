# Animation timing: portal open/overshoot/close, the ghost spiral, halo fade, and the speed slider.
from mousehole import anim

def test_portal_opens_overshoots_holds_and_closes():
    hold = anim.EXIT_HOLD_MS
    assert anim.portal_scale(-1, hold) == 0
    assert anim.portal_scale(0, hold) == 0
    peak = max(anim.portal_scale(t, hold) for t in range(0, anim.OPEN_MS))
    assert 1.04 < peak < 1.12  # slight overshoot
    assert anim.portal_scale(anim.OPEN_MS + 10, hold) == 1.0
    assert anim.portal_scale(hold + anim.CLOSE_MS / 2, hold) > 0.8  # snaps shut: slow start...
    assert anim.portal_scale(hold + anim.CLOSE_MS * 0.95, hold) < 0.2  # ...fast finish
    assert anim.portal_scale(hold + anim.CLOSE_MS, hold) == 0

def test_lengths_match_the_brief():
    assert anim.portal_length(anim.EXIT_HOLD_MS) == 410  # ~400ms core effect
    assert anim.portal_length(anim.ENTRY_HOLD_MS) == 520
    assert anim.portal_length(anim.EXIT_HOLD_MS, speed=2) == 205

def test_speed_scales_time():
    assert anim.portal_scale(50, anim.EXIT_HOLD_MS, speed=2) == anim.portal_scale(100, anim.EXIT_HOLD_MS)

def test_ghost_gets_swallowed():
    start, target = (40.0, 50.0), (88.0, 47.0)
    first = anim.ghost(0, start, target)
    assert first[:2] == (start[0] + 12, start[1]) and first[2] == 1 and first[4] == 1  # full size, fully visible, on the spiral
    late = anim.ghost(anim.GHOST_MS - 1, start, target)
    assert abs(late[0] - target[0]) < 1 and abs(late[1] - target[1]) < 1
    assert late[2] < 0.1 and late[4] < 0.45  # shrunk and faded
    assert anim.ghost(anim.GHOST_MS, start, target) is None
    assert anim.ghost(anim.GHOST_MS / 2, start, target, speed=2) is None
    assert anim.ghost(0, start, target, inward=-1)[0] == start[0] - 12  # right edge: spiral swings onto the screen

def test_halo_fades_straight():
    assert anim.halo_alpha(0, 750) == 1 and anim.halo_alpha(375, 750) == 0.5 and anim.halo_alpha(750, 750) == 0
    assert anim.halo_alpha(-5, 750) == 0

def test_preview_cursor_glides_out():
    x0, y0 = anim.preview_cursor(0, (2, 400), 400, 1)
    x1, y1 = anim.preview_cursor(anim.PREVIEW_TRAVEL_MS, (2, 400), 400, 1)
    assert (x0, y0) == (2, 400) and x1 == 402 and y1 > 400
    assert anim.preview_cursor(anim.PREVIEW_TRAVEL_MS, (500, 400), 100, -1)[0] == 400

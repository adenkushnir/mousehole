# Animation timing with no Qt in it, so it can be tested. Times in ms, matched to reference/portal_reference.html.
import math

OPEN_MS = 170  # portal opens with ease-out and a little overshoot
CLOSE_MS = 170
GHOST_MS = 240  # ghost cursor spiral into the exit portal
EXIT_HOLD_MS = 240  # exit portal snaps shut once the ghost is swallowed, so ~410ms in all
ENTRY_HOLD_MS = 350  # entry portal stays open a bit longer, ~520ms in all like the reference
PREVIEW_GAP_MS = 140  # in the preview the blue portal opens this long after the orange one
PREVIEW_EMERGE_MS = 120  # and the fake cursor comes out this long after that
PREVIEW_TRAVEL_MS = 1100
OVERSHOOT = 1.4  # back-out easing strength, peaks about 8% past full size

def clamp(v):
    return max(0.0, min(1.0, v))

def ease_out(p):
    return 1 - (1 - p) ** 3

def ease_in(p):
    return p ** 3

def back_out(p, c1=OVERSHOOT):
    u = p - 1
    return 1 + (c1 + 1) * u ** 3 + c1 * u ** 2

def portal_scale(t, hold_ms, speed=1.0, s0=0.0):
    # 0 -> pops a bit past 1 -> settles at 1, holds, then snaps shut (slow start, fast finish)
    # s0 = how open it already was (the approach effect hands over a half or fully open portal, so no second pop)
    t *= speed
    if t < 0: return s0
    if t < OPEN_MS: return s0 + back_out(t / OPEN_MS) * (1 - s0)
    if t < hold_ms: return 1.0
    return max(0.0, 1 - ease_in(clamp((t - hold_ms) / CLOSE_MS)))

def portal_length(hold_ms, speed=1.0):
    return (hold_ms + CLOSE_MS) / speed

def ghost(t, start, target, speed=1.0, inward=1):
    # the ghost cursor gets dragged from where the cursor was into the portal, spiralling, shrinking, turning, fading
    # gives (x, y, scale, angle, alpha) or None once it's been swallowed. inward = which way is "into the screen"
    # (-1 for a right edge portal) so the spiral swings on screen instead of off it
    t *= speed
    if t < 0 or t >= GHOST_MS: return None
    p = t / GHOST_MS
    e = ease_in(p) * 0.4 + p * 0.6  # a bit of acceleration, like being sucked in
    ang, rad = p * math.pi * 2.2, (1 - p) * 12
    x = start[0] + (target[0] - start[0]) * e + math.cos(ang) * rad * inward
    y = start[1] + (target[1] - start[1]) * e + math.sin(ang) * rad * 0.6
    return x, y, 1 - p * 0.95, ang, 1 - p * 0.6

def halo_alpha(t, fade_ms):
    # full strength on arrival then a straight fade, like the reference. not tied to the speed slider, it has its own
    if t < 0: return 0.0
    return clamp(1 - t / fade_ms)

APPROACH_MIN_SPEED = 120  # px/s towards the edge before the portal starts showing, slower than that is just drifting
APPROACH_IDLE_MS = 5000  # once it's up it stays while you're in the zone, unless the mouse is left completely alone this long
APPROACH_FADE_MS = 200
APPROACH_RISE_MS = 120  # fastest it can go from nothing to full
APPROACH_PREVIEW_MS = 600
SPECKS = 12

def approach_prox(dist, zone):
    # 0 at the outside of the zone up to 1 at the edge, curved so most of the growing happens in the last stretch
    if zone <= 0: return 0.0
    return clamp(1 - dist / zone) ** 1.6

class Approach:
    # works out how strongly the exit portal should show while the cursor heads for an edge.
    # it switches on when you move towards the edge, then just follows how close you are until you leave the zone.
    # feed it the distance to the edge every frame (and whether the mouse moved at all), it gives back 0..1
    def __init__(self, zone):
        self.zone, self.v, self.last, self.on, self.moved_at, self.i = zone, 0.0, None, False, 0.0, 0.0

    def update(self, t, dist, moved=True):
        dt = 16.0
        if self.last:
            dt = max(1.0, t - self.last[0])
            self.v = 0.5 * self.v + 0.5 * (self.last[1] - dist) / dt * 1000  # px/s towards the edge, smoothed a bit
        self.last = (t, dist)
        if moved: self.moved_at = t
        prox = approach_prox(dist, self.zone)
        if prox <= 0: self.on = False  # left the zone, you have to head back in to bring it back
        elif self.v >= APPROACH_MIN_SPEED: self.on = True
        if t - self.moved_at > APPROACH_IDLE_MS: self.on = False  # mouse left alone for a while, let it go
        target = prox if self.on else 0.0
        if target > self.i: self.i = min(target, self.i + dt / APPROACH_RISE_MS)
        else: self.i = max(target, self.i - dt / APPROACH_FADE_MS)
        return self.i

    def done(self, t):
        return self.i == 0 and not self.on

def speck(k, n, secs, cursor, centre, strength):
    # one of the specks getting pulled off the cursor into the portal, speeding up as it goes in.
    # gives (x, y, radius, alpha). golden angle spread so they don't bunch up
    f = (k / n + secs * (0.9 + 1.3 * strength)) % 1.0
    a = k * 2.39996
    spread = 6 + k % 3 * 4
    sx, sy = cursor[0] + 4 + math.cos(a) * spread, cursor[1] + 8 + math.sin(a) * spread  # around the arrow's body
    e = f * f
    swirl = math.sin(f * math.pi) * (5 + k % 4 * 2)
    x = sx + (centre[0] - sx) * e + swirl * math.sin(a)
    y = sy + (centre[1] - sy) * e + swirl * math.cos(a) * 0.6
    return x, y, 1.7 * (1 - 0.5 * f), strength * math.sin(f * math.pi) ** 0.6

def preview_cursor(t, start, travel, direction, speed=1.0):
    # the pretend cursor in the preview glides out of the entry portal and curves down a little, like the reference
    e = ease_out(clamp(t * speed / PREVIEW_TRAVEL_MS))
    return start[0] + direction * travel * e, start[1] + travel * 0.18 * math.sin(e * math.pi / 2) * e

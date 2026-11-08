# animation timing with no qt in it, so it can be tested. times in ms, matched to reference/portal_reference.html
import math

OPEN_MS = 170  # portal opening time, with a little overshoot
CLOSE_MS = 170  # portal closing time
GHOST_MS = 240  # ghost cursor spiral into the exit portal
EXIT_HOLD_MS = 240  # exit portal starts closing once the ghost is swallowed, ~410ms in all
ENTRY_HOLD_MS = 350  # entry portal stays open a bit longer, ~520ms in all
PREVIEW_GAP_MS = 140  # in the preview the blue portal opens this long after the orange one
PREVIEW_EMERGE_MS = 120  # and the pretend cursor comes out this long after that
PREVIEW_TRAVEL_MS = 1100  # how long the pretend cursor glides out of the blue portal
OVERSHOOT = 1.4  # how far the opening pops past full size, ~8%

# keep a number between 0 and 1
def clamp(v):
    return max(0.0, min(1.0, v))

# fast start, slow finish
def ease_out(p):
    return 1 - (1 - p) ** 3

# slow start, fast finish
def ease_in(p):
    return p ** 3

# ease out that pops a little past 1 before settling
def back_out(p, c1=OVERSHOOT):
    u = p - 1
    return 1 + (c1 + 1) * u ** 3 + c1 * u ** 2

# portal size over time: opens with a pop, holds, then snaps shut.
# s0 is how open it already was (a handed-over approach portal), so it doesn't pop twice
def portal_scale(t, hold_ms, speed=1.0, s0=0.0):
    t *= speed
    if t < 0: return s0
    if t < OPEN_MS: return s0 + back_out(t / OPEN_MS) * (1 - s0)
    if t < hold_ms: return 1.0
    return max(0.0, 1 - ease_in(clamp((t - hold_ms) / CLOSE_MS)))

# how long a portal plays for at this speed
def portal_length(hold_ms, speed=1.0):
    return (hold_ms + CLOSE_MS) / speed

# the ghost cursor dragged from where the cursor was into the portal, spiralling, shrinking, turning, fading.
# gives (x, y, scale, angle, alpha) or None once it's gone. inward is -1 on a right edge so the spiral stays on screen
def ghost(t, start, target, speed=1.0, inward=1):
    t *= speed
    if t < 0 or t >= GHOST_MS: return None
    p = t / GHOST_MS
    e = ease_in(p) * 0.4 + p * 0.6  # a bit of acceleration, like being sucked in
    ang, rad = p * math.pi * 2.2, (1 - p) * 12
    x = start[0] + (target[0] - start[0]) * e + math.cos(ang) * rad * inward
    y = start[1] + (target[1] - start[1]) * e + math.sin(ang) * rad * 0.6
    return x, y, 1 - p * 0.95, ang, 1 - p * 0.6

# halo strength: full on arrival then a straight fade. has its own time, the speed slider doesn't touch it
def halo_alpha(t, fade_ms):
    if t < 0: return 0.0
    return clamp(1 - t / fade_ms)

APPROACH_MIN_SPEED = 120  # px/s towards the edge before the portal shows, slower is just drifting
APPROACH_IDLE_MS = 5000  # it stays while you're in range unless the mouse is left completely still this long
APPROACH_FADE_MS = 200  # fade out time
APPROACH_RISE_MS = 120  # fastest it can go from nothing to full
APPROACH_PREVIEW_MS = 600  # how long the pretend cursor takes to reach the edge in the preview
SPECKS = 12  # how many specks get pulled off the cursor

# 0 at the outside of the zone up to 1 at the edge, curved so most of the growing happens near the edge
def approach_prox(dist, zone):
    if zone <= 0: return 0.0
    return clamp(1 - dist / zone) ** 1.6

# how strongly the approach portal shows: switches on when you move towards the edge, then follows how close you are
# until you leave the zone or leave the mouse alone. feed it the distance every frame, it gives back 0 to 1
class Approach:
    # zone is the approach distance in px
    def __init__(self, zone):
        self.zone, self.v, self.last, self.on, self.moved_at, self.i = zone, 0.0, None, False, 0.0, 0.0

    # one frame: work out the speed towards the edge, switch on or off, ease the strength towards its target
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

    # faded out and switched off, nothing left to show
    def done(self, t):
        return self.i == 0 and not self.on

# speck k of n being pulled off the cursor into the portal, speeding up as it goes. gives (x, y, radius, alpha).
# spread by the golden angle so they don't bunch up
def speck(k, n, secs, cursor, centre, strength):
    f = (k / n + secs * (0.9 + 1.3 * strength)) % 1.0
    a = k * 2.39996
    spread = 6 + k % 3 * 4
    sx, sy = cursor[0] + 4 + math.cos(a) * spread, cursor[1] + 8 + math.sin(a) * spread  # around the arrow's body
    e = f * f
    swirl = math.sin(f * math.pi) * (5 + k % 4 * 2)
    x = sx + (centre[0] - sx) * e + swirl * math.sin(a)
    y = sy + (centre[1] - sy) * e + swirl * math.cos(a) * 0.6
    return x, y, 1.7 * (1 - 0.5 * f), strength * math.sin(f * math.pi) ** 0.6

# where the preview's pretend cursor is as it glides out of the entry portal, curving down a little
def preview_cursor(t, start, travel, direction, speed=1.0):
    e = ease_out(clamp(t * speed / PREVIEW_TRAVEL_MS))
    return start[0] + direction * travel * e, start[1] + travel * 0.18 * math.sin(e * math.pi / 2) * e

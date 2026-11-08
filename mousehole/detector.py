# the switch detector: turns mouse hook events, cursor samples and foreground changes into "left this pc" and "arrived" events.
# plain python with no windows calls, so it can run off the live hook or replay a recording
from dataclasses import dataclass
from . import edges

HELPER = 'mousewithoutbordershelper'  # mwb's helper exe, it grabs focus when the cursor leaves
EDGE_ZONE = 60  # how close to an edge counts as touching it. fast flicks can stop ~10px short
EDGE_RECENT_MS = 100  # the edge touch has to be this fresh when mwb parks the cursor
PARK_X, PARK_Y = 40, 8  # how close to the top centre counts as parked
NEAR_PARK = 150  # wiggles around the park spot on the controlling pc land within this, ignored while away
JUMP = 150  # the cursor has to jump into the park spot, not wander in by hand
MIN_AWAY_MS = 100  # right after leaving, mwb sometimes bounces the cursor back to the edge for ~10ms
MIN_HOME_MS = 50  # shortest stay before leaving again counts. real round trips were 200ms+
CONFIRM_MS = 15  # an arrival needs a cursor sample this long after showing the cursor really left the park spot
EDGE_REST = 4  # sitting this close to an edge counts as touching it however long ago, mwb can swallow the final nudge

# one detected switch
@dataclass
class Switch:
    what: str  # 'depart' or 'arrive'
    how: str  # 'edge' or 'shortcut'
    t: float  # when, in ms
    pt: tuple = None  # where the cursor was, real pixels
    side: str = None  # 'left' or 'right' for edge switches
    frac: float = None  # how far down the edge, 0 top to 1 bottom
    via: str = ''  # which signal gave it away, for the log

    # plain words for the log and the detections window
    def describe(self):
        if self.how == 'edge':
            verb = 'left via' if self.what == 'depart' else 'arrived via'
            return f'{verb} the {self.side} edge, {self.frac:.0%} down'
        return ('left' if self.what == 'depart' else 'arrived') + ' by shortcut (no animation)'

# are two points more than a jump apart
def far(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) > JUMP

# keeps track of whether the cursor is here or away and spots the moments it changes
class Detector:
    # screen box, which edges switch, where mwb parks, where the cursor starts and what's in front
    def __init__(self, box, sides=('left', 'right'), parks=None, start=None, fg=''):
        self.set_screen(box, sides, parks)
        self.state, self.since, self.edge, self.last, self.fg = 'home', -1e9, None, start, (fg or '').lower()
        self.pending = None  # (t, point) of an arrival waiting for the real cursor to back it up
        if (start and self.parked(start)) or HELPER in self.fg: self.state = 'away'  # started while the cursor is on the other pc

    # new screen size, switching edges or park spots
    def set_screen(self, box, sides=None, parks=None):
        self.box = tuple(box)
        if sides is not None: self.sides = tuple(sides)
        self.parks = parks or edges.park_spots(self.box)

    # is the point right on a park spot
    def parked(self, p):
        return any(abs(p[0] - x) <= PARK_X and p[1] - y <= PARK_Y for x, y in self.parks)  # checks each park spot

    # is the point anywhere around a park spot
    def near_park(self, p):
        return any(abs(p[0] - x) <= NEAR_PARK and p[1] - y <= NEAR_PARK for x, y in self.parks)  # checks each park spot

    # which switching edge the point is touching, if any
    def side(self, p):
        return None if self.near_park(p) else edges.side_of(p[0], self.box, EDGE_ZONE, self.sides)

    # a mouse hook event. at home it just notes edge touches, away it can start an arrival
    def hook(self, t, x, y):
        p = (x, y)
        if self.state == 'home':
            if self.side(p): self.edge = (t, p)
            self.last = p
            return None
        # away: input that isn't just wiggling round the park spot might mean we're back, a cursor sample has to confirm it
        if not self.pending and t - self.since >= MIN_AWAY_MS and not self.near_park(p): self.pending = (t, p)
        return None

    # a cursor sample. confirms or drops a pending arrival, or spots mwb parking the cursor (a departure)
    def cursor(self, t, x, y):
        p, sw = (x, y), None
        if self.state == 'away' and self.pending and t - self.pending[0] >= CONFIRM_MS:
            pt, pp = self.pending
            self.pending = None
            if not self.parked(p): sw = self._arrive(pt, pp, 'input')  # still parked means it was just a wiggle
        elif self.state == 'home':
            if self.parked(p) and self.last and far(p, self.last) and t - self.since >= MIN_HOME_MS: sw = self._depart(t, 'park')
            elif self.side(p): self.edge = (t, p)
        self.last = p
        return sw

    # the window in front changed. mwb's helper taking focus means we left, it letting go means we're back
    def foreground(self, t, exe, cursor=None):
        exe = (exe or '').lower()
        was, self.fg = self.fg, exe
        if HELPER in exe and HELPER not in was and self.state == 'home' and t - self.since >= MIN_HOME_MS:
            # with an admin window in front the hook goes blind, so where the cursor is now counts as the edge touch
            if cursor and not self._recent_edge(t) and not self.parked(cursor) and self.side(cursor): self.edge = (t, cursor)
            return self._depart(t, 'focus')
        if HELPER in was and HELPER not in exe and self.state == 'away' and t - self.since >= MIN_AWAY_MS and cursor and not self.near_park(cursor):
            return self._arrive(t, cursor, 'focus')
        return None

    # was an edge touched in the last moment
    def _recent_edge(self, t):
        return self.edge is not None and t - self.edge[0] <= EDGE_RECENT_MS

    # is the last place we saw the cursor right on a switching edge
    def _resting_on_edge(self):
        p = self.last
        return p is not None and not self.near_park(p) and edges.side_of(p[0], self.box, EDGE_REST, self.sides) is not None

    # mark the cursor as away and say whether it went through an edge or by shortcut
    def _depart(self, t, via):
        self.state, self.since, self.pending = 'away', t, None
        if self._recent_edge(t):
            p = self.edge[1]
            sw = Switch('depart', 'edge', t, p, self.side(p), edges.edge_frac(p[1], self.box), f'{via}, edge {t - self.edge[0]:.0f}ms before')
        elif self._resting_on_edge():
            p = self.last
            sw = Switch('depart', 'edge', t, p, self.side(p), edges.edge_frac(p[1], self.box), f'{via}, was resting on the edge')
        else:
            sw = Switch('depart', 'shortcut', t, self.last, via=f'{via}, no edge touch')
        self.edge = None
        return sw

    # mark the cursor as home and say whether it came in on an edge or by shortcut
    def _arrive(self, t, p, via):
        self.state, self.since, self.pending = 'home', t, None
        self.last = p
        s = self.side(p)
        if s:
            self.edge = (t, p)  # we're sitting on the edge, so going straight back out still counts as an edge
            return Switch('arrive', 'edge', t, p, s, edges.edge_frac(p[1], self.box), via)
        self.edge = None
        return Switch('arrive', 'shortcut', t, p, via=via)

# The switch detector: turns mouse hook events, cursor samples and foreground changes into "left this PC" / "arrived" events.
# Plain python with no windows calls, so it can run off the live hook or replay a recording. Rules come from the M1 recordings.
from dataclasses import dataclass
from . import edges

HELPER = 'mousewithoutbordershelper'  # PowerToys.MouseWithoutBordersHelper.exe grabs focus when the cursor leaves
EDGE_ZONE = 60  # on a fast flick the last position can be ~10px short of the edge, 60 to be safe
EDGE_RECENT_MS = 100  # the edge touch has to be this fresh when MWB parks the cursor
PARK_X, PARK_Y = 40, 8  # MWB parks the leaving cursor at the top centre
NEAR_PARK = 150  # moving the mouse on the controlling PC wiggles around the park spot, ignore that while away
JUMP = 150  # the cursor has to jump into the park spot, not wander in by hand
MIN_AWAY_MS = 100  # right after leaving MWB sometimes bounces the cursor back to the edge for ~10ms
MIN_HOME_MS = 50  # real round trips seen were 200ms+
CONFIRM_MS = 15  # an arrival has to be backed up by the real cursor this long after. wiggles on the controlling PC
# can land 150px+ from the park spot (fast flicks) but MWB keeps the actual cursor pinned there, so check the cursor
EDGE_REST = 4  # sitting this close to a switching edge counts as touching it, however long ago you stopped there
# (if MWB's own hook runs before ours it can swallow the final nudge that triggers the switch, so we never see it)

@dataclass
class Switch:
    what: str  # 'depart' or 'arrive'
    how: str  # 'edge' or 'shortcut'
    t: float
    pt: tuple = None
    side: str = None
    frac: float = None
    via: str = ''

    def describe(self):
        if self.how == 'edge':
            verb = 'left via' if self.what == 'depart' else 'arrived via'
            return f'{verb} the {self.side} edge, {self.frac:.0%} down'
        return ('left' if self.what == 'depart' else 'arrived') + ' by shortcut (no animation)'

def far(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) > JUMP

class Detector:
    def __init__(self, box, sides=('left', 'right'), parks=None, start=None, fg=''):
        self.set_screen(box, sides, parks)
        self.state, self.since, self.edge, self.last, self.fg = 'home', -1e9, None, start, (fg or '').lower()
        self.pending = None  # (t, point) of an arrival waiting for the real cursor to back it up
        # if we start while the cursor is already over on the other PC
        if (start and self.parked(start)) or HELPER in self.fg: self.state = 'away'

    def set_screen(self, box, sides=None, parks=None):
        self.box = tuple(box)
        if sides is not None: self.sides = tuple(sides)
        self.parks = parks or edges.park_spots(self.box)

    def parked(self, p):
        return any(abs(p[0] - x) <= PARK_X and p[1] - y <= PARK_Y for x, y in self.parks)

    def near_park(self, p):
        return any(abs(p[0] - x) <= NEAR_PARK and p[1] - y <= NEAR_PARK for x, y in self.parks)

    def side(self, p):
        return None if self.near_park(p) else edges.side_of(p[0], self.box, EDGE_ZONE, self.sides)

    def hook(self, t, x, y):
        p = (x, y)
        if self.state == 'home':
            if self.side(p): self.edge = (t, p)
            self.last = p
            return None
        # away: the first input that isn't just wiggling around the park spot might mean the cursor is back.
        # don't believe it until a cursor sample says the cursor really left the park spot
        if not self.pending and t - self.since >= MIN_AWAY_MS and not self.near_park(p): self.pending = (t, p)
        return None

    def cursor(self, t, x, y):
        p, sw = (x, y), None
        if self.state == 'away' and self.pending and t - self.pending[0] >= CONFIRM_MS:
            pt, pp = self.pending
            self.pending = None
            if not self.parked(p): sw = self._arrive(pt, pp, 'input')
            # else it was a wiggle on the controlling PC, MWB still has the cursor pinned at the park spot
        elif self.state == 'home':
            if self.parked(p) and self.last and far(p, self.last) and t - self.since >= MIN_HOME_MS: sw = self._depart(t, 'park')
            elif self.side(p): self.edge = (t, p)
        self.last = p
        return sw

    def foreground(self, t, exe, cursor=None):
        exe = (exe or '').lower()
        was, self.fg = self.fg, exe
        if HELPER in exe and HELPER not in was and self.state == 'home' and t - self.since >= MIN_HOME_MS:
            # with an admin window in front the hook goes blind, so use where the cursor is right now as the edge touch
            if cursor and not self._recent_edge(t) and not self.parked(cursor) and self.side(cursor): self.edge = (t, cursor)
            return self._depart(t, 'focus')
        if HELPER in was and HELPER not in exe and self.state == 'away' and t - self.since >= MIN_AWAY_MS and cursor and not self.near_park(cursor):
            return self._arrive(t, cursor, 'focus')
        return None

    def _recent_edge(self, t):
        return self.edge is not None and t - self.edge[0] <= EDGE_RECENT_MS

    def _resting_on_edge(self):
        p = self.last
        return p is not None and not self.near_park(p) and edges.side_of(p[0], self.box, EDGE_REST, self.sides) is not None

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

    def _arrive(self, t, p, via):
        self.state, self.since, self.pending = 'home', t, None
        self.last = p
        s = self.side(p)
        if s:
            self.edge = (t, p)  # we're sitting on the edge now, so going straight back out still counts as an edge
            return Switch('arrive', 'edge', t, p, s, edges.edge_frac(p[1], self.box), via)
        self.edge = None
        return Switch('arrive', 'shortcut', t, p, via=via)

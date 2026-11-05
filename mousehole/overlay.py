# The portal overlay: small click-through windows that pop up on the screen edge (and one that rides along with the
# cursor for the halo), repainted at ~60fps only while something is playing. Idle = no timer, no windows shown.
import logging
from PySide6.QtCore import QElapsedTimer, QObject, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget
from . import anim, edges, portal, win32

log = logging.getLogger('mousehole')

class OverlayWin(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.draw = None
        win32.make_click_through(int(self.winId()))

    def showEvent(self, e):
        win32.make_click_through(int(self.winId()))  # in case Qt rebuilt the native window
        super().showEvent(e)

    def paintEvent(self, e):
        if not self.draw: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.draw(p)
        p.end()

def screen_for(pt):
    # which Qt screen a real-pixel point is on. Qt keeps each screen's top-left in real pixels and scales the size down
    best = None
    for s in QGuiApplication.screens():
        g, d = s.geometry(), s.devicePixelRatio()
        rect = (g.x(), g.y(), g.x() + round(g.width() * d), g.y() + round(g.height() * d))
        dist = max(rect[0] - pt[0], 0, pt[0] - rect[2] + 1) + max(rect[1] - pt[1], 0, pt[1] - rect[3] + 1)
        if best is None or dist < best[0]: best = (dist, s, rect)
    return best[1], best[2]

def to_logical(pt):
    s, rect = screen_for(pt)
    g = s.geometry()
    x, y = edges.to_logical(pt, rect, s.devicePixelRatio(), (g.x(), g.y()))
    # hook points can be a few px past the edge, keep it on the screen
    return s, QPointF(min(max(x, g.x()), g.x() + g.width() - 1), min(max(y, g.y()), g.y() + g.height() - 1))

class ApproachPiece:
    # the exit portal growing on the edge while the cursor heads for it, specks getting pulled off the cursor.
    # follows the cursor's height. fake=True draws a pretend cursor (preview)
    def __init__(self, a, geo, side, follow, fake=False):
        s = a.s
        self.geo, self.side, self.follow, self.fake = geo, side, follow, fake
        self.col, self.glow, self.size, self.speed = s['exit_color'], s['glow'], s['portal_size'], s['speed']
        self.edge_x = geo.x() if side == 'left' else geo.x() + geo.width()
        self.w = int(s['approach_px'] + 60)
        self.h = int(max(2 * (28 * self.size * 1.1 + 16 + 8 * self.glow), 90)) + 30
        self.win = a.win()
        self.win.resize(self.w, self.h)
        self.win.draw = self.paint
        self.state = anim.Approach(s['approach_px'])
        self.t0, self.t, self.phase, self.i = a.now(), 0.0, 600.0, 0.0
        self.tip = self.gy = self.jumped = None
        self.c, self.tip_local, self.dead = QPointF(0, 0), (0, 0), False
        self.still_since, self.resting = 0.0, False

    def kill(self):
        self.dead = True
        self.win.hide()

    def update(self, now):
        if self.dead: return False
        t = now - self.t0
        dt, self.t = t - self.t, t
        tip = self.follow(t)
        moved = self.tip is None or tip != self.tip  # any movement at all, up/down along a scrollbar counts too
        if self.tip is not None and abs(tip.x() - self.tip.x()) + abs(tip.y() - self.tip.y()) > 150:
            # the cursor jumped, most likely MWB just parked it. hang on to the last spot, the departure lands any ms now
            if self.jumped is None: self.jumped = t
            if t - self.jumped < 120: tip = self.tip
        else:
            self.jumped = None
        self.tip = tip
        dist = max(0.0, tip.x() - self.edge_x if self.side == 'left' else self.edge_x - tip.x())
        self.i = self.state.update(t, dist, moved)
        if moved: self.still_since = t
        self.resting = not self.fake and t - self.still_since > 250  # mouse is still, the animator can relax to 30fps
        self.phase += dt * (1 + 2 * self.i) * self.speed  # spins faster the closer you are
        g = self.geo
        self.gy = min(max(tip.y() + 8, g.y() + 30), g.y() + g.height() - 30)  # level with the arrow's body
        x0 = self.edge_x if self.side == 'left' else self.edge_x - self.w
        y0 = int(min(max(self.gy - self.h / 2, g.y()), g.y() + g.height() - self.h))
        if self.win.x() != x0 or self.win.y() != y0: self.win.move(int(x0), y0)
        self.c = QPointF(self.edge_x - x0, self.gy - y0)
        self.tip_local = (tip.x() - x0, tip.y() - y0)
        if self.i > 0.01 or self.fake:
            if not self.win.isVisible(): self.win.show()
            self.win.update()
        elif self.win.isVisible():
            self.win.hide()
        return self.fake or t < 150 or not self.state.done(t)  # give it a few frames to see which way you're moving

    def paint(self, p):
        if self.i > 0.005:
            portal.draw_vortex(p, self.c.x(), self.c.y(), self.i, self.col, self.phase, self.glow, self.size)
            secs = self.t / 1000 * self.speed
            portal.draw_specks(p, [anim.speck(k, anim.SPECKS, secs, self.tip_local, (self.c.x(), self.c.y()), self.i) for k in range(anim.SPECKS)], self.col)
        if self.fake: portal.draw_cursor(p, *self.tip_local)

class PortalPiece:
    # one vortex on a screen edge, optionally with the ghost cursor getting sucked in.
    # s0/phase let it carry straight on from an approach portal that's already open
    def __init__(self, a, geo, side, y, col, hold, ghost_from=None, delay=0, s0=0.0, phase=600.0):
        s = a.s
        self.col, self.hold, self.speed, self.glow, self.size = col, hold, s['speed'], s['glow'], s['portal_size']
        edge_x = geo.x() if side == 'left' else geo.x() + geo.width()
        pad = 16 + 8 * self.glow  # room for the glow around the oval
        w, h = 12 * self.size * 1.1 + pad, 2 * (28 * self.size * 1.1 + pad)
        if ghost_from is not None:
            w, h = max(w, abs(ghost_from.x() - edge_x) + 30 + 12), max(h, 2 * abs(ghost_from.y() - y) + 50)  # +12 for the spiral
        w, h = int(w) + 2, int(h) + 2
        x0 = edge_x if side == 'left' else edge_x - w
        y0 = int(min(max(y - h / 2, geo.y()), geo.y() + geo.height() - h))  # stay on this screen near corners
        self.win = a.win()
        self.win.setGeometry(QRect(int(x0), y0, w, h))
        self.c = QPointF(edge_x - x0, y - y0)  # oval centre sits right on the edge, so the window clips the outer half
        self.ghost_from = None if ghost_from is None else (ghost_from.x() - x0, ghost_from.y() - y0)
        self.inward = 1 if side == 'left' else -1
        self.target = (self.c.x() + 4 * self.inward, self.c.y() - 8)
        self.t0, self.t, self.s0, self.phase = a.now() + delay, -1, s0, phase
        self.length = anim.portal_length(hold, self.speed)
        self.win.draw = self.paint

    def update(self, now):
        self.t = now - self.t0
        if self.t >= 0:
            if not self.win.isVisible(): self.win.show()
            self.win.update()
        return self.t < self.length

    def paint(self, p):
        if self.t < 0: return
        sc = anim.portal_scale(self.t, self.hold, self.speed, self.s0)
        # an approach portal hands over spinning fast, so keep that pace while it swallows
        spin = self.phase + self.t * (3 if self.s0 else 1) * self.speed
        portal.draw_vortex(p, self.c.x(), self.c.y(), sc, self.col, spin, self.glow, self.size)
        if self.ghost_from:
            g = anim.ghost(self.t, self.ghost_from, self.target, self.speed, self.inward)
            if g: portal.draw_cursor(p, *g)

class HaloPiece:
    # soft glow riding along with the cursor and fading out. fake=True draws a pretend cursor too (preview)
    def __init__(self, a, follow, delay=0, fake=False):
        s = a.s
        self.follow, self.fake = follow, fake
        self.r, self.fade, self.col = s['halo_size'], s['halo_fade_ms'], s['entry_color']
        self.n = int(2 * self.r + 12)
        self.win = a.win()
        self.win.resize(self.n, self.n)
        self.win.draw = self.paint
        self.t0, self.t, self.alpha, self.tip = a.now() + delay, -1, 0.0, (0, 0)
        self.length = max(self.fade, anim.PREVIEW_TRAVEL_MS / s['speed']) if fake else self.fade

    def update(self, now):
        self.t = now - self.t0
        if self.t < 0: return True
        self.alpha = anim.halo_alpha(self.t, self.fade)
        tip = self.follow(self.t)
        # like the reference, the glow is centred on the arrow's body, a bit right of and below the tip
        wx, wy = round(tip.x() + 4 - self.n / 2), round(tip.y() + 8 - self.n / 2)
        self.win.move(wx, wy)
        self.tip = (tip.x() - wx, tip.y() - wy)
        if not self.win.isVisible(): self.win.show()
        self.win.update()
        return self.t < self.length

    def paint(self, p):
        if self.t < 0: return
        portal.draw_halo(p, self.tip[0] + 4, self.tip[1] + 8, self.r, self.col, self.alpha)
        if self.fake: portal.draw_cursor(p, *self.tip)

class Animator(QObject):
    def __init__(self, settings):
        super().__init__()
        self.s = settings
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.pieces, self.approaching = [], None
        # make the windows up front, creating them mid-switch made the first frame ~70ms late
        self.pool = [OverlayWin() for _ in range(4)]

    def now(self):
        return self.clock.elapsed()

    def win(self):
        # windows get reused, making a fresh native window every switch would cost a few ms of lag
        return self.pool.pop() if self.pool else OverlayWin()

    def add(self, piece):
        self.pieces.append(piece)
        piece.update(self.now())
        self.timer.setInterval(16)
        if not self.timer.isActive(): self.timer.start()

    def tick(self):
        now = self.now()
        for pc in list(self.pieces):
            if not pc.update(now):
                pc.win.hide()
                pc.win.draw = None
                self.pool.append(pc.win)
                self.pieces.remove(pc)
                if pc is self.approaching: self.approaching = None
        if not self.pieces:
            self.timer.stop()  # nothing playing, nothing ticking
            return
        # only a portal sitting there while the mouse is still: 30fps looks the same and halves the cost
        want = 33 if all(getattr(pc, 'resting', False) for pc in self.pieces) else 16
        if self.timer.interval() != want: self.timer.setInterval(want)

    def busy(self):
        return bool(self.pieces)

    def approach(self, side, screen=None, follow=None, fake=False):
        # the cursor is near a switching edge. start the approach portal unless one is already running
        if self.approaching and not self.approaching.dead: return self.approaching
        if not self.s['approach_px']: return None
        cur = QCursor.pos()
        screen = screen or QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        self.approaching = ApproachPiece(self, screen.geometry(), side, follow or (lambda t: QPointF(QCursor.pos())), fake)
        self.add(self.approaching)
        return self.approaching

    def exit_portal(self, geo, side, y, ghost_from):
        # if the approach portal is already open on this edge, carry straight on from it instead of popping a new one open
        ap, s0, phase = self.approaching, 0.0, 600.0
        if ap and not ap.dead and ap.side == side and ap.gy is not None:
            y, s0, phase = ap.gy, ap.i, ap.phase
            ap.kill()
        self.add(PortalPiece(self, geo, side, y, self.s['exit_color'], anim.EXIT_HOLD_MS, ghost_from=ghost_from, s0=s0, phase=phase))

    def play(self, sw):
        if sw.how != 'edge' or not sw.pt: return
        screen, at = to_logical(sw.pt)
        if sw.what == 'depart':
            self.exit_portal(screen.geometry(), sw.side, at.y(), at)
        else:
            self.add(PortalPiece(self, screen.geometry(), sw.side, at.y(), self.s['entry_color'], anim.ENTRY_HOLD_MS))
            self.add(HaloPiece(self, lambda t: QPointF(QCursor.pos())))

    def preview(self, screen=None):
        # the whole thing on one screen: a pretend cursor heads for the right edge and the orange portal grows and swallows it,
        # then blue on the left lets it back out
        cur = QCursor.pos()
        screen = screen or QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        g, sp = screen.geometry(), self.s['speed']
        y = min(max(cur.y(), g.y() + 120), g.y() + g.height() - 120)
        right, zone = g.x() + g.width(), self.s['approach_px']
        if not zone: return self._preview_tail(g, y, QPointF(right - 60, y - 8))
        x0, dur = right - zone * 1.15, anim.APPROACH_PREVIEW_MS / sp
        path = lambda t: QPointF(x0 + (right - 2 - x0) * anim.clamp(t / dur) ** 1.5, y - 8)  # speeds up into the edge
        if self.approaching: self.approaching.kill()
        self.approaching = None
        self.approach('right', screen, path, fake=True)
        QTimer.singleShot(int(dur), lambda: self._preview_tail(g, y, QPointF(right - 2, y - 8)))

    def _preview_tail(self, g, y, ghost_from):
        sp = self.s['speed']
        self.exit_portal(g, 'right', y, ghost_from)
        gap = anim.PREVIEW_GAP_MS / sp
        self.add(PortalPiece(self, g, 'left', y, self.s['entry_color'], anim.ENTRY_HOLD_MS, delay=gap))
        start, travel = (g.x() + 2, y - 8), g.width() * 0.25
        self.add(HaloPiece(self, lambda t: QPointF(*anim.preview_cursor(t, start, travel, 1, sp)), delay=gap + anim.PREVIEW_EMERGE_MS / sp, fake=True))

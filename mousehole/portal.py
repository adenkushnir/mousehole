# QPainter drawing for the portal look: swirling vortex, ghost cursor, halo, plus the little mousehole logo.
import math
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient

CURSOR = QPolygonF([QPointF(*p) for p in ((0, 0), (0, 17), (4.5, 13), (7.5, 19.5), (10, 18.5), (7, 12), (12.5, 12))])

def colour(c, alpha):
    q = QColor(c)
    q.setAlphaF(max(0.0, min(1.0, alpha)))
    return q

_rims = {}

def rim(col, rx, ry, glow, size, dpr):
    # the glow, fill and outline only change when the size does, and the wide soft glow strokes are by far the
    # slowest thing to draw, so draw them once into a pixmap and reuse it every frame
    key = (col, rx, ry, glow, size, dpr)
    pm = _rims.get(key)
    if pm is None:
        if len(_rims) > 300: _rims.clear()
        pad = 9 * size + 3
        w, h = 2 * (rx + pad), 2 * (ry + pad)
        pm = QPixmap(max(1, round(w * dpr)), max(1, round(h * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing)
        c = QPointF(w / 2, h / 2)
        q.setBrush(Qt.NoBrush)
        # canvas shadowBlur doesn't exist in QPainter, a few wide faint strokes fake the glow
        for pw, a in ((14, 0.07), (9, 0.12), (6, 0.2)):
            q.setPen(QPen(colour(col, a * glow), pw * size))
            q.drawEllipse(c, rx, ry)
        q.setBrush(colour(col, 0.25))
        q.setPen(QPen(QColor(col), 3 * max(0.7, size)))
        q.drawEllipse(c, rx, ry)
        q.end()
        _rims[key] = pm
    return pm

def draw_vortex(p, cx, cy, s, col, t, glow=1.0, size=1.0):
    # glowing oval with a see-through fill, 3 arcs turning inside and 8 specks orbiting.
    # cx sits on the screen edge so only the inner half shows. s is the open/close scale, t just drives the spin
    if s <= 0: return
    s = round(s * 50) / 50 or 0.02  # steps of 2% are invisible and let the rim pixmaps get reused
    rx, ry = 12 * size * s, 28 * size * s
    dev = p.device()
    pm = rim(col, rx, ry, glow, size, dev.devicePixelRatioF() if dev else 1.0)
    w, h = pm.width() / pm.devicePixelRatio(), pm.height() / pm.devicePixelRatio()
    p.drawPixmap(QPointF(cx - w / 2, cy - h / 2), pm)
    p.setPen(QPen(QColor(col), 1.6 * max(0.7, size), Qt.SolidLine, Qt.RoundCap))
    inner = QRectF(cx - rx * 0.65, cy - ry * 0.65, rx * 1.3, ry * 1.3)
    for i in range(3):
        a = (t * 0.012 + i * 2.094) % (2 * math.pi)  # radians, wrapped so it never overflows qt's int. qt wants 1/16ths of a degree and counts the other way
        p.drawArc(inner, int(-math.degrees(a) * 16), int(-math.degrees(1.3) * 16))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor('#ffffff'))
    for i in range(8):
        a, k = t * 0.008 + i * 0.785, 0.35 + 0.4 * ((i * 37) % 10) / 10
        p.drawEllipse(QPointF(cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k), 1.3, 1.3)

def draw_specks(p, specks, col):
    # the bits getting pulled off the cursor, every other one white so they read against any background
    p.setPen(Qt.NoPen)
    for k, (x, y, r, a) in enumerate(specks):
        if a <= 0.01: continue
        p.setBrush(colour('#ffffff' if k % 2 else col, a))
        p.drawEllipse(QPointF(x, y), r, r)

def draw_cursor(p, x, y, scale=1.0, angle=0.0, alpha=1.0):
    # plain white arrow with a black outline, tip at (x, y)
    p.save()
    p.setOpacity(alpha)
    p.translate(x, y)
    p.rotate(math.degrees(angle))
    p.scale(scale, scale)
    p.setPen(QPen(QColor('#000000'), 1.2))
    p.setBrush(QColor('#ffffff'))
    p.drawPolygon(CURSOR)
    p.restore()

def draw_halo(p, cx, cy, r, col, alpha):
    if alpha <= 0: return
    g = QRadialGradient(QPointF(cx, cy), r)
    g.setColorAt(0, colour(col, 0.6 * alpha))
    g.setColorAt(1, colour(col, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(cx, cy), r, r)

def logo(size=64, recording=False):
    # dark mousehole arch with an orange rim, drawn on a 64 grid and scaled. red dot while recording
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 64, size / 64)
    arch = QPainterPath()
    arch.moveTo(10, 60); arch.lineTo(10, 32); arch.arcTo(10, 6, 44, 52, 180, -180); arch.lineTo(54, 60); arch.closeSubpath()
    p.setPen(QPen(QColor('#FF8A1F'), 6))
    p.setBrush(QColor('#0e1015'))
    p.drawPath(arch)
    if recording:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#e02020'))
        p.drawEllipse(34, 34, 28, 28)
    p.end()
    return pm

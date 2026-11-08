# paints the portal into an off-screen image and checks the pixels: right colour, half clipped at the edge, size follows the setting
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from mousehole import portal

# one qt app for this whole file, qt needs one before it can draw
@pytest.fixture(scope='module', autouse=True)
def app():
    return QGuiApplication.instance() or QGuiApplication([])

# run a drawing function on a blank see-through image and hand the image back
def paint(fn, w=100, h=120):
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    fn(p)
    p.end()
    return img

# the columns between x0 and x1 that have any visible pixel
def lit(img, x0=0, x1=None):
    x1 = img.width() if x1 is None else x1
    return {x for x in range(x0, x1) for y in range(img.height()) if QColor.fromRgba(img.pixel(x, y)).alpha() > 20}  # every column with at least one visible pixel

# centred on the image's right edge like the exit portal: only the inner half shows, and it's orange
def test_vortex_is_orange_and_clipped_at_the_edge():
    img = paint(lambda p: portal.draw_vortex(p, 100, 60, 1.0, '#FF8A1F', 0))
    cols = lit(img)
    assert cols and min(cols) >= 100 - 12 - 10
    c = QColor.fromRgba(img.pixel(100 - 12, 60))
    assert c.red() > c.green() > c.blue()

# a bigger portal size reaches further in from the edge
def test_vortex_size_follows_the_setting():
    small = min(lit(paint(lambda p: portal.draw_vortex(p, 100, 60, 1.0, '#2E9BFF', 0, size=0.5))))
    big = min(lit(paint(lambda p: portal.draw_vortex(p, 100, 60, 1.0, '#2E9BFF', 0, size=1.5))))
    assert big < small

# a fully closed portal draws nothing
def test_closed_portal_draws_nothing():
    assert not lit(paint(lambda p: portal.draw_vortex(p, 100, 60, 0.0, '#FF8A1F', 0)))

# the halo is blue in the middle and stops at its radius, and the cursor is white
def test_halo_and_cursor():
    img = paint(lambda p: portal.draw_halo(p, 50, 60, 32, '#2E9BFF', 1.0))
    c = QColor.fromRgba(img.pixel(50, 60))
    assert c.blue() > c.red() and c.alpha() > 100
    assert QColor.fromRgba(img.pixel(50, 60 + 33)).alpha() == 0
    assert not lit(paint(lambda p: portal.draw_halo(p, 50, 60, 32, '#2E9BFF', 0.0)))
    cur = paint(lambda p: portal.draw_cursor(p, 10, 10))
    assert QColor.fromRgba(cur.pixel(12, 20)).lightness() > 200

# the logo draws at the size asked for
def test_logo():
    pm = portal.logo(32)
    assert pm.width() == 32 and not pm.toImage().isNull()

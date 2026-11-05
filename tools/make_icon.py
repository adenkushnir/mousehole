# Makes assets/mousehole.ico from the same logo the tray draws. Run: python tools/make_icon.py
import os, struct, sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication
app = QGuiApplication([])
from mousehole import portal

SIZES = [16, 20, 24, 32, 40, 48, 64, 256]
pngs = []
for s in SIZES:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    portal.logo(s).save(buf, 'PNG')
    pngs.append(bytes(ba))
# .ico = 6 byte header, a 16 byte entry per image, then the images. png inside ico works on anything since vista
out = struct.pack('<HHH', 0, 1, len(SIZES))
off = 6 + 16 * len(SIZES)
for s, data in zip(SIZES, pngs):
    out += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(data), off)  # 256 is written as 0
    off += len(data)
out += b''.join(pngs)
path = os.path.join(ROOT, 'assets', 'mousehole.ico')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'wb') as f: f.write(out)
print('wrote', path, len(out), 'bytes')

# Tray icon and menu. Runs the switch detector, plays the portal on each edge switch, and holds the settings and diagnostics.
import logging, os
from datetime import datetime
from PySide6.QtCore import QLockFile, QObject, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QPlainTextEdit, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget
from . import __version__, paths, portal, settings, win32
from .overlay import Animator
from .recorder import Recorder
from .settings_ui import SettingsWindow
from .watcher import Watcher

log = logging.getLogger('mousehole')
SERVER = 'mousehole-' + os.environ.get('USERNAME', 'user')  # a second copy pokes this so the first can say "already running"

class Bridge(QObject):
    # the detector runs on a worker thread, a Qt signal hops its events over to the gui thread safely
    switched = Signal(object)
    near = Signal(str)  # cursor is inside the approach zone of this edge

class DetectionsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mousehole - detections')
        self.resize(620, 360)
        self.state = QLabel()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setMaximumBlockCount(500)
        clear = QPushButton('Clear')
        clear.clicked.connect(self.text.clear)
        lay = QVBoxLayout(self)
        lay.addWidget(self.state)
        lay.addWidget(self.text)
        lay.addWidget(clear)

    def add(self, line):
        self.text.appendPlainText(f'{datetime.now():%H:%M:%S.%f}'[:12] + '   ' + line)

    def set_state(self, here):
        self.state.setText('Cursor is on this PC' if here else 'Cursor is on the other PC')

class Tray:
    def __init__(self, app, quiet=False):
        self.app = app
        self.s = settings.load()
        self.rec = None
        self.last_saved = self.last_switch = ''
        self.animator = Animator(self.s)
        self.icon = QSystemTrayIcon(QIcon(portal.logo()), app)
        self.window = DetectionsWindow()
        self.settings_win = SettingsWindow(self.s, self.settings_changed, self.animator.preview)
        self.menu = QMenu()  # keep a reference, otherwise python garbage collects the menu
        self.anim_act = QAction('Animations on', self.menu)
        self.anim_act.setCheckable(True)
        self.anim_act.setChecked(self.s['animations'])
        self.anim_act.toggled.connect(self.toggle_animations)
        self.menu.addAction(self.anim_act)
        self.menu.addAction('Preview animation', lambda: self.animator.preview())
        self.menu.addAction('Settings...', self.settings_win.show_up)
        diag = self.menu.addMenu('Diagnostics')
        diag.addAction('Show detections', self.show_window)
        self.rec_act = QAction('Record signals', diag)
        self.rec_act.setCheckable(True)
        self.rec_act.toggled.connect(self.toggle_record)
        diag.addAction(self.rec_act)
        diag.addAction('Open recordings folder', lambda: os.startfile(paths.recordings_dir()))
        diag.addAction('Open log folder', lambda: os.startfile(paths.home()))
        self.menu.addSeparator()
        self.menu.addAction('Quit', self.quit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(lambda why: self.settings_win.show_up() if why == QSystemTrayIcon.DoubleClick else None)
        self.bridge = Bridge()
        self.bridge.switched.connect(self.on_switch)
        self.bridge.near.connect(self.on_near)
        self.watcher = Watcher(self.bridge.switched.emit, settings.SIDES[self.s['edge_side']], self.bridge.near.emit, self.s['approach_px'])
        try: self.watcher.start()
        except Exception:
            log.exception('switch detector failed to start')
            self.watcher = None
        self.window.set_state(not self.watcher or self.watcher.det.state == 'home')
        self.update_look()
        self.icon.show()
        if not quiet:
            # new tray icons hide under the ^ on windows 11, so say where we went
            QTimer.singleShot(800, lambda: self.icon.showMessage('Mousehole is running',
                'It lives in the tray: click ^ near the clock. Right-click the icon for options.', QSystemTrayIcon.Information, 5000))

    def show_window(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def already_running(self):
        self.icon.showMessage('Mousehole', 'Already running. Click ^ near the clock and right-click the icon.', QSystemTrayIcon.Information, 4000)

    def skip_reason(self):
        if not self.s['animations']: return 'animations are off'
        if not win32.animations_enabled(): return 'Windows animation effects are off'
        if self.watcher and win32.fullscreen_busy(self.watcher.user_hwnd): return 'a full screen app is in front'
        return ''

    def on_switch(self, sw):
        self.window.set_state(sw.what == 'arrive')
        self.last_switch = f'{datetime.now():%H:%M:%S} {sw.describe()}'
        line = sw.describe()
        if sw.how == 'edge':
            why = self.skip_reason()
            if why:
                line += f'  (no animation: {why})'
                log.info('animation skipped, %s', why)
            else:
                try: self.animator.play(sw)
                except Exception: log.exception('animation failed')
        self.window.add(line)
        self.update_look()

    def on_near(self, side):
        # heading for an edge: grow the exit portal, unless one's already going or animations shouldn't play right now
        if self.animator.approaching or not self.s['approach_px'] or self.skip_reason(): return
        try: self.animator.approach(side)
        except Exception: log.exception('approach animation failed')

    def toggle_animations(self, on):
        if self.s['animations'] != on:
            self.s['animations'] = on
            settings.save(self.s)
            self.settings_win.refresh()

    def settings_changed(self, key):
        # the settings window already saved, just pass the changes on
        self.anim_act.blockSignals(True)
        self.anim_act.setChecked(self.s['animations'])
        self.anim_act.blockSignals(False)
        if key in ('edge_side', None) and self.watcher: self.watcher.set_sides(settings.SIDES[self.s['edge_side']])
        if key in ('approach_px', None) and self.watcher: self.watcher.approach_px = self.s['approach_px']

    def recording(self):
        return bool(self.rec and self.rec.running)

    def toggle_record(self, on):
        try:
            if on:
                self.rec = Recorder()
                self.rec.start()
            elif self.rec:
                self.rec.stop()
                self.last_saved = os.path.basename(self.rec.csv_path)
                self.rec = None
        except Exception:
            log.exception('recording failed')
            self.rec = None
            self.rec_act.blockSignals(True); self.rec_act.setChecked(False); self.rec_act.blockSignals(False)
            self.last_saved = 'recording failed, see mousehole.log'
        self.update_look()

    def update_look(self):
        self.icon.setIcon(QIcon(portal.logo(64, self.recording())))
        tip = f'Mousehole {__version__}'
        if not self.watcher: tip += '\nswitch detector failed, see mousehole.log'
        elif self.last_switch: tip += f'\n{self.last_switch}'
        if self.recording(): tip += '\nrecording signals...'
        elif self.last_saved: tip += f'\nlast recording: {self.last_saved}'
        self.icon.setToolTip(tip[:127])  # windows cuts tray tooltips at 128 chars

    def quit(self):
        if self.rec: self.rec.stop()
        if self.watcher: self.watcher.stop()
        self.icon.hide()
        self.app.quit()

def preview_once():
    # "mousehole preview": play the animation once on the screen under the cursor and quit. no tray, no detector
    app = QApplication.instance() or QApplication([])
    a = Animator(settings.load())
    frames = []
    a.timer.timeout.connect(lambda: frames.append(1))
    QTimer.singleShot(100, a.preview)
    QTimer.singleShot(2400, app.quit)
    app.exec()
    log.info('preview played, %d frames', len(frames))
    return 0

def run(quiet=False):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)  # closing a window shouldn't quit, the tray stays
    app.setWindowIcon(QIcon(portal.logo(256)))
    lock = QLockFile(os.path.join(paths.home(), 'mousehole.lock'))
    if not lock.tryLock(100):
        s = QLocalSocket()
        s.connectToServer(SERVER)
        if s.waitForConnected(500):
            s.write(b'hi')
            s.flush()
            s.waitForBytesWritten(500)
        log.info('already running, quitting this copy')
        return 0
    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.error('no system tray available')
        return 1
    tray = Tray(app, quiet)
    server = QLocalServer()
    QLocalServer.removeServer(SERVER)
    server.listen(SERVER)
    def poked():
        c = server.nextPendingConnection()
        if c: c.deleteLater()
        log.info('a second copy was started, told the user this one is already running')
        tray.already_running()
    server.newConnection.connect(poked)
    log.info('tray started, version %s', __version__)
    code = app.exec()
    server.close()
    lock.unlock()
    return code

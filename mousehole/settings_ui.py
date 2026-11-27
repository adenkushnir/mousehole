# settings window: sliders and pickers for the look, switching edges, start with windows, and a preview button.
# every change applies and saves straight away, there's no ok or cancel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QVBoxLayout, QWidget)
from . import autostart, settings

SLIDERS = [  # one row per slider: key, label, slider min, max, step, setting = slider value / div, how to show it
    ('portal_size', 'Portal size', 50, 200, 10, 100, lambda v: f'{v:.0%}'),
    ('speed', 'Animation speed', 50, 200, 10, 100, lambda v: f'{v:.0%}'),
    ('glow', 'Glow strength', 0, 200, 10, 100, lambda v: f'{v:.0%}'),
    ('halo_size', 'Halo size', 16, 64, 2, 1, lambda v: f'{v:.0f} px'),
    ('halo_fade_ms', 'Halo fade time', 300, 1500, 50, 1, lambda v: f'{v:.0f} ms'),
    ('approach_px', 'Approach effect', 0, 400, 25, 1, lambda v: 'Off' if v == 0 else f'within {v:.0f} px'),
]
EDGE_NAMES = [('auto', 'Auto (from PowerToys layout)'), ('left', 'Left only'), ('right', 'Right only'), ('both', 'Left and right')]  # edge choices: setting value, what the dropdown shows

# the settings window itself
class SettingsWindow(QWidget):
    # s is the shared settings dict, on_change is told which key changed, on_preview plays the preview
    def __init__(self, s, on_change, on_preview):
        super().__init__()
        self.s, self.on_change = s, on_change
        self.setWindowTitle('Mousehole settings')
        form = QFormLayout()
        self.anim = QCheckBox('Play the portal animation when the cursor switches PCs')
        self.anim.toggled.connect(lambda on: self.set('animations', on))
        form.addRow(self.anim)
        self.sliders = {}
        for key, label, lo, hi, step, div, show in SLIDERS:  # loops over each slider row and builds the slider and its value label
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            sl.setSingleStep(step)
            sl.setPageStep(step)
            val = QLabel()
            val.setMinimumWidth(60)
            # the slider moved: snap to its step, show the value and save it
            def moved(v, key=key, step=step, lo=lo, div=div, show=show, sl=sl, val=val):
                v = lo + round((v - lo) / step) * step
                if v != sl.value(): sl.setValue(v); return
                val.setText(show(v / div))
                self.set(key, v / div if div != 1 else int(v))
            sl.valueChanged.connect(moved)
            row = QHBoxLayout()
            row.addWidget(sl, 1)
            row.addWidget(val)
            form.addRow(label, row)
            self.sliders[key] = (sl, val, div, show)
        self.colours = {}
        for key, label in (('exit_color', 'Exit portal colour'), ('entry_color', 'Entry portal colour')):  # loops over the 2 colour settings and makes a picker button for each
            b = QPushButton()
            b.setMinimumWidth(120)
            b.clicked.connect(lambda _=False, key=key, label=label: self.pick(key, label))
            form.addRow(label, b)
            self.colours[key] = b
        self.edge = QComboBox()
        for key, name in EDGE_NAMES: self.edge.addItem(name, key)  # loops over the edge choices and adds each to the dropdown
        self.edge.currentIndexChanged.connect(lambda i: self.set('edge_side', self.edge.itemData(i)))
        form.addRow('Switching edges', self.edge)
        self.boot = QCheckBox('Start with Windows')
        if autostart.available(): self.boot.toggled.connect(autostart.set_on)
        else:
            self.boot.setEnabled(False)
            self.boot.setToolTip('Only for the built Mousehole.exe, not when running from source')
        form.addRow(self.boot)
        self.pt = QCheckBox("Start PowerToys if it isn't running")
        self.pt.setToolTip('Checked once when Mousehole starts, or a minute after signing in. PowerToys opens in the tray')
        self.pt.toggled.connect(lambda on: self.set('start_powertoys', on))
        form.addRow(self.pt)
        buttons = QHBoxLayout()
        prev = QPushButton('Preview')
        prev.clicked.connect(lambda: on_preview(self.screen()))
        reset = QPushButton('Reset to defaults')
        reset.clicked.connect(self.reset)
        close = QPushButton('Close')
        close.clicked.connect(self.close)
        buttons.addWidget(prev)
        buttons.addStretch(1)
        buttons.addWidget(reset)
        buttons.addWidget(close)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addSpacing(8)
        lay.addLayout(buttons)
        self.refresh()

    # put the current settings into the widgets without firing their change handlers
    def refresh(self):
        self.loading = True
        self.anim.setChecked(self.s['animations'])
        self.pt.setChecked(self.s['start_powertoys'])
        for key, (sl, val, div, show) in self.sliders.items():  # loops over each slider and sets it from the settings
            sl.setValue(round(self.s[key] * div))
            val.setText(show(self.s[key]))
        for key, b in self.colours.items():  # loops over the 2 colour buttons and paints each in its colour
            b.setText(self.s[key].upper())
            b.setStyleSheet(f"background: {self.s[key]}; color: {'#000' if QColor(self.s[key]).lightness() > 140 else '#fff'};")
        self.edge.setCurrentIndex([k for k, _ in EDGE_NAMES].index(self.s['edge_side']))  # list of the edge setting values, to find the one that's set
        self.boot.blockSignals(True)
        self.boot.setChecked(autostart.is_on() if autostart.available() else False)
        self.boot.blockSignals(False)
        self.loading = False

    # change one setting, save it and tell the tray
    def set(self, key, value):
        if self.loading or self.s.get(key) == value: return
        self.s[key] = value
        settings.save(self.s)
        self.on_change(key)

    # open the colour picker for one of the portal colours
    def pick(self, key, label):
        c = QColorDialog.getColor(QColor(self.s[key]), self, label)
        if c.isValid():
            self.set(key, c.name().upper())
            self.refresh()

    # put every setting back to its default
    def reset(self):
        for k, v in settings.DEFAULTS.items(): self.s[k] = v  # loops over every default setting and copies it back in
        settings.save(self.s)
        self.refresh()
        self.on_change(None)

    # show the window up to date and in front
    def show_up(self):
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()

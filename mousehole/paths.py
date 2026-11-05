# Where mousehole keeps settings, logs and recordings. MOUSEHOLE_HOME overrides it so tests never touch the real folder.
import logging, os, sys
from logging.handlers import RotatingFileHandler
from . import win32

def home():
    p = os.environ.get('MOUSEHOLE_HOME')
    if not p:
        appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
        pfn = None if getattr(sys, 'frozen', False) else win32.package_family()
        if pfn:
            # store python: windows would secretly move AppData writes into the package folder anyway,
            # so just use that folder on purpose, then "open folder" shows the right place
            appdata = os.path.join(os.environ['LOCALAPPDATA'], 'Packages', pfn, 'LocalCache', 'Roaming')
        p = os.path.join(appdata, 'Mousehole')
    os.makedirs(p, exist_ok=True)
    return p

def recordings_dir():
    p = os.path.join(home(), 'recordings')
    os.makedirs(p, exist_ok=True)
    return p

def setup_logging():
    log = logging.getLogger('mousehole')
    if log.handlers: return log
    h = RotatingFileHandler(os.path.join(home(), 'mousehole.log'), maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(h)
    log.setLevel(logging.INFO)
    return log

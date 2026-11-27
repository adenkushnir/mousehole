# starts powertoys when mousehole starts, if it isn't running already. mouse without borders lives inside it
import logging, os, subprocess
from . import win32

log = logging.getLogger('mousehole')  # shared app log
EXE = 'PowerToys.exe'  # the main powertoys program, it starts mouse without borders and the rest
SIGN_IN_WAIT_MS = 60_000  # started with windows: give powertoys this long to start itself before we check
NOTES = {'started': ('Started PowerToys for you.', False),
    'missing': ("Couldn't find PowerToys, so Mouse Without Borders can't switch.", True),
    'failed': ("Couldn't start PowerToys, see mousehole.log.", True)}  # what to tell the user after a check, and if it's a problem

# where powertoys installs to: for all users, then just for this user
def exe_paths():
    programs = os.environ.get('ProgramW6432') or os.environ.get('ProgramFiles') or r'C:\Program Files'
    return [os.path.join(programs, 'PowerToys', EXE), os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PowerToys', EXE)]

# the installed powertoys exe, None if it isn't in either place
def find_exe(paths=None):
    return next((p for p in paths or exe_paths() if os.path.isfile(p)), None)  # goes through the install spots, first one that has it

# is powertoys running in this windows session
def is_running(names=None):
    return EXE.lower() in (win32.process_names() if names is None else names)

# start powertoys with no arguments, so it goes to the tray without opening its settings window
def launch(exe):
    # under store python anything we start runs inside python's package with its appdata moved, so explorer starts it instead
    if win32.package_family(): subprocess.Popen(['explorer.exe', exe])
    else: os.startfile(exe)

# start powertoys if it isn't running. says what happened: 'running', 'started', 'missing' or 'failed'
def ensure(running=is_running, find=find_exe, start=launch):
    if running(): return 'running'
    exe = find()
    if not exe:
        log.warning('powertoys is not running and could not be found')
        return 'missing'
    try: start(exe)
    except OSError:
        log.exception('could not start powertoys: %s', exe)
        return 'failed'
    log.info('powertoys was not running, started %s', exe)
    return 'started'

# "start with windows": a value under the current user's run key. only offered for the built exe
import sys, winreg

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'  # the registry key windows starts things from at sign-in
NAME = 'Mousehole'  # our value's name in it

# only the built exe can start with windows, from source there's no single exe to point at
def available():
    return bool(getattr(sys, 'frozen', False))

# what windows runs at sign-in: this exe, told to skip the hello
def command():
    return f'"{sys.executable}" --startup'

# is start with windows switched on
def is_on():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k: return bool(winreg.QueryValueEx(k, NAME)[0])
    except OSError:
        return False

# switch start with windows on or off
def set_on(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on: winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, command())
        else:
            try: winreg.DeleteValue(k, NAME)
            except FileNotFoundError: pass

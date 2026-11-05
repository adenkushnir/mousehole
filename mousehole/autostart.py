# "Start with Windows": a value under the current user's Run key. Only offered for the built exe.
import sys, winreg

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Mousehole'

def available():
    # from source there's no single exe to point windows at, so don't pretend
    return bool(getattr(sys, 'frozen', False))

def command():
    return f'"{sys.executable}" --startup'

def is_on():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k: return bool(winreg.QueryValueEx(k, NAME)[0])
    except OSError:
        return False

def set_on(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on: winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, command())
        else:
            try: winreg.DeleteValue(k, NAME)
            except FileNotFoundError: pass

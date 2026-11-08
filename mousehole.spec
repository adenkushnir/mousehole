# pyinstaller recipe for a one-folder windowed build. run: python -m PyInstaller mousehole.spec --noconfirm
a = Analysis(['launch.py'], hiddenimports=['pynput.mouse._win32', 'pynput.keyboard._win32'], excludes=['tkinter'])  # pynput picks its windows backend at runtime, so name it here
DROP = ('opengl32sw.dll', 'qt6quick', 'qt6qml', 'qt6pdf', 'qt6opengl', 'qt6virtualkeyboard', 'qpdf.dll', '/translations/')  # qt parts we never use, ~35mb
# keep a file unless its name matches something in DROP
def keep(entry):
    name = entry[0].replace('\\', '/').lower()
    return not any(d in name for d in DROP)  # checks the name against each DROP entry
a.binaries = [b for b in a.binaries if keep(b)]  # every dll, minus the dropped ones
a.datas = [d for d in a.datas if keep(d)]  # every data file, minus the dropped ones
pyz = PYZ(a.pure)  # the python code, bundled
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Mousehole', icon='assets/mousehole.ico', console=False, upx=False)  # Mousehole.exe, no console window
coll = COLLECT(exe, a.binaries, a.datas, name='Mousehole', upx=False)  # the exe and everything it needs, in dist\Mousehole

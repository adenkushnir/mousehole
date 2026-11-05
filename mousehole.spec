# PyInstaller recipe for a one-folder windowed build. Run: python -m PyInstaller mousehole.spec --noconfirm
# pynput picks its windows backend at runtime so pyinstaller can't see it, hence the hidden imports
a = Analysis(['launch.py'], hiddenimports=['pynput.mouse._win32', 'pynput.keyboard._win32'], excludes=['tkinter'])
# Qt drags in a lot we never touch (software OpenGL, QML/Quick, PDF). leaving them out saves ~35MB
DROP = ('opengl32sw.dll', 'qt6quick', 'qt6qml', 'qt6pdf', 'qt6opengl', 'qt6virtualkeyboard', 'qpdf.dll', '/translations/')
def keep(entry):
    name = entry[0].replace('\\', '/').lower()
    return not any(d in name for d in DROP)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Mousehole', icon='assets/mousehole.ico', console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='Mousehole', upx=False)

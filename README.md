# Mousehole

A small Windows companion for [PowerToys Mouse Without Borders](https://learn.microsoft.com/windows/powertoys/mouse-without-borders). When your cursor hops from one PC to another, Mousehole plays a quick portal animation:

- As you **head for** an edge that leads to another PC, an orange vortex starts forming there, level with your cursor. It grows and spins faster the closer you get, and specks get pulled off your cursor into it. It stays while you're near the edge, even if you stop, shrinks as you back away, and fades once you're out of range (or if the mouse is left completely still for 5 seconds).
- When the cursor **leaves**, that vortex carries straight on: a ghost cursor spirals into it and it snaps shut.
- On the PC it **arrives** at, a blue vortex opens where it comes in, and a soft blue glow follows the cursor for a moment.

Mouse Without Borders has no API or events, so Mousehole runs next to it on each PC and works out when a switch happens by watching the mouse and the cursor. It never modifies, patches or injects anything into PowerToys. It only reads a few layout settings from the PowerToys settings file (never the security key).

Not affiliated with Microsoft or PowerToys.

## Requirements

- Windows 10 or 11 on every PC you share a mouse between, with Mousehole installed on each.
- PowerToys with Mouse Without Borders set up and working. Machines arranged in one row (the default) work best; Mousehole reads the layout to know which screen edges lead to another PC.

## Install

1. Download `Mousehole-<version>-win64.zip` from Releases and unzip it anywhere, e.g. `C:\Programs\Mousehole`.
2. Run `Mousehole.exe`. A notification says it's running. Its icon (a dark arch with an orange rim) is in the tray. On Windows 11 new tray icons hide under the **^** next to the clock; drag it onto the taskbar to keep it visible.
3. Do the same on your other PC(s).

The exe isn't code-signed, so Windows SmartScreen may say "Windows protected your PC". Click **More info → Run anyway**. Some antivirus tools also flag apps that use a mouse hook, because keyloggers use the same Windows feature. Mousehole only hooks the mouse (never the keyboard) and makes no network connections.

To start it automatically, tick **Start with Windows** in Settings.

## Using it

Right-click the tray icon:

- **Animations on** - switch the animation on or off. Switches are still detected (and logged) while it's off.
- **Preview animation** - plays the whole thing on the current screen.
- **Settings...** (or double-click the icon)
- **Diagnostics** - a live list of detected switches, the signal recorder, and the log folder.
- **Quit**

Starting it a second time just reminds you it's already running.

### Settings

| Setting | What it does |
|---|---|
| Portal size | 50-200%. At 100% the oval is about 56 px tall (roughly three lines of text), scaled for each monitor's DPI |
| Animation speed | 50-200%. At 100% the core effect takes about 400 ms |
| Glow strength | How much the portals glow, 0-200% |
| Halo size / halo fade time | The blue glow that follows the cursor after arriving |
| Approach effect | How close to the edge (0-400 px, default 200) the orange portal starts forming. It only appears when you move towards the edge, then stays while you're within range. Heading for a scrollbar or a window's X on that edge brings it up too; turn it down or Off if that bugs you |
| Exit / entry portal colour | Orange and blue by default |
| Switching edges | Auto reads the PowerToys layout (including wrap-around). Pick left/right/both to override |
| Start with Windows | Only available in the built exe |

Settings are saved straight away to `%APPDATA%\Mousehole\settings.json`.

### When it stays quiet

- **Shortcut switches** (Ctrl+Alt+F1/F2 etc.) don't touch an edge, so there's no portal. They're still recognised, so they never trigger by mistake.
- **Full screen apps and games** in front: no animation. Mouse Without Borders blocks edge switching there anyway unless you've turned that off.
- **Windows "Animation effects"** off (Settings → Accessibility → Visual effects): no animation.
- Hugging an edge without crossing, or moving to the top centre of the screen yourself, does nothing.

## How switches are spotted

These rules come from recordings of real switches:

- **Leaving:** the cursor touches an outer edge that leads to another PC. Within about 10 ms, Mouse Without Borders parks it at the top centre of the screen, and/or its helper window takes focus.
- **Arriving:** the first mouse input that isn't just wiggling around that parked spot, at least 100 ms after leaving, or the helper window losing focus again.
- Both PCs see a switch at practically the same moment, so they don't need to talk to each other. Height along the edge maps proportionally between screens of different sizes, just like Mouse Without Borders does.

The approach effect is purely visual: it never moves your cursor. The PC you're arriving at can't know you're coming, so the blue portal only opens once you land.

The detector only wakes up on mouse input and focus changes. It polls the cursor (every 10 ms) only for a moment while the cursor is near a switching edge. When idle it uses no measurable CPU.

## Admin windows (e.g. Task Manager)

Windows doesn't let normal apps send input to admin windows. With an admin window in front on the PC being controlled remotely, Mouse Without Borders can't move or click there, so you can get stuck. Use that PC's own mouse or keyboard to get out. PowerToys' "Use Service" option for Mouse Without Borders is meant for this. Mousehole's own mouse hook also goes quiet while an admin window has focus, but switches are still spotted through the helper window's focus change.

## Troubleshooting

- **Nothing happens on a switch:** check **Diagnostics → Show detections** on both PCs while you cross. If switches show up but nothing animates, the line says why (full screen app, animations off). If nothing shows up, see `mousehole.log` (Diagnostics → Open log folder).
- **Wrong edge:** set **Switching edges** in Settings instead of Auto.
- **Recording signals for a bug report:** Diagnostics → Record signals on both PCs, do the thing that goes wrong, stop, then share the `.csv` + `.json` pairs from the recordings folder. Recordings hold mouse positions, cursor state, the file name of the program in front (never window titles) and your PC names, so check them before posting. No keystrokes are recorded.

## Uninstall

Untick Start with Windows (or Quit), delete the Mousehole folder, and delete `%APPDATA%\Mousehole`.

## For developers

You don't need any of this to use Mousehole; the download from Releases is all there is to it. This part is for changing the code, or for building the exe yourself if you'd rather not run one you downloaded.

### Run from source

Python 3.11+ on Windows.

```
pip install -r requirements-dev.txt
python -m mousehole                                 # tray app
python -m mousehole preview                         # play the animation once and quit
python -m mousehole record --seconds 60             # record signals without the tray
python -m mousehole replay path\to\recording.csv    # run a recording through the detector
python -m pytest
```

Set `MOUSEHOLE_HOME` to keep settings, the log and recordings somewhere else (the tests do).

### Build

```
python tools\make_icon.py                           # only if you change the logo
python -m PyInstaller mousehole.spec --noconfirm
```

The one-folder build ends up in `dist\Mousehole\`. Zip that folder to share it.

### Layout

| File | What's in it |
|---|---|
| `mousehole/detector.py` | the switch rules, pure Python |
| `mousehole/watcher.py` | feeds the detector from the live mouse hook, focus changes and cursor polling |
| `mousehole/edges.py` | edge maths: which edges switch, mapping between screens, DPI |
| `mousehole/overlay.py`, `portal.py`, `anim.py` | the click-through overlay windows, drawing and timing |
| `mousehole/tray.py`, `settings_ui.py`, `settings.py` | tray menu, settings window, settings file |
| `mousehole/recorder.py`, `replay.py` | diagnostic signal recorder and replay |
| `mousehole/win32.py`, `hook.py`, `fgwatch.py` | the Windows calls |
| `reference/portal_reference.html` | the animation the portal look and timing are based on |

## License

MIT, see [LICENSE](LICENSE).

# Starts mousehole: the tray app by default, "record --seconds N" for a quick recording, "replay" to test the detector.
import argparse, sys, time
from . import paths, win32

def main(argv=None):
    win32.set_dpi_aware()  # before anything Qt, so all coordinates are real pixels
    ap = argparse.ArgumentParser(prog='mousehole', description='portal animation when the mouse switches PCs with Mouse Without Borders')
    ap.add_argument('--startup', action='store_true', help=argparse.SUPPRESS)  # started by Windows at sign-in, skip the hello
    sub = ap.add_subparsers(dest='cmd')
    r = sub.add_parser('record', help='record mouse signals to csv for a while, no tray icon')
    r.add_argument('--seconds', type=float, default=60)
    rp = sub.add_parser('replay', help='run saved recordings through the switch detector and print what it finds')
    rp.add_argument('csv', nargs='+')
    sub.add_parser('preview', help='play the portal animation once on this screen and quit')
    a = ap.parse_args(argv)
    if a.cmd == 'replay':
        from .replay import main as replay_main
        return replay_main(a.csv)
    paths.setup_logging()
    if a.cmd == 'record':
        from .recorder import Recorder
        rec = Recorder()
        rec.start()
        print(f'recording {a.seconds:g}s to {rec.csv_path} (ctrl+c stops early)')
        try: time.sleep(a.seconds)
        except KeyboardInterrupt: pass
        rec.stop()
        print('saved', rec.csv_path, rec.counts)
        return 0
    if a.cmd == 'preview':
        from .tray import preview_once
        return preview_once()
    from .tray import run
    return run(quiet=a.startup)

if __name__ == '__main__':
    sys.exit(main())

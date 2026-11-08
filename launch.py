# entry point for the pyinstaller build. from source just run: python -m mousehole
import sys
from mousehole.__main__ import main

sys.exit(main())

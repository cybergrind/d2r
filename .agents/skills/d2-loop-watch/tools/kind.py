"""Switch the KP_6 loop's kind without a restart: `python3 kind.py <key>` (`--socket PATH` for another service).

The keys are macros/loop.py `loop_kinds()`'s: lk, andariel, tz, tzclear, and act1 ... act5 (each once its script is
ready, macros/acts/). With the loop off it switches at once; with it on, from the next game (macros/runner.py
`choose_kind`); an open KP_6 kind picker (macros/kindpick.py, the player's three presses) closes. The card says
which. A restart keeps the chosen kind.
"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'inventory_tracking'))
import request  # the hotkey sender: the standard library only


if __name__ == '__main__':
    sys.exit(request.main(['loop-kind', *sys.argv[1:]]))

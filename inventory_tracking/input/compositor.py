"""The service's hotkeys in niri's config, there only while `make serve` runs.

The binds used to be lines edited by hand into `~/.config/niri/config.kdl`. On 2026-10-10 00:34
that file was replaced by a copy without them and every hotkey went dead at once (Alt+D first
noticed). Now the service owns them: it writes `d2r-hotkeys.kdl` next to the config and appends
one `include` line for it when the line is missing, so a restored config heals on the next start.
On exit the file is emptied; niri watches included files and reloads on both writes.

The include is the config's last line: a later bind overrides an earlier one for the same key
(niri wiki, Configuration: Include), so Mod+C is the level map while the service runs and the
user's own `center-column` otherwise. The keypad keys are named by their raw keysyms, the level
without Num Lock, because that is what niri matches (macros/plan.md).

This file is the one place that names keys: the rest of the code speaks of the actions (the macro
request, the teleport, seek and pickup steps, the attack mode toggle), since the keys will change.
"""

import logging
import os
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from inventory_tracking import request


LOG = logging.getLogger(__name__)

HOTKEYS_FILE = 'd2r-hotkeys.kdl'
INCLUDE = f'include optional=true "{HOTKEYS_FILE}"'
# niri key -> request.py kind.
BINDS = {
    'Alt+D': 'appraise',
    'Alt+Shift+D': 'disagree',
    'Mod+S': 'collect',
    'Mod+D': 'shop',
    'Mod+C': 'level',
    'Mod+X': 'macro',
    'KP_Left': 'teleport',  # keypad 4
    'KP_Down': 'hunt-elites',  # keypad 2
    'KP_Next': 'hunt-any',  # keypad 3
    'KP_End': 'pickup',  # keypad 1
}
# X key names a step binding may leave down when its request arrives: the keypad keys above under either
# Num Lock state (the compositor swallows them, but a release can come late) and the Mod key.
STEP_KEYS = ('KP_4', 'KP_Left', 'KP_2', 'KP_Down', 'KP_3', 'KP_Next', 'KP_1', 'KP_End', 'Super_L', 'Super_R')
HEADER = '// Written by `make serve` (inventory_tracking/input/compositor.py); edits are overwritten.\n'
IDLE = HEADER + '// The service is not running: no hotkeys.\n'


def default_config() -> Path:
    home = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(home) / 'niri' / 'config.kdl'


def binds_text(python: str = sys.executable, sender: str = request.__file__) -> str:
    """The binds section: each key spawns the fast sender (request.py) with its kind."""
    lines = [
        f'    {key} repeat=false {{ spawn "{python}" "-S" "{sender}" "{kind}"; }}\n' for key, kind in BINDS.items()
    ]
    return f'{HEADER}binds {{\n{"".join(lines)}}}\n'


def ensure_include(config: Path) -> bool:
    """Append the include line unless the config already names the hotkeys file; True when added."""
    text = config.read_text()
    if any(HOTKEYS_FILE in line and not line.lstrip().startswith('//') for line in text.splitlines()):
        return False
    with config.open('a') as stream:
        stream.write(f'{"" if text.endswith("\n") else "\n"}\n// D2R hotkeys, last so that they win. {HEADER[3:]}')
        stream.write(f'{INCLUDE}\n')
    return True


def invalid(config: Path) -> str | None:
    """niri's own complaint about the config, or None when it parses (or niri cannot be asked)."""
    try:
        done = subprocess.run(
            ['niri', 'validate', '-c', str(config)], capture_output=True, text=True, timeout=5, check=False
        )
    except OSError, subprocess.SubprocessError:
        return None
    return None if done.returncode == 0 else (done.stderr or done.stdout).strip()


@contextmanager
def hotkeys(config: Path | None = None) -> Generator[bool]:
    """Bind the service's keys in niri for the length of the block; False when nothing was bound."""
    config = config or default_config()
    if not config.is_file():
        LOG.info('No niri config at %s: hotkeys are not installed', config)
        yield False
        return
    target = config.with_name(HOTKEYS_FILE)
    try:
        # The file first: the include line must never name binds that are not there yet.
        target.write_text(binds_text())
        added = ensure_include(config)
    except OSError as exc:
        LOG.warning('Could not install the niri hotkeys: %s', exc)
        yield False
        return
    problem = invalid(config)
    if problem:
        # A config niri rejects keeps the old binds loaded; do not leave our half in it.
        target.write_text(IDLE)
        LOG.warning('niri rejects the config with the hotkeys, they are removed again: %s', problem)
        yield False
        return
    LOG.info('niri hotkeys installed in %s%s', target, ' (include line added to the config)' if added else '')
    try:
        yield True
    finally:
        try:
            target.write_text(IDLE)
        except OSError as exc:
            LOG.warning('Could not remove the niri hotkeys: %s', exc)

"""Compositor focus and X11 window ownership checks for the game process."""

import json
import subprocess

from .config import INPUT, InputConfig
from .linux_process import identity, is_game
from .models import SessionIdentity


class FocusProbe:
    """Require both Niri focus on the game app id and the exact X11 game process behind it."""

    def __init__(self, config: InputConfig = INPUT) -> None:
        self.config = config

    def _query(self, *command: str) -> str:
        return subprocess.check_output(command, timeout=self.config.focus_timeout, text=True)

    def __call__(self, session: SessionIdentity) -> bool:
        try:
            window = json.loads(self._query('niri', 'msg', '--json', 'focused-window'))
            if not window or window.get('app_id') != self.config.game_app_id:
                return False
            pid = int(self._query('xdotool', 'getwindowfocus', 'getwindowpid').strip())
            return (
                pid == session.process_id
                and is_game(pid)
                and identity(pid) == {'pid': pid, 'start_ticks': session.process_start}
            )
        except OSError, ValueError, subprocess.SubprocessError:
            return False

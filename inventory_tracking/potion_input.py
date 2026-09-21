"""Focused XWayland key delivery; cooldown policy is owned by PotionsController."""

import ctypes
import json
import subprocess
import time

from .belt import usable_cells
from .config import INPUT
from .linux_process import identity, is_game
from .models import Actor


def game_is_focused(state, config=INPUT):
    """Require both compositor focus and the exact X11 game process."""
    try:
        window = json.loads(
            subprocess.check_output(
                ['niri', 'msg', '--json', 'focused-window'], timeout=config.focus_timeout, text=True
            )
        )
        if not window or window.get('app_id') != config.game_app_id:
            return False
        pid = int(
            subprocess.check_output(
                ['xdotool', 'getwindowfocus', 'getwindowpid'], timeout=config.focus_timeout, text=True
            ).strip()
        )
        return (
            pid == state.process_id
            and is_game(pid)
            and identity(pid) == {'pid': pid, 'start_ticks': state.process_start}
        )
    except OSError, ValueError, subprocess.SubprocessError:
        return False


class PotionInput:
    def __init__(self, config=INPUT, *, clock=time.monotonic):
        self.config = config
        self.clock = clock

    def __call__(self, state, request, *, max_age, before_send):
        cells = usable_cells(state, request.potion)
        if (
            request.actor not in Actor
            or request.item.column not in (1, 2, 3, 4)
            or request.item not in cells
            or not state.gameplay_ready
            or not 0 <= self.clock() - state.sampled_at <= max_age
        ):
            return False
        if not game_is_focused(state, self.config):
            return False
        x11 = ctypes.CDLL('libX11.so.6')
        xtst = ctypes.CDLL('libXtst.so.6')
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        x11.XStringToKeysym.restype = ctypes.c_ulong
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        x11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        display = x11.XOpenDisplay(None)
        if not display:
            return False
        try:
            column = request.item.column
            names = [b'Shift_L', str(column).encode()] if request.actor == Actor.MERC else [str(column).encode()]
            keys = [x11.XKeysymToKeycode(display, x11.XStringToKeysym(name)) for name in names]
            if not all(keys):
                return False
            keymap = ctypes.create_string_buffer(32)
            x11.XQueryKeymap(display, keymap)
            # Never disturb keys physically held by the player.
            if any(keymap.raw) or not game_is_focused(state, self.config):
                return False
            if not 0 <= self.clock() - state.sampled_at <= max_age:
                return False
            before_send()
            try:
                for key in keys:
                    if not xtst.XTestFakeKeyEvent(display, key, 1, 0):
                        raise RuntimeError('Potion key press failed')
                x11.XSync(display, 0)
                time.sleep(self.config.key_hold_seconds)
            finally:
                release_failed = False
                for key in reversed(keys):
                    try:
                        if not xtst.XTestFakeKeyEvent(display, key, 0, 0):
                            release_failed = True
                    except Exception:
                        release_failed = True
                x11.XSync(display, 0)
                if release_failed:
                    raise RuntimeError('Potion key release failed')
            return True
        finally:
            x11.XCloseDisplay(display)

"""Focused XWayland key delivery with shared cooldown and guaranteed key release."""

import ctypes
import fcntl
import json
import subprocess
import time
from pathlib import Path

from .healing_config import (
    PLAYER_REJUVENATION_COOLDOWN_SECONDS,
    POTION_COOLDOWN_SECONDS,
    SAMPLE_MAX_AGE_SECONDS,
)
from .linux_process import identity, is_game


def game_is_focused(state):
    """Require both compositor focus and the exact X11 game process."""
    try:
        window = json.loads(
            subprocess.check_output(['niri', 'msg', '--json', 'focused-window'], timeout=0.3, text=True)
        )
        if not window or window.get('app_id') != 'steam_app_2536520':
            return False
        pid = int(
            subprocess.check_output(['xdotool', 'getwindowfocus', 'getwindowpid'], timeout=0.3, text=True).strip()
        )
        return (
            pid == state.process_id
            and is_game(pid)
            and identity(pid) == {'pid': pid, 'start_ticks': state.process_start}
        )
    except OSError, ValueError, subprocess.SubprocessError:
        return False


class MercInput:
    def __init__(self, directory):
        self.lock_path = directory / 'merc-input.lock'
        self.boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def __call__(self, state, column, *, target='merc'):
        if target not in ('merc', 'player') or column not in (1, 2, 3, 4) or not state.gameplay_ready:
            return False
        with self.lock_path.open('a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            lock.seek(0)
            contents = lock.read()
            previous = json.loads(contents) if contents else {}
            now = time.monotonic()
            cooldown = (
                PLAYER_REJUVENATION_COOLDOWN_SECONDS
                if target == 'player' and any(c == column for c, _ in state.rejuvenation_cells)
                else POTION_COOLDOWN_SECONDS
            )
            if previous.get('boot') == self.boot_id and now - previous.get('sent_at', now) < cooldown:
                return False
            if not game_is_focused(state) or not 0 <= time.monotonic() - state.sampled_at <= SAMPLE_MAX_AGE_SECONDS:
                return False
            return (
                self.press(state, column, lock) if target == 'merc' else self.press(state, column, lock, target=target)
            )

    def press(self, state, column, lock, *, target='merc'):
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
            names = [b'Shift_L', str(column).encode()] if target == 'merc' else [str(column).encode()]
            keys = [x11.XKeysymToKeycode(display, x11.XStringToKeysym(name)) for name in names]
            if not all(keys):
                return False
            keymap = ctypes.create_string_buffer(32)
            x11.XQueryKeymap(display, keymap)
            # Never disturb keys physically held by the player.
            if any(keymap.raw) or not game_is_focused(state):
                return False
            if not 0 <= time.monotonic() - state.sampled_at <= SAMPLE_MAX_AGE_SECONDS:
                return False
            lock.seek(0)
            lock.truncate()
            lock.write(json.dumps({'boot': self.boot_id, 'sent_at': time.monotonic()}))
            lock.flush()
            try:
                for key in keys:
                    if not xtst.XTestFakeKeyEvent(display, key, 1, 0):
                        raise RuntimeError('Potion key press failed')
                x11.XSync(display, 0)
                time.sleep(0.025)
            finally:
                for key in reversed(keys):
                    xtst.XTestFakeKeyEvent(display, key, 0, 0)
                x11.XSync(display, 0)
            return True
        finally:
            x11.XCloseDisplay(display)

"""Send one hotkey request to the running service, fast: the standard library only, no package imports.

The compositor spawns a process per key press. `appraisal_service request` imports the whole service
before it sends (0.35 s measured on 2026-10-09), too slow for a step asked for again and again (macros/teleport.py,
macros/hunt.py). This file imports only what a press needs: with
argparse, subprocess and pathlib its start took 57 ms of every press with the game running (36
teleport presses, 21:26 on 2026-10-11; the interpreter alone starts in 6 ms). It says in its datagram
how long its own start took (macros/latency.py):

    .venv/bin/python -S /mnt/extra/1000/games/d2r/inventory_tracking/request.py teleport

The prefixes must stay those of the workers (tests/inventory_tracking/test_request.py checks them
against the modules). Without a running service a desktop notification says so, as the CLI does.
"""

import math
import os
import socket
import sys
import time


PREFIXES = {
    'appraise': '',  # Alt+D
    'collect': 'collect ',  # Win+S
    'equipped': 'equipped ',
    'disagree': 'disagree ',  # Alt+Shift+D
    'shop': 'shop ',  # Win+D
    'level': 'level ',  # Win+C
    'macro': 'macro ',  # the macro request
    'teleport': 'teleport ',  # the teleport step
    'hunt-elites': 'hunt elites ',  # the seek step: one step toward the nearest elite
    'hunt-any': 'hunt any ',  # the attack mode toggle: attack mode on/off
    'pickup': 'pickup ',  # the pickup step: pick up a valuable or a potion, else a seek step
    'pad': 'pad ',  # the gamepad experiment: one tap of a virtual pad's button (input/gamepad.py)
    'loop': 'loop ',  # the Lower Kurast loop on/off (macros/loop.py)
    'tz-loop': 'tz-loop ',  # separate TZ coordinator; unbound and disabled until explicitly configured
    'tz-pickup': 'tz-pickup ',  # one explicitly named ground valuable; no attack or seek fallback
    'safe-exit': 'safe-exit ',  # one explicit named-game Rogue Encampment Save and Exit
}
TIMED = frozenset(('macro', 'teleport', 'hunt-elites', 'hunt-any', 'pickup', 'loop', 'tz-loop'))
DEFAULT_SOCKET = os.path.join(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'), 'd2r-appraisal.sock')
USAGE = f'usage: request.py [--socket PATH] {{{",".join(sorted(PREFIXES))}}}\nSend one hotkey request to `make serve`.'


def startup() -> tuple[float, float] | None:
    """Milliseconds since this process started (to a clock tick, 10 ms) and the CPU it has used."""
    try:
        with open('/proc/self/stat') as stat:
            ticks = int(stat.read().rsplit(')', 1)[1].split()[19])  # starttime, since boot
        age = time.clock_gettime(time.CLOCK_BOOTTIME) - ticks / os.sysconf('SC_CLK_TCK')
    except OSError, ValueError, IndexError:
        return None
    return 1000 * age, 1000 * time.process_time()


def send(kind: str, endpoint=DEFAULT_SOCKET, *, clock=time.monotonic, began=None, payload: str = '') -> bool:
    """Send `kind`'s datagram, stamped with the monotonic clock the service compares against; a
    macro request with `began` (`startup`) says after the stamp how long the start took."""
    took = f' {began[0]:.1f} {began[1]:.1f}' if began is not None and kind in TIMED else ''
    message = f'{PREFIXES[kind]}{clock()}{took}{payload}'
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.sendto(message.encode('ascii'), str(endpoint))
    except OSError:
        return False
    return True


def main(argv=None) -> int:
    began = startup()
    words = list(sys.argv[1:] if argv is None else argv)
    endpoint = DEFAULT_SOCKET
    if '--help' in words or '-h' in words:
        print(USAGE)
        return 0
    if '--socket' in words[:-1]:
        at = words.index('--socket')
        endpoint = words[at + 1]
        del words[at : at + 2]
    if len(words) in (6, 8) and words[0] == 'tz-pickup':
        _, game, area, label, x, y = words[:6]
        size = words[6:]
        try:
            valid = (
                bool(game)
                and all(char.isascii() and (char.isalnum() or char in '_-') for char in game)
                and bool(label)
                and label[0].isascii()
                and label[0].isalpha()
                and all(char.isascii() and (char.isalnum() or char == '_') for char in label)
                and int(area) > 0
                and all(math.isfinite(float(value)) for value in (x, y))
                and (not size or (1 <= int(size[0]) <= 3 and 1 <= int(size[1]) <= 4))
            )
        except ValueError:
            valid = False
        payload = f' {game} {area} {label} {x} {y}' + ''.join(f' {value}' for value in size)
        if valid and send('tz-pickup', endpoint, payload=payload):
            return 0
        return 2
    if len(words) == 2 and words[0] == 'safe-exit':
        game = words[1]
        valid = bool(game) and all(char.isascii() and (char.isalnum() or char in '_-') for char in game)
        return 0 if valid and send('safe-exit', endpoint, payload=f' {game}') else 2
    if len(words) != 1 or words[0] not in PREFIXES or words[0] in ('tz-pickup', 'safe-exit'):
        print(USAGE, file=sys.stderr)
        return 2
    if send(words[0], endpoint, began=began):
        return 0
    import contextlib
    import subprocess

    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            ['notify-send', '--app-name=D2R appraisal', 'D2R appraisal worker is not running', 'Start: make serve'],
            timeout=2,
            check=False,
        )
    return 1


if __name__ == '__main__':
    sys.exit(main())

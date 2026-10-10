"""Send one hotkey request to the running service, fast: the standard library only, no package imports.

The compositor spawns a process per key press. `appraisal_service request` imports the whole service
before it sends (0.35 s measured on 2026-10-09), too slow for a key pressed again and again (KP_4,
macros/teleport.py; KP_2/KP_3, macros/hunt.py). This file starts in about 10 ms:

    .venv/bin/python -S /mnt/extra/1000/games/d2r/inventory_tracking/request.py teleport

The prefixes must stay those of the workers (tests/inventory_tracking/test_request.py checks them
against the modules). Without a running service a desktop notification says so, as the CLI does.
"""

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


PREFIXES = {
    'appraise': '',  # Alt+D
    'collect': 'collect ',  # Win+S
    'equipped': 'equipped ',
    'disagree': 'disagree ',  # Alt+Shift+D
    'shop': 'shop ',  # Win+D
    'level': 'level ',  # Win+C
    'macro': 'macro ',  # Win+X
    'teleport': 'teleport ',  # KP_4 (Win+T before)
    'hunt-elites': 'hunt elites ',  # KP_2: one step toward the nearest elite
    'hunt-any': 'hunt any ',  # KP_3: attack mode on/off
}
DEFAULT_SOCKET = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'd2r-appraisal.sock'


def send(kind: str, endpoint: Path = DEFAULT_SOCKET, *, clock=time.monotonic) -> bool:
    """Send `kind`'s datagram, stamped with the monotonic clock the service compares against."""
    message = f'{PREFIXES[kind]}{clock()}'
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            client.sendto(message.encode('ascii'), str(endpoint))
    except OSError:
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Send one hotkey request to `make serve`.')
    parser.add_argument('kind', choices=sorted(PREFIXES))
    parser.add_argument('--socket', type=Path, default=DEFAULT_SOCKET)
    args = parser.parse_args(argv)
    if send(args.kind, args.socket):
        return 0
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            ['notify-send', '--app-name=D2R appraisal', 'D2R appraisal worker is not running', 'Start: make serve'],
            timeout=2,
            check=False,
        )
    return 1


if __name__ == '__main__':
    sys.exit(main())

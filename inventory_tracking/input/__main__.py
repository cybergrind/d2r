"""Host diagnostics: enter guarded attempts for every binding, never send keys."""

import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ..config import INPUT, MERC_HEALING, PLAYER_HEALING
from ..linux_process import find_game_processes, identity, is_game
from ..models import Actor, BeltCell, PotionRequest, PotionType, SessionIdentity
from ..reports import publish
from .facade import InputError, PotionInput, Target
from .focus import FocusTracker
from .keyboard import X11Keyboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True, help='Check input guards without pressing keys')
    parser.add_argument('--pid', type=int, help='Pin one D2R process')
    parser.add_argument('--output', type=Path, help='Atomically save a completed JSON report for host review')
    parser.add_argument('--duration', type=float, default=0, help='Repeat checks for this many seconds (0: once)')
    parser.add_argument('--interval', type=float, default=0.1, help='Seconds between check passes')
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or not 0 <= args.duration <= 300:
        parser.error('--duration must be between 0 and 300 seconds')
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error('--interval must be positive')
    report: dict[str, object] = {'state': 'running', 'started_at': datetime.now(UTC).isoformat(), 'checks': []}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        publish(args.output, report)
    try:
        pids = [args.pid] if args.pid is not None else find_game_processes()
        if len(pids) != 1:
            raise ValueError(f'Expected one game process; found {pids}. Use --pid to select one.')
        pid = pids[0]
        if not is_game(pid):
            raise ValueError(f'PID {pid} is not a game process')
        process = identity(pid)
        # Focus needs only the process identity; no player/health memory read is needed.
        session = SessionIdentity(pid, process['start_ticks'], 0)
        probe = FocusTracker(INPUT)
        delivery = PotionInput(INPUT, focus=probe, keyboard=X11Keyboard(), clock=time.monotonic)
        checks = []
        try:
            probe.wait_ready(timeout=1)
            deadline = time.monotonic() + args.duration
            while True:
                for actor in Actor:
                    config = PLAYER_HEALING if actor == Actor.PLAYER else MERC_HEALING
                    for column in INPUT.column_keys:
                        target = Target(session, time.monotonic(), config.sample_max_age)
                        request = PotionRequest(actor, PotionType.HEALING, BeltCell(column, 0))
                        row: dict[str, object] = {
                            'actor': actor.value,
                            'column': column,
                            'checked_at': time.monotonic(),
                            'app_id': None,
                            'owner_pid': None,
                            'identity_match': None,
                            'keycodes': None,
                            'held': None,
                            'result': 'input_error',
                        }
                        started = time.monotonic()
                        try:
                            with delivery.attempt(target, request) as attempt:
                                row.update(
                                    display_open_ms=attempt.display_open_ms,
                                    keycodes=attempt.keycodes,
                                    held=attempt.held,
                                    owner_pid=attempt.owner_pid,
                                    identity_match=attempt.identity_match,
                                )
                                # Avoid stale diagnostics when display/keycode guards stopped before focus.
                                if attempt.refusal not in ('no_display', 'unknown_key'):
                                    row.update(asdict(probe.status))
                                row['result'] = attempt.refusal.value if attempt.refusal else 'ready'
                        except InputError as exc:
                            row['result'] = 'input_error'
                            row['error'] = str(exc)
                        row['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)
                        checks.append(row)
                        print(json.dumps(row), flush=True)
                if time.monotonic() >= deadline:
                    break
                time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
        finally:
            probe.close()
        code = 0 if all(row['result'] == 'ready' for row in checks) else 2
        report.update(state='complete', checks=checks, exit_code=code)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        code = 1
        report.update(state='failed', error=str(exc), exit_code=code)
    report['finished_at'] = datetime.now(UTC).isoformat()
    if args.output:
        publish(args.output, report)
    return code


if __name__ == '__main__':
    raise SystemExit(main())

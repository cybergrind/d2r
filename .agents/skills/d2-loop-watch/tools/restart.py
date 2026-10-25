"""Restart `make serve` at a safe moment and say whether the new service took up the asked mode.

A restart is the service's own (appraisal/service.py `restart_asked`: the file runs/alt-d/restart.request, JSON: the
state the next service takes up, `{"loop": true}` / `{"loop": false}`; empty keeps the state). The service takes it at
once, wherever the character is, so this waits for a safe moment first (`--when`):

- the loop is off (the player's KP_6, a stop): at once, whatever `--when`;
- `lobby` (the default), the loop on: until its leg `next game` starts (the character is out of a game, at the lobby).
  Never in a game, where a restart could leave loot on the ground or a panel open;
- `town` / `safe`, the loop on: in the middle of the game (macros/midgame.py; the player, 2026-10-21 ~14:50: "pick new
  code in the middle of the act run, without save/exit, just continue"). The request goes at once with `"when"`; the
  service holds it and the loop stands at its next safe point between two legs (`town`: in a town; `safe`: a town, or
  a field level with no hostile within 30, no valuable on the ground, no package under way; the lobby too), then the
  service restarts and the new one goes on in the same game, the agenda where it was (no second shard). Past `--wait`
  the hold is cancelled (`"when": "cancel"`) and nothing restarts. `--kind` here is the kind from the next game.
- `trip`, the loop on (the player, 2026-10-24 ~13:35: "go to town and restart -> return back"): in a town at once; in
  a field level at its next safe moment (`safe`'s, and no boss alive on the level, no Herald known there) the loop
  casts Town Portal, stands in town for the restart, and the new service goes back through the portal it left (gone:
  the loop's own way back from town). Once the trip has begun the wait is at least TRIP_SECONDS more.

Then it waits for the new service's `resumed after a restart` line and prints it.

    python3 .agents/skills/d2-loop-watch/tools/restart.py [--loop on|off|keep] [--when lobby|town|safe|trip]
        [--wait 300]

Exit 0: restarted and resumed; 1: no safe moment within --wait (nothing restarted); 2: asked, no resume seen.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import logwords
from logwords import (
    LEG,
    LOOP_OFF,
    LOOP_ON,
    LOOP_RESUMED,
    LOOP_STOPPED,
    NOT_SAFE,
    RESTART_DROPPED,
    RESTART_HELD,
    RESUMED_ANY,
    RESUMED_OFF,
    RESUMED_ON,
    SAFE_POINT,
    TRIP_BEGUN,
)


RUNS = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'alt-d'
REQUEST_FILE = 'restart.request'
ON = (LOOP_ON, LOOP_RESUMED, RESUMED_ON)
OFF = (LOOP_OFF, LOOP_STOPPED, RESUMED_OFF)
LOBBY, TOWN, SAFE, TRIP = 'lobby', 'town', 'safe', 'trip'  # macros/midgame.py's words
CANCEL = 'cancel'
# `trip`: the wait once the loop's Town Portal for the restart is begun (its cast, the stand in town, ~10 s)
TRIP_SECONDS = 60.0
RESUME_SECONDS = 60.0  # for the new service's resume line
TAKEN_SECONDS = 5.0  # for the service to take a request (its loop ticks every ~0.1 s)


def newest(runs: Path) -> Path:
    log = logwords.newest(runs)
    if log is None:
        raise SystemExit(f'no serve session under {runs}')
    return log


def loop_on(lines: list[str]) -> bool:
    on = False
    for line in lines:
        if any(word in line for word in ON) or LEG.search(line):
            on = True
        if any(word in line for word in OFF):
            on = False
    return on


# The shard act kinds (macros/loop.py ACT_KINDS), one per act
ACT_KINDS = tuple(f'act{act}' for act in range(1, 6))


def say(text: str) -> None:
    print(text, flush=True)


def resumed(runs: Path, log: Path) -> str | None:
    """The new service's resume line (a session newer than `log`), None with none yet."""
    fresh = logwords.newest(runs)
    if fresh is None or fresh == log or not fresh.exists():
        return None
    for text in fresh.read_text(errors='replace').splitlines():
        if RESUMED_ANY in text:
            return f'{fresh.parent.name}: {text[11:200]}'
    return None


def wait_resumed(runs: Path, log: Path, request: Path, seconds: float = RESUME_SECONDS) -> int:
    """Exit 0 once the new service's resume line is seen within `seconds`, else 2."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(1)
        if (line := resumed(runs, log)) is not None:
            say(line)
            return 0
    say(f'no resume line within {seconds:.0f} s: check `make serve` (the restart file is '
        f'{"still there" if request.exists() else "taken"})')  # fmt: skip
    return 2


def lobby_wait(handle, args, log: Path) -> bool:
    """The loop on: until its next game's leg (True), the player's pause (True, `args.loop` off), or --wait (False)."""
    say(f'the loop is on ({log.parent.name}): waiting for its next game')
    deadline = time.time() + args.wait
    while True:
        text = handle.readline()
        if not text:
            if time.time() > deadline:
                say('no safe moment: nothing written')
                return False
            time.sleep(0.2)
            continue
        if any(word in text for word in OFF):
            # The player's pause wins (SKILL.md hard rule 4): the restart keeps the loop off whatever was asked
            # (10:39:02 on 2026-10-18: KP_6 pressed while a restart waited, and it turned the loop on)
            say(f'the loop went off: {text[11:160].rstrip()}: it stays off')
            args.loop = 'off'
            return True
        if (m := LEG.search(text)) and m.group(2).strip() == 'next game':
            say(f'at the lobby: {text[11:120].rstrip()}')
            return True


def safe_wait(handle, args, runs: Path, log: Path, request: Path, target: dict) -> int:
    """`--when town|safe` with the loop on: the request with `when` written now, the service's lines followed until
    the new service's resume line (0); past --wait the hold cancelled (1), or a restart asked and no resume seen (2)."""
    request.write_text(json.dumps({**target, 'when': args.when}))
    say(f'restart asked at the next {args.when} point: {target or "the state as it is"}')
    deadline = time.time() + args.wait
    standing = False
    while time.time() < deadline:
        text = handle.readline()
        if text:
            if RESTART_HELD in text:
                say(f'held by the service: {text[11:160].rstrip()}')
            elif (m := NOT_SAFE.search(text)) is not None:
                say(f'not yet: {m.group(1)}')
            elif (m := TRIP_BEGUN.search(text)) is not None:
                deadline = max(deadline, time.time() + TRIP_SECONDS)  # never cancelled with the portal cast
                say(f'portal trip for the restart from {m.group(1)}: {text[11:200].rstrip()}')
            elif SAFE_POINT.search(text) is not None:
                standing = True
                say(f'at a safe point: {text[11:200].rstrip()}')
            elif any(word in text for word in OFF):
                say(f'the loop went off: {text[11:160].rstrip()}: the service restarts with it off')
                standing = True
            continue
        if (standing or not request.exists()) and (line := resumed(runs, log)) is not None:
            say(line)
            return 0
        time.sleep(0.2)
    request.write_text(json.dumps({'when': CANCEL}))
    say(f'no safe point within {args.wait:.0f} s: the hold is cancelled')
    cancelled = time.time() + TAKEN_SECONDS
    while time.time() < cancelled:
        text = handle.readline()
        if text and RESTART_DROPPED in text:
            say('nothing restarted')
            return 1
        if (line := resumed(runs, log)) is not None:
            say(f'restarted all the same (a safe point came as it was cancelled): {line}')  # fmt: skip
            return 0
        if not text:
            time.sleep(0.2)
    return wait_resumed(runs, log, request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--loop', choices=('on', 'off', 'keep'), default='keep')
    parser.add_argument(
        '--kind',
        choices=('lk', 'andariel', 'baal', 'tz', 'tzclear', *ACT_KINDS),
        help="the loop's run (macros/loop.py `loop_kinds`: tz and tzclear only once macros/tzloop.py ENABLED; "
        "act1 ... act5 once macros/actloop.py ENABLED and the act's script is ready, macros/acts/); with --when "
        'town|safe from the next game',
    )
    parser.add_argument(
        '--when',
        choices=(LOBBY, TOWN, SAFE, TRIP),
        default=LOBBY,
        help='the safe moment with the loop on: the next lobby (default); the next safe point in a town, or in a town '
        'or a field level, or a town reached by Town Portal from a field level and back (the game goes on, '
        'macros/midgame.py)',
    )
    parser.add_argument('--wait', type=float, default=300.0, help='seconds to wait for a safe moment')
    parser.add_argument('--runs', type=Path, default=RUNS, help=argparse.SUPPRESS)  # tests
    args = parser.parse_args(argv)
    runs = args.runs
    request = runs / REQUEST_FILE
    log = newest(runs)
    with open(log, errors='replace') as handle:
        on = loop_on(handle.readlines())
        target: dict = {} if args.loop == 'keep' else {'loop': args.loop == 'on'}
        mid_game = on and args.when != LOBBY
        if args.kind is not None:
            # Mid-game the game goes on in its kind (a shard's act is not played as another), the asked one next
            target['loop_pending' if mid_game else 'loop_kind'] = args.kind
        if mid_game:
            say(f'the loop is on ({log.parent.name}): a restart at its next {args.when} point')
            return safe_wait(handle, args, runs, log, request, target)
        if on and not lobby_wait(handle, args, log):
            return 1
    if args.loop == 'off':
        target['loop'] = False
    request.write_text(json.dumps(target) if target else '')
    say(f'restart asked: {target or "the state as it is"}')
    return wait_resumed(runs, log, request)


if __name__ == '__main__':
    sys.exit(main())

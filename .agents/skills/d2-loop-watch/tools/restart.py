"""Restart `make serve` at a safe moment and say whether the new service took up the asked mode.

A restart is the service's own (appraisal/service.py `restart_asked`: the file runs/alt-d/restart.request, JSON: the
state the next service takes up, `{"loop": true}` / `{"loop": false}`; empty keeps the state). The service takes it at
once, wherever the character is, so this waits for a safe moment first:

- the loop is off (the player's KP_6, a stop): at once;
- the loop is on: until its leg `next game` starts (the character is out of a game, at the lobby). Never in a game,
  where a restart could leave loot on the ground or a panel open.

Then it waits for the new service's `resumed after a restart` line and prints it.

    python3 .agents/skills/d2-loop-watch/tools/restart.py [--loop on|off|keep] [--wait 300]

Exit 0: restarted and resumed; 1: no safe moment within --wait (nothing written); 2: written, no resume seen.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import logwords
from logwords import LEG, LOOP_OFF, LOOP_ON, LOOP_RESUMED, LOOP_STOPPED, RESUMED_ANY, RESUMED_OFF, RESUMED_ON


RUNS = Path(__file__).resolve().parents[4] / 'inventory_tracking' / 'runs' / 'alt-d'
REQUEST = RUNS / 'restart.request'
ON = (LOOP_ON, LOOP_RESUMED, RESUMED_ON)
OFF = (LOOP_OFF, LOOP_STOPPED, RESUMED_OFF)


def newest() -> Path:
    log = logwords.newest(RUNS)
    if log is None:
        raise SystemExit('no serve session under runs/alt-d')
    return log


def loop_on(lines: list[str]) -> bool:
    on = False
    for line in lines:
        if any(word in line for word in ON) or LEG.search(line):
            on = True
        if any(word in line for word in OFF):
            on = False
    return on


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--loop', choices=('on', 'off', 'keep'), default='keep')
    parser.add_argument(
        '--kind',
        choices=('lk', 'andariel', 'tz', 'tzclear'),
        help="the loop's run (macros/loop.py `loop_kinds`: tz and tzclear only once macros/tzloop.py ENABLED)",
    )
    parser.add_argument('--wait', type=float, default=300.0, help='seconds to wait for a safe moment')
    args = parser.parse_args()
    log = newest()
    with open(log, errors='replace') as handle:
        lines = handle.readlines()
        if loop_on(lines):
            print(f'the loop is on ({log.parent.name}): waiting for its next game', flush=True)
            deadline = time.time() + args.wait
            while True:
                text = handle.readline()
                if not text:
                    if time.time() > deadline:
                        print('no safe moment: nothing written', flush=True)
                        return 1
                    time.sleep(0.2)
                    continue
                if any(word in text for word in OFF):
                    # The player's pause wins (SKILL.md hard rule 4): the restart keeps the loop off whatever was
                    # asked (10:39:02 on 2026-10-18: KP_6 pressed while a restart waited, and it turned the loop on)
                    print(f'the loop went off: {text[11:160].rstrip()}: it stays off', flush=True)
                    args.loop = 'off'
                    break
                if (m := LEG.search(text)) and m.group(2).strip() == 'next game':
                    print(f'at the lobby: {text[11:120].rstrip()}', flush=True)
                    break
    target = {} if args.loop == 'keep' else {'loop': args.loop == 'on'}
    if args.kind is not None:
        target['loop_kind'] = args.kind
    REQUEST.write_text(json.dumps(target) if target else '')
    print(f'restart asked: {target or "the state as it is"}', flush=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(1)
        fresh = newest()
        if fresh == log or not fresh.exists():
            continue
        for text in fresh.read_text(errors='replace').splitlines():
            if RESUMED_ANY in text:
                print(f'{fresh.parent.name}: {text[11:200]}', flush=True)
                return 0
    print('no resume line within 60 s: check `make serve` (the restart file is '
          f'{"still there" if REQUEST.exists() else "taken"})', flush=True)  # fmt: skip
    return 2


if __name__ == '__main__':
    sys.exit(main())

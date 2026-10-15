"""First look at a played session for a root-cause analysis: stdlib only.

    python3 .agents/skills/d2-rca/tools/session.py find              # newest session logs and combat takes
    python3 .agents/skills/d2-rca/tools/session.py log <probe.log>   # presses, repeated lines, bursts, warnings
    python3 .agents/skills/d2-rca/tools/session.py idle <take dir>   # stretches with no move and no cast
    python3 .agents/skills/d2-rca/tools/session.py unit <take dir> <unit id>... [--txt N]   # who stood where
    python3 .agents/skills/d2-rca/tools/session.py inputs <take dir> [--osd osd.log] [--all]  # the player's own input

Times are the log's clock (local); a take's frame time is turned into it by the manifest's `started_at`.
"""

import argparse
import bisect
import collections
import gzip
import itertools
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path


RUNS = Path('inventory_tracking/runs')
STAMP = re.compile(r'^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d),(\d{3}) (\w+) (.*)$')
NO_OWNER = 4294967295
DEAD = (0, 12)  # monster modes: dying, dead
CASTING = 10  # the character's mode in a cast


def rows(path: Path) -> list[dict]:
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


class Take:
    def __init__(self, directory: Path) -> None:
        self.manifest = json.loads((directory / 'manifest.json').read_text())
        self.frames = [f for f in rows(directory / 'frames.jsonl.gz') if f.get('p')]
        self.events = rows(directory / 'events.jsonl.gz')
        self.start = datetime.fromisoformat(self.manifest['started_at']).astimezone()
        self.zero = rows(directory / 'frames.jsonl.gz')[0]['t']

    def clock(self, t: float) -> str:
        return (self.start + timedelta(seconds=t - self.zero)).strftime('%H:%M:%S.%f')[:-5]


def hostiles(frame: dict) -> list[list]:
    return [m for m in frame['m'] if m[8] == NO_OWNER and not m[9] and m[2] not in DEAD and m[5] > 0]


def find(_: argparse.Namespace) -> None:
    for kind, name in (('alt-d', 'probe.log'), ('osd', None), ('combat', 'manifest.json')):
        print(f'## {RUNS / kind}')
        for directory in sorted((RUNS / kind).glob('2*'))[-6:]:
            note = ''
            if kind == 'combat' and (directory / 'manifest.json').exists():
                m = json.loads((directory / 'manifest.json').read_text())
                began = datetime.fromisoformat(m['started_at']).astimezone().strftime('%m-%d %H:%M:%S')
                note = f'area {m["area"]}, {m.get("seconds", 0):.0f}s from {began} local, schema {m.get("schema")}'
                note += f', {m.get("reason")}'
            elif name and (directory / name).exists():
                lines = (directory / name).read_text(errors='replace').splitlines()
                note = f'{len(lines)} lines, {lines[0][:19]} to {lines[-1][:19]}' if lines else 'empty'
            print(f'  {directory}  {note}')


def log(args: argparse.Namespace) -> None:
    lines = [m.groups() for m in map(STAMP.match, Path(args.path).read_text(errors='replace').splitlines()) if m]
    seconds = lambda row: int(row[1][:2]) * 3600 + int(row[1][3:5]) * 60 + int(row[1][6:]) + int(row[2]) / 1000  # ruff: ignore[lambda-assignment]
    presses = [(seconds(row), row) for row in lines if 'Macro: request ' in row[4]]
    print('## presses by routine')
    for routine, count in collections.Counter(
        row[4].split('request ')[1].split(',')[0] for _, row in presses
    ).most_common():
        print(f'  {count:4d}  {routine}')
    print('## bursts: 5 or more presses, each within 0.7s of the one before')
    burst: list = []
    for at, row in [*presses, (math.inf, None)]:
        if burst and at - burst[-1][0] > 0.7:
            if len(burst) >= 5:
                print(
                    f'  {burst[0][1][1]},{burst[0][1][2]} to {burst[-1][1][1]},{burst[-1][1][2]}: {len(burst)} presses'
                )
            burst = []
        burst.append((at, row))
    print('## the lines said most often (numbers folded): a line said many times is a loop')
    folded = collections.Counter(re.sub(r'-?\d+(\.\d+)?', 'N', row[4]) for row in lines if row[4].startswith('Macro'))
    for text, count in folded.most_common(args.top):
        print(f'  {count:4d}  {text[:150]}')
    print('## warnings and errors')
    for row in lines:
        if row[3] not in ('INFO', 'DEBUG') and 'slow press' not in row[4]:
            print(f'  {row[1]},{row[2]} {row[3]} {row[4][:170]}')


def idle(args: argparse.Namespace) -> None:
    take = Take(Path(args.take))
    casts = sorted(e['t'] for e in take.events if e.get('event') == 'cast')
    print(
        f'area {take.manifest["area"]}, {len(take.frames)} frames; '
        f'no move (< {args.moved} units) and no cast for {args.least}s or more'
    )
    start = 0
    for index in range(1, len(take.frames) + 1):
        first = take.frames[start]
        last = take.frames[index - 1]
        over = index == len(take.frames)
        if not over:
            now = take.frames[index]
            still = math.dist(first['p'][3:5], now['p'][3:5]) < args.moved and now['p'][1] != CASTING
            still = still and not _cast_between(casts, last['t'], now['t'])
            if still:
                continue
        length = last['t'] - first['t']
        if length >= args.least:
            near = [math.dist(first['p'][3:5], m[3:5]) for m in hostiles(last)]
            counts = '/'.join(str(sum(d <= reach for d in near)) for reach in (25, 40, 60))
            p = last['p']
            print(
                f'  {take.clock(first["t"])} to {take.clock(last["t"])}  {length:5.1f}s  at ({p[3]:.0f}, {p[4]:.0f})  '
                f'hostiles within 25/40/60: {counts}  nearest {min(near, default=math.nan):.0f}'
                f'  life {p[7]}/{p[8]}  macro {last.get("macro")}'
            )
        start = index


def _cast_between(casts: list[float], after: float, upto: float) -> bool:
    return any(after < c <= upto for c in casts)


def unit(args: argparse.Namespace) -> None:
    take = Take(Path(args.take))
    wanted = {int(u) for u in args.units}
    second = None
    for frame in take.frames:
        if int(frame['t']) == second:
            continue
        second = int(frame['t'])
        p = frame['p']
        seen = [m for m in frame['m'] if m[0] in wanted or (args.txt is not None and m[1] == args.txt)]
        told = '  '.join(
            f'{m[0]}:{m[1]} mode {m[2]} ({m[3]:.0f}, {m[4]:.0f}) life {m[5]}/{m[6]} '
            f'{math.dist(p[3:5], m[3:5]):.0f} away'
            for m in seen
        )
        print(
            f'{take.clock(frame["t"])}  player mode {p[1]} ({p[3]:.0f}, {p[4]:.0f}) life {p[7]}/{p[8]}'
            f'  |  {told or "-"}'
        )


# `inputs`: a change of a frame's `in` (pointer, buttons, keys) is the macro's when a `sent` event of the same
# input lies within WINDOW of the frame. Frames come 25 a second (40 ms); a frame's `t` is taken before its
# reads and the pointer and keys are read last, up to a frame's length later; 1.5% of frames come one or more
# periods late. A sent input so shows in a frame between about one period before and two after it:
# 0.15 s is that with a late frame's margin, and less than the gap between two of the player's own clicks.
WINDOW = 0.15
POINTER_TOLERANCE = 3  # pixels: a frame's pointer at a sent move's target
BUTTON_BITS = {1: 1 << 8, 2: 1 << 9, 3: 1 << 10, 8: 1 << 15, 9: 1 << 16}  # combat/record.py
OSD_PRESS = re.compile(r'(?:(\w+) \w+ potion: column (\d)|Show Items was off: pressed (\S+))')
STROKE_GAP = 0.2  # seconds between two of the player's pointer changes that are one stroke


def jsonl(directory: Path, name: str) -> list[dict]:
    """A take's file as written (open take) or packed (closed take)."""
    plain = directory / name
    if plain.exists():
        with plain.open(encoding='utf-8') as handle:
            return [json.loads(line) for line in handle if line.strip()]
    packed = directory / (name + '.gz')
    return rows(packed) if packed.exists() else []


class Clock:
    """A frame's monotonic time on the log's local clock, and back: by the manifest's `clock` (since schema 4)
    or its `started_at` and the first frame."""

    def __init__(self, manifest: dict, first: float) -> None:
        clock = manifest.get('clock')
        if clock:
            self.offset = clock['wall'] - clock['monotonic']
        else:
            self.offset = datetime.fromisoformat(manifest['started_at']).timestamp() - first

    def local(self, t: float) -> str:
        return datetime.fromtimestamp(t + self.offset).strftime('%H:%M:%S.%f')[:-4]

    def monotonic(self, epoch: float) -> float:
        return epoch - self.offset


def osd_presses(path: Path, clock: Clock, codes: dict[str, int]) -> list[tuple[float, frozenset[int] | None, str]]:
    """The healer's presses from its own log: (monotonic time, the key codes, the line). The line is written
    after the keys are let go (automation/potions.py, show_items.py: 25 ms held). Codes None: a key the
    take's manifest does not name (a take before the belt keys were named): any key at that time is the healer's."""
    found = []
    for line in path.read_text(errors='replace').splitlines():
        stamp, press = STAMP.match(line), OSD_PRESS.search(line)
        if not stamp or not press:
            continue
        actor, column, keys = press.groups()
        names = keys.split('+') if keys else ([column] + (['Shift_L'] if actor == 'merc' else []))
        epoch = datetime.strptime(f'{stamp[1]} {stamp[2]}.{stamp[3]}', '%Y-%m-%d %H:%M:%S.%f').timestamp()
        known = [codes.get(name) for name in names]
        found.append((clock.monotonic(epoch), None if None in known else frozenset(known), stamp[5][:80]))
    return found


def osd_log_for(take: Path) -> Path | None:
    """The newest healer log begun before the take (runs/osd/<UTC stamp>-<id>/osd.log)."""
    logs = [d / 'osd.log' for d in sorted((take.parent.parent / 'osd').glob('2*')) if (d / 'osd.log').exists()]
    before = [log for log in logs if log.parent.name[:16] <= take.name[:16]]
    return before[-1] if before else None


def changes(frames: list[dict]) -> list[tuple[float, str, tuple, dict]]:
    """What differs in `in` from one frame to the next: (time, 'move', (x, y), frame), ('button', (n, down)),
    ('key', (code, down))."""
    found = []
    for before, now in itertools.pairwise(frames):
        was, came = before.get('in') or [None] * 6, now.get('in') or [None] * 6
        if None not in (was[0], came[0]) and (was[0], was[1]) != (came[0], came[1]):
            found.append((now['t'], 'move', (came[0], came[1]), now))
        for button, bit in BUTTON_BITS.items():
            if None not in (was[2], came[2]) and was[2] & bit != came[2] & bit:
                found.append((now['t'], 'button', (button, bool(came[2] & bit)), now))
        held, holding = set(was[5] or ()), set(came[5] or ())
        found += [(now['t'], 'key', (code, True), now) for code in sorted(holding - held)]
        found += [(now['t'], 'key', (code, False), now) for code in sorted(held - holding)]
    return found


def near(times: list[float], items: list, t: float) -> list:
    return items[bisect.bisect_left(times, t - WINDOW) : bisect.bisect_right(times, t + WINDOW)]


def whose(change: tuple, sent: list[dict], times: list[float], osd: list, osd_times: list[float]) -> str:
    """'macro', 'healer', 'player', or 'player (during a macro move)': a pointer away from every target the
    macro sent around then."""
    t, kind, what, _ = change
    close = [e for e in near(times, sent, t) if e.get('input') == kind]
    if kind == 'move':
        if any(max(abs(e['xy'][0] - what[0]), abs(e['xy'][1] - what[1])) <= POINTER_TOLERANCE for e in close):
            return 'macro'
        return 'player (during a macro move)' if close else 'player'
    field = 'button' if kind == 'button' else 'code'
    if any(e.get(field) == what[0] and e.get('down') == what[1] for e in close):
        return 'macro'
    if kind == 'key' and any(codes is None or what[0] in codes for _, codes, _ in near(osd_times, osd, t)):
        return 'healer'
    return 'player'


def inputs(args: argparse.Namespace) -> None:
    directory = Path(args.take)
    manifest = json.loads((directory / 'manifest.json').read_text())
    frames = jsonl(directory, 'frames.jsonl')
    events = sorted(jsonl(directory, 'events.jsonl'), key=lambda e: e['t'])
    if not frames:
        print('no frames')
        return
    clock = Clock(manifest, frames[0]['t'])
    names = manifest.get('keys') or {}
    sent = [e for e in events if e.get('event') == 'sent']
    times = [e['t'] for e in sent]
    osd_path = Path(args.osd) if args.osd else osd_log_for(directory)
    osd = osd_presses(osd_path, clock, {name: int(code) for code, name in names.items()}) if osd_path else []
    osd = sorted(press for press in osd if frames[0]['t'] - 1 <= press[0] <= frames[-1]['t'] + 1)
    osd_times = [press[0] for press in osd]
    print(
        f'{directory.name}: {len(frames)} frames, {clock.local(frames[0]["t"])} to {clock.local(frames[-1]["t"])}; '
        f'{len(sent)} sent inputs by {dict(collections.Counter(e.get("by") for e in sent))}; '
        f'{len(osd)} healer presses ({osd_path or "no healer log"}); window {WINDOW} s'
    )
    if not sent:
        print('  this take has no `sent` events (recorded before 2026-10-13 night, or no macro input): '
              'every change below counts as the player\'s')  # fmt: skip
    found = [(change, whose(change, sent, times, osd, osd_times)) for change in changes(frames)]
    tally = collections.Counter((change[1], owner.split(' (')[0]) for change, owner in found)
    print('## changes in the frames by whose: ' + ', '.join(f'{k} {o} {n}' for (k, o), n in sorted(tally.items())))
    print("## the player's inputs" + (' (and every other change: --all)' if args.all else ''))
    stroke: list = []

    def flush() -> None:
        if stroke:
            first, last = stroke[0][0], stroke[-1][0]
            f0, f1 = first[3]['in'][3:5], last[3]['in'][3:5]
            print(
                f'  {clock.local(first[0])}  pointer  {len(stroke)} frames over {last[0] - first[0]:.2f}s to '
                f'{last[2]} (window {f0} -> {f1}){"  " + stroke[-1][1] if stroke[-1][1] != "player" else ""}'
                f'  macro {"on" if any(c[3].get("macro") for c, _ in stroke) else "off"}'
            )
            stroke.clear()

    for change, owner in found:
        t, kind, what, frame = change
        mine = owner.startswith('player')
        if kind == 'move' and mine and not args.all:
            if stroke and t - stroke[-1][0][0] > STROKE_GAP:
                flush()
            stroke.append((change, owner))
            continue
        if not mine and not args.all:
            continue
        flush()
        at = frame['in']
        if kind == 'move':
            told = f'pointer at {what} (window {at[3]}, {at[4]})'
        elif kind == 'button':
            told = f'button {what[0]} {"down" if what[1] else "up"} at ({at[0]}, {at[1]}) (window {at[3]}, {at[4]})'
        else:
            told = f'key {what[0]} {names.get(str(what[0]), "?")} {"down" if what[1] else "up"}'
        print(f'  {clock.local(t)}  {told}  [{owner}]  macro {"on" if frame.get("macro") else "off"}')
    flush()
    checks = [e for e in events if e.get('event') == 'pointer_check']
    if checks:
        print("## the actuator's pointer check that stopped a move ('the mouse was moved'; macros/actuator.py `guard`)")
        for e in checks:
            print(f"  {clock.local(e['t'])}  left at {e.get('left_at')}, pointer {e.get('pointer')}: "
                  f"{e.get('drift')} px off, limit {e.get('limit')}")  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(required=True)
    commands.add_parser('find').set_defaults(run=find)
    sub = commands.add_parser('log')
    sub.add_argument('path')
    sub.add_argument('--top', type=int, default=25)
    sub.set_defaults(run=log)
    sub = commands.add_parser('idle')
    sub.add_argument('take')
    sub.add_argument('--least', type=float, default=1.0)
    sub.add_argument('--moved', type=float, default=1.0)
    sub.set_defaults(run=idle)
    sub = commands.add_parser('unit')
    sub.add_argument('take')
    sub.add_argument('units', nargs='*')
    sub.add_argument('--txt', type=int)
    sub.set_defaults(run=unit)
    sub = commands.add_parser('inputs', help="the player's own pointer moves, buttons and keys in a take")
    sub.add_argument('take')
    sub.add_argument('--osd', help='the healer log (default: the newest runs/osd/*/osd.log begun before the take)')
    sub.add_argument('--all', action='store_true', help="list the macro's and the healer's changes too")
    sub.set_defaults(run=inputs)
    args = parser.parse_args()
    args.run(args)


if __name__ == '__main__':
    main()

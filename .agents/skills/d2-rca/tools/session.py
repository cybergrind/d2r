"""First look at a played session for a root-cause analysis: stdlib only.

    python3 .agents/skills/d2-rca/tools/session.py find              # newest session logs and combat takes
    python3 .agents/skills/d2-rca/tools/session.py log <probe.log>   # presses, repeated lines, bursts, warnings
    python3 .agents/skills/d2-rca/tools/session.py idle <take dir>   # stretches with no move and no cast
    python3 .agents/skills/d2-rca/tools/session.py unit <take dir> <unit id>... [--txt N]   # who stood where

Times are the log's clock (local); a take's frame time is turned into it by the manifest's `started_at`.
"""

import argparse
import collections
import gzip
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
    seconds = lambda row: int(row[1][:2]) * 3600 + int(row[1][3:5]) * 60 + int(row[1][6:]) + int(row[2]) / 1000  # noqa: E731
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
    args = parser.parse_args()
    args.run(args)


if __name__ == '__main__':
    main()

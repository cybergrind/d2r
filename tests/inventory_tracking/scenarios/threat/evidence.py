"""Where the character lost life in the recorded takes, what stood near, and where the pointer aimed.

    PYTHONPATH=. uv run --offline python -m tests.inventory_tracking.scenarios.threat.evidence [takes directory]

Only the takes whose `p` row has the vitals count (schema 2, 2026-10-10: the Catacombs; the Chaos Sanctuary
takes of 2026-10-09 have none). A frame's loss is the fall of the character's life since the frame before,
with the same maximum (a Battle Orders running out is no hit). Reported:

- the life lost a second with a monster type within CLOSE units, and with it further off but in the blades' reach;
- the life lost while the macro fought standing, split by whether the monster terror/danger.py scores highest
  among those in reach was on the pointer's line (within LINE units of it) or not;
- the worst seconds: the life lost, what stood near, what was on the line;
- the elites the blades cannot hurt (physical resistance 100 on first sight, units.jsonl stat 36) against the
  others: how long each stood in reach of the standing fight, and whether it died.
"""

import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

from inventory_tracking.combat.policy import REACH
from inventory_tracking.combat.takes import ground_under_pointer
from inventory_tracking.terror.danger import DANGER, Unit, table, threat


TAKES = Path('inventory_tracking/runs/combat')
NO_OWNER = 0xFFFFFFFF
DEAD = (0, 12)
MOVING = (2, 3, 6)
ELITE, MINION = 0x0E, 0x10
CLOSE, LINE, WINDOW, WORST = 8.0, 2.5, 1.0, 0.07


def on_line(here, ground, at) -> bool:
    """Whether `at` lies within LINE of the blades' way from `here` toward the ground under the pointer."""
    length = math.dist(ground, here)
    if length < 0.5:
        return False
    ux, uy = (ground[0] - here[0]) / length, (ground[1] - here[1]) / length
    dx, dy = at[0] - here[0], at[1] - here[1]
    return 0 < dx * ux + dy * uy <= REACH and abs(dx * uy - dy * ux) <= LINE


def main(argv=None) -> int:
    root = Path((argv or sys.argv[1:] or [TAKES])[0])
    threats = table()
    name = lambda txt: threats.monsters[txt].name if txt in threats.monsters else str(txt)  # noqa: E731
    close, reach = defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0])
    lined = defaultdict(lambda: [0.0, 0.0])  # top-threat type -> life lost with it [off the line, on it]
    elites = defaultdict(list)  # immune -> [(seconds in reach of the standing fight, died)]
    worst, takes = [], 0
    for directory in sorted(root.iterdir()):
        if not (directory / 'frames.jsonl').exists() or not (directory / 'units.jsonl').exists():
            continue
        firsts = {unit['unit']: unit for unit in map(json.loads, (directory / 'units.jsonl').open())}
        immune = {
            unit: row['stats'].get('36', 0) >= 100
            for unit, row in firsts.items()
            if row.get('owner') == NO_OWNER
            and not row.get('ally')
            and row['flags'] & ELITE
            and not row['flags'] & MINION
        }
        frames = [
            f
            for f in map(json.loads, (directory / 'frames.jsonl').open())
            if f.get('p') and len(f['p']) >= 11 and f['p'][8]
        ]
        if len(frames) < 50:
            continue
        takes += 1
        rect = next((f['rect'] for f in frames if f.get('rect')), [0, 0, 2560, 1418])
        aspect = rect[2] / rect[3]
        stood, died, losses = defaultdict(float), set(), [0.0]
        for before, frame in pairwise(frames):
            was, player = before['p'], frame['p']
            seconds = min(frame['t'] - before['t'], 0.2)
            loss = was[7] - player[7] if was[8] == player[8] and player[7] < was[7] else 0
            losses.append(loss)
            here = (player[3], player[4])
            hostile = [m for m in frame['m'] if m[8] == NO_OWNER and not m[9] and m[2] not in DEAD]
            near = {m[1] for m in hostile if math.dist(here, (m[3], m[4])) <= CLOSE}
            for txt in near:
                close[txt][0] += seconds
                close[txt][1] += loss
            for txt in {m[1] for m in hostile if math.dist(here, (m[3], m[4])) <= REACH} - near:
                reach[txt][0] += seconds
                reach[txt][1] += loss
            died |= {m[0] for m in frame['m'] if m[0] in immune and m[2] in DEAD}
            if not frame.get('macro') or player[1] in MOVING:
                continue
            ground = ground_under_pointer(frame, aspect)
            for m in hostile:
                if m[0] in immune and math.dist(here, (m[3], m[4])) <= REACH:
                    stood[m[0]] += seconds
            units = [Unit(m[0], m[1], m[3], m[4]) for m in hostile if math.dist(here, (m[3], m[4])) <= REACH]
            if loss and units and ground:
                score, top = max(
                    ((threat(unit, units, threats, DANGER)[0], unit) for unit in units), key=lambda pair: pair[0]
                )
                if score:
                    lined[name(top.txt_id)][on_line(here, ground, (top.x, top.y))] += loss
        for unit, seconds in stood.items():
            elites[immune[unit]].append((seconds, unit in died))
        worst += worst_seconds(directory.name, frames, losses, aspect, name)
    print(f'{takes} takes with vitals')
    print('life lost a second with the type within 8 units | 8 to 22 units (seconds there):')
    for txt, (seconds, lost) in sorted(close.items(), key=lambda item: -item[1][1] / max(item[1][0], 1)):
        if seconds >= 20:
            far = reach[txt]
            beyond = far[1] / max(far[0], 1)
            print(f'  {name(txt):14} {lost / seconds:5.1f} ({seconds:4.0f} s) | {beyond:5.1f} ({far[0]:4.0f} s)')
    print('life lost while the macro fought standing, by the top-threat type in reach: off the line | on it')
    for kind, (off, on) in sorted(lined.items(), key=lambda item: -sum(item[1])):
        print(f'  {kind:14} {off:5.0f} | {on:5.0f}')
    off, on = (sum(pair[k] for pair in lined.values()) for k in (0, 1))
    print(f'  {"all":14} {off:5.0f} | {on:5.0f}  ({off / (off + on):.0%} off the line)')
    print(f'the worst seconds (at least {WORST:.0%} of the life):')
    for row in sorted(worst, reverse=True)[:20]:
        print('  ' + row[1])
    for flag, label in ((True, 'immune to the blades'), (False, 'not immune')):
        rows = elites[flag]
        if rows:
            seconds = sorted(s for s, _ in rows)
            median, ninth = statistics.median(seconds), seconds[int(len(seconds) * 0.9)]
            gone = sum(1 for _, dead in rows if dead)
            print(f'elites {label}: {len(rows)}, in reach of the standing fight {median:.1f} s at the median,')
            print(f'  {ninth:.1f} s at the ninth decile, {gone} died')
    return 0


def worst_seconds(take: str, frames, losses, aspect: float, name) -> list[tuple[float, str]]:
    """The take's one-second windows that cost WORST of the life or more, none overlapping another."""
    times = [f['t'] for f in frames]
    windows, last = [], 0
    for first in range(len(frames)):
        last = max(last, first)
        while last + 1 < len(frames) and times[last + 1] - times[first] <= WINDOW:
            last += 1
        windows.append((sum(losses[first + 1 : last + 1]), first, last))
    taken, rows = [], []
    for lost, first, last in sorted(windows, reverse=True):
        if lost < WORST * frames[first]['p'][8]:
            break
        if any(first <= b and last >= a for a, b in taken):
            continue
        taken.append((first, last))
        frame = frames[next(k for k in range(first + 1, last + 1) if losses[k])]
        here = (frame['p'][3], frame['p'][4])
        hostile = [m for m in frame['m'] if m[8] == NO_OWNER and not m[9] and m[2] not in DEAD]
        ground = ground_under_pointer(frame, aspect)

        def told(monsters) -> str:
            count = Counter(name(m[1]) + ('*' if m[7] & ELITE and not m[7] & MINION else '') for m in monsters)
            return ', '.join(f'{n} {kind}' for kind, n in count.most_common()) or 'nothing'

        near = [m for m in hostile if math.dist(here, (m[3], m[4])) <= CLOSE]
        far = [m for m in hostile if CLOSE < math.dist(here, (m[3], m[4])) <= REACH]
        line = [m for m in hostile if ground and on_line(here, ground, (m[3], m[4]))]
        share = lost / frame['p'][8]
        life = f'{frames[first]["p"][7]} -> {frames[last]["p"][7]} of {frame["p"][8]}'
        macro = 'on' if frame.get('macro') else 'off'
        stood = f'within 8: {told(near)} | to 22: {told(far)} | on the line: {told(line)}'
        rows.append((share, f'{share:.0%} {take} frame {frame["n"]}: {life}, macro {macro} | {stood}'))
    return rows


if __name__ == '__main__':
    raise SystemExit(main())

"""The evidence pass over the service logs: every exit the teleport step took, and every stop near one.

Run it as `uv run --offline python -m tests.inventory_tracking.scenarios.exits.evidence` (add `--json`
for the rows). It reads `inventory_tracking/runs/alt-d/*/probe.log` and nothing else; the numbers it
printed on 2026-10-10 are in the scenarios' docstrings and reasons.

An exit is a "<label>: there" line. Its approach is the run of hops toward the same label before it,
back to the level's first; the last stretch is the part that began within LAST_STRETCH units of the
mark. The fewest hops possible is counted without walls (a teleport crosses them): hops of the view's
reach along the line to the door until the character is within the walk the step itself allows
(teleport.ENTRY_WALK from a remembered spot, teleport.NEAR_WARP from a mark with none).
"""

import json
import math
import re
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from inventory_tracking.macros.teleport import ENTRY_WALK, NEAR_WARP
from inventory_tracking.macros.view import Viewport


LOGS = Path('inventory_tracking/runs/alt-d')
LAST_STRETCH = 60.0  # world units from the mark: where the last stretch begins
AFTER_SECONDS = 4.0  # a stop this soon after an arrival came from the action asked for again
PAIR = r'\((-?[\d.]+), (-?[\d.]+)\)'
STAMP = re.compile(r'^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d),(\d{3}) \w+ (.*)$')
HOP = re.compile(r'^Macro: Teleport toward (.+): (\d+) left after this')
MARKED = re.compile(rf'^Macro: door (.+) marked at {PAIR}, entry (not known yet|{PAIR}); this hop aims ([\d.]+)')
LANDED = re.compile(rf'^Macro: teleport aimed at {PAIR}, ([\d.]+) from {PAIR},.*landed at {PAIR}')
STILL = re.compile(rf'^Macro: teleport aimed at {PAIR}, ([\d.]+) from {PAIR},.*did not move')
WALK = re.compile(r'^Macro: Walking into (.+?)(?:, (\d+) away)?$')
AT_DOOR = re.compile(
    rf'^Macro: door (.+) marked at {PAIR}; the character at {PAIR}, ([\d.]+) from the mark; entry (.*)$'
)
MISSED = re.compile(r'^Macro: the door did not take the click')
IN = re.compile(rf'^Macro: door (.+): in after ([\d.]+)s, walked ([\d.]+) from {PAIR} to {PAIR}; .*\((.*)\)$')
THERE = re.compile(r'^Macro: (.+): there$')
STOPPED = re.compile(r'^Macro stopped: (.*)$')
AGAIN = re.compile(r'^Macro: the pointer was found at')
HUNTED = ('the elite', 'the monster', 'the unexplored', 'the remembered')


def seconds(match: re.Match) -> float:
    _, _, day, hour, minute, second, milli = (int(part) for part in match.groups()[:7])
    return ((day * 24 + hour) * 60 + minute) * 60 + second + milli / 1000


def reach(start: tuple[float, float], end: tuple[float, float]) -> float:
    """World units a hop from `start` covers along the line to `end` before it leaves the view."""
    view, away = Viewport(), math.dist(start, end)
    if away == 0:
        return 0.0
    low, high = 0.0, 60.0
    for _ in range(20):
        middle = (low + high) / 2
        point = (start[0] + (end[0] - start[0]) * middle / away, start[1] + (end[1] - start[1]) * middle / away)
        low, high = (middle, high) if view.in_view(view.ground(start, *point)) else (low, middle)
    return low


@dataclass
class Hop:
    at: float
    left: float  # the step's own word: from the landing to the mark
    start: tuple[float, float] | None = None
    aim: tuple[float, float] | None = None
    landed: tuple[float, float] | None = None
    door: tuple[float, float] | None = None
    entry: tuple[float, float] | None = None
    done: float | None = None  # when the landing was logged
    away: float | None = None  # from the start to the mark


@dataclass
class Exit:
    log: str
    stamp: str
    label: str
    hops: int  # made inside the last stretch
    fewest: int | None
    walk_from: float | None  # units from the mark when the click was made
    landing_to_there: float | None  # seconds from the last landing to the arrival
    landing_to_click: float | None  # of which: until the walk-in began (the next request and its checks)
    walk_seconds: float | None
    walked: float | None
    misses: int
    aims_again: int
    entry: str  # 'remembered', 'not known yet', 'unknown' (an older log)
    last_hop: float | None  # units the last hop covered
    last_hop_from: float | None  # units from the mark it started at
    door: tuple[float, float] | None = None  # the mark, where the log gives it
    start: tuple[float, float] | None = None  # where the last stretch began
    notes: list[str] = field(default_factory=list)


def read(path: Path):
    """The exits of one log and its stops as (seconds, stamp, message, seconds since the last arrival, units
    from the mark at the last landing toward a door or None)."""
    exits, stops = [], []
    approach: list[Hop] = []
    label = None
    walk = None  # the walk-in under way: its numbers so far
    arrived = -math.inf
    for line in path.read_text(errors='replace').splitlines():
        stamped = STAMP.match(line)
        if stamped is None:
            continue
        now, text = seconds(stamped), stamped.group(8)
        text = text[text.find('Macro') :] if 'Macro' in text else text
        if found := HOP.match(text):
            if found.group(1).startswith(HUNTED):
                continue
            if found.group(1) != label:
                label, approach = found.group(1), []
            approach.append(Hop(now, float(found.group(2))))
        elif (found := MARKED.match(text)) and approach and found.group(1) == label:
            hop = approach[-1]
            hop.door = (float(found.group(2)), float(found.group(3)))
            if found.group(5) is not None:
                hop.entry = (float(found.group(5)), float(found.group(6)))
        elif (found := LANDED.match(text) or STILL.match(text)) and approach and approach[-1].aim is None:
            numbers = [float(value) for value in found.groups()]
            hop = approach[-1]
            if hop.door is None and not (hop.at <= now <= hop.at + 2.5):
                continue
            hop.aim, hop.start, hop.done = (numbers[0], numbers[1]), (numbers[3], numbers[4]), now
            hop.landed = (numbers[5], numbers[6]) if len(numbers) > 5 else hop.start
            if hop.door is not None:
                hop.away = math.dist(hop.start, hop.door)
            elif len(approach) > 1 and approach[-2].landed is not None:
                hop.away = approach[-2].left + math.dist(approach[-2].landed, hop.start)
            else:
                hop.away = hop.left + numbers[2]
        elif found := WALK.match(text):
            walk = {'label': found.group(1), 'at': now, 'from': float(found.group(2) or 'nan'), 'misses': 0, 'again': 0}
        elif (found := AT_DOOR.match(text)) and walk is not None:
            walk['from'] = float(found.group(6))
            walk['entry'] = 'remembered' if found.group(7).startswith('remembered') else 'not known yet'
            walk['door'] = (float(found.group(2)), float(found.group(3)))
            walk['stood'] = (float(found.group(4)), float(found.group(5)))
        elif MISSED.match(text) and walk is not None:
            walk['misses'] += 1
        elif AGAIN.match(text) and walk is not None:
            walk['again'] += 1
        elif (found := IN.match(text)) and walk is not None:
            walk['seconds'], walk['walked'] = float(found.group(2)), float(found.group(3))
        elif found := THERE.match(text):
            arrived = now
            if walk is None:
                continue
            hops = [hop for hop in approach if hop.landed is not None] if walk['label'] == label else []
            stretch = [hop for hop in hops if hop.away is not None and hop.away <= LAST_STRETCH]
            fewest = None
            if stretch:
                first = stretch[0]
                goal = first.entry or first.door
                allowed = ENTRY_WALK if first.entry else NEAR_WARP
                if goal is not None:
                    away = math.dist(first.start, goal)
                    fewest = 0 if away <= allowed else math.ceil((away - allowed) / reach(first.start, goal))
                else:  # an older log: the mark's distance only, the reach of the hop that was made
                    fewest = 0 if first.away <= NEAR_WARP else math.ceil((first.away - NEAR_WARP) / 26.0)
            last = hops[-1] if hops else None
            exit_ = Exit(
                path.parent.name, line[:23], walk['label'], len(stretch), fewest, walk['from'],
                None if last is None else round(now - last.done, 2),
                None if last is None else round(walk['at'] - last.done, 2),
                walk.get('seconds', round(now - walk['at'], 2)), walk.get('walked'), walk['misses'], walk['again'],
                walk.get('entry', 'unknown'),
                None if last is None else round(math.dist(last.start, last.landed), 1),
                None if last is None or last.away is None else round(last.away, 1),
            )  # fmt: skip
            if stretch:
                exit_.door, exit_.start = stretch[0].door, stretch[0].start
            if last is not None and last.entry is not None and math.dist(last.aim, last.entry) > 1.0:
                exit_.notes.append(f'the last hop aimed {math.dist(last.aim, last.entry):.1f} off the remembered spot')
            if walk.get('walked') and 'stood' in walk and walk['walked'] > 1.5 * walk['from'] + 2:
                exit_.notes.append(f'walked {walk["walked"]:.1f} from {walk["from"]:.1f} away: round a wall')
            exits.append(exit_)
            walk, approach, label = None, [], None
        elif found := STOPPED.match(text):
            near = approach[-1].left if approach and approach[-1].landed is not None else None
            stops.append((now, line[:23], found.group(1), round(now - arrived, 2), near))
            if walk is not None and found.group(1).startswith('no click took'):
                walk = None
    return exits, stops


def median(values) -> float | None:
    values = [value for value in values if value is not None and not math.isnan(value)]
    return round(statistics.median(values), 2) if values else None


def badness(exit_: Exit) -> float:
    """Seconds lost, roughly: a hop is 0.6 s with its request, a walk-in 0.25 s, a click miss 1.4 s."""
    extra = max(0, exit_.hops - (exit_.fewest or 0)) * 0.6
    return extra + max(0.0, (exit_.walk_seconds or 0) - 0.25) + max(0.0, (exit_.landing_to_click or 0) - 0.1)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    exits: list[Exit] = []
    stops = []
    for path in sorted(LOGS.glob('*/probe.log')):
        found, stopped = read(path)
        exits += found
        stops += [(path.parent.name, *stop) for stop in stopped]
    if '--json' in argv:
        print(json.dumps([asdict(exit_) for exit_ in exits], indent=1))
        return 0
    counted = [exit_ for exit_ in exits if exit_.fewest is not None]
    print(f'exits taken: {len(exits)} in {len({exit_.log for exit_ in exits})} logs; with hops logged: {len(counted)}')
    print('hops inside the last 60 units:', Counter(exit_.hops for exit_ in counted).most_common())
    print('extra hops over the fewest:', Counter(exit_.hops - exit_.fewest for exit_ in counted).most_common())
    print('sum of extra hops:', sum(max(0, exit_.hops - exit_.fewest) for exit_ in counted))
    for name in ('walk_from', 'landing_to_there', 'landing_to_click', 'walk_seconds', 'walked', 'last_hop'):
        values = [getattr(exit_, name) for exit_ in exits]
        known = sorted(value for value in values if value is not None and not math.isnan(value))
        if known:
            print(
                f'{name}: median {median(known)}, p90 {known[int(len(known) * 0.9)]}, max {known[-1]} (n={len(known)})'
            )
    print('entry at the click:', Counter(exit_.entry for exit_ in exits).most_common())
    for kind in ('remembered', 'not known yet', 'unknown'):
        some = [exit_ for exit_ in exits if exit_.entry == kind]
        print(
            f'  {kind}: n={len(some)}, walk seconds median {median(e.walk_seconds for e in some)}, '
            f'landing to there median {median(e.landing_to_there for e in some)}, '
            f'misses {sum(e.misses for e in some)} in {sum(1 for e in some if e.misses)} exits'
        )
    print('click misses:', sum(e.misses for e in exits), 'in', sum(1 for e in exits if e.misses), 'exits')
    print('aims made again during a walk-in:', sum(e.aims_again for e in exits))
    print('short last hops (under 16 units):', sum(1 for e in exits if e.last_hop is not None and e.last_hop < 16))
    print('notes:', Counter(note.split(':')[0][:40] for e in exits for note in e.notes).most_common())
    print(f'\nstops within {AFTER_SECONDS:.0f} s after an arrival:')
    after = Counter(re.sub(r'\d+', 'N', stop[3]) for stop in stops if 0 <= stop[4] <= AFTER_SECONDS)
    for message, count in after.most_common():
        print(f'  {count:3d}  {message}')
    print('stops with a door at most 60 units off (by the last landing):')
    close = Counter(re.sub(r'\d+', 'N', s[3]) for s in stops if s[5] is not None and s[5] <= LAST_STRETCH)
    for message, count in close.most_common():
        print(f'  {count:3d}  {message}')
    print('\nthe 10 worst exits:')
    for exit_ in sorted(exits, key=badness, reverse=True)[:10]:
        print(
            f'  {exit_.log} {exit_.stamp} {exit_.label}: {exit_.hops} hops (fewest {exit_.fewest}), walk from '
            f'{exit_.walk_from}, landing to there {exit_.landing_to_there}s (click after {exit_.landing_to_click}s, '
            f'in after {exit_.walk_seconds}s, walked {exit_.walked}), misses {exit_.misses}, entry {exit_.entry}; '
            f'{"; ".join(exit_.notes)}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

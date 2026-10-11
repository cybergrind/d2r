"""What the service logs say about the teleport hops made so far: every hop, and the journeys they add up to.

A hop is one 'teleport aimed at' line of a probe.log (macros/teleport.py `hop_toward`), with the 'Teleport
toward' line before it for the mark's name. A journey is a run of hops toward one mark where each hop
starts where the last one landed: a fight, a walk or the player's own move in between ends it. Its end is
where the last hop landed, so a journey the player broke off is judged on the ground it covered.

The ideal a journey is held against here needs no level map: the fewest hops that cover its straight line
when every hop may land anywhere the window shows (`free_hops`). The reference planner (harness.py) gives
the ideal over the real walls for the journeys whose level was recorded.

    uv run --offline python -m tests.inventory_tracking.scenarios.navigation.evidence
"""

import json
import math
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from inventory_tracking.levels.model import Ground, Walkable
from inventory_tracking.macros.view import Viewport
from tests.inventory_tracking.scenarios.navigation.harness import Footing, HopField


Point = tuple[float, float]
LOGS = Path('inventory_tracking/runs/alt-d')
TAKES = Path('inventory_tracking/runs/combat')
SLACK = timedelta(seconds=1)  # a hop may be logged a moment after its take ended
DOOR_ZONE = 30.0  # world units round a door left to scenarios/exits
REWORKED = '2026-10-10 20:56'  # the log's clock: the first run on the planner as it is now (macros/plan.md)
NUMBER = r'(-?\d+(?:\.\d+)?)'
PAIR = rf'\({NUMBER}, {NUMBER}\)'
STAMP = r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3})'
TOWARD = re.compile(rf'^{STAMP} INFO Macro: Teleport toward (.+?): (\d+) left after this(?:, (\d+) charges)?')
HOP = re.compile(
    rf'^{STAMP} INFO Macro: teleport aimed at {PAIR}, {NUMBER} from {PAIR}, (\S+(?: by ground)?) off the way, '
    rf'footing (\w+), (\d+) grids, pointer \((-?\d+), (-?\d+)\) in \((\d+), (\d+), (\d+), (\d+)\); (.*)$'
)
LANDED = re.compile(rf'landed at {PAIR}, off by {NUMBER}')
DOOR = re.compile(rf'Macro: door (.+?) marked at {PAIR}')
SPOT = re.compile(rf'Macro: hunting (.+?) at {PAIR}, \d+ away from {PAIR}, firing spot {PAIR}')
ROOM = re.compile(r'Macro: exploring toward room (\d+) at \((-?\d+), (-?\d+)\)')
JOINED = 6.0  # world units between a landing and the next hop's start for both to be one journey
HAND_PIXELS = 60.0  # the pointer this far from where the macro put it: the player's hand moved the mouse
MISSED = 2.5  # world units off the aim from which a landing is not the spot aimed at
TILE_UNITS = 5
HUNTED = ('the elite', 'the remembered', 'the monster')


@dataclass(frozen=True)
class Hop:
    log: str
    stamp: str  # the log's own clock (local time), to the millisecond
    label: str
    aim: Point
    start: Point
    gain: float | None  # world units the hop was to take off the way; None where the log has no number
    grids: int
    pointer: tuple[int, int]
    rect: tuple[int, int, int, int]
    landed: Point | None  # None: the character did not move
    mark: Point | None  # the door, the firing spot or the unexplored tile the hop was made for (world units)
    quarry: Point | None = None  # where the monster hunted stood when the hop was planned

    @property
    def end(self) -> Point:
        return self.landed or self.start

    @property
    def length(self) -> float:
        return math.dist(self.start, self.aim)

    @property
    def off(self) -> float | None:
        return None if self.landed is None else math.dist(self.landed, self.aim)

    @property
    def view(self) -> Viewport:
        return Viewport.of(self.rect)

    @property
    def hand(self) -> bool:
        """Whether the pointer was not where the aim put it when the hop was logged (the player's hand)."""
        across, down = self.view.ground(self.start, *self.aim)
        x, y, width, height = self.rect
        return math.dist(self.pointer, (x + across * width, y + down * height)) > HAND_PIXELS


@dataclass
class Journey:
    hops: list[Hop] = field(default_factory=list)

    @property
    def start(self) -> Point:
        return self.hops[0].start

    @property
    def end(self) -> Point:
        return self.hops[-1].end

    @property
    def straight(self) -> float:
        return math.dist(self.start, self.end)

    @property
    def ideal(self) -> int:
        return free_hops(self.hops[0].view, self.start, self.end)

    @property
    def over(self) -> int:
        return len(self.hops) - self.ideal

    @property
    def kind(self) -> str:
        label = self.hops[0].label
        if label.startswith('an unexplored'):
            return 'explore'
        if label.startswith(HUNTED) or re.search(r'\(\d+\)$', label):
            return 'hunt'
        return 'door'

    def turns(self) -> tuple[int, int]:
        """(hops that went backward, hops that went sideways) against the journey's own straight line:
        more than 90 and more than 45 degrees off it."""
        if self.straight < 1.0:
            return 0, 0
        along = ((self.end[0] - self.start[0]) / self.straight, (self.end[1] - self.start[1]) / self.straight)
        back = side = 0
        for hop in self.hops:
            moved = math.dist(hop.start, hop.end)
            if moved < 1.0:
                continue
            cosine = ((hop.end[0] - hop.start[0]) * along[0] + (hop.end[1] - hop.start[1]) * along[1]) / moved
            back += cosine < 0
            side += 0 <= cosine < math.cos(math.pi / 4)
        return back, side

    def causes(self) -> Counter[str]:
        """What the hops beyond the ideal were spent on, by what the log lines themselves show."""
        found: Counter[str] = Counter()
        marks = {hop.mark for hop in self.hops if hop.mark is not None}
        for hop in self.hops:
            if hop.landed is None:
                found['the character did not move'] += 1
            elif hop.hand:
                found["the player's hand on the mouse"] += 1
            elif hop.off is not None and hop.off > MISSED:
                found['landed off the aim'] += 1
            elif hop.length < 0.6 * reach_along(hop.view, hop.start, hop.aim) and hop is not self.hops[-1]:
                found['a short hop with the journey not over'] += 1
        back, side = self.turns()
        found['backward hops'] += back
        found['sideways hops'] += side
        if len(marks) > 1:
            found['the mark moved between hops'] += len(marks) - 1
        return +found


def free_hops(view: Viewport, start: Point, end: Point) -> int:
    """The fewest hops from `start` to `end` with no walls: the window is convex around the character, so
    k equal hops along the line are in view when one k-th of the line is."""
    if math.dist(start, end) < 0.5:
        return 0
    for count in range(1, 400):
        step = (start[0] + (end[0] - start[0]) / count, start[1] + (end[1] - start[1]) / count)
        if view.in_view(view.ground(start, *step)):
            return count
    return 400


def reach_along(view: Viewport, start: Point, toward: Point) -> float:
    """World units the window shows from `start` along the line to `toward`."""
    away = math.dist(start, toward)
    if away == 0:
        return 0.0
    low, high = 0.0, 80.0
    for _ in range(24):
        middle = (low + high) / 2
        point = (start[0] + (toward[0] - start[0]) * middle / away, start[1] + (toward[1] - start[1]) * middle / away)
        low, high = (middle, high) if view.in_view(view.ground(start, *point)) else (low, middle)
    return low


def hops_of(lines: list[str], log: str) -> list[Hop]:
    """Every hop of one probe.log, each with the mark its step named."""
    found: list[Hop] = []
    label, mark, quarry = '', None, None
    for line in lines:
        if match := TOWARD.match(line):
            if not match[3].startswith(HUNTED):
                quarry = None
            label = match[3]
            continue
        if match := DOOR.search(line):
            mark = (float(match[2]), float(match[3]))
            continue
        if match := SPOT.search(line):
            mark, quarry = (float(match[6]), float(match[7])), (float(match[2]), float(match[3]))
            continue
        if match := ROOM.search(line):
            mark = ((int(match[2]) + 0.5) * TILE_UNITS, (int(match[3]) + 0.5) * TILE_UNITS)
            continue
        match = HOP.match(line)
        if match is None:
            continue
        numbers = match.groups()
        landed = LANDED.search(numbers[-1])
        gain = numbers[7]
        found.append(
            Hop(
                log=log,
                stamp=f'{numbers[0]}.{numbers[1]}',
                label=label,
                aim=(float(numbers[2]), float(numbers[3])),
                start=(float(numbers[5]), float(numbers[6])),
                gain=float(gain) if re.fullmatch(NUMBER, gain) else None,
                grids=int(numbers[9]),
                pointer=(int(numbers[10]), int(numbers[11])),
                rect=(int(numbers[12]), int(numbers[13]), int(numbers[14]), int(numbers[15])),
                landed=(float(landed[1]), float(landed[2])) if landed else None,
                mark=mark,
                quarry=quarry,
            )
        )
    return found


def journeys_of(hops: list[Hop]) -> list[Journey]:
    """The hops of one log as journeys: one mark's name, each hop from where the last one ended."""
    found: list[Journey] = []
    for hop in hops:
        last = found[-1].hops[-1] if found else None
        if last is not None and last.label == hop.label and math.dist(last.end, hop.start) <= JOINED:
            found[-1].hops.append(hop)
        else:
            found.append(Journey([hop]))
    return found


def read_logs(root: Path = LOGS) -> list[Journey]:
    found: list[Journey] = []
    for path in sorted(root.glob('*/probe.log')):
        lines = path.read_text(errors='replace').splitlines()
        found.extend(journeys_of(hops_of(lines, str(path))))
    return found


def quantiles(values: list[float]) -> str:
    if not values:
        return 'none'
    ordered = sorted(values)
    high = ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]
    return f'median {statistics.median(ordered):.1f}, p90 {high:.1f}, worst {ordered[-1]:.1f} (n={len(ordered)})'


def local_hours(journey: Journey) -> int:
    """Hours the log's clock is ahead of the UTC stamp in its directory's name."""
    first = journey.hops[0]
    named = datetime.strptime(Path(first.log).parent.name.split('-')[0], '%Y%m%dT%H%M%SZ')
    return round((datetime.fromisoformat(first.stamp) - named).total_seconds() / 3600)


class Levels:
    """The levels the combat recorder kept (runs/combat/<stamp>-<area>/level.json), found again for a
    hop by its time and by its start lying on one of the level's grids."""

    def __init__(self, root: Path = TAKES) -> None:
        self.takes = []
        for manifest in sorted(root.glob('*/manifest.json')):
            found = json.loads(manifest.read_text())
            if (manifest.parent / 'level.json').exists() and found.get('finished_at'):
                began, ended = (
                    datetime.fromisoformat(found[key]).replace(tzinfo=None) for key in ('started_at', 'finished_at')
                )
                self.takes.append((began, ended, manifest.parent))
        self.footings: dict[Path, tuple[Ground, Footing]] = {}

    def of(self, journey: Journey) -> tuple[Path, Ground, Footing] | None:
        at = datetime.fromisoformat(journey.hops[0].stamp) - timedelta(hours=local_hours(journey))
        for began, ended, take in self.takes:
            if began - SLACK <= at <= ended + SLACK:
                if take not in self.footings:
                    level = json.loads((take / 'level.json').read_text())
                    ground = Ground(
                        Walkable(g['x'], g['y'], g['width'], g['height'], g['cells']) for g in level['ground']
                    )
                    self.footings[take] = (ground, Footing(ground))
                ground, footing = self.footings[take]
                if ground.walkable(*journey.start) is not None:
                    return take, ground, footing
        return None


def short_of_doors(journey: Journey) -> list[Hop]:
    """The journey's hops without the last ones beside a door (scenarios/exits has those)."""
    hops = list(journey.hops)
    door = hops[0].mark
    if journey.kind == 'door' and door is not None:
        while hops and math.dist(hops[-1].end, door) < DOOR_ZONE:
            hops.pop()
    return hops


def against_reference(journeys: list[Journey], levels: Levels) -> list[tuple[int, int, Journey, Path]]:
    """(hops made, fewest hops by the reference planner, journey, take) of every journey whose level
    was recorded: from its start to within a tile of where it ended, over the level's real footing."""
    found = []
    for journey in journeys:
        level = levels.of(journey)
        hops = short_of_doors(journey)
        if level is None or not hops:
            continue
        take, _, footing = level
        fewest = HopField(footing, hops[-1].end, hops[0].view).hops(hops[0].start)
        if fewest is not None:
            found.append((len(hops), fewest, journey, take))
    return found


def summary(journeys: list[Journey]) -> list[str]:
    hops = [hop for journey in journeys for hop in journey.hops]
    moved = [hop for hop in hops if hop.landed is not None]
    own = [hop for hop in moved if not hop.hand]
    used = [hop.length / reach_along(hop.view, hop.start, hop.aim) for hop in hops if hop.length > 0]
    gains = [hop.gain for hop in hops if hop.gain is not None]
    lines = [
        f'{len(hops)} hops in {len(journeys)} journeys from {len({hop.log for hop in hops})} logs',
        f'hops that did not move the character: {len(hops) - len(moved)}',
        f"hops with the player's hand on the mouse: {len(moved) - len(own)}",
        f'hop length aimed: {quantiles([hop.length for hop in hops])}',
        f'share of the reach along the hop used: {quantiles(used)}',
        f'"off the way" per hop: {quantiles(gains)}',
        f'landing error, all hops that moved: {quantiles([hop.off for hop in moved if hop.off is not None])}',
        f'landing error, pointer where the macro put it: {quantiles([hop.off for hop in own if hop.off is not None])}',
        f'landings more than {MISSED} off the aim, pointer where the macro put it: '
        f'{sum(1 for hop in own if hop.off is not None and hop.off > MISSED)} of {len(own)}',
    ]
    for kind in ('door', 'hunt', 'explore'):
        some = [journey for journey in journeys if journey.kind == kind]
        if not some:
            continue
        back = sum(journey.turns()[0] for journey in some)
        side = sum(journey.turns()[1] for journey in some)
        lines.append(
            f'{kind}: {len(some)} journeys, {sum(len(j.hops) for j in some)} hops, {sum(j.ideal for j in some)} ideal '
            f'with no walls; hops over that ideal: {quantiles([float(j.over) for j in some])}; '
            f'{back} backward and {side} sideways hops'
        )
    causes: Counter[str] = Counter()
    for journey in journeys:
        causes.update(journey.causes())
    shown = ', '.join(f'{name} {count}' for name, count in causes.most_common())
    lines.append(f'what the log lines show, in hops: {shown}')
    return lines


def describe(journey: Journey, made: int, ideal: int) -> str:
    first = journey.hops[0]
    return (
        f'  {first.log} {first.stamp} {first.label!r}: {made} hops for {journey.straight:.0f} units '
        f'(ideal {ideal}), from ({journey.start[0]:.1f}, {journey.start[1]:.1f}) to '
        f'({journey.end[0]:.1f}, {journey.end[1]:.1f}); {dict(journey.causes())}'
    )


def report(journeys: list[Journey], levels: Levels | None = None) -> str:
    """The evidence as text: the totals, the distributions, the causes and the ten worst journeys;
    the same for the journeys since the planner's last rework; and, where the level was recorded,
    the journeys against the reference planner."""
    lines = ['== every log ==', *summary(journeys)]
    lines.append('the ten journeys furthest over the ideal with no walls:')
    for journey in sorted(journeys, key=lambda j: (-j.over, -len(j.hops)))[:10]:
        lines.append(describe(journey, len(journey.hops), journey.ideal))
    late = [journey for journey in journeys if journey.hops[0].stamp >= REWORKED]
    lines += [f'== since {REWORKED} (one window for the way and the landing) ==', *summary(late)]
    if levels is not None:
        scored = against_reference(journeys, levels)
        made, fewest = sum(row[0] for row in scored), sum(row[1] for row in scored)
        over = Counter(row[0] - row[1] for row in scored)
        lines += [
            '== journeys on recorded levels, against the reference planner (door routes cut 30 units short) ==',
            f'{len(scored)} journeys, {made} hops made, {fewest} by the reference: {made - fewest} over '
            f'({100 * (made - fewest) / max(fewest, 1):.1f}%)',
            f'hops over the reference per journey: {quantiles([float(row[0] - row[1]) for row in scored])}; '
            f'journeys by hops over: {dict(sorted(over.items()))}',
            'the ten journeys furthest over the reference:',
        ]
        for count, ideal, journey, take in sorted(scored, key=lambda row: (row[1] - row[0], -row[0]))[:10]:
            lines.append(f'{describe(journey, count, ideal)} [{take.name}]')
    return '\n'.join(lines)


if __name__ == '__main__':
    print(report(read_logs(Path(sys.argv[1]) if len(sys.argv) > 1 else LOGS), Levels()))

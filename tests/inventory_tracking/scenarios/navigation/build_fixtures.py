"""Cut the route situations out of the recorded takes: where each fixture came from, kept runnable.

A fixture is the whole level of one take (its rooms and their walkable sub-tiles, a few kilobytes
without the flight layer and the raw masks), a start, a mark and the window's shape. The takes are
under inventory_tracking/runs/combat and are not in the repository, so the fixtures are committed and
this module is only run to add or change one:

    uv run --offline python -m tests.inventory_tracking.scenarios.navigation.build_fixtures

A route toward a door stops about 30 units short of it: the last hops beside a door are another
directory's topic (scenarios/exits).
"""

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.levels.model import Room
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.navigation.harness import FIXTURES


Point = tuple[float, float]
TAKES = Path('inventory_tracking/runs/combat')
LOGS = 'inventory_tracking/runs/alt-d'


@dataclass(frozen=True)
class Spec:
    name: str
    take: str
    start: Point
    mark: Point
    note: str
    aspect: float | None = None  # None: the host's window
    hide_at: tuple[Point, ...] = ()  # world points: the rooms holding them are not given to the planner
    journey: str = ''  # '<log directory> <time>' of the recorded journey the route is from
    recorded_hops: int | None = None


SPECS = (
    Spec(
        'recorded-hunt-1848',
        '20261010T154734Z-36',
        (22568.5, 8042.5),
        (22674.5, 8092.5),
        'A hunt across Catacombs 3, down the screen and to the right: the first hop takes 21 of the 25 '
        'units the window shows downward, and the route is the one hop longer for it.',
        journey='20261010T154652Z-2795d203 2026-10-10 18:48:18.489',
        recorded_hops=7,
    ),
    Spec(
        'recorded-door-1837',
        '20261010T153645Z-35',
        (22663.5, 6752.5),
        (22598.5, 6787.5),
        'Toward the stairs of Catacombs 2, cut where the door comes within 30 units: the third hop lands '
        'a tile short of the mark and a fourth, short one follows.',
        journey='20261010T153209Z-8cf6b9de 2026-10-10 18:37:44.228',
        recorded_hops=4,
    ),
    Spec(
        'recorded-hunt-2124',
        '20261010T182405Z-35',
        (22603.5, 6715.5),
        (22625.5, 6774.5),
        'A hunt straight down the screen on the code of the evening of 2026-10-10: 59 units in four hops.',
        journey='20261010T181433Z-e945ba1c 2026-10-10 21:24:38.559',
        recorded_hops=4,
    ),
    Spec(
        'recorded-door-1725',
        '20261010T142541Z-35',
        (22521.5, 6586.5),
        (22563.5, 6813.5),
        'The longest recorded run down a level, eleven hops as the reference has it; the planner of today '
        'makes twelve of the same route.',
        journey='20261010T142454Z-0c433a9f 2026-10-10 17:25:45.577',
        recorded_hops=11,
    ),
    Spec(
        'recorded-door-1658',
        '20261010T135703Z-35',
        (22653.5, 6526.5),
        (22542.5, 6808.5),
        'Thirteen recorded hops across Catacombs 2, and thirteen is the fewest: what a good route looks like.',
        journey='20261010T135554Z-3ccab82a 2026-10-10 16:58:13.351',
        recorded_hops=13,
    ),
    Spec(
        'corner-east',
        '20261010T145344Z-35',
        (22646.5, 6719.5),
        (22760.5, 6664.5),
        'Round a corner of the corridors: the straight line would take six hops with no walls, the footing '
        'allows seven, with a turn of about 80 degrees.',
    ),
    Spec(
        'corner-west',
        '20261010T145344Z-35',
        (22753.5, 6723.5),
        (22623.5, 6696.5),
        'The same corner from the other side: five hops with no walls, seven over the footing.',
    ),
    Spec(
        'u-detour',
        '20261010T153747Z-36',
        (22720.5, 8031.5),
        (22894.5, 8094.5),
        'A U round a slot of the level with no rooms, wider than any hop: down, across and up again, '
        'fifteen hops for a line of ten.',
    ),
    Spec(
        'around-the-void',
        '20261010T145403Z-36',
        (22585.5, 8169.5),
        (22577.5, 8265.5),
        'The mark is 96 units away across a void: the only way is round three sides of it, sixteen hops.',
    ),
    Spec(
        'dead-end',
        '20261010T112329Z-35',
        (22550.5, 6892.5),
        (22559.5, 6701.5),
        'Hops that each land on the footing nearest the mark stop after two, in a pocket with nothing nearer '
        'in view: the way on leads away from the mark first.',
    ),
    Spec(
        'down-the-screen',
        '20261010T153645Z-35',
        (22585.5, 6700.5),
        (22606.5, 6828.5),
        'Straight down the screen, the short side of the window, across a band without footing some 20 '
        'units deep: one hop of 25 units crosses it, the planner goes round.',
    ),
    Spec(
        'down-the-screen-narrow',
        '20261010T153645Z-35',
        (22585.5, 6700.5),
        (22606.5, 6828.5),
        'The same route in a 4:3 window, which shows 24 units to a side where the host shows 32: the way '
        'round is the longer for it.',
        aspect=4 / 3,
    ),
    Spec(
        'up-the-screen',
        '20261010T135922Z-37',
        (22561.5, 9645.5),
        (22538.5, 9536.5),
        'Straight up the screen in Catacombs 4, where the window shows 33 units a hop.',
    ),
    Spec(
        'across-and-back',
        '20261010T183624Z-36',
        (22666.5, 8144.5),
        (22907.5, 8082.5),
        'The worst of 2,640 routes drawn at random over the takes: ten hops by the reference, thirteen by '
        'the planner, one of them onto a spot the reference counts further from the mark than the last.',
    ),
    Spec(
        'last-hop-short',
        '20261010T114636Z-37',
        (22556.5, 9622.5),
        (22540.5, 9569.5),
        'Two hops reach the mark; the second lands a tile and a half short of it and a third, of a few units, follows.',
    ),
    Spec(
        'unloaded-room',
        '20261010T135703Z-35',
        (22653.5, 6526.5),
        (22542.5, 6808.5),
        'The thirteen-hop route with the walls of two rooms on the way not read, as rooms the game had not '
        'loaded: the planner takes their whole rectangles for footing.',
        hide_at=((22620.5, 6620.5), (22590.5, 6700.5)),
    ),
)


def build(spec: Spec) -> dict:
    level = json.loads((TAKES / spec.take / 'level.json').read_text())
    rooms = [Room(**{**room, 'block': room['block'] and tuple(room['block'])}) for room in level['rooms']]
    hidden = sorted(
        index
        for index, room in enumerate(rooms)
        for x, y in spec.hide_at
        if room.x <= x / TILE_UNITS < room.x + room.width and room.y <= y / TILE_UNITS < room.y + room.height
    )
    source = f'{TAKES / spec.take}/level.json'
    if spec.journey:
        log, stamp = spec.journey.split(' ', 1)
        source += f'; journey of {stamp} in {LOGS}/{log}/probe.log'
    found = {
        'area': level['area'],
        'source': source,
        'note': spec.note,
        'start': list(spec.start),
        'mark': list(spec.mark),
        'rooms': [[room.preset, room.x, room.y, room.width, room.height] for room in rooms],
        'ground': [[g['x'], g['y'], g['width'], g['height'], g['cells']] for g in level['ground']],
    }
    if spec.aspect is not None:
        found['aspect'] = spec.aspect
    if hidden:
        found['hidden'] = hidden
    if spec.recorded_hops is not None:
        found['recorded_hops'] = spec.recorded_hops
    return found


def main() -> None:
    FIXTURES.mkdir(exist_ok=True)
    for spec in SPECS:
        text = json.dumps(build(spec), separators=(',', ':'))
        path = FIXTURES / f'{spec.name}.json'
        if len(text) > 200_000:
            with gzip.open(path.with_suffix('.json.gz'), 'wt', encoding='utf-8') as handle:
                handle.write(text)
        else:
            path.write_text(text + '\n')
        print(f'{spec.name}: {len(text) // 1000} KB')


if __name__ == '__main__':
    main()

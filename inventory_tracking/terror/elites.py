"""Elite groups of a level: how many were killed, how many are known alive, out of how many.

A level's elite groups are of two sorts (terror/data/elites.json, built by build_elites.py):
random ones, a number the game rolls within the level's range and places as rooms come alive,
so where the unseen ones are is not known; and fixed ones on top, placed by the level's map
pieces (a super unique, a unique pack or a champion group at a spot of the piece) or spawned
by a script (seal bosses, Baal's waves). The client holds every room of the level with its
piece from entry on, so the fixed ones are known before they are seen.

A group is a unique with its minions, a super unique, or the champions of one type that stood
together when first seen (3,023 champions of the probe logs to 2026-10-06 each had another of
their type within 10 units). A unique or champion group first seen at a fixed spot is that
spot's group; every super unique is fixed. The ranges are Hell's. Pure data and arithmetic.
"""

import json
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from inventory_tracking.native.layout import TILE_UNITS


DATA = Path(__file__).parent / 'data' / 'elites.json'
CHAMPION_LINK = 15  # world units between champions of one group at first sight
SPOT_REACH = 25  # world units from a fixed spot to the group first seen there (seen: up to 21)


@dataclass(frozen=True)
class Table:
    levels: dict[int, tuple[int, int]]  # area -> the fewest and the most random groups
    presets: dict[tuple[int, int], tuple[tuple[str, str, int, int], ...]]  # (Def, variant) -> kind, name, x, y
    scripted: dict[int, tuple[str, ...]]  # area -> super uniques a script spawns
    supers: dict[int, str]  # superuniques.txt hcIdx -> name


@cache
def table(path: Path = DATA) -> Table:
    data = json.loads(path.read_text(encoding='utf-8'))
    presets = {
        (int(preset), int(variant)): tuple((kind, name, x, y) for kind, name, x, y in groups)
        for preset, variants in data['presets'].items()
        for variant, groups in variants.items()
    }
    return Table(
        {int(area): (low, high) for area, (low, high) in data['levels'].items()},
        presets,
        {int(area): tuple(names) for area, names in data['scripted'].items()},
        {int(found): name for found, name in data['supers'].items()},
    )


@dataclass(frozen=True)
class Fixed:
    kind: str  # 'super', 'unique' or 'champion'
    name: str  # a super unique's
    x: float | None = None  # world units; None: spawned by a script
    y: float | None = None


@dataclass(frozen=True)
class Sighting:
    """A pack leader as first seen: a unique, a super unique or one champion."""

    unit_id: int
    kind: str  # 'unique', 'super' or 'champion'
    txt_id: int
    x: float
    y: float
    name: str | None = None  # a super unique's
    dead: bool = False


@dataclass(frozen=True)
class Tally:
    killed: int  # random groups
    alive: int
    expected: tuple[int, int] | None  # the level's range of random groups
    fixed_killed: int
    fixed_alive: int
    fixed_total: int


def fixed_groups(area: int, rooms, elites: Table | None = None) -> list[Fixed]:
    """The level's fixed groups, from its rooms' pieces and its scripts. A piece whose file is
    not read yet counts as its first one; a super unique a piece names at several spots, or
    several pieces name, is one group."""
    elites = elites or table()
    found: list[Fixed] = []
    pieces, named = set(), set()
    for room in rooms:
        origin = room.block[:2] if room.block else (room.x, room.y)
        if (room.preset, origin) in pieces:
            continue
        pieces.add((room.preset, origin))
        variant = room.variant
        if variant is None:
            variant = min((v for preset, v in elites.presets if preset == room.preset), default=0)
        for kind, name, x, y in elites.presets.get((room.preset, variant), ()):
            if kind == 'super' and name in named:
                continue
            named.add(name)
            found.append(Fixed(kind, name, origin[0] * TILE_UNITS + x, origin[1] * TILE_UNITS + y))
    found += [Fixed('super', name) for name in elites.scripted.get(area, ()) if name not in named]
    return found


def champion_groups(champions) -> list[list[Sighting]]:
    """Champions of one type within CHAMPION_LINK of another of the group are one group."""
    groups: list[list[Sighting]] = []
    left = list(champions)
    while left:
        group, queue = [], [left.pop(0)]
        while queue:
            member = queue.pop()
            group.append(member)
            near = [
                other
                for other in left
                if other.txt_id == member.txt_id and math.hypot(other.x - member.x, other.y - member.y) <= CHAMPION_LINK
            ]
            for other in near:
                left.remove(other)
            queue += near
        groups.append(group)
    return groups


def tally(area: int, rooms, sightings, elites: Table | None = None) -> Tally:
    elites = elites or table()
    sightings = list(sightings)
    fixed = fixed_groups(area, rooms, elites)
    supers = {s.name or f'super unique {s.unit_id}': s.dead for s in sightings if s.kind == 'super'}
    fixed_names = {group.name for group in fixed if group.kind == 'super'}
    states = [supers.get(name) for name in fixed_names | set(supers)]  # True killed, False alive, None unseen
    groups = [('unique', [s]) for s in sightings if s.kind == 'unique']
    groups += [('champion', group) for group in champion_groups(s for s in sightings if s.kind == 'champion')]
    taken: set[int] = set()
    for spot in fixed:
        if spot.kind == 'super' or spot.x is None or spot.y is None:
            continue
        reach, index = min(
            (
                (min(math.hypot(s.x - spot.x, s.y - spot.y) for s in members), index)
                for index, (kind, members) in enumerate(groups)
                if kind == spot.kind and index not in taken
            ),
            default=(math.inf, -1),
        )
        if reach <= SPOT_REACH:
            taken.add(index)
            states.append(all(s.dead for s in groups[index][1]))
        else:
            states.append(None)
    free = [all(s.dead for s in members) for index, (_kind, members) in enumerate(groups) if index not in taken]
    return Tally(
        sum(free),
        len(free) - sum(free),
        elites.levels.get(area),
        sum(state is True for state in states),
        sum(state is False for state in states),
        len(states),
    )


def line(found: Tally) -> str | None:
    """'Elites: 3 killed · 2 alive of 7-9 · fixed: 1 killed of 3'; None where there are none."""
    parts = []
    if found.expected or found.killed or found.alive:
        text = f'{found.killed} killed · {found.alive} alive'
        if found.expected:
            low, high = found.expected
            text += f' of {low}-{high}' if low != high else f' of {low}'
        parts.append(text)
    if found.fixed_total:
        alive = f' · {found.fixed_alive} alive' if found.fixed_alive else ''
        parts.append(f'fixed: {found.fixed_killed} killed{alive} of {found.fixed_total}')
    return 'Elites: ' + ' · '.join(parts) if parts else None

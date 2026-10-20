"""Current active Terror Zone combinations from the installed game's zone table.

Town memory decides which group is active. This table identifies that group and
its full level set; it does not predict the rotation or authorize travel.

The table's `manual_zones` are the five acts a Worldstone Shard terrorizes for a game, on top of the rotation
(rca/2026-10-20/act-terrorize-findings.md §1); `match_zones` reads an act and the rotation together.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from inventory_tracking.terror.zones import GROUPS, group_of


GAME_TABLE = Path(__file__).resolve().parents[2] / 'terror_zones/data/desecratedzones-game.json'


@dataclass(frozen=True)
class ActiveZone:
    name: str
    areas: tuple[int, ...]
    core: frozenset[int]
    unreported: tuple[int, ...] = ()


@cache
def installed_active_zones() -> tuple[ActiveZone, ...]:
    """Load every regular RotW active combination from the extracted game file."""
    configurations = json.loads(GAME_TABLE.read_text(encoding='utf-8'))['desecrated_zones']
    if len(configurations) != 1:
        raise ValueError('installed active TZ configuration is ambiguous')
    known = {group.zone: set() for group in GROUPS}
    for group in GROUPS:
        known[group.zone].update(group.areas)
    zones = []
    for row in configurations[0]['zones']:
        name = row['id']
        areas = tuple(level['level_id'] for level in row['levels'])
        core = frozenset(known.get(name, ()))
        if not areas or len(set(areas)) != len(areas) or not core or not core.issubset(areas):
            raise ValueError(f'invalid installed active TZ group: {name}')
        zones.append(ActiveZone(name, areas, core))
    if len({zone.name for zone in zones}) != len(zones) or len({zone.areas for zone in zones}) != len(zones):
        raise ValueError('duplicate installed active TZ group')
    return tuple(zones)


def match_active_zone(observed: frozenset[int]) -> ActiveZone | None:
    """Match one complete group; only levels without Herald counters may be absent."""
    matches = [
        zone for zone in installed_active_zones() if zone.core.issubset(observed) and observed.issubset(zone.areas)
    ]
    if len(matches) != 1:
        return None
    zone = matches[0]
    return replace(zone, unreported=tuple(area for area in zone.areas if area not in observed))


@cache
def installed_manual_zones() -> tuple[ActiveZone, ...]:
    """The five acts a Worldstone Shard terrorizes (`manual_zones`, Act1-Manual ... Act5-Manual), in act order. `core`:
    the levels of a Herald group, the ones the tracker can read (terror/tracker.py `terrorized`); the others (the
    Forgotten Tower 20, Valley of Snakes 45, Harem 1 50, Duriel's Lair 73, the Worldstone Chamber 132) are terrorized
    too but never read (findings §1 #7)."""
    configurations = json.loads(GAME_TABLE.read_text(encoding='utf-8'))['desecrated_zones']
    if len(configurations) != 1:
        raise ValueError('installed active TZ configuration is ambiguous')
    groups = sorted(configurations[0]['manual_zones'], key=lambda group: group['group_id'])
    zones = []
    for group in groups:
        for row in group['zones']:
            areas = tuple(level['level_id'] for level in row['levels'])
            core = frozenset(area for area in areas if group_of(area) is not None)
            if not areas or len(set(areas)) != len(areas) or not core:
                raise ValueError(f'invalid installed manual TZ group: {row["id"]}')
            zones.append(ActiveZone(row['id'], areas, core))
    if [zone.name for zone in zones] != [f'Act{act}-Manual' for act in range(1, 6)]:
        raise ValueError('the installed manual TZ groups are not the five acts')
    return tuple(zones)


def manual_zone(act: int) -> ActiveZone | None:
    """Act `act`'s manual zone (1-5); None for any other number."""
    zones = installed_manual_zones()
    return zones[act - 1] if 1 <= act <= len(zones) else None


def act_of_manual(zone: ActiveZone) -> int | None:
    """The act (1-5) of a manual zone; None for a rotating zone."""
    return next((act for act, each in enumerate(installed_manual_zones(), 1) if each.name == zone.name), None)


def match_zones(observed: frozenset[int]) -> tuple[ActiveZone, ...]:
    """Every terrorized zone `observed` reads, the acts first: each act whose core is all observed (a Worldstone
    Shard's), then every rotating zone whose core is all observed among the levels left. The player, 2026-10-20 ~19:00:
    "for TZ/TZ+ modes we want to know how to handle whole terrorized act (when we terrorized it manually with stone)".

    A partly read act is no act: its groups are read one by one when the client's list does not hold it (its plain
    monsters' votes, findings §1 #14), and each group wholly read is a zone to play meanwhile (one rotating zone alone
    is today's match). A level of no group wholly read is left out (logged by tzroutine.py `itinerary`). Nothing read:
    `()` (`match_active_zone`'s None)."""
    acts = [
        replace(zone, unreported=tuple(area for area in zone.areas if area not in observed))
        for zone in installed_manual_zones()
        if zone.core.issubset(observed)
    ]
    rest = observed.difference(*(zone.areas for zone in acts))
    rotating = [
        replace(zone, unreported=tuple(area for area in zone.areas if area not in rest))
        for zone in installed_active_zones()
        if zone.core.issubset(rest)
    ]
    return (*acts, *rotating)

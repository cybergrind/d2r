"""Current active Terror Zone combinations from the installed game's zone table.

Town memory decides which group is active. This table identifies that group and
its full level set; it does not predict the rotation or authorize travel.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

from inventory_tracking.terror.zones import GROUPS


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

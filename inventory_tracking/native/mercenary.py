"""Act 2 mercenary selection and approximate health from client monster stats."""

import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from inventory_tracking.native.layout import DEAD_MODES, HIRELING_CLASS_ID, LIFE_FRACTION_MAX, LIFE_STAT, MAX_LIFE_STAT
from inventory_tracking.native.units import read_stats


def describe_monster(read: Callable[[int, int], bytes], unit: dict[str, Any]) -> dict[str, Any]:
    if unit['txt_id'] != HIRELING_CLASS_ID:
        return {'not_mercenary': True}
    result: dict[str, Any] = {}
    for name, offset in [('base_stats', 0x30), ('full_stats', 0xE8)]:
        try:
            result[name] = read_stats(read, unit['stats_pointer'] + offset)
        except (OSError, ValueError) as exc:
            result[name] = {'error': str(exc)}
    # Bounded fields for finding the player-owner association in this build.
    header = read(unit['address'], 0x200)
    data = read(unit['data_pointer'], 0x100) if unit['data_pointer'] else bytes(0x100)
    result['unit_u32'] = list(struct.unpack('<128I', header))
    result['monster_data_u32'] = list(struct.unpack('<64I', data))
    return result


@dataclass(frozen=True)
class Mercenary:
    unit_id: int
    # Hit-point estimates from the life fraction; the fraction itself drives thresholds.
    current_raw: int
    maximum_raw: int
    life_fraction_raw: int
    alive: bool


def select_mercenary(monsters: list[dict[str, Any]], player_id: int) -> Mercenary | None:
    # Owner association at monster_data u32[21] verified against controlled probes on 2026-09-21.
    candidates = [
        m
        for m in monsters
        if m['txt_id'] == HIRELING_CLASS_ID
        and len(m['details'].get('monster_data_u32', [])) > 21
        and m['details']['monster_data_u32'][21] == player_id
    ]
    if len(candidates) != 1:
        return None
    unit = candidates[0]
    stats = unit['details'].get('full_stats')
    if not isinstance(stats, list):
        return None
    life = [s['raw'] for s in stats if s['id'] == LIFE_STAT and s['layer'] == 0]
    maximum = [s['raw'] for s in stats if s['id'] == MAX_LIFE_STAT and s['layer'] == 0]
    if len(life) != 1 or len(maximum) != 1 or not 0 <= life[0] <= LIFE_FRACTION_MAX or maximum[0] <= 0:
        return None
    alive = life[0] > 0 and unit['mode'] not in DEAD_MODES
    estimate = maximum[0] * life[0] // LIFE_FRACTION_MAX if alive else 0
    return Mercenary(unit['unit_id'], estimate, maximum[0], life[0], alive)

"""Mercenary location research; ownership fields are candidates until verified."""

import struct
from dataclasses import dataclass

from .units import read_stats


def describe_monster(read, unit):
    if unit['txt_id'] != 338:
        return {'not_mercenary': True}
    result = {}
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
    current_raw: int
    maximum_raw: int
    life_fraction_raw: int
    alive: bool


def select_mercenary(monsters, player_id):
    # Act 2 hireling 338 verified against d2data monstats on 2026-09-21.
    candidates = [
        m
        for m in monsters
        if m['txt_id'] == 338
        and len(m['details'].get('monster_data_u32', [])) > 21
        and m['details']['monster_data_u32'][21] == player_id
    ]
    if len(candidates) != 1:
        return None
    unit = candidates[0]
    stats = unit['details'].get('full_stats')
    if not isinstance(stats, list):
        return None
    life = [s['raw'] for s in stats if s['id'] == 6 and s['layer'] == 0]
    maximum = [s['raw'] for s in stats if s['id'] == 7 and s['layer'] == 0]
    if len(life) != 1 or len(maximum) != 1 or not 0 <= life[0] <= 32768 or maximum[0] <= 0:
        return None
    alive = life[0] > 0 and unit['mode'] not in (0, 12)
    return Mercenary(unit['unit_id'], maximum[0] * life[0] // 32768 if alive else 0, maximum[0], life[0], alive)

"""Render a single captured poison source; retain mixed-source cases for review."""

from typing import Any


POISON_STATS = frozenset((57, 58, 59, 326))
FRAMES_PER_SECOND = 25
DAMAGE_SCALE = 256


def combine_poison(decoded) -> list[dict[str, Any]]:
    components = [r for r in decoded if r.get('memory_stat', {}).get('id') in POISON_STATS]
    stats = [r['memory_stat'] for r in components]
    if len(stats) != 4 or {s['id'] for s in stats} != POISON_STATS:
        return decoded
    if any(s['layer'] or type(s['raw']) is not int or s['raw'] <= 0 for s in stats):
        return decoded
    values = {s['id']: s['raw'] for s in stats}
    if values[326] != 1 or values[57] > values[58] or values[59] % FRAMES_PER_SECOND:
        return decoded
    # Native rates are 1/256 damage per frame. Tooltip integer rounding and
    # 25-fps duration verified with captured Atma's Scarab: 102,102,100,1 -> 40/4s.
    low = (values[57] * values[59] + DAMAGE_SCALE // 2) // DAMAGE_SCALE
    high = (values[58] * values[59] + DAMAGE_SCALE // 2) // DAMAGE_SCALE
    damage = str(low) if low == high else f'{low}-{high}'
    combined = {
        'status': 'decoded',
        'name': 'poison_damage',
        'memory_stats': stats,
        'native_values': {
            '57:0': {'value': values[57] / DAMAGE_SCALE, 'unit': 'damage_per_frame'},
            '58:0': {'value': values[58] / DAMAGE_SCALE, 'unit': 'damage_per_frame'},
            '59:0': {'value': values[59] / FRAMES_PER_SECOND, 'unit': 'seconds'},
            '326:0': {'value': values[326], 'unit': 'count'},
        },
        'text': f'+{damage} Poison Damage over {values[59] // FRAMES_PER_SECOND} Seconds',
    }
    result = []
    for row in decoded:
        if row is components[0]:
            result.append(combined)
        elif row not in components:
            result.append(row)
    return result

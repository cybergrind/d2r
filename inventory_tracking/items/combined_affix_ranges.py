"""Joint ranges for captured additive affixes, without guessing contribution splits."""

from itertools import product
from math import prod

from inventory_tracking.items.identity import FLAGS_OFFSET, SOCKETED_FLAG


# Native property mappings verified in d2data properties.json. Flat damage/defense,
# poison, charged skills and per-level properties have different total semantics.
ADDITIVE_PROPERTIES = {
    '39': frozenset(('res-all', 'res-fire')),
    '41': frozenset(('res-all', 'res-ltng')),
    '43': frozenset(('res-all', 'res-cold')),
    '45': frozenset(('res-all', 'res-pois')),
    '80': frozenset(('mag%',)),
}


def uncontaminated_by_sockets(raw, arrays):
    scan = arrays.get('socket_items', {})
    if scan.get('children'):
        return False
    socketed = int.from_bytes(raw[FLAGS_OFFSET : FLAGS_OFFSET + 4], 'little') & SOCKETED_FLAG
    socketed = socketed or any(
        stat.get('id') == 194 and stat.get('raw') != 0
        for array in arrays.get('arrays', [])
        for stat in array.get('stats', [])
    )
    return not socketed or (scan.get('complete') is True and scan.get('children') == [])


def valid_bounds(row):
    return (
        isinstance(row, dict)
        and type(row.get('min')) is int
        and type(row.get('max')) is int
        and 0 <= row['min'] <= row['max']
    )


def combined_scalar_ranges(entries, pool):
    result = {}
    keys = {key: (int(key), 0, properties) for key, properties in ADDITIVE_PROPERTIES.items()}
    # A native skill-tab prefix and inherent Amazon bonus are additive only for
    # the same tab. Preserve the parameter through validation and annotation.
    for entry in entries:
        for key in entry['roll_ranges']:
            if not isinstance(key, str) or not key.startswith('188:'):
                continue
            parameter = key.removeprefix('188:')
            if parameter.isdecimal() and str(int(parameter)) == parameter and 0 <= int(parameter) <= 65535:
                keys[key] = (188, int(parameter), frozenset(('skilltab',)))
    for stat, (stat_id, layer, properties) in keys.items():
        contributors = [entry for entry in entries if stat in entry['roll_ranges']]
        if not 2 <= len(contributors) <= 6:
            continue
        groups = [(e['affix_table'], e.get('game_definition', {}).get('group')) for e in contributors]
        if any(type(group) is not int or group <= 0 for _, group in groups) or len(set(groups)) != len(groups):
            continue
        definitions = [e['roll_ranges'][stat] for e in contributors]
        if any(
            not valid_bounds(row)
            or row.get('stat_id') != stat_id
            or row.get('property') not in properties
            or row.get('layer', 0) != layer
            or row.get('better', 'higher') != 'higher'
            for row in definitions
        ):
            continue
        pools = [pool(e, stat) for e in contributors]
        if any(
            not valid_bounds(p.get('range'))
            or not p.get('tiers')
            or not all(valid_bounds(t) for t in p['tiers'])
            or {'min': d['min'], 'max': d['max']} not in p['tiers']
            or p['range'] != {'min': min(t['min'] for t in p['tiers']), 'max': max(t['max'] for t in p['tiers'])}
            for p, d in zip(pools, definitions, strict=True)
        ):
            continue
        # Corrupt metadata must not produce unbounded Cartesian products.
        if prod(len(p['tiers']) for p in pools) > 4096:
            continue
        tiers = {
            (sum(t['min'] for t in combination), sum(t['max'] for t in combination))
            for combination in product(*(p['tiers'] for p in pools))
        }
        result[stat] = {
            'stat_id': stat_id,
            **({'layer': layer} if stat_id == 188 else {}),
            'min': sum(d['min'] for d in definitions),
            'max': sum(d['max'] for d in definitions),
            'properties': [d['property'] for d in definitions],
            'better': 'higher',
            'affixes': [e['name'] for e in contributors],
            'affix_ids': [e['table_id'] for e in contributors],
            'source': [e['source'] for e in contributors],
            'quality_range': {key: sum(p['range'][key] for p in pools) for key in ('min', 'max')},
            'tiers': [
                {'min': low, 'max': high} for low, high in sorted(tiers, key=lambda t: (t[1], t[0]), reverse=True)
            ],
        }
    return result

"""Add flat-damage bounds only for a verified magic charm prefix/suffix pair."""

from itertools import product


CHARM_TYPES = frozenset(('scha', 'mcha', 'lcha'))
DAMAGE_PROPERTIES = {
    '21': 'dmg-min',
    '23': 'dmg-min',
    '159': 'dmg-min',
    '22': 'dmg-max',
    '24': 'dmg-max',
    '160': 'dmg-max',
}


def _bounds(value):
    return (
        isinstance(value, dict)
        and type(value.get('min')) is int
        and type(value.get('max')) is int
        and 0 <= value['min'] <= value['max']
    )


def combined_damage_ranges(entries, base, quality, pool):
    if quality != 4 or base.get('type') not in CHARM_TYPES:
        return {}
    result = {}
    for stat, prop in DAMAGE_PROPERTIES.items():
        contributors = [entry for entry in entries if stat in entry['roll_ranges']]
        if len(contributors) != 2 or {entry['affix_table'] for entry in contributors} != {'prefix', 'suffix'}:
            continue
        contributors.sort(key=lambda entry: entry['affix_table'])
        groups = [entry.get('game_definition', {}).get('group') for entry in contributors]
        if any(type(group) is not int or group <= 0 for group in groups) or groups[0] == groups[1]:
            continue
        definitions = [entry['roll_ranges'][stat] for entry in contributors]
        if any(
            not _bounds(row) or row.get('property') != prop or row.get('stat_id') != int(stat) for row in definitions
        ):
            continue
        pools = [pool(entry, stat) for entry in contributors]
        if any(
            not _bounds(p.get('range')) or not p.get('tiers') or not all(_bounds(t) for t in p['tiers']) for p in pools
        ):
            continue
        tiers = {
            (sum(part['min'] for part in pair), sum(part['max'] for part in pair))
            for pair in product(*(p['tiers'] for p in pools))
        }
        result[stat] = {
            'stat_id': int(stat),
            'min': sum(row['min'] for row in definitions),
            'max': sum(row['max'] for row in definitions),
            'property': prop,
            'better': 'higher',
            'affixes': [entry['name'] for entry in contributors],
            'affix_ids': [entry['table_id'] for entry in contributors],
            'source': [entry['source'] for entry in contributors],
            'quality_range': {key: sum(p['range'][key] for p in pools) for key in ('min', 'max')},
            'tiers': [
                {'min': low, 'max': high}
                for low, high in sorted(tiers, key=lambda pair: (pair[1], pair[0]), reverse=True)
            ],
        }
    return result

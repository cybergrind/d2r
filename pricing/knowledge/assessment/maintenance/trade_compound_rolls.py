"""Native proof and independent axes for explicitly reviewed shared rolls."""

from itertools import product

from pricing.knowledge.assessment.policies.trade_rolls import (
    ALL_ATTRIBUTE_KEYS,
    ALL_RESISTANCE_KEYS,
    ENHANCED_DAMAGE_KEYS,
)


# Native property and each member's name, market property and operation.
COMPOUND_SPECS = {
    'enhanced_damage': (
        'dmg%',
        {
            17: ('item_maxdamage_percent', None, 13),
            18: ('item_mindamage_percent', None, 13),
        },
    ),
    'all_resistances': (
        'res-all',
        {
            39: ('fireresist', '427', 0),
            41: ('lightresist', '428', 0),
            43: ('coldresist', '426', 0),
            45: ('poisonresist', '401', 0),
        },
    ),
    # D2MOO D2StatList.cpp cases8/9 affect player mana/life/stamina totals;
    # the captured item Energy/Vitality modifiers retain their integer rolls.
    'all_attributes': (
        'all-stats',
        {
            0: ('strength', '437', 0),
            1: ('energy', '421', 8),
            2: ('dexterity', '429', 0),
            3: ('vitality', '582', 9),
        },
    ),
}
GROUPS = {
    'enhanced_damage': ENHANCED_DAMAGE_KEYS,
    'all_resistances': ALL_RESISTANCE_KEYS,
    'all_attributes': ALL_ATTRIBUTE_KEYS,
}


def _verified_group(definition, stat_specs, compound):
    prop, members = COMPOUND_SPECS[compound]
    rows = [r for r in definition.get('roll_ranges', {}).values() if r.get('property') == prop]
    if len(rows) != len(members) or {r.get('stat_id') for r in rows} != members.keys():
        return False
    if len({(r.get('min'), r.get('max')) for r in rows}) != 1:
        return False
    for row in rows:
        name, market, operation = members[row['stat_id']]
        spec = stat_specs.get(str(row['stat_id']), {})
        if (
            row.get('layer', 0) != 0
            or spec.get('name') != name
            or spec.get('op') != operation
            or spec.get('op_base') is not None
            or spec.get('property_id') != market
            or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        ):
            return False
    low, high = rows[0].get('min'), rows[0].get('max')
    if type(low) is not int or type(high) is not int or low >= high:
        return False
    if compound in ('all_resistances', 'all_attributes'):
        # Equal ranges alone do not establish one shared property roll.
        game = definition.get('game_definition', {})
        slots = [k.removeprefix('prop') for k, v in game.items() if k.startswith('prop') and v == prop]
        if len(slots) != 1 or (game.get('min' + slots[0]), game.get('max' + slots[0])) != (low, high):
            return False
    return True


def verified_definition(definition, stat_specs, compounds):
    if not compounds or len(compounds) != len(set(compounds)) or set(compounds) - COMPOUND_SPECS.keys():
        return False
    keys = grouped_keys(compounds)
    return len(keys) == len(set(keys)) and all(_verified_group(definition, stat_specs, c) for c in compounds)


def grouped_keys(compounds):
    return tuple(key for compound in compounds for key in GROUPS.get(compound, ()))


def agree(keys, vector, compounds):
    values = dict(zip(keys, vector, strict=True))
    return all(all(values[key] == values[group[0]] for key in group) for c in compounds if (group := GROUPS.get(c)))


def legal_vectors(keys, points, compounds):
    representative = dict(zip(keys, keys, strict=True))
    for compound in compounds:
        group = GROUPS[compound]
        representative.update(dict.fromkeys(group, group[0]))
    axes = tuple(dict.fromkeys(representative[key] for key in keys))
    partitions = {axis: set() for axis in axes}
    for key in keys:
        partitions[representative[key]].update(points[key])
    for values in product(*(sorted(partitions[axis]) for axis in axes)):
        selected = dict(zip(axes, values, strict=True))
        yield tuple(selected[representative[key]] for key in keys)


def mismatched_vectors(keys, maxima, bounds, compounds):
    for key in grouped_keys(compounds):
        values = list(maxima)
        values[keys.index(key)] = bounds[key][0]
        yield tuple(values)

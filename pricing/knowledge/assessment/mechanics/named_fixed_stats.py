"""Verified fixed native bonuses which have no market property.

Only reviewed, unshifted, layer-zero modifiers belong here. Native ac-hth uses
PropertyFunc01 and armorclass_vs_hth; unlike total defense it has no base armor
contribution. Exact named identity guarantees this fixed bonus in a comparison.
Variable rolls and unreviewed stats must retain their mapping gaps.
"""

FIXED_SCALARS = {33: 'ac-hth', 157: 'magicarrow', 158: 'explosivearrow'}


def fixed_scalar_keys(facts, definition):
    consumed, gaps = set(), []
    record = definition.get('game_definition', {})
    for spec in definition.get('roll_ranges', {}).values():
        stat = spec['stat_id']
        if stat not in FIXED_SCALARS:
            continue
        prop = FIXED_SCALARS[stat]
        key = f'{stat}:{spec.get("layer", 0)}'
        slots = [i for i in range(1, 13) if record.get(f'prop{i}') == prop]
        row = facts.stats.get(key, {})
        if row.get('market_property') is not None:
            continue  # Existing verified market projection retains ownership.
        expected = spec['min']
        if (
            spec.get('layer', 0) != 0
            or spec.get('property') != prop
            or type(expected) is not int
            or expected != spec['max']
            or len(slots) != 1
            or record.get(f'min{slots[0]}') != expected
            or record.get(f'max{slots[0]}') != expected
            or row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != expected
            or type(row.get('value')) is not int
            or row['value'] != expected
            or row.get('market_property') is not None
        ):
            gaps.append(f'Named fixed modifier {key} is missing, changed or unverified.')
        else:
            consumed.add(key)
    return consumed, gaps


def fixed_repair_keys(facts, definition):
    """PropertyFunc17 takes rep-dur's parameter as the native repair rate.

    The displayed integer seconds lose information, so compare both the native
    rate and its decoded seconds. Do not manufacture a market property for it.
    """
    record = definition.get('game_definition', {})
    slots = [i for i in range(1, 13) if record.get(f'prop{i}') == 'rep-dur']
    if not slots:
        return set(), []
    rate = record.get(f'par{slots[0]}')
    row = facts.stats.get('252:0', {})
    if (
        len(slots) != 1
        or type(rate) is not int
        or not 0 < rate <= 100
        or row.get('status') != 'decoded'
        or type(row.get('raw')) is not int
        or row['raw'] != rate
        or type(row.get('value')) is not int
        or row['value'] != 100 // rate
        or row.get('market_property') is not None
    ):
        return set(), ['Named fixed repair rate 252:0 is missing, changed or unverified.']
    return {'252:0'}, []


def fixed_magic_damage_keys(facts, definition):
    """Native dmg-mag functions15/16 set fixed min/max damage endpoints.

    These are not independent rolls between min and max. Named identity fixes
    both endpoints; absence of a market field never proves the captured values.
    """
    record = definition.get('game_definition', {})
    slots = [i for i in range(1, 13) if record.get(f'prop{i}') == 'dmg-mag']
    if not slots:
        return set(), []
    low = record.get(f'min{slots[0]}')
    high = record.get(f'max{slots[0]}')
    error = ['Named fixed magic damage endpoints are missing, changed or unverified.']
    if len(slots) != 1 or type(low) is not int or type(high) is not int or not 0 < low <= high:
        return set(), error
    for stat, expected in ((52, low), (53, high)):
        row = facts.stats.get(f'{stat}:0', {})
        if (
            row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != expected
            or type(row.get('value')) is not int
            or row['value'] != expected
            or row.get('market_property') is not None
        ):
            return set(), error
    return {'52:0', '53:0'}, []

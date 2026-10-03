"""Verify fixed nonweapon damage replicated by native property functions05/06.

Armor has no weapon damage total to mix with these bonuses. Functions05/06 write
primary, secondary and throwing channels together; dmg-norm functions15/16 call
those same functions with fixed endpoints. Throwing weapons require separate
base/ethereal/enhanced-damage proof and cannot use this invariant.
"""

ARMOR_FAMILIES = frozenset({'helm', 'armor', 'shield', 'accessory'})
MINIMUM_STATS = (21, 23, 159)
MAXIMUM_STATS = (22, 24, 160)


def fixed_armor_damage_keys(facts, definition, family):
    if family not in ARMOR_FAMILIES:
        return set(), []
    record = definition.get('game_definition', {})
    expected = {}
    error = ['Named flat armor damage is missing, changed or unverified.']
    for i in range(1, 13):
        prop = record.get(f'prop{i}')
        if prop not in ('dmg-min', 'dmg-max', 'dmg-norm'):
            continue
        low, high = record.get(f'min{i}'), record.get(f'max{i}')
        if (
            type(low) is not int
            or type(high) is not int
            or not 0 <= low <= high
            or (prop != 'dmg-norm' and low != high)
        ):
            return set(), error
        values = (
            ((MINIMUM_STATS, low), (MAXIMUM_STATS, high))
            if prop == 'dmg-norm'
            else (((MINIMUM_STATS if prop == 'dmg-min' else MAXIMUM_STATS), low),)
        )
        for stats, value in values:
            if value:
                for stat in stats:
                    expected[stat] = expected.get(stat, 0) + value
    for stat, value in expected.items():
        row = facts.stats.get(f'{stat}:0', {})
        if (
            row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != value
            or type(row.get('value')) is not int
            or row['value'] != value
        ):
            return set(), error
    return {f'{stat}:0' for stat in expected if facts.stats[f'{stat}:0'].get('market_property') is None}, []

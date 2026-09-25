"""Validate recipe rolls using known rune and base contributions."""

import math

from inventory_tracking.items.metadata import metadata


# Native integer modifiers; exclude defense, enhanced damage/defense, staffmods,
# resistances and attack rating, which need base/contribution-aware validation.
BOUNDED_STATS = frozenset(
    {
        9,
        36,
        60,
        62,
        93,
        97,
        99,
        105,
        127,
        136,
        142,
        143,
        144,
        147,
        148,
        151,
        329,
        330,
        331,
        332,
        333,
        334,
        335,
        336,
        357,
    }
)


def variable_roll_gaps(facts, definition, family):
    gaps = []
    contributions = definition.get('socket_bonus_ranges', {}).get(family, {})
    for key, spec in definition.get('roll_ranges', {}).items():
        native_key = f'{spec["stat_id"]}:{spec.get("layer", 0)}'
        enhancement = spec['stat_id'] in (16, 17, 18) and family in ('weapon', 'armor', 'helm')
        if spec['min'] == spec['max'] and not (enhancement and native_key in facts.stats):
            continue
        row = facts.stats.get(native_key, {})
        value = row.get('value')
        if row.get('status') != 'decoded' or type(value) not in (int, float) or not math.isfinite(value):
            gaps.append(f'Runeword roll {key} was not captured.')
        elif enhancement:
            gaps.extend(enhancement_gaps(facts, spec, contributions.get(key, {}), value, family))
        elif spec['stat_id'] in BOUNDED_STATS:
            rune = contributions.get(key, {})
            low = spec['min'] + rune.get('min', 0)
            high = spec['max'] + rune.get('max', 0)
            if value != int(value) or not low <= value <= high:
                gaps.append(f'Runeword roll {native_key} is outside its possible integer range {low}-{high}.')
    return [*gaps, *resistance_gaps(facts, definition, family)]


def resistance_gaps(facts, definition, family):
    keys = [str(stat) for stat in (39, 41, 43, 45) if f'{stat}:0' in facts.stats]
    if not keys:
        return []
    recipes = definition.get('roll_ranges', {})
    options = definition.get('base_resistance_options', {}).get(facts.base_code)
    if options is None:
        return ['Runeword base resistance contributions are unverified.']
    runes = definition.get('socket_bonus_ranges', {}).get(family, {})
    possible = set(options)
    shared = []
    for key in keys:
        spec = recipes.get(key, {'min': 0, 'max': 0})
        row = facts.stats.get(f'{key}:0', {})
        value = row.get('value')
        if row.get('status') != 'decoded' or type(value) not in (int, float) or not math.isfinite(value):
            return [f'Captured runeword resistance {key}:0 is invalid or undecoded.']
        rune = runes.get(key, {'min': 0, 'max': 0})
        if rune['min'] != rune['max']:
            return ['Runeword resistance rune contribution is not fixed.']
        residual = value - rune['min']
        possible &= {
            base for base in options if residual == int(residual) and spec['min'] <= residual - base <= spec['max']
        }
        if spec.get('property') == 'res-all':
            shared.append(residual)
    if not possible or len(set(shared)) > 1:
        return ['Runeword resistance totals conflict with recipe, rune or shared base bonuses.']
    return []


def enhancement_gaps(facts, spec, rune, value, family):
    """Recipe totals include optional superior quality and fixed rune bonuses.

    Shield automods require a separate contribution model; callers exclude them.
    This verifies possible totals, without assigning an ambiguous recipe roll.
    """
    offsets = {0}
    if facts.rarity == 'superior':
        category = 'weapons' if family == 'weapon' else 'armor'
        quality = metadata()['superior'][category]['roll_ranges'].get(str(spec['stat_id']))
        if quality:
            offsets.update(range(quality['min'], quality['max'] + 1))
    low = spec['min'] + rune.get('min', 0)
    high = spec['max'] + rune.get('max', 0)
    if value == int(value) and any(low <= value - offset <= high for offset in offsets):
        return []
    return [f'Runeword roll {spec["stat_id"]}:0 conflicts with recipe, rune or superior base bonuses.']

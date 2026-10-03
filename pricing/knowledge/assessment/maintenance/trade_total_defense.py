"""Native aggregate defense and shifted mana axes for Trang-Oul's Girth."""

from pricing.knowledge.assessment.policies.trade_defense import MODE


SCALES = {'9:0': 256}


def verified_bounds(review, definition, stat_specs):
    if (
        review.get('total_defense') != MODE
        or review.get('base_defense')
        or review.get('compound_stats')
        or (definition.get('rarity'), definition.get('name')) != ('set', "Trang-Oul's Girth")
        or definition.get('base_name') != 'Troll Belt'
        or definition.get('base_defense_range')
        or review.get('market_stat_properties') != {'31:0': '1855', '9:0': '400'}
    ):
        return None
    base = definition.get('base_definition', {})
    game = definition.get('game_definition', {})
    rolls = definition.get('roll_ranges', {})
    # Reviewed native ranges, not an inference of the flat bonus from total defense.
    if (
        base.get('type') != 'belt'
        or base.get('gemsockets') != 0
        or (base.get('minac'), base.get('maxac')) != (59, 66)
        or not base.get('code')
        or base.get('code') != base.get('ultracode')
        or definition.get('base_code') != base['code']
        or list(definition.get('base_codes', ())) != [base['code']]
        or game.get('item') != base['code']
        or {k: v for k, v in game.items() if k.startswith('prop')}
        != {
            'prop1': 'ac',
            'prop2': 'stam',
            'prop3': 'regen',
            'prop4': 'hp',
            'prop5': 'nofreeze',
            'prop6': 'ease',
            'prop7': 'mana',
        }
        or {k: v for k, v in game.items() if k.startswith('aprop')} != {'aprop2a': 'res-cold'}
        or (game.get('min1'), game.get('max1'), game.get('min7'), game.get('max7')) != (75, 100, 25, 50)
    ):
        return None
    variable = {key for key, row in rolls.items() if row.get('min') != row.get('max')}
    if variable != {'31', '9'}:
        return None
    for key, name, prop, market, shift, bounds in (
        ('31', 'armorclass', 'ac', '399', 0, (75, 100)),
        ('9', 'maxmana', 'mana', '400', 8, (25, 50)),
    ):
        row, spec = rolls.get(key, {}), stat_specs.get(key, {})
        if (
            row.get('stat_id') != int(key)
            or row.get('layer', 0) != 0
            or row.get('property') != prop
            or (row.get('min'), row.get('max')) != bounds
            or spec.get('name') != name
            or spec.get('property_id') != market
            or spec.get('shift') != shift
            or spec.get('op_base') is not None
            or any(spec.get(k) != 0 for k in ('encode', 'parameter_bits', 'op', 'op_param'))
        ):
            return None
    return {'31:0': (134, 166), '9:0': (25, 50)}

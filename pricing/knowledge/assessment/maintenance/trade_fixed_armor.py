"""Reviewed fixed-affix armor; defense and set bonuses do not imply premiums.

This scope proves reviewed original Pillar and Claws trade qualifications. It cannot certify
build fit, upgraded demand, set completion, collector defense or numerical price.
"""

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED, variant_predicate


IDENTITY = ('set', "Immortal King's Pillar")
AFFIXES = {'ac': 75, 'move3': 40, 'att': 110, 'hp': 44}
ROLL_PROPERTIES = {'19': 'att', '31': 'ac', '7': 'hp', '96': 'move3'}
SET_BONUSES = {'mag%': 25, 'skilltab': 2, 'ac': 160, 'half-freeze': 1}


def _fixed_properties(game, prefix, minimum, maximum, expected):
    properties = {key: value for key, value in game.items() if key.startswith(prefix)}
    if len(properties) != len(expected) or set(properties.values()) != set(expected):
        return False
    return all(
        type(game.get(minimum + key.removeprefix(prefix))) is int
        and type(game.get(maximum + key.removeprefix(prefix))) is int
        and game.get(minimum + key.removeprefix(prefix)) == expected[prop]
        and game.get(maximum + key.removeprefix(prefix)) == expected[prop]
        for key, prop in properties.items()
    )


def _variant_rule(rule, code):
    if set(rule) == {'all'}:
        return bool(rule['all']) and all(_variant_rule(child, code) for child in rule['all'])
    return variant_predicate(rule) or rule == {'op': 'fact_eq', 'field': 'base_code', 'value': code}


def _variant_fields(rule):
    if 'all' in rule:
        return set().union(*(_variant_fields(child) for child in rule['all']))
    return {rule['field']}


def specification(policy, variants, stat_specs):
    if (policy.get('quality'), policy.get('name')) == ('set', "Trang-Oul's Claws"):
        from pricing.knowledge.assessment.maintenance.trade_claws import specification as claws_specification

        return claws_specification(policy, variants, stat_specs)
    if len(variants) != 1:
        return None
    definition = variants[0]
    base = definition.get('base_definition', {})
    game = definition.get('game_definition', {})
    rolls = definition.get('roll_ranges', {})
    review = policy.get('trade_qualification', {})
    code = definition.get('base_code')
    defense_spec = stat_specs.get('31', {})
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or (policy.get('quality'), policy.get('name')) != IDENTITY
        or definition.get('base_name') != 'War Boots'
        or base.get('type') != 'boot'
        or base.get('gemsockets') != 0
        or (base.get('minac'), base.get('maxac')) != (43, 53)
        or not code
        or base.get('code') != code
        or base.get('ubercode') != code
        or base.get('ultracode') in (None, code)
        or list(definition.get('base_codes', ())) != [code]
        or game.get('item') != code
        or type(game.get('add func')) is not int
        or game['add func'] != 2
        or not _fixed_properties(game, 'prop', 'min', 'max', AFFIXES)
        or not _fixed_properties(game, 'aprop', 'amin', 'amax', SET_BONUSES)
        or set(rolls) != set(ROLL_PROPERTIES)
        or any(
            row.get('property') != ROLL_PROPERTIES[key]
            or row.get('stat_id') != int(key)
            or row.get('layer', 0) != 0
            or type(row.get('min')) is not int
            or type(row.get('max')) is not int
            or row.get('min') != AFFIXES[ROLL_PROPERTIES[key]]
            or row.get('max') != AFFIXES[ROLL_PROPERTIES[key]]
            for key, row in rolls.items()
        )
        or any(definition.get(key) for key in ('native_socket_range', 'variable_per_level_effects', 'property_groups'))
        or defense_spec.get('name') != 'armorclass'
        or defense_spec.get('op_base') is not None
        or any(defense_spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param'))
        or review.get('default_status') != 'candidate'
        or review.get('material_stats') != []
        or review.get('bands') != []
        or policy.get('overrides')
        or policy.get('variant_rules')
        or any(review.get(k) for k in ('base_defense', 'total_defense', 'compound_stats', 'base_inference'))
        or not _variant_rule(policy['valid_if'], code)
        or not _variant_rule(review['valid_if'], code)
        or not {'ethereal', 'sockets', 'socket_contents', 'base_code'}
        <= (_variant_fields(policy['valid_if']) | _variant_fields(review['valid_if']))
    ):
        return None
    # The upgrade name is verified from the same native base catalog, never
    # guessed from a fixture or accepted merely because its name differs.
    from pricing.knowledge.artifacts import read_artifact
    from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
    from pricing.knowledge.market_base_catalog import equipment_index

    index, _ = equipment_index(read_artifact(CATALOG))
    upgraded = [row for row in index.values() if row['base_code'] == base['ultracode']]
    if len(upgraded) != 1 or upgraded[0].get('name') != 'Myrmidon Greaves':
        return None
    return {
        'definition': definition,
        'upgraded_base': upgraded[0]['name'],
        'defense_cases': {118, 128, 278, 288},
    }


def case_gap(cases, policy, spec):
    variants, defense, upgraded = set(), set(), False
    for item, checks, signature in cases:
        original = item['base'] == spec['definition']['base_name']
        qualified = original and signature == LEGAL
        status = 'candidate' if qualified else 'unresolved'
        expected = {'status': status, **({'material_stats': []} if qualified else {})}
        lines = (
            [
                {
                    'text': 'Trade: candidate — ' + policy['trade_qualification']['default_reason'],
                    'tone': 'tier_' + policy['default_tier'],
                }
            ]
            if qualified
            else []
        )
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Fixed armor verdict and rendered text/color are not explicitly asserted.'
        if qualified and spec.get('fixed_native_stats'):
            captured = {(stat, layer): value for stat, layer, value in item['raw_stats']}
            if any(captured.get(key) != value for key, value in spec['fixed_native_stats'].items()):
                return 'Fixed armor functional modifiers are not present in the native cases.'
        if original:
            variants.add(signature)
            if signature == LEGAL:
                values = [value for stat, layer, value in item['raw_stats'] if (stat, layer) == (31, 0)]
                if len(values) == 1 and type(values[0]) is int:
                    defense.add(values[0])
        elif item['base'] == spec['upgraded_base'] and signature == LEGAL:
            upgraded = True
    if not variants >= REQUIRED or not defense >= spec['defense_cases'] or not upgraded:
        return 'Fixed armor native defense, conditional set defense or variant boundaries are missing.'
    return None

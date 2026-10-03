"""Original Claws qualification: fixed caster affixes, no defense premium."""

from pricing.knowledge.assessment.maintenance.trade_fixed_armor import (
    _fixed_properties,
    _variant_fields,
    _variant_rule,
)
from pricing.knowledge.set_properties import extra_properties_are_unconditional


IDENTITY = ('set', "Trang-Oul's Claws")
AFFIXES = {'ac': 30, 'cast3': 20, 'res-cold': 30, 'skilltab': 2}
ROLLS = {
    '31': ('ac', 30, 'armorclass'),
    '105': ('cast3', 20, 'item_fastercastrate'),
    '43': ('res-cold', 30, 'coldresist'),
    '188:16': ('skilltab', 2, 'item_addskill_tab'),
    '332': ('extra-pois', 25, 'passive_pois_mastery'),
}


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base = definition.get('base_definition', {})
    game = definition.get('game_definition', {})
    rolls = definition.get('roll_ranges', {})
    trade = policy.get('trade_qualification', {})
    code = definition.get('base_code')
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or (policy.get('quality'), policy.get('name')) != IDENTITY
        or definition.get('base_name') != 'Heavy Bracers'
        or base.get('type') != 'glov'
        or base.get('gemsockets') != 0
        or (base.get('minac'), base.get('maxac')) != (37, 44)
        or not code
        or base.get('code') != code
        or base.get('ubercode') != code
        or list(definition.get('base_codes', ())) != [code]
        or game.get('item') != code
        or not extra_properties_are_unconditional(game)
        or not _fixed_properties(game, 'prop', 'min', 'max', AFFIXES)
        or not _fixed_properties(game, 'aprop', 'amin', 'amax', {'extra-pois': 25})
        or {k: v for k, v in game.items() if k.startswith(('par', 'apar'))} != {'par4': 6}
        or type(game.get('par4')) is not int
        or game.get('prop4') != 'skilltab'
        or set(rolls) != set(ROLLS)
        or any(
            definition.get(k)
            for k in (
                'native_socket_range',
                'variable_per_level_effects',
                'fixed_per_level_effects',
                'property_groups',
            )
        )
        or trade.get('default_status') != 'candidate'
        or trade.get('material_stats') != []
        or trade.get('bands') != []
        or trade.get('base_inference') != 'original_total_defense'
        or any(trade.get(k) for k in ('base_defense', 'total_defense', 'compound_stats'))
        or policy.get('overrides')
        or policy.get('variant_rules')
        or not _variant_rule(policy['valid_if'], code)
        or not _variant_rule(trade['valid_if'], code)
        or not {'ethereal', 'sockets', 'socket_contents', 'base_code'}
        <= (_variant_fields(policy['valid_if']) | _variant_fields(trade['valid_if']))
    ):
        return None
    for key, (prop, value, name) in ROLLS.items():
        stat, _, layer = key.partition(':')
        row, spec = rolls[key], stat_specs.get(stat, {})
        if (
            row.get('property') != prop
            or type(row.get('stat_id')) is not int
            or row['stat_id'] != int(stat)
            or type(row.get('layer', 0)) is not int
            or row.get('layer', 0) != int(layer or 0)
            or any(type(row.get(k)) is not int or row[k] != value for k in ('min', 'max'))
            or spec.get('name') != name
            or spec.get('parameter_bits') != (16 if stat == '188' else 0)
            or spec.get('op_base') is not None
            or any(spec.get(k) != 0 for k in ('shift', 'encode', 'op', 'op_param'))
        ):
            return None
    from pricing.knowledge.artifacts import read_artifact
    from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
    from pricing.knowledge.market_base_catalog import equipment_index

    index, _ = equipment_index(read_artifact(CATALOG))
    upgraded = [row for row in index.values() if row['base_code'] == base.get('ultracode')]
    if len(upgraded) != 1 or upgraded[0].get('name') != 'Vambraces':
        return None
    return {
        'definition': definition,
        'upgraded_base': upgraded[0]['name'],
        'defense_cases': {67, 74},
        'fixed_native_stats': {(105, 0): 20, (43, 0): 30, (188, 16): 2, (332, 0): 25},
    }

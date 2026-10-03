"""Original Tal belt trade segment, without borrowing upgraded or set value."""

from pricing.knowledge.assessment.maintenance.trade_fixed_armor import _fixed_properties, _variant_rule
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED


IDENTITY = ('set', "Tal Rasha's Fine-Spun Cloth")
PROPERTIES = (
    ('ease', 91, -20, -20, 'item_req_percent', 0),
    ('mana', 9, 30, 30, 'maxmana', 8),
    ('dex', 2, 20, 20, 'dexterity', 0),
    ('dmg-to-mana', 114, 37, 37, 'item_damagetomana', 0),
    ('mag%', 80, 10, 15, 'item_magicbonus', 0),
)
DEFENSE_STAGES = {(35, 0), (40, 0), (95, 0), (100, 0), (95, 10), (100, 10)}
FIXED_RAW = {(91, 0): -20, (9, 0): 30 * 256, (2, 0): 20, (114, 0): 37}


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    rolls, trade = definition.get('roll_ranges', {}), policy.get('trade_qualification', {})
    code = definition.get('base_code')
    guard = {
        'all': [
            {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
            {'op': 'fact_eq', 'field': 'sockets', 'value': 0},
            {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'empty'},
            {'op': 'fact_eq', 'field': 'base_code', 'value': code},
            {'op': 'stat_at_least', 'key': '80:0', 'value': 10},
            {'not': {'op': 'stat_at_least', 'key': '80:0', 'value': 16}},
        ]
    }
    bands = trade.get('bands', [])
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or (policy.get('quality'), policy.get('name')) != IDENTITY
        or definition.get('base_name') != 'Mesh Belt'
        or base.get('type') != 'belt'
        or base.get('gemsockets') != 0
        or (base.get('minac'), base.get('maxac')) != (35, 40)
        or not code
        or base.get('code') != code
        or base.get('ubercode') != code
        or list(definition.get('base_codes', ())) != [code]
        or game.get('item') != code
        or type(game.get('add func')) is not int
        or game['add func'] != 2
        or not _fixed_properties(game, 'aprop', 'amin', 'amax', {'ac': 60, 'cast2': 10})
        or game.get('aprop1a') != 'ac'
        or game.get('aprop2a') != 'cast2'
        or any(k.startswith(('par', 'apar')) for k in game)
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 6)}
        or set(rolls) != {str(row[1]) for row in PROPERTIES}
        or any(
            definition.get(k)
            for k in (
                'native_socket_range',
                'variable_per_level_effects',
                'fixed_per_level_effects',
                'property_groups',
            )
        )
        or trade.get('default_status') != 'unresolved'
        or trade.get('material_stats') != ['80:0']
        or trade.get('base_inference') != 'original_total_defense'
        or any(trade.get(k) for k in ('base_defense', 'total_defense', 'compound_stats'))
        or policy.get('overrides')
        or policy.get('variant_rules')
        or not _variant_rule(policy['valid_if'], code)
        or trade.get('valid_if') != guard
        or len(bands) != 1
        or bands[0].get('status') != 'candidate'
        or bands[0].get('when') != {'op': 'stat_at_least', 'key': '80:0', 'value': 15}
    ):
        return None
    for i, (prop, stat, low, high, name, shift) in enumerate(PROPERTIES, 1):
        row, spec = rolls[str(stat)], stat_specs.get(str(stat), {})
        if (
            game.get(f'prop{i}') != prop
            or any(type(game.get(k)) is not int for k in (f'min{i}', f'max{i}'))
            or (game[f'min{i}'], game[f'max{i}']) != (low, high)
            or row.get('property') != prop
            or row.get('stat_id') != stat
            or row.get('layer', 0) != 0
            or any(type(row.get(k)) is not int for k in ('min', 'max'))
            or (row['min'], row['max']) != (low, high)
            or spec.get('name') != name
            or spec.get('shift') != shift
            or spec.get('op_base') is not None
            or any(spec.get(k) != 0 for k in ('encode', 'parameter_bits', 'op', 'op_param'))
        ):
            return None
    for stat, name in (('31', 'armorclass'), ('105', 'item_fastercastrate')):
        spec = stat_specs.get(stat, {})
        if (
            spec.get('name') != name
            or spec.get('op_base') is not None
            or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param'))
        ):
            return None
    from pricing.knowledge.artifacts import read_artifact
    from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
    from pricing.knowledge.market_base_catalog import equipment_index

    index, _ = equipment_index(read_artifact(CATALOG))
    upgraded = [r for r in index.values() if r['base_code'] == base.get('ultracode')]
    if len(upgraded) != 1 or upgraded[0].get('name') != 'Mithril Coil':
        return None
    return {'definition': definition, 'upgraded_base': upgraded[0]['name']}


def case_gap(cases, policy, spec):
    seen, variants, invalid, upgraded = set(), set(), set(), False
    for item, checks, signature in cases:
        raw = item['raw_stats']
        stats = {(s, p): value for s, p, value in raw}
        if len(stats) != len(raw) or any(type(v) is not int for v in stats.values()):
            return 'Tal belt native stats contain duplicate or noninteger values.'
        original = item['base'] == spec['definition']['base_name']
        mf = stats.get((80, 0))
        candidate = original and signature == LEGAL and mf == 15
        expected = {'status': 'candidate', 'material_stats': ['80:0']} if candidate else {'status': 'unresolved'}
        lines = (
            [
                {
                    'text': 'Trade: ordinary candidate — ' + policy['trade_qualification']['bands'][0]['reason'],
                    'tone': 'tier_low',
                }
            ]
            if candidate
            else []
        )
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Tal belt verdict and rendered text/color are not explicitly asserted.'
        if original:
            variants.add(signature)
            if signature == LEGAL:
                if any(stats.get(k) != v for k, v in FIXED_RAW.items()):
                    return 'Tal belt cases omit fixed native modifiers.'
                if mf in range(10, 16):
                    seen.add((mf, stats.get((31, 0)), stats.get((105, 0), 0)))
                else:
                    invalid.add(mf)
        elif item['base'] == spec['upgraded_base'] and signature == LEGAL and mf == 15:
            upgraded = True
    required = {(mf, defense, fcr) for mf in range(10, 16) for defense, fcr in DEFENSE_STAGES}
    if not (seen >= required and variants >= REQUIRED and invalid >= {None, 9, 16} and upgraded):
        return 'Tal belt roll, conditional set or variant boundaries are missing.'
    return None

"""Native original Bane belt review, including both possible upgrade exclusions."""

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.trade_fixed_armor import _fixed_properties, _variant_rule
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
from pricing.knowledge.market_base_catalog import equipment_index


IDENTITY = ('set', "Bane's Authority")
BONUSES = {'105': ('cast1', 10, 'item_fastercastrate', 0), '7': ('hp', 20, 'maxhp', 8)}
BAD_ROLLS = {(9, 5120), (11, 5120), (10, 4864), (10, 5376), (None, None)}


def specification(policy, variants, stat_specs):
    if (policy.get('quality'), policy.get('name')) != IDENTITY or len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    trade, rolls = policy.get('trade_qualification', {}), definition.get('roll_ranges', {})
    code = definition.get('base_code')
    guard = [
        {'op': 'fact_eq', 'field': k, 'value': v}
        for k, v in [('ethereal', False), ('sockets', 0), ('socket_contents', 'empty'), ('base_code', code)]
    ]
    for key, (_, value, _, _) in BONUSES.items():
        guard.extend(
            [
                {'op': 'stat_at_least', 'key': key + ':0', 'value': value},
                {'not': {'op': 'stat_at_least', 'key': key + ':0', 'value': value + 1}},
            ]
        )
    if (
        (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Light Belt'
        or not code
        or base.get('code') != code
        or base.get('normcode') != code
        or list(definition.get('base_codes', ())) != [code]
        or (base.get('type'), base.get('gemsockets'), base.get('minac'), base.get('maxac')) != ('belt', 0, 3, 3)
        or game.get('item') != code
        or game.get('add func') != 2
        or not _fixed_properties(game, 'prop', 'min', 'max', {'cast1': 10, 'hp': 20})
        or not _fixed_properties(game, 'aprop', 'amin', 'amax', {'enr': 15})
        or any(k.startswith(('par', 'apar')) for k in game)
        or set(rolls) != set(BONUSES)
        or any(definition.get(k) for k in ('native_socket_range', 'property_groups', 'variable_per_level_effects'))
        or trade.get('valid_if') != {'all': guard}
        or trade.get('default_status') != 'candidate'
        or trade.get('bands') != []
        or trade.get('base_inference') != 'original_total_defense'
        or trade.get('material_stats') != ['105:0', '7:0']
        or trade.get('market_stat_properties') != {'105:0': '520', '7:0': '418'}
        or policy.get('default_tier') != 'low'
        or policy.get('overrides')
        or policy.get('variant_rules')
        or not _variant_rule(policy['valid_if'], code)
    ):
        return None
    for key, (prop, value, name, shift) in BONUSES.items():
        row, stat = rolls[key], stat_specs.get(key, {})
        if row.get('layer', 0) != 0:
            return None
        if (row.get('property'), row.get('stat_id'), row.get('min'), row.get('max')) != (prop, int(key), value, value):
            return None
        if stat.get('name') != name or stat.get('shift') != shift or stat.get('op_base') is not None:
            return None
        if any(stat.get(k) != 0 for k in ('encode', 'parameter_bits', 'op', 'op_param')):
            return None
    index, _ = equipment_index(read_artifact(CATALOG))
    upgrades = []
    for field in ('ubercode', 'ultracode'):
        choices = [r for r in index.values() if r.get('base_code') == base.get(field)]
        if len(choices) != 1 or choices[0]['base_code'] == code:
            return None
        upgrades.append(choices[0]['name'])
    if len(set(upgrades)) != 2:
        return None
    return {'definition': definition, 'additional_bases': tuple(upgrades)}


def case_gap(cases, policy, spec):
    seen, upgrades, bad, positives = set(), set(), set(), set()
    for item, checks, signature in cases:
        raw = {(s, layer): value for s, layer, value in item['raw_stats']}
        if len(raw) != len(item['raw_stats']) or any(type(v) is not int for v in raw.values()):
            return 'Ambiguous Bane native stats.'
        original = item['base'] == spec['definition']['base_name']
        pair = raw.get((105, 0)), raw.get((7, 0))
        qualifies = original and signature == LEGAL and pair == (10, 5120)
        expected = {'status': 'candidate' if qualifies else 'unresolved'}
        lines = (
            [
                {
                    'text': 'Trade: ordinary candidate — ' + policy['trade_qualification']['default_reason'],
                    'tone': 'tier_low',
                }
            ]
            if qualifies
            else []
        )
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Bane native verdict, text or color is not asserted.'
        if original:
            seen.add(signature)
            if signature == LEGAL:
                bad.add(pair)
            if qualifies:
                if raw.get((31, 0)) != 3 or raw.get((1, 0), 0) not in (0, 15):
                    return 'Unverified Bane defense or partial-set energy.'
                positives.add(raw.get((1, 0), 0))
        elif item['base'] in spec['additional_bases'] and signature == LEGAL:
            upgrades.add(item['base'])
        else:
            return 'Unreviewed Bane upgrade case.'
    if (
        not seen >= REQUIRED
        or upgrades != set(spec['additional_bases'])
        or not bad >= BAD_ROLLS
        or positives != {0, 15}
    ):
        return 'Missing Bane original, upgrade, fixed-stat or unknown boundaries.'
    return None

"""Independent native and report-boundary proof for both Gore Rider bases."""

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _outcome, _vector


IDENTITY = ('unique', 'Gore Rider')
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}
FIXED = {(91, 0): -25, (141, 0): 15, (96, 0): 30, (136, 0): 15, (135, 0): 10, (73, 0): 34, (11, 0): 20 * 256}
PROPERTIES = (
    ('ease', -25, -25),
    ('deadly', 15, 15),
    ('move2', 30, 30),
    ('crush', 15, 15),
    ('openwounds', 10, 10),
    ('ac%', 160, 200),
    ('dur', 10, 10),
    ('stam', 20, 20),
)


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    trade = policy.get('trade_qualification', {})
    guard = [
        {'op': 'fact_eq', 'field': k, 'value': v}
        for k, v in (('ethereal', False), ('sockets', 0), ('socket_contents', 'empty'))
    ]
    guard += [
        {'any': [{'op': 'fact_eq', 'field': 'base_code', 'value': c} for c in ('xhb', 'uhb')]},
        {'op': 'stat_at_least', 'key': '16:0', 'value': 160},
        {'not': {'op': 'stat_at_least', 'key': '16:0', 'value': 201}},
    ]
    bands = trade.get('bands', [])
    expected_bands = [
        {'op': 'fact_eq', 'field': 'base_code', 'value': 'xhb'},
        {
            'all': [
                {'op': 'fact_eq', 'field': 'base_code', 'value': 'uhb'},
                {'op': 'stat_at_least', 'key': '16:0', 'value': 200},
            ]
        },
    ]
    roll, stat = definition.get('roll_ranges', {}).get('16', {}), stat_specs.get('16', {})
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'War Boots'
        or definition.get('base_code') != 'xhb'
        or list(definition.get('base_codes', ())) != ['xhb']
        or any(
            base.get(k) != v
            for k, v in {
                'code': 'xhb',
                'ultracode': 'uhb',
                'minac': 43,
                'maxac': 53,
                'gemsockets': 0,
                'durability': 24,
                'type': 'boot',
            }.items()
        )
        or game.get('code') != 'xhb'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 9)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}')) != v for i, v in enumerate(PROPERTIES, 1)
        )
        or (roll.get('stat_id'), roll.get('property'), roll.get('min'), roll.get('max')) != (16, 'ac%', 160, 200)
        or stat.get('name') != 'item_armor_percent'
        or stat.get('op') != 13
        or stat.get('op_base') is not None
        or any(stat.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        or trade.get('material_stats') != ['16:0']
        or trade.get('market_stat_properties') != {'16:0': '425'}
        or trade.get('valid_if') != {'all': guard}
        or trade.get('base_inference') != 'gore_rider_variant_defense'
        or trade.get('ethereal_inference') != 'gore_rider_variant_defense'
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or len(bands) != 2
        or any(b.get('status') != 'candidate' for b in bands)
        or [b.get('when') for b in bands] != expected_bands
        or policy.get('variant_rules')
    ):
        return None
    return {'definition': definition, 'upgraded_base': 'Myrmidon Greaves', 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, variants, upgraded_totals = set(), set(), set()
    for item, checks, signature in cases:
        stats = {(s, p): v for s, p, v in item['raw_stats']}
        if len(stats) != len(item['raw_stats']) or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous Gore Rider native stats.'
        if any(stats.get(k) != v for k, v in FIXED.items()):
            return 'Fixed combat, durability or stamina stats do not match native Gore Rider.'
        vector = _vector(item, ('16:0',))
        if vector is None:
            return 'Ambiguous Gore Rider enhanced defense.'
        (ed,) = vector
        base = item['base']
        upgraded = base == spec['upgraded_base']
        legal = type(ed) is int and 160 <= ed <= 200
        expected = 'candidate' if signature == LEGAL and legal and (not upgraded or ed == 200) else 'unresolved'
        status, reason = _outcome(
            policy, spec['definition'], item, ('16:0',), vector, verified_base_code='uhb' if upgraded else 'xhb'
        )
        if status != expected:
            return 'Gore Rider rule does not preserve separate original and upgraded boundaries.'
        lines = [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if status == 'candidate' else []
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'Gore Rider verdict and rendered text/color are not explicitly asserted.'
        if expected == 'candidate':
            totals = {b * (100 + ed) // 100 for b in (range(62, 72) if upgraded else (54,))}
            if stats.get((31, 0)) not in totals:
                return 'Candidate defense is not a legal native base/ED outcome.'
        if signature == LEGAL:
            seen.add((base, ed))
            if upgraded and ed == 200:
                upgraded_totals.add(stats.get((31, 0)))
        if ed == (200 if upgraded else 160):
            variants.add((base, signature))
    bases = (spec['definition']['base_name'], spec['upgraded_base'])
    required = {(b, v) for b in bases for v in (160, 199, 200, None, 159, 201)}
    if not required <= seen or not {(b, v) for b in bases for v in VARIANTS} <= variants:
        return 'Gore Rider roll or variant boundary reports are missing.'
    if upgraded_totals != {b * 3 for b in range(62, 72)}:
        return 'Perfect-ED upgraded boots do not cover every base-defense outcome.'
    return None

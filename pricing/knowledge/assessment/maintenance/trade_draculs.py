"""Native Dracul's Grasp boundaries independent of the report's own verdict."""

from itertools import product

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _outcome, _vector


IDENTITY = ('unique', "Dracul's Grasp")
BOUNDS = {'60:0': (7, 10), '0:0': (10, 15), '16:0': (90, 120), '86:0': (5, 10)}
MAPPINGS = {'60:0': '462', '0:0': '437', '16:0': '425', '86:0': '721'}
PROPERTIES = (
    ('ac%', 90, 120),
    ('lifesteal', 7, 10),
    ('openwounds', 25, 25),
    ('hit-skill', 5, 10),
    ('heal-kill', 5, 10),
    ('str', 10, 15),
)
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    trade = policy.get('trade_qualification', {})
    guard = [
        {'op': 'fact_eq', 'field': k, 'value': v}
        for k, v in (('ethereal', False), ('sockets', 0), ('socket_contents', 'empty'), ('base_code', 'uvg'))
    ]
    for key, (low, high) in BOUNDS.items():
        guard += [
            {'op': 'stat_at_least', 'key': key, 'value': low},
            {'not': {'op': 'stat_at_least', 'key': key, 'value': high + 1}},
        ]
    bands = trade.get('bands', [])
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Vampirebone Gloves'
        or definition.get('base_code') != 'uvg'
        or any(base.get(k) != v for k, v in {'code': 'uvg', 'minac': 56, 'maxac': 65, 'gemsockets': 0}.items())
        or game.get('code') != 'uvg'
        or game.get('par4') != 'Life Tap'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 7)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}')) != v for i, v in enumerate(PROPERTIES, 1)
        )
        or trade.get('material_stats') != list(BOUNDS)
        or trade.get('market_stat_properties') != MAPPINGS
        or trade.get('valid_if') != {'all': guard}
        or trade.get('ethereal_inference') != 'draculs_total_defense'
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or len(bands) != 1
        or bands[0].get('status') != 'candidate'
        or bands[0].get('when') != {'op': 'stat_at_least', 'key': '60:0', 'value': 10}
        or policy.get('variant_rules')
    ):
        return None
    for key, bounds in BOUNDS.items():
        sid = key.split(':')[0]
        roll, stat = definition.get('roll_ranges', {}).get(sid, {}), stat_specs.get(sid, {})
        if (
            (roll.get('min'), roll.get('max')) != bounds
            or stat.get('op') != (13 if sid == '16' else 0)
            or stat.get('op_base') is not None
            or any(stat.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        ):
            return None
    return {'definition': definition, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, invalid, variants = set(), set(), set()
    keys = tuple(BOUNDS)
    for item, checks, signature in cases:
        stats = {(s, p): v for s, p, v in item['raw_stats']}
        vector = _vector(item, keys)
        if (
            len(stats) != len(item['raw_stats'])
            or vector is None
            or any(type(v) is not int for v in stats.values())
            or item['base'] != 'Vampirebone Gloves'
            or stats.get((135, 0)) != 25
            or stats.get((198, (82 << 6) | 10)) != 5
        ):
            return 'Dracul native identity, Open Wounds or Life Tap differs.'
        legal = all(type(v) is int and BOUNDS[k][0] <= v <= BOUNDS[k][1] for k, v in zip(keys, vector, strict=True))
        if signature == LEGAL and legal and stats.get((31, 0)) != 66 * (100 + vector[2]) // 100:
            return 'Dracul defense is not the native nonethereal total.'
        expected = 'candidate' if signature == LEGAL and legal and vector[0] == 10 else 'unresolved'
        status, reason = _outcome(policy, spec['definition'], item, keys, vector)
        if status != expected:
            return 'Dracul life-leech qualification does not match independent boundaries.'
        lines = [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if status == 'candidate' else []
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'Dracul report verdict, text and color are not asserted.'
        if signature == LEGAL:
            seen.add(vector)
            for key, value in zip(keys, vector, strict=True):
                low, high = BOUNDS[key]
                if value in (None, low - 1, high + 1):
                    invalid.add((key, value))
        if legal and vector[0] == 10:
            variants.add(signature)
    required = set(product((7, 9, 10), (10, 15), (90, 120), (5, 10)))
    missing = {(k, v) for k, (low, high) in BOUNDS.items() for v in (None, low - 1, high + 1)}
    if not required <= seen or not missing <= invalid or not variants >= VARIANTS:
        return 'Dracul roll corners, missing/illegal rolls or variants are not all executed.'
    return None

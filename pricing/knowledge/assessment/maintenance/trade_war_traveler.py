"""Native War Traveler material rolls and executed-report coverage."""

from itertools import product

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _outcome, _vector


IDENTITY = ('unique', 'War Traveler')
KEYS = ('80:0', '16:0', '78:0')
BOUNDS = ((30, 50), (150, 190), (5, 10))
POINTS = ((30, 49, 50), (150, 190), (5, 10))
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}
FIXED = {(0, 0): 10, (3, 0): 10, (96, 0): 25, (154, 0): 40, (21, 0): 15, (22, 0): 25}
PROPERTIES = (
    ('vit', 10, 10),
    ('str', 10, 10),
    ('mag%', 30, 50),
    ('dur', 30, 30),
    ('move2', 25, 25),
    ('ac%', 150, 190),
    ('dmg-norm', 15, 25),
    ('thorns', 5, 10),
    ('stamdrain', 40, 40),
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
    for key, (low, high) in zip(KEYS, BOUNDS, strict=True):
        guard += [
            {'op': 'stat_at_least', 'key': key, 'value': low},
            {'not': {'op': 'stat_at_least', 'key': key, 'value': high + 1}},
        ]
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Battle Boots'
        or definition.get('base_code') != 'xtb'
        or list(definition.get('base_codes', ())) != ['xtb']
        or any(
            base.get(k) != v
            for k, v in {
                'code': 'xtb',
                'ultracode': 'utb',
                'minac': 39,
                'maxac': 47,
                'gemsockets': 0,
                'type': 'boot',
            }.items()
        )
        or game.get('code') != 'xtb'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 10)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}')) != values
            for i, values in enumerate(PROPERTIES, 1)
        )
        or trade.get('material_stats') != list(KEYS)
        or trade.get('market_stat_properties') != dict(zip(KEYS, ('461', '425', '415'), strict=True))
        or trade.get('ethereal_inference') != 'war_traveler_total_defense'
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or trade.get('valid_if') != {'all': guard}
        or len(trade.get('bands', [])) != 1
        or trade['bands'][0].get('status') != 'candidate'
        or trade['bands'][0].get('when') != {'op': 'stat_at_least', 'key': '80:0', 'value': 50}
        or policy.get('variant_rules')
    ):
        return None
    for key, bounds, prop, name, operation in zip(
        KEYS,
        BOUNDS,
        ('mag%', 'ac%', 'thorns'),
        ('item_magicbonus', 'item_armor_percent', 'item_attackertakesdamage'),
        (0, 13, 0),
        strict=True,
    ):
        stat = key.split(':')[0]
        roll, spec = definition.get('roll_ranges', {}).get(stat, {}), stat_specs.get(stat, {})
        if (
            (roll.get('min'), roll.get('max')) != bounds
            or roll.get('property') != prop
            or roll.get('stat_id') != int(stat)
            or roll.get('layer', 0) != 0
            or spec.get('name') != name
            or spec.get('op') != operation
            or spec.get('op_base') is not None
            or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        ):
            return None
    return {'definition': definition, 'upgraded_base': 'Mirrored Boots', 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, variants = set(), set()
    for item, checks, signature in cases:
        stats = {(s, p): value for s, p, value in item['raw_stats']}
        if len(stats) != len(item['raw_stats']) or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous War Traveler native stats.'
        if any(stats.get(k) != v for k, v in FIXED.items()):
            return 'War Traveler fixed native stats are missing.'
        vector = _vector(item, KEYS)
        if vector is None:
            return 'Ambiguous War Traveler material roll.'
        base = item['base']
        status, reason = _outcome(
            policy,
            spec['definition'],
            item,
            KEYS,
            vector,
            verified_base_code='utb' if base == spec['upgraded_base'] else 'xtb',
        )
        legal = all(type(v) is int and lo <= v <= hi for v, (lo, hi) in zip(vector, BOUNDS, strict=True))
        expected = 'candidate' if signature == LEGAL and legal and vector[0] == 50 else 'unresolved'
        if status != expected:
            return 'War Traveler policy differs from the reviewed MF boundary.'
        lines = [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if status == 'candidate' else []
        if checks.get('qualification') != {'status': status} or checks.get('lines') != lines:
            return 'War Traveler verdict and rendered text/color are not explicitly asserted.'
        if signature == LEGAL:
            seen.add((base, vector))
        if vector == (50, 190, 10):
            variants.add((base, signature))
    bases = (spec['definition']['base_name'], spec['upgraded_base'])
    required = {(base, v) for base in bases for v in product(*POINTS)}
    for base in bases:
        for i, (lo, hi) in enumerate(BOUNDS):
            for value in (None, lo - 1, hi + 1):
                vector = [50, 190, 10]
                vector[i] = value
                required.add((base, tuple(vector)))
    if not required <= seen or not {(b, v) for b in bases for v in VARIANTS} <= variants:
        return 'War Traveler native endpoints, material unknowns or variant boundaries are missing.'
    return None

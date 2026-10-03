"""Independent native boundary and visible-report oracle for Waterwalk's reviewed cohort."""

from itertools import product

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _outcome, _vector


IDENTITY = ('unique', 'Waterwalk')
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}
KEYS = ('7:0', '16:0', '31:0')
FIXED = {(32, 0): 100, (96, 0): 20, (2, 0): 15, (11, 0): 40 * 256, (40, 0): 5, (28, 0): 50}
PROPERTIES = (
    ('ac-miss', 100, 100),
    ('move2', 20, 20),
    ('dex', 15, 15),
    ('ac%', 180, 210),
    ('hp', 45, 65),
    ('stam', 40, 40),
    ('res-fire-max', 5, 5),
    ('regen-stam', 50, 50),
)


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    definition = variants[0]
    base, game = definition.get('base_definition', {}), definition.get('game_definition', {})
    trade = policy.get('trade_qualification', {})
    bands = trade.get('bands', [])
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or (definition.get('rarity'), definition.get('name')) != IDENTITY
        or definition.get('base_name') != 'Sharkskin Boots'
        or definition.get('base_code') != 'xvb'
        or list(definition.get('base_codes', ())) != ['xvb']
        or any(
            base.get(k) != v
            for k, v in {'code': 'xvb', 'ultracode': 'uvb', 'minac': 33, 'maxac': 39, 'gemsockets': 0}.items()
        )
        or game.get('code') != 'xvb'
        or {k for k in game if k.startswith('prop')} != {f'prop{i}' for i in range(1, 9)}
        or any(
            (game.get(f'prop{i}'), game.get(f'min{i}'), game.get(f'max{i}')) != v for i, v in enumerate(PROPERTIES, 1)
        )
        or trade.get('material_stats') != list(KEYS)
        or trade.get('market_stat_properties') != {'7:0': '418', '16:0': '425', '31:0': '1855'}
        or any(
            trade.get(k) != 'waterwalk_variant_defense'
            for k in ('base_inference', 'ethereal_inference', 'total_defense')
        )
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or len(bands) != 2
        or any(b.get('status') != 'candidate' for b in bands)
        or policy.get('variant_rules')
    ):
        return None
    for sid, name, shift, op in [('7', 'maxhp', 8, 0), ('16', 'item_armor_percent', 0, 13), ('31', 'armorclass', 0, 0)]:
        stat = stat_specs.get(sid, {})
        if (stat.get('name'), stat.get('shift'), stat.get('op')) != (name, shift, op) or (
            stat.get('op_base') is not None or any(stat.get(k) != 0 for k in ('encode', 'parameter_bits', 'op_param'))
        ):
            return None
    return {'definition': definition, 'upgraded_base': 'Scarabshell Boots', 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    seen, variants, invalid, special = set(), set(), set(), set()
    for item, checks, signature in cases:
        stats = {(s, p): v for s, p, v in item['raw_stats']}
        vector = _vector(item, KEYS, {'7:0': 256})
        if len(stats) != len(item['raw_stats']) or vector is None or any(type(v) is not int for v in stats.values()):
            return 'Ambiguous Waterwalk native stats.'
        if any(stats.get(k) != v for k, v in FIXED.items()):
            return 'Waterwalk fixed native modifiers differ.'
        base = item['base']
        if base not in ('Sharkskin Boots', 'Scarabshell Boots'):
            return 'Waterwalk base is unreviewed.'
        forbidden = {s for s, p in stats if s in (214, 215)}
        life, ed, total = vector
        original = (
            base == 'Sharkskin Boots'
            and all(type(v) is int for v in vector)
            and 45 <= life <= 65
            and 180 <= ed <= 210
            and total == 40 * (100 + ed) // 100
        )
        upgraded = base == spec['upgraded_base'] and vector == (65, 210, 198)
        candidate = signature == LEGAL and item['complete'] is True and not forbidden and (original or upgraded)
        expected = 'candidate' if candidate else 'unresolved'
        status, reason = _outcome(
            policy,
            spec['definition'],
            item,
            KEYS,
            vector,
            verified_base_code='uvb' if base == spec['upgraded_base'] else 'xvb',
        )
        if status != expected:
            return 'Waterwalk rule differs from the independently reviewed cohort.'
        lines = [{'text': 'Trade: ordinary candidate — ' + reason, 'tone': 'tier_low'}] if candidate else []
        if checks.get('qualification') != {'status': expected} or checks.get('lines') != lines:
            return 'Waterwalk verdict or visible text/color is not asserted.'
        if signature == LEGAL:
            if item['complete'] and not forbidden:
                seen.add((base, *vector))
            for key, value in zip(KEYS, vector, strict=True):
                invalid.add((key, value))
        if vector == (65, 210, 124 if base == 'Sharkskin Boots' else 198) or (
            signature[1] is True and vector[:2] == (65, 210)
        ):
            variants.add((base, signature))
            special.update((base, key) for key in forbidden)
            if item['complete'] is False:
                special.add((base, 'incomplete'))
    required = {
        (base, life, ed, defense * (100 + ed) // 100)
        for base, defenses in [('Sharkskin Boots', (40,)), ('Scarabshell Boots', (56, 63, 64, 65))]
        for defense, life, ed in product(defenses, (45, 64, 65), (180, 209, 210))
    }
    missing = {
        (key, value)
        for key, values in [('7:0', (None, 44, 66)), ('16:0', (None, 179, 211)), ('31:0', (None, 197, 199))]
        for value in values
    }
    if (
        not required <= seen
        or not missing <= invalid
        or not variants >= {(b, v) for b in ('Sharkskin Boots', 'Scarabshell Boots') for v in VARIANTS}
        or special != {(b, v) for b in ('Sharkskin Boots', 'Scarabshell Boots') for v in (214, 215, 'incomplete')}
    ):
        return 'Waterwalk native corners, missing/illegal rolls or variant reports are missing.'
    return None

"""Verified native and upgraded Titan's Revenge trade boundaries."""

from itertools import product

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.maintenance.trade_compound_rolls import verified_definition
from pricing.knowledge.assessment.maintenance.trade_review_cases import ETHEREAL_LEGAL, ETHEREAL_REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _collect, _outcome, _vector
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG
from pricing.knowledge.market_base_catalog import equipment_index


IDENTITY = ('unique', "Titan's Revenge")
BASE_CODES = {'Ceremonial Javelin': 'ama', 'Matriarchal Javelin': 'amf'}
THRESHOLDS = {'ama': 190, 'amf': 200}
BOUNDS = {'17:0': (150, 200), '18:0': (150, 200), '60:0': (5, 9)}
FIXED = {(83, 0): 2, (188, 2): 2, (96, 0): 30, (253, 0): 30, (0, 0): 20, (2, 0): 20, (254, 0): 60}
ROLLS = {
    (83, 0): ('ama', 2, 2),
    (188, 2): ('skilltab', 2, 2),
    (17, 0): ('dmg%', 150, 200),
    (18, 0): ('dmg%', 150, 200),
    (96, 0): ('move2', 30, 30),
    (0, 0): ('str', 20, 20),
    (2, 0): ('dex', 20, 20),
    (60, 0): ('lifesteal', 5, 9),
    (254, 0): ('stack', 60, 60),
}
STAT_SPECS = {
    83: ('item_addclassskills', None, 3),
    188: ('item_addskill_tab', None, 16),
    96: ('item_fastermovevelocity', '480', 0),
    253: ('item_replenish_quantity', '563', 0),
    0: ('strength', '437', 0),
    2: ('dexterity', '429', 0),
    254: ('item_extra_stack', '562', 0),
    60: ('lifedrainmindam', '462', 0),
}


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    d, trade = variants[0], policy.get('trade_qualification', {})
    base, game = d.get('base_definition', {}), d.get('game_definition', {})
    if (
        (d.get('rarity'), d.get('name')) != IDENTITY
        or (policy.get('quality'), policy.get('name')) != IDENTITY
        or d.get('base_name') != 'Ceremonial Javelin'
        or d.get('base_code') != BASE_CODES['Ceremonial Javelin']
        or list(d.get('base_codes', ())) != [d['base_code']]
        or base.get('code') != d['base_code']
        or base.get('ubercode') != d['base_code']
        or base.get('ultracode') != BASE_CODES['Matriarchal Javelin']
        or base.get('type') != 'ajav'
        or base.get('stackable') != 1
        or base.get('gemsockets') not in (None, 0)
        or game.get('code') != d['base_code']
        or any(
            d.get(k)
            for k in ('native_socket_range', 'property_groups', 'variable_per_level_effects', 'fixed_per_level_effects')
        )
        or not verified_definition(d, stat_specs, ('enhanced_damage',))
        or trade.get('compound_stats') != ['enhanced_damage']
        or set(trade.get('material_stats', ())) != set(BOUNDS)
        or len(trade.get('material_stats', ())) != 3
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or any(trade.get(k) for k in ('property_choice', 'base_defense', 'total_defense'))
        or policy.get('variant_rules')
    ):
        return None
    # Verify the base-name/code mapping and upgrade relationship from the same
    # native catalog, before it can override the scalar checker's original base.
    index, _ = equipment_index(read_artifact(CATALOG))
    resolved = {row['name']: row['base_code'] for row in index.values() if row.get('base_code') in THRESHOLDS}
    if resolved != BASE_CODES:
        return None
    rolls = d.get('roll_ranges', {})
    if len(rolls) != len(ROLLS) or {(r.get('stat_id'), r.get('layer', 0)) for r in rolls.values()} != set(ROLLS):
        return None
    for row in rolls.values():
        key = row.get('stat_id'), row.get('layer', 0)
        if (
            key not in ROLLS
            or (row.get('property'), row.get('min'), row.get('max')) != ROLLS[key]
            or any(type(row.get(k)) is not int for k in ('stat_id', 'min', 'max'))
        ):
            return None
    native = (
        ('ama', 2, 2, None),
        ('skilltab', 2, 2, 2),
        ('dmg%', 150, 200, None),
        ('move2', 30, 30, None),
        ('rep-quant', None, None, 30),
        ('str', 20, 20, None),
        ('dex', 20, 20, None),
        ('lifesteal', 5, 9, None),
        ('dmg-norm', 25, 50, None),
        ('stack', 60, 60, None),
    )
    for slot in range(1, 13):
        if slot > len(native):
            if game.get(f'prop{slot}'):
                return None
            continue
        prop, lo, hi, parameter = native[slot - 1]
        if (game.get(f'prop{slot}'), game.get(f'min{slot}'), game.get(f'max{slot}')) != (prop, lo, hi):
            return None
        for field, value in ((f'min{slot}', lo), (f'max{slot}', hi), (f'par{slot}', parameter)):
            if value is None:
                if game.get(field) not in (None, '', 0):
                    return None
            elif type(game.get(field)) is not int or game[field] != value:
                return None
    for stat, (name, prop, bits) in STAT_SPECS.items():
        row = stat_specs.get(str(stat), {})
        if (
            (row.get('name'), row.get('property_id'), row.get('parameter_bits')) != (name, prop, bits)
            or row.get('op_base') is not None
            or any(row.get(k) != 0 for k in ('op', 'shift', 'encode', 'op_param'))
        ):
            return None
    bands = trade.get('bands', [])
    if len(bands) != 2:
        return None
    points = {key: {low, high} for key, (low, high) in BOUNDS.items()}
    for band, (code, threshold) in zip(bands, THRESHOLDS.items(), strict=True):
        expected = {
            'all': [
                {'op': 'fact_eq', 'field': 'base_code', 'value': code},
                *({'op': 'stat_at_least', 'key': key, 'value': threshold} for key in ('17:0', '18:0')),
            ]
        }
        if band.get('when') != expected or band.get('status') != 'premium':
            return None
        for key in ('17:0', '18:0'):
            points[key].update((threshold - 1, threshold))
    # Existing original-base boundary gets an above-boundary execution too.
    points['17:0'].add(191)
    points['18:0'].add(191)
    guard = {
        'all': [
            *(
                {'op': 'fact_eq', 'field': f, 'value': v}
                for f, v in (('ethereal', True), ('sockets', 0), ('socket_contents', 'empty'))
            ),
            *(
                {
                    'all': [
                        {'op': 'stat_at_least', 'key': k, 'value': BOUNDS[k][0]},
                        {'not': {'op': 'stat_at_least', 'key': k, 'value': BOUNDS[k][1] + 1}},
                    ]
                }
                for k in ('18:0', '60:0')
            ),
        ]
    }
    if trade.get('valid_if') != guard or not _collect(policy['valid_if'], BOUNDS, points):
        return None
    return {
        'definition': d,
        'base_codes': dict(BASE_CODES),
        'thresholds': dict(THRESHOLDS),
        'bounds': dict(BOUNDS),
        'points': points,
        'upgraded_base': 'Matriarchal Javelin',
        'variants': ETHEREAL_REQUIRED,
    }


def case_gap(cases, policy, spec):
    keys = ('17:0', '18:0', '60:0')
    maxima = (200, 200, 9)
    required = set()
    for base in BASE_CODES:
        required.update(
            (base, ETHEREAL_LEGAL, (ed, ed, leech))
            for ed, leech in product(spec['points']['17:0'] | spec['points']['18:0'], spec['points']['60:0'])
        )
        required.update((base, variant, maxima) for variant in ETHEREAL_REQUIRED)
        for index, key in enumerate(keys):
            for value in (None, BOUNDS[key][0] - 1, BOUNDS[key][1] + 1):
                vector = list(maxima)
                vector[index] = value
                required.add((base, ETHEREAL_LEGAL, tuple(vector)))
        required.update((base, ETHEREAL_LEGAL, v) for v in ((200, 199, 9), (199, 200, 9), (149, 149, 9), (201, 201, 9)))
    seen = set()
    for item, checks, variant in cases:
        raw, base = item['raw_stats'], item['base']
        if base not in BASE_CODES or len({tuple(r[:2]) for r in raw}) != len(raw):
            return 'Ambiguous native Titan base or stats.'
        captured = {(s, p): v for s, p, v in raw}
        if any(type(captured.get(key)) is not int or captured[key] != value for key, value in FIXED.items()):
            return 'Native Titan skill, replenish or utility properties are missing.'
        vector = _vector(item, keys)
        if vector is None:
            return 'Ambiguous native Titan material roll.'
        native = all(type(v) is int and BOUNDS[k][0] <= v <= BOUNDS[k][1] for k, v in zip(keys, vector, strict=True))
        status, reason = (
            _outcome(policy, spec['definition'], item, keys, vector, verified_base_code=BASE_CODES[base])
            if native
            else ('unresolved', None)
        )
        expected_status = (
            'premium'
            if native
            and vector[0] == vector[1]
            and vector[0] >= THRESHOLDS[BASE_CODES[base]]
            and variant == ETHEREAL_LEGAL
            else 'unresolved'
        )
        if status != expected_status:
            return 'Native Titan base-specific disposition differs from the reviewed threshold.'
        expected = {
            'status': status,
            **({'material_stats': policy['trade_qualification']['material_stats']} if status == 'premium' else {}),
        }
        lines = [{'text': f'Trade: premium candidate — {reason}', 'tone': 'tier_high'}] if status == 'premium' else []
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Titan verdict and rendered text/color are not explicitly asserted.'
        seen.add((base, variant, vector))
    if not required <= seen:
        return 'Native/upgraded Titan rolls, paired damage or variant boundaries are not all executed.'
    return None

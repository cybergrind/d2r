"""Native Arachnid roll and report coverage, including unqualified lower rolls."""

from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _outcome, _vector
from pricing.knowledge.assessment.policies.market_ethereal_inference import BASE_CODE, IDENTITY, MODE, native_arachnid


BOUNDS = {'16:0': (90, 120)}
POINTS = {90, 109, 110, 119, 120}
VARIANTS = REQUIRED | {(True, False, 0, 'filled')}
FIXED = {(105, 0): 20, (127, 0): 1, (150, 0): 10, (77, 0): 5}
ROLLS = {
    16: ('ac%', 90, 120),
    105: ('cast2', 20, 20),
    127: ('allskills', 1, 1),
    150: ('slow', 10, 10),
    77: ('mana%', 5, 5),
}
SPECS = {
    16: ('item_armor_percent', '425', 13),
    105: ('item_fastercastrate', '520', 0),
    127: ('item_allskills', '587', 0),
    150: ('item_slow', '584', 0),
    77: ('item_maxmana_percent', '617', 11),
}


def specification(policy, variants, stat_specs):
    if len(variants) != 1 or not native_arachnid(variants[0]):
        return None
    definition, trade = variants[0], policy.get('trade_qualification', {})
    if (
        (policy.get('quality'), policy.get('name')) != IDENTITY
        or policy.get('variant_rules')
        or set(definition.get('roll_ranges', {})) != {str(k) for k in ROLLS}
        or trade.get('material_stats') != ['16:0']
        or trade.get('market_stat_properties') != {'16:0': '425'}
        or trade.get('ethereal_inference') != MODE
        or trade.get('default_status') != 'unresolved'
        or trade.get('default_evidence_ids') != []
        or any(
            trade.get(k)
            for k in ('compound_stats', 'property_choice', 'base_defense', 'total_defense', 'base_inference')
        )
    ):
        return None
    for stat, (prop, low, high) in ROLLS.items():
        row = definition['roll_ranges'][str(stat)]
        if (row.get('stat_id'), row.get('layer', 0), row.get('property'), row.get('min'), row.get('max')) != (
            stat,
            0,
            prop,
            low,
            high,
        ):
            return None
        if any(type(row.get(k)) is not int for k in ('stat_id', 'min', 'max')):
            return None
    for stat, (name, prop, operation) in SPECS.items():
        row = stat_specs.get(str(stat), {})
        if (
            (row.get('name'), row.get('property_id'), row.get('op')) != (name, prop, operation)
            or row.get('op_base') is not None
            or any(row.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        ):
            return None
    guard = {
        'all': [
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (
                ('ethereal', False),
                ('sockets', 0),
                ('socket_contents', 'empty'),
            )
        ]
    }
    validity = {
        'all': [
            guard['all'][0],
            {
                'all': [
                    {'op': 'stat_at_least', 'key': '16:0', 'value': 90},
                    {'not': {'op': 'stat_at_least', 'key': '16:0', 'value': 121}},
                ]
            },
            guard['all'][2],
            {'op': 'fact_eq', 'field': 'base_code', 'value': BASE_CODE},
            guard['all'][1],
        ]
    }
    bands = trade.get('bands', [])
    if (
        policy.get('valid_if') != validity
        or trade.get('valid_if') != guard
        or len(bands) != 1
        or bands[0].get('status') != 'premium'
        or bands[0].get('when') != {'op': 'stat_at_least', 'key': '16:0', 'value': 120}
    ):
        return None
    return {'definition': definition, 'bounds': dict(BOUNDS), 'points': {'16:0': set(POINTS)}, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    required = {(LEGAL, (ed,)) for ed in (*POINTS, None, 89, 121)}
    required.update((variant, (120,)) for variant in VARIANTS)
    seen = set()
    for item, checks, variant in cases:
        raw = item['raw_stats']
        if item.get('complete') is not False or len({tuple(r[:2]) for r in raw}) != len(raw):
            return 'Ambiguous Arachnid capture or unsupported complete-stat claim.'
        captured = {(s, p): v for s, p, v in raw}
        if any(type(captured.get(k)) is not int or captured[k] != v for k, v in FIXED.items()):
            return 'Native fixed Arachnid caster modifiers are missing.'
        vector = _vector(item, ('16:0',))
        if vector is None:
            return 'Ambiguous Arachnid ED roll.'
        native = type(vector[0]) is int and 90 <= vector[0] <= 120
        status, reason = (
            _outcome(policy, spec['definition'], item, ('16:0',), vector) if native else ('unresolved', None)
        )
        expected_status = 'premium' if variant == LEGAL and vector == (120,) else 'unresolved'
        if status != expected_status:
            return 'Arachnid disposition differs from its native perfect-roll boundary.'
        expected = {'status': status, **({'material_stats': ['16:0']} if status == 'premium' else {})}
        lines = [{'text': f'Trade: premium candidate — {reason}', 'tone': 'tier_high'}] if status == 'premium' else []
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Arachnid trade verdict and rendered reason/color are not explicitly asserted.'
        seen.add((variant, vector))
    if not required <= seen:
        return 'Arachnid native endpoints, former threshold or variant boundaries are not all executed.'
    return None

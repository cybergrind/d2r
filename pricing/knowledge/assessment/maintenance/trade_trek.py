"""Native ethereal Sandstorm Trek attribute-segment verification."""

from itertools import product

from pricing.knowledge.assessment.maintenance.trade_review_cases import (
    ETHEREAL_LEGAL as LEGAL,
    ETHEREAL_REQUIRED as VARIANTS,
)
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _collect, _outcome, _vector


IDENTITY = ('unique', 'Sandstorm Trek')
BOUNDS = {'0:0': (10, 15), '3:0': (10, 15), '16:0': (140, 170), '45:0': (40, 70)}
FIXED = {(96, 0): 20, (99, 0): 20, (154, 0): 50, (242, 0): 8, (252, 0): 5}
PROPERTIES = {
    16: ('ac%', 140, 170),
    96: ('move2', 20, 20),
    99: ('balance2', 20, 20),
    154: ('stamdrain', 50, 50),
    45: ('res-pois', 40, 70),
    0: ('str', 10, 15),
    3: ('vit', 10, 15),
}
STAT_SPECS = {
    0: ('strength', '437', 0),
    3: ('vitality', '582', 9),
    16: ('item_armor_percent', '425', 13),
    45: ('poisonresist', '401', 0),
    96: ('item_fastermovevelocity', '480', 0),
    99: ('item_fastergethitrate', '430', 0),
    154: ('item_staminadrainpct', '481', 0),
    252: ('item_replenish_durability', None, 0),
}


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    d = variants[0]
    base, game, trade = (
        d.get('base_definition', {}),
        d.get('game_definition', {}),
        policy.get('trade_qualification', {}),
    )
    code = d.get('base_code')
    if (
        (d.get('rarity'), d.get('name')) != IDENTITY
        or (policy.get('quality'), policy.get('name')) != IDENTITY
        or d.get('base_name') != 'Scarabshell Boots'
        or not code
        or base.get('code') != code
        or base.get('ultracode') != code
        or list(d.get('base_codes', ())) != [code]
        or game.get('code') != code
        or (base.get('type'), base.get('minac'), base.get('maxac'), base.get('gemsockets')) != ('boot', 56, 65, 0)
        or any(d.get(k) for k in ('native_socket_range', 'variable_per_level_effects', 'property_groups'))
        or d.get('fixed_per_level_effects') != [{'stat_id': 242, 'coefficient_raw': 8, 'denominator': 8}]
        or set(d.get('roll_ranges', {})) != {str(s) for s in PROPERTIES}
        or policy.get('variant_rules')
        or set(trade.get('material_stats', ())) != set(BOUNDS)
        or len(trade.get('material_stats', ())) != 4
        or trade.get('default_status') != 'candidate'
        or any(trade.get(k) for k in ('compound_stats', 'property_choice', 'base_defense', 'total_defense'))
    ):
        return None
    for stat, (prop, low, high) in PROPERTIES.items():
        r = d['roll_ranges'][str(stat)]
        if (r.get('stat_id'), r.get('layer', 0), r.get('property'), r.get('min'), r.get('max')) != (
            stat,
            0,
            prop,
            low,
            high,
        ) or any(type(r.get(k)) is not int for k in ('stat_id', 'min', 'max')):
            return None
    native = (
        ('ac%', 140, 170, None),
        ('move2', 20, 20, None),
        ('balance2', 20, 20, None),
        ('stam/lvl', None, None, 8),
        ('stamdrain', 50, 50, None),
        ('res-pois', 40, 70, None),
        ('rep-dur', None, None, 5),
        ('str', 10, 15, None),
        ('vit', 10, 15, None),
    )
    for slot in range(1, 13):
        if slot > len(native):
            if game.get(f'prop{slot}'):
                return None
            continue
        prop, low, high, parameter = native[slot - 1]
        if (game.get(f'prop{slot}'), game.get(f'min{slot}'), game.get(f'max{slot}')) != (prop, low, high):
            return None
        for field, expected in ((f'min{slot}', low), (f'max{slot}', high), (f'par{slot}', parameter)):
            if expected is None:
                if game.get(field) not in (None, '', 0):
                    return None
            elif type(game.get(field)) is not int or game[field] != expected:
                return None
    for stat, (name, prop, operation) in STAT_SPECS.items():
        r = stat_specs.get(str(stat), {})
        if (
            (r.get('name'), r.get('property_id'), r.get('op')) != (name, prop, operation)
            or r.get('op_base') is not None
            or any(r.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
        ):
            return None
    stamina = stat_specs.get('242', {})
    if (stamina.get('name'), stamina.get('op'), stamina.get('op_param'), stamina.get('op_base')) != (
        'item_stamina_perlevel',
        2,
        3,
        'level',
    ) or any(stamina.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits')):
        return None
    guard = {
        'all': [
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (('ethereal', True), ('sockets', 0), ('socket_contents', 'empty'))
        ]
    }
    threshold = {'all': [{'op': 'stat_at_least', 'key': key, 'value': 15} for key in ('0:0', '3:0')]}
    bands = trade.get('bands', [])
    if (
        trade.get('valid_if') != guard
        or len(bands) != 1
        or bands[0].get('when') != threshold
        or bands[0].get('status') != 'premium'
    ):
        return None
    points = {key: {lo, hi} for key, (lo, hi) in BOUNDS.items()}
    if not all(_collect(rule, BOUNDS, points) for rule in (policy['valid_if'], threshold)):
        return None
    return {'definition': d, 'bounds': dict(BOUNDS), 'points': points, 'variants': VARIANTS}


def case_gap(cases, policy, spec):
    keys = tuple(sorted(BOUNDS))
    maxima = tuple(BOUNDS[k][1] for k in keys)
    required = {(LEGAL, values) for values in product(*(spec['points'][k] for k in keys))}
    required.update((variant, maxima) for variant in VARIANTS)
    for index, key in enumerate(keys):
        for value in (None, BOUNDS[key][0] - 1, BOUNDS[key][1] + 1):
            vector = list(maxima)
            vector[index] = value
            required.add((LEGAL, tuple(vector)))
    seen = set()
    for item, checks, variant in cases:
        raw = item['raw_stats']
        if len({tuple(r[:2]) for r in raw}) != len(raw):
            return 'Ambiguous native Trek stat capture.'
        fixed = {(s, p): v for s, p, v in raw}
        if any(type(fixed.get(key)) is not int or fixed[key] != value for key, value in FIXED.items()):
            return 'Native fixed repair, movement, recovery or stamina modifiers are missing.'
        vector = _vector(item, keys)
        if vector is None:
            return 'Ambiguous native Trek material roll.'
        native = all(type(v) is int and BOUNDS[k][0] <= v <= BOUNDS[k][1] for k, v in zip(keys, vector, strict=True))
        status, reason = _outcome(policy, spec['definition'], item, keys, vector) if native else ('unresolved', None)
        if variant == LEGAL and native and status not in ('candidate', 'premium'):
            return 'A legal ethereal Trek roll branch lacks a trade disposition.'
        expected = {
            'status': status,
            **({'material_stats': policy['trade_qualification']['material_stats']} if status != 'unresolved' else {}),
        }
        label = 'premium candidate' if status == 'premium' else 'ordinary candidate'
        lines = (
            []
            if status == 'unresolved'
            else [{'text': f'Trade: {label} — {reason}', 'tone': 'tier_high' if status == 'premium' else 'tier_low'}]
        )
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Trek trade verdict and rendered attribute-segment text/color are not explicitly asserted.'
        seen.add((variant, vector))
    if not required <= seen:
        return 'Native Trek roll limits, 15/15 threshold or ethereal variant boundaries are not all executed.'
    return None

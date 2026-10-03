"""Native proof for the reviewed Opalvein single-choice trade configuration."""

from itertools import combinations, product

from pricing.knowledge.assessment.maintenance.trade_compound_rolls import verified_definition
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL, REQUIRED
from pricing.knowledge.assessment.maintenance.trade_scalar_jewelry import _collect, _outcome


CHOICES = (
    ('extra-mag', (357,), 3, 5),
    ('dmg%', (17, 18), 20, 40),
    ('extra-fire', (329,), 3, 5),
    ('extra-cold', (331,), 3, 5),
    ('extra-ltng', (330,), 3, 5),
    ('extra-pois', (332,), 3, 5),
)
FIXED = ((105, 0, 10), (195, 25487, 2))
RESISTS = (39, 41, 43, 45)
GUARANTEED = {
    105: ('cast1', 10, 10),
    **dict.fromkeys(RESISTS, ('res-all', 6, 8)),
    86: ('heal-kill', 1, 3),
    138: ('mana-kill', 1, 3),
}
MATERIAL = {'329:0', '331:0', '330:0', '86:0', '138:0', *(f'{s}:0' for s in RESISTS)}


def _ranges(rows, expected):
    return (
        len(rows) == len(expected)
        and {
            (r.get('stat_id'), r.get('layer', 0), r.get('property'), r.get('min'), r.get('max')) for r in rows.values()
        }
        == {(stat, 0, prop, low, high) for stat, (prop, low, high) in expected.items()}
        and all(type(r.get(k)) is int for r in rows.values() for k in ('stat_id', 'min', 'max'))
    )


def specification(policy, variants, stat_specs):
    if len(variants) != 1:
        return None
    d = variants[0]
    trade = policy.get('trade_qualification', {})
    if (
        (d.get('name'), d.get('base_name')) != ('Opalvein', 'Ring')
        or any(
            d.get(k)
            for k in (
                'native_socket_range',
                'base_defense_range',
                'variable_per_level_effects',
                'fixed_per_level_effects',
            )
        )
        or not _ranges(d.get('roll_ranges', {}), GUARANTEED)
        or len(d.get('property_groups', ())) != 1
        or trade.get('property_choice') != 'opalvein_elemental'
        or set(trade.get('choice_keys', ())) != {'329:0', '331:0'}
        or len(trade.get('choice_keys', ())) != 2
        or trade.get('compound_stats') != ['all_resistances']
        or not verified_definition(d, stat_specs, ('all_resistances',))
        or set(trade.get('material_stats', ())) != MATERIAL
        or len(trade.get('material_stats', ())) != len(MATERIAL)
        or trade.get('default_status') != 'candidate'
        or trade.get('bands') != []
        or policy.get('variant_rules')
    ):
        return None
    game = d['game_definition']
    expected = (
        ('att-skill', 2, 15, 'Flame Wave'),
        ('magdam-rand', 1, 1, None),
        ('cast1', 10, 10, None),
        ('res-all', 6, 8, None),
        ('heal-kill', 1, 3, None),
        ('mana-kill', 1, 3, None),
    )
    for slot in range(1, 13):
        if slot > len(expected):
            if game.get(f'prop{slot}'):
                return None
            continue
        prop, low, high, parameter = expected[slot - 1]
        if (game.get(f'prop{slot}'), game.get(f'min{slot}'), game.get(f'max{slot}')) != (prop, low, high):
            return None
        if type(game.get(f'min{slot}')) is not int or type(game.get(f'max{slot}')) is not int:
            return None
        if game.get(f'par{slot}') not in ((parameter,) if parameter else (None, '', 0)):
            return None
    group = d['property_groups'][0]
    native = group.get('game_definition', {})
    if (
        (group.get('code'), group.get('slot'), group.get('selection')) != ('magdam-rand', 2, 'single_scalar_choice')
        or type(native.get('PickMode')) is not int
        or native['PickMode'] != 1
        or len(group.get('choices', ())) != 6
    ):
        return None
    bounds = {f'{s}:0': (lo, hi) for s, (_, lo, hi) in GUARANTEED.items() if lo != hi}
    for slot, (prop, stats, low, high) in enumerate(CHOICES, 1):
        c = group['choices'][slot - 1]
        if c.get('property') != prop or not _ranges(c.get('roll_ranges', {}), dict.fromkeys(stats, (prop, low, high))):
            return None
        if (
            native.get(f'Prop{slot}'),
            native.get(f'ModMin{slot}'),
            native.get(f'ModMax{slot}'),
            native.get(f'Chance{slot}'),
        ) != (prop, low, high, 1):
            return None
        if any(type(native.get(f'{k}{slot}')) is not int for k in ('ModMin', 'ModMax', 'Chance')) or any(
            native.get(f'{k}{slot}') not in (None, '', 0) for k in ('ParMin', 'ParMax')
        ):
            return None
        bounds.update({f'{s}:0': (low, high) for s in stats})
    if any(native.get(f'Prop{i}') for i in range(7, 13)):
        return None
    for key in {*bounds, '105:0'}:
        stat = key.split(':')[0]
        spec = stat_specs.get(stat, {})
        if (
            any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op_param'))
            or spec.get('op') != (13 if stat in ('17', '18') else 0)
            or spec.get('op_base') is not None
        ):
            return None
    mappings = {
        '105': ('item_fastercastrate', '520'),
        '86': ('item_healafterkill', '721'),
        '138': ('item_manaafterkill', '511'),
        '357': ('passive_mag_mastery', '1879'),
        '329': ('passive_fire_mastery', '750'),
        '331': ('passive_cold_mastery', '747'),
        '330': ('passive_ltng_mastery', '743'),
        '332': ('passive_pois_mastery', '783'),
        '17': ('item_maxdamage_percent', None),
        '18': ('item_mindamage_percent', None),
    }
    if any(
        (stat_specs[s].get('name'), stat_specs[s].get('property_id')) != expected for s, expected in mappings.items()
    ):
        return None
    proc = stat_specs.get('195', {})
    if (proc.get('name'), proc.get('shift'), proc.get('encode'), proc.get('parameter_bits')) != (
        'item_skillonattack',
        0,
        2,
        16,
    ):
        return None
    points = {k: {lo, hi} for k, (lo, hi) in bounds.items()}
    if not all(_collect(rule, bounds, points) for rule in (policy['valid_if'], trade['valid_if'])):
        return None
    return {'definition': d, 'choices': CHOICES, 'bounds': bounds, 'points': points, 'supported': {'329:0', '331:0'}}


def _raw(stats, roll, resistance=6, life=1, mana=1):
    return tuple(
        sorted(
            (
                *FIXED,
                *((s, 0, roll) for s in stats),
                *((s, 0, resistance) for s in RESISTS),
                (86, 0, life),
                (138, 0, mana),
            )
        )
    )


def _required(spec):
    required = set()
    points = spec['points']
    for _, stats, _low, _high in CHOICES:
        rolls = set().union(*(points[f'{s}:0'] for s in stats))
        for roll, resist, life, mana in product(
            rolls, set().union(*(points[f'{s}:0'] for s in RESISTS)), points['86:0'], points['138:0']
        ):
            required.add((LEGAL, True, _raw(stats, roll, resist, life, mana)))
    for stat in (329, 331):
        raw = _raw((stat,), 3)
        required.update((variant, True, raw) for variant in REQUIRED)
        required.add((LEGAL, False, raw))
        for key in (stat, *RESISTS, 86, 138):
            low, high = spec['bounds'][f'{key}:0']
            for value in (None, low - 1, high + 1):
                changed = tuple((s, p, value if s == key else v) for s, p, v in raw if s != key or value is not None)
                required.add((LEGAL, True, changed))
        # Shared all-resistance must not be accepted as four independent rolls.
        required.add((LEGAL, True, tuple((s, p, 7 if s == 39 else v) for s, p, v in raw)))
    for left, right in combinations(CHOICES, 2):
        raw = tuple(sorted((*_raw(left[1], left[2]), *((s, 0, right[2]) for s in right[1]))))
        required.add((LEGAL, True, raw))
    return required


def case_gap(cases, policy, spec):
    required, seen = _required(spec), set()
    all_choice_keys = {s for _, stats, _, _ in CHOICES for s in stats}
    keys = tuple(sorted(spec['bounds']))
    for item, checks, variant in cases:
        if type(item.get('complete')) is not bool:
            return 'Unknown native capture completeness.'
        raw = tuple(sorted(tuple(r) for r in item['raw_stats']))
        if len({r[:2] for r in raw}) != len(raw) or any(type(v) is not int for row in raw for v in row):
            return 'Ambiguous native Opalvein stat capture.'
        if not set(FIXED) <= set(raw):
            return 'Native fixed casting and proc properties are missing.'
        values = {f'{s}:{p}': v for s, p, v in raw}
        selected = {s for s, p, _ in raw if s in all_choice_keys and p == 0}
        choice = next((stats for _, stats, _, _ in CHOICES if set(stats) == selected), ())
        native = (
            bool(choice)
            and all(
                key in values and low <= values[key] <= high
                for key, (low, high) in spec['bounds'].items()
                if int(key.split(':')[0]) in {*choice, *RESISTS, 86, 138}
            )
            and len({values.get(f'{s}:0') for s in choice}) == 1
        )
        supported = bool(choice) and {f'{s}:0' for s in choice} <= spec['supported']
        status, reason = ('unresolved', None)
        if native and supported and item['complete'] is True:
            status, reason = _outcome(policy, spec['definition'], item, keys, tuple(values.get(k) for k in keys))
            if variant == LEGAL and len({values[f'{s}:0'] for s in RESISTS}) == 1 and status != 'candidate':
                return 'A reviewed elemental branch lacks its trade disposition.'
        expected = {
            'status': status,
            **({'material_stats': policy['trade_qualification']['material_stats']} if status == 'candidate' else {}),
        }
        lines = [{'text': f'Trade: ordinary candidate — {reason}', 'tone': 'tier_low'}] if status == 'candidate' else []
        if checks.get('qualification') != expected or checks.get('lines') != lines:
            return 'Native choice verdict and rendered text/color are not explicitly asserted.'
        seen.add((variant, item['complete'], raw))
    if not required <= seen:
        return 'Native choice, shared rolls, missing/invalid stats or variant boundaries are not all executed.'
    return None

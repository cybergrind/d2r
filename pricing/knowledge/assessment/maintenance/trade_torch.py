"""Torch class-selection coverage alongside independent compound roll coverage."""

from itertools import product

from pricing.knowledge.assessment.domain.facts import thaw
from pricing.knowledge.assessment.maintenance import trade_scalar_jewelry
from pricing.knowledge.assessment.maintenance.trade_review_cases import LEGAL
from pricing.knowledge.assessment.policies.trade_class_skills import IDENTITY, specification as class_specification


def specification(policy, variants, stat_specs):
    if (policy.get('quality'), policy.get('name')) != IDENTITY or len(variants) != 1:
        return None
    try:
        class_spec = class_specification(policy.get('trade_qualification', {}))
    except KeyError, TypeError, ValueError:
        return None
    if class_spec is None or thaw(variants[0]) != thaw(class_spec[0]):
        return None
    scalar = trade_scalar_jewelry.specification(
        policy, variants, stat_specs, allowed_bases=('Large Charm',), compounds=('all_attributes', 'all_resistances')
    )
    if scalar is None:
        return None
    return {'definition': variants[0], 'scalar': scalar, 'classes': class_spec[1]}


def class_state(item):
    if item['complete'] is not True:
        return 'incomplete', None
    rows = [row for row in item['raw_stats'] if row[0] == 83]
    if not rows:
        return 'missing', None
    if len(rows) != 1:
        return ('duplicate' if len({tuple(r) for r in rows}) == 1 else 'multiple'), None
    _, layer, value = rows[0]
    if type(layer) is not int or not 0 <= layer <= 7:
        return 'invalid', None
    if type(value) is not int or value != 3:
        return ('low_bonus' if type(value) is int and value < 3 else 'high_bonus'), None
    return 'class', layer


def case_gap(cases, policy, spec):
    scalar = spec['scalar']
    keys = tuple(sorted(scalar[1]))
    maxima = tuple(scalar[1][key][1] for key in keys)
    allowed = spec['classes']
    grouped = {i: [] for i in allowed}
    invalid, unknown, examples = set(), set(), set()
    for item, checks, signature in cases:
        state, class_id = class_state(item)
        vector = trade_scalar_jewelry._vector(item, keys)
        if state == 'class' and class_id in allowed:
            grouped[class_id].append((item, checks, signature))
            if signature == LEGAL:
                examples.add((class_id, vector))
            continue
        if checks.get('qualification') != {'status': 'unresolved'} or checks.get('lines') != []:
            return 'Unverified or unreviewed Torch classes must not receive trade credit.'
        if signature == LEGAL:
            if state == 'class':
                unknown.add((class_id, vector))
            elif vector == maxima:
                invalid.add(state)
    if invalid != {'incomplete', 'missing', 'duplicate', 'multiple', 'invalid', 'low_bonus', 'high_bonus'}:
        return 'Incomplete, missing, ambiguous and invalid Torch class boundaries are not all executed.'
    required_unknown = {
        (class_id, tuple(attributes if int(key.split(':')[0]) < 4 else resists for key in keys))
        for class_id, attributes, resists in product(set(range(8)) - allowed, (10, 20), (10, 20))
    }
    if not required_unknown <= unknown:
        return 'Unreviewed Torch classes are not tested at both compound roll limits.'
    # Require replay of the actual asking tuples in addition to native extrema.
    for row in policy['trade_qualification']['market_evidence']:
        from pricing.knowledge.assessment.policies.trade_class_skills import market_class

        class_id = market_class(policy['trade_qualification'], row)
        vector = tuple(row['properties']['727' if int(key.split(':')[0]) < 4 else '441'] for key in keys)
        if (class_id, vector) not in examples:
            return 'An observed Torch class and roll combination is not executed.'
    for selected in grouped.values():
        if gap := trade_scalar_jewelry.case_gap(selected, policy, scalar):
            return gap
    return None

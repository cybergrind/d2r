"""Extra proof obligations for the narrowly reviewed native boot defense axis."""

from pricing.knowledge.assessment.policies.trade_base_defense import FORBIDDEN, MODE, definition_bounds


READY = (True, ())
REQUIRED_CONTEXTS = {(False, ()), *((True, (key,)) for key in FORBIDDEN)}


def verified_bounds(review, definition, stat_specs):
    spec = stat_specs.get('31', {})
    if (
        review.get('base_defense') != MODE
        or spec.get('name') != 'armorclass'
        or spec.get('property_id') != '399'
        or spec.get('op_base') is not None
        or any(spec.get(k) != 0 for k in ('shift', 'encode', 'parameter_bits', 'op', 'op_param'))
    ):
        return None
    return definition_bounds(definition)


def case_context(item):
    native = {f'{stat}:{layer}' for stat, layer, _ in item['raw_stats']}
    return item.get('complete'), tuple(key for key in FORBIDDEN if key in native)

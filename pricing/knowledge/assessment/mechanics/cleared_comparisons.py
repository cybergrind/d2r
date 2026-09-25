"""Equipment contracts after destroying fully verified fixed socket fillers."""

from dataclasses import replace

from pricing.knowledge.assessment.domain.comparison_requests import ComparisonRequest
from pricing.knowledge.assessment.domain.preparation import PreparationOption
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.handlers.intrinsic import fixed_properties
from pricing.knowledge.assessment.handlers.socket_fillers import compare_equipment_sockets, compare_named_sockets
from pricing.knowledge.assessment.mechanics.preparation_costs import with_costs


def cleared_item_request(facts, contract):
    # The existing bounded contribution proof excludes runewords, unknown jewels,
    # incomplete identities, impossible totals and unexplained innate bonuses.
    definition = None
    if facts.runeword or contract.policy not in ('base', 'affixed', 'named'):
        return ()
    if contract.policy == 'named':
        definition, _ = resolve_named_definition(facts)
        if definition is None:
            return ()
        comparison = compare_named_sockets(facts, definition, contract.family)
    else:
        comparison = compare_equipment_sockets(facts, contract.family, contract.policy)
    if comparison is None:
        return ()
    properties = dict(contract.properties)
    for key, row in comparison.facts.stats.items():
        original = facts.stats[key]
        if row['value'] == original['value']:
            continue
        prop = original['market_property']
        if row['value'] == 0:
            properties.pop(prop, None)
        else:
            properties[prop] = row['value']
    intrinsic = dict(contract.intrinsic_properties)
    if definition is not None:
        # Fixed bonuses obscured by a filler become fixed again after clearing.
        # This derived view is not an observed stat capture.
        innate = replace(comparison.facts, properties=properties)
        intrinsic.update(fixed_properties(innate, definition.get('roll_ranges', {})))
    destination = replace(
        contract,
        socket_contents='empty',
        socket_payload=(),
        properties=properties,
        intrinsic_properties=intrinsic,
    )
    action = with_costs(
        PreparationOption('empty sockets', facts.sockets, 'clear_sockets', 'possible', destroys_contents=True),
        facts,
    ).to_dict()
    action['destroyed_items'] = list(comparison.payload)
    return (
        ComparisonRequest(
            'clear_sockets',
            'empty_base_after_clearing' if contract.policy == 'base' else 'item_after_clearing',
            destination.to_dict(),
            state='prepared',
            preparation=action,
        ),
    )

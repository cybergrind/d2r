from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.definitions import named_definitions
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts, scalar_properties


def wraithstep(tree=56):
    definition = named_definitions()['unique', 'Wraithstep']
    stats = {
        f'{spec["stat_id"]}:{spec.get("layer", 0)}': {'status': 'decoded', 'value': spec['min']}
        for spec in definition['roll_ranges'].values()
    }
    stats[f'188:{tree}'] = {'status': 'decoded', 'value': 1}
    return replace(facts('Mirrored Boots', 'unique', 'Wraithstep'), stats=stats, properties=scalar_properties(stats))


@pytest.mark.parametrize('layer', [56, 57, 58])
def test_random_tree_must_be_captured_and_projected_before_named_comparison(layer):
    candidate = wraithstep(layer)
    contract, gaps = NamedHandler().contract(candidate, 'armor')
    assert contract is None
    assert any('random skill' in gap.lower() for gap in gaps)
    projected = replace(candidate, properties={**candidate.properties, str(1546 + layer - 56): 1})
    contract, gaps = NamedHandler().contract(projected, 'armor')
    assert contract is not None, gaps
    missing = replace(projected, stats={k: v for k, v in candidate.stats.items() if not k.startswith('188:')})
    assert NamedHandler().contract(missing, 'armor')[0] is None
    multiple = replace(
        projected, stats=dict(candidate.stats) | {f'188:{56 if layer != 56 else 57}': {'status': 'decoded', 'value': 1}}
    )
    assert NamedHandler().contract(multiple, 'armor')[0] is None
    assert NamedHandler().contract(replace(projected, capture_complete=False), 'armor')[0] is None


@pytest.mark.parametrize(
    'row',
    [
        {'status': 'decoded', 'value': 2},
        {'status': 'unresolved', 'value': 1},
        {'status': 'decoded', 'value': float('nan')},
    ],
)
def test_random_skill_contract_rejects_invalid_or_unresolved_native_bonus(row):
    candidate = wraithstep()
    candidate = replace(candidate, stats=dict(candidate.stats) | {'188:56': row}, properties={'1546': row['value']})
    assert NamedHandler().contract(candidate, 'armor')[0] is None

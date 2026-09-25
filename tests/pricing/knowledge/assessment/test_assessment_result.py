import pytest

from pricing.knowledge.assessment.adapters.assessment import legacy_payload
from pricing.knowledge.assessment.engine import assess, assess_result
from tests.pricing.knowledge.assessment.test_base_use import capture


def test_typed_result_owns_detached_outcomes_and_legacy_projection():
    observation = capture()
    result = assess_result(observation, profiles=[])
    expected = assess(observation, profiles=[])
    assert legacy_payload(result) == expected
    observation['item']['base_name'] = 'Changed input'
    assert result.facts.base_name == 'Giant Thresher'
    with pytest.raises(TypeError):
        result.base_uses[0]['status'] = 'changed'
    payload = legacy_payload(result)
    payload['base_uses'][0]['missing'].append('mutated output')
    assert 'mutated output' not in legacy_payload(result)['base_uses'][0]['missing']
    assert result.generation.definitions == expected['definition_generation']


def test_comparison_contract_is_deeply_immutable_before_becoming_a_request():
    from pricing.knowledge.assessment.domain.contracts import ComparableContract

    properties = {'93': 20}
    intrinsic = {'591': 1}
    contract = ComparableContract(
        1, 'named', 'weapon', 'Fixture', 'unique', False, 0, 'empty', properties, intrinsic_properties=intrinsic
    )
    properties['93'] = 40
    intrinsic['591'] = 0
    assert contract.to_dict()['properties'] == {'93': 20}
    assert contract.to_dict()['intrinsic_properties'] == {'591': 1}
    with pytest.raises(TypeError):
        contract.properties['93'] = 40

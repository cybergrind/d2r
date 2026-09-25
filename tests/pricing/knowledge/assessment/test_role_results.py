from dataclasses import FrozenInstanceError, replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_role_result_freezes_rule_and_preparation_evidence_before_projection():
    from pricing.knowledge.assessment.adapters.roles import legacy_role
    from pricing.knowledge.assessment.profiles import assess_role_results, assess_roles

    profile = next(p for p in build()['profiles'] if p['id'] == 'strafe-amazon-deaths-guard-upgrade')
    item = replace(facts('Sash', 'set', "Death's Guard"), stats={'153:0': {'status': 'decoded', 'value': 1}})
    result = assess_role_results(item, [profile], {'player_class': 'Amazon'})[0]
    assert result.status == 'partial'
    expected = assess_roles(item, [profile], {'player_class': 'Amazon'})[0]
    assert legacy_role(result) == expected
    profile['source']['review'] = 'Mutated caller evidence'
    assert legacy_role(result)['source'] == expected['source']
    with pytest.raises(FrozenInstanceError):
        result.status = 'matched'
    with pytest.raises(TypeError):
        result.dependencies[0]['status'] = 'true'
    output = legacy_role(result)
    output['dependencies'][0]['preparation']['steps'][0]['resources'].clear()
    assert legacy_role(result) == expected


def test_engine_retains_typed_role_results_and_projects_the_same_public_payload():
    from pricing.knowledge.assessment.adapters.assessment import legacy_payload
    from pricing.knowledge.assessment.domain.roles import RoleAssessment
    from pricing.knowledge.assessment.engine import assess, assess_result
    from tests.pricing.knowledge.assessment.test_base_use import capture

    profile = next(p for p in build()['profiles'] if p['id'] == 'strafe-amazon-deaths-guard-upgrade')
    extraction = capture('Sash', quality='set', sockets=0, ethereal=False)
    extraction['item']['name'] = "Death's Guard"
    result = assess_result(extraction, profiles=[profile], loadout={'player_class': 'Amazon'})
    assert isinstance(result.roles[0], RoleAssessment)
    assert legacy_payload(result) == assess(extraction, profiles=[profile], loadout={'player_class': 'Amazon'})

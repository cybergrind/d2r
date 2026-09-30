from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_rare_weapon import CONTEXT, ITEM, ROLE


def test_native_low_roll_rare_axe_has_a_reviewed_zeal_configuration():
    role = next(r for r in build()['profiles'] if r['id'] == ROLE)
    result = assess_role_results(normalize(ITEM.capture()), [role], CONTEXT)
    assert result[0].rule_trace['truth'].value == 'true'
    assert not result[0].failed
    assert result[0].preferences[0]['status'].value == 'false'

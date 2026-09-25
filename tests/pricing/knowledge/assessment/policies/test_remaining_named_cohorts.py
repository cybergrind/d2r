from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def item(name, values):
    base = 'Amulet' if name == 'Metalgrid' else 'Colossal Jewel'
    return replace(
        facts(base, 'unique', name), stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()}
    )


@pytest.mark.parametrize(('ar', 'res'), [(400, 25), (449, 35), (450, 34)])
def test_metalgrid_other_cohort_has_medium_tier_without_invented_perfect_premium(ar, res):
    observed = item('Metalgrid', {31: 324, 19: ar, **dict.fromkeys((39, 41, 43, 45), res)})
    assert assess_tier(observed)['tier'] == 'med'
    perfect = item('Metalgrid', {31: 350, 19: 450, **dict.fromkeys((39, 41, 43, 45), 35)})
    assert assess_tier(perfect)['status'] == 'pending_review'
    assert assess_tier(perfect)['tier'] is None
    assert assess_tier(replace(observed, ethereal=True))['tier'] is None
    assert assess_tier(replace(observed, sockets=1))['tier'] is None
    assert assess_tier(replace(observed, stats={}))['tier'] is None


def test_guardian_light_medium_cohort_requires_known_legal_rolls():
    values = {357: 8, 358: 6, 85: 3, 80: 18, 79: 25}
    observed = item("Guardian's Light", values)
    assert assess_tier(observed)['tier'] == 'med'
    assert assess_tier(item("Guardian's Light", {**values, 357: 11}))['tier'] is None
    assert assess_tier(item("Guardian's Light", {**values, 358: 4}))['tier'] is None
    assert assess_tier(replace(observed, socket_contents='filled'))['tier'] is None
    assert assess_tier(replace(observed, stats={}))['tier'] is None
    # Perfect rolls do not turn an unsegmented asking cohort into a supported high tier.
    assert assess_tier(item("Guardian's Light", {357: 10, 358: 10, 85: 5, 80: 35, 79: 50}))['tier'] == 'med'

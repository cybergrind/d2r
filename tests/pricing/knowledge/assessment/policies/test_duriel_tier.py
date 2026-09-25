from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('ed', [183, 190, 196, 197])
def test_original_ethereal_duriel_reviewed_segment(ed):
    item = replace(
        facts('Cuirass', 'unique', "Duriel's Shell"),
        ethereal=True,
        stats={'16:0': {'status': 'decoded', 'value': ed}},
    )
    result = assess_tier(item)
    assert result['status'] == 'reviewed'
    assert result['tier'] == 'med'
    assert result['source']['locator'] == '/duriel-ethereal-original-nonperfect'
    for changed in (
        replace(item, ethereal=False),
        replace(item, stats={'16:0': {'status': 'decoded', 'value': 182}}),
        replace(item, stats={'16:0': {'status': 'decoded', 'value': 198}}),
        replace(item, socket_contents='filled'),
        replace(item, base_code=facts('Great Hauberk').base_code),
    ):
        assert assess_tier(changed)['tier'] is None
    assert assess_tier(replace(item, ethereal=None))['status'] == 'conditional'
    assert assess_tier(replace(item, stats={}))['status'] == 'conditional'

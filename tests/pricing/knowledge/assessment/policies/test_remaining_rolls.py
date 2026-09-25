from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def item(base, name, values):
    return replace(facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})


@pytest.mark.parametrize(('defense', 'premium'), [(98, False), (129, False), (130, True), (141, True)])
def test_shako_defense_segment_keeps_med_tier_and_specific_premium(defense, premium):
    result = assess_tier(item('Shako', 'Harlequin Crest', {'31:0': defense}))
    assert result['tier'] == 'med'
    assert bool(result['reasons']) is premium


@pytest.mark.parametrize(('mf', 'tier'), [(20, 'med'), (37, 'med'), (38, 'high'), (40, 'high')])
def test_gheed_magic_find_segment(mf, tier):
    assert assess_tier(item('Grand Charm', "Gheed's Fortune", {'80:0': mf}))['tier'] == tier


def test_ravenlore_uses_native_max_not_socket_augmented_market_values():
    assert assess_tier(item('Sky Spirit', 'Ravenlore', {'333:0': 19}))['tier'] == 'low'
    assert assess_tier(item('Sky Spirit', 'Ravenlore', {'333:0': 20}))['tier'] == 'high'
    assert assess_tier(item('Sky Spirit', 'Ravenlore', {'333:0': 25}))['tier'] is None


def test_eschuta_lightning_premium_requires_class_skills_and_leaves_other_variants_pending():
    base = item('Eldritch Orb', "Eschuta's Temper", {'83:1': 3, '330:0': 20})
    assert assess_tier(base)['tier'] == 'high'
    for values in ({'83:1': 2, '330:0': 20}, {'83:1': 3, '330:0': 19}, {}):
        other = item('Eldritch Orb', "Eschuta's Temper", values)
        assert assess_tier(other)['tier'] is None
    assert assess_tier(replace(base, socket_contents='filled'))['tier'] is None

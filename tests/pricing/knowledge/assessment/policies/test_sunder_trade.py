from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.fixture(params=[('Flame Rift', 39, 189), ('Crack of the Heavens', 41, 190)])
def charm(request):
    name, resist, sunder = request.param
    return Item('Grand Charm', 'unique', name, ((sunder, 0, 300), (resist, 0, -70)))


@pytest.mark.parametrize('penalty', [-90, -71, -70])
def test_original_sunder_legal_penalty_is_ordinary_without_automatic_perfect_premium(charm, penalty):
    raw = (charm.raw_stats[0], (*charm.raw_stats[1][:2], penalty))
    assert assess_trade_qualification(normalize(replace(charm, raw_stats=raw).capture()))['status'] == 'candidate'


@pytest.mark.parametrize('penalty', [None, -91, -69, 70, 90])
def test_original_sunder_native_capture_must_contain_a_legal_negative_penalty(charm, penalty):
    raw = charm.raw_stats[:1] if penalty is None else (charm.raw_stats[0], (*charm.raw_stats[1][:2], penalty))
    assert assess_trade_qualification(normalize(replace(charm, raw_stats=raw).capture()))['status'] == 'unresolved'


def test_original_sunder_tier_does_not_accept_impossible_ethereal_or_socketed_charms(charm):
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    for changes in ({'ethereal': True}, {'sockets': 1}):
        assert assess_tier(normalize(replace(charm, **changes).capture()))['tier'] is None


@pytest.mark.parametrize(
    ('name', 'stat', 'sunder', 'minimum', 'maximum', 'premium'),
    [
        ('Cold Rupture', 43, 187, -90, -70, True),
        ('Rotting Fissure', 45, 191, -90, -70, False),
        ('Black Cleft', 37, 193, -65, -45, True),
        ('Bone Break', 36, 192, -20, -10, True),
    ],
)
def test_remaining_sunders_have_item_specific_penalty_segments(name, stat, sunder, minimum, maximum, premium):
    from pricing.knowledge.assessment.policies.named_tiers import assess_tier

    item = Item('Grand Charm', 'unique', name, ((sunder, 0, 300), (stat, 0, maximum)))
    for penalty in (minimum, maximum - 1, maximum):
        specimen = replace(item, raw_stats=((sunder, 0, 300), (stat, 0, penalty)))
        expected = 'premium' if premium and penalty == maximum else 'candidate'
        assert assess_trade_qualification(normalize(specimen.capture()))['status'] == expected
    for penalty in (None, minimum - 1, maximum + 1, -maximum):
        stats = ((sunder, 0, 300),) + (((stat, 0, penalty),) if penalty is not None else ())
        assert assess_trade_qualification(normalize(replace(item, raw_stats=stats).capture()))['status'] == 'unresolved'
    for changes in ({'ethereal': True}, {'sockets': 1}):
        assert assess_tier(normalize(replace(item, **changes).capture()))['tier'] is None

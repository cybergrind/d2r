from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def item(name, totals, jewel):
    bases = {"Griffon's Eye": 'Diadem', "Nightwing's Veil": 'Spired Helm', "Death's Fathom": 'Dimensional Shard'}

    def stats(values):
        return {k: {'status': 'decoded', 'value': v} for k, v in values.items()}

    return replace(
        facts(bases[name], 'unique', name),
        sockets=1,
        socket_contents='filled',
        stats=stats(totals),
        socket_items=[{'name': 'Jewel', 'item_type': 'jewl', 'stats_complete': True, 'stats': stats(jewel)}],
    )


@pytest.mark.parametrize(
    ('name', 'totals', 'jewel', 'tier'),
    [
        ("Death's Fathom", {'331:0': 35}, {'331:0': 5}, 'high'),
        ("Death's Fathom", {'331:0': 29}, {'331:0': 5}, 'med'),
        ("Nightwing's Veil", {'331:0': 20, '2:0': 20}, {'331:0': 5}, 'high'),
        ("Nightwing's Veil", {'331:0': 19, '2:0': 20}, {'331:0': 5}, 'low'),
        ("Nightwing's Veil", {'331:0': 15, '2:0': 25}, {'2:0': 5}, 'high'),
        ("Griffon's Eye", {'330:0': 20, '334:0': 25}, {'330:0': 5, '334:0': 5}, 'high'),
    ],
)
def test_socketed_elemental_tiers_preserve_the_intrinsic_threshold(name, totals, jewel, tier):
    captured = item(name, totals, jewel)
    result = assess_tier(captured)
    assert result['tier'] == tier
    for key, total in totals.items():
        assert result['intrinsic_rolls'][key]['intrinsic'] == total - jewel.get(key, 0)
        assert captured.stats[key]['value'] == total


def test_griffon_perfect_claim_uses_both_intrinsic_rolls():
    result = assess_tier(item("Griffon's Eye", {'330:0': 19, '334:0': 24}, {'330:0': 5, '334:0': 5}))
    assert result['tier'] == 'high'
    assert result['reasons'] == []
    result = assess_tier(item("Griffon's Eye", {'330:0': 20, '334:0': 24}, {'330:0': 5, '334:0': 5}))
    assert 'One perfect' in result['reasons'][0]


@pytest.mark.parametrize(
    ('name', 'totals', 'jewel'),
    [
        ("Death's Fathom", {'331:0': 36}, {'331:0': 5}),
        ("Nightwing's Veil", {'331:0': 20, '2:0': 9}, {'331:0': 5}),
        ("Griffon's Eye", {'330:0': 21, '334:0': 25}, {'330:0': 5, '334:0': 5}),
    ],
)
def test_out_of_range_intrinsic_rolls_stay_unassessed(name, totals, jewel):
    assert assess_tier(item(name, totals, jewel))['tier'] is None


def test_unknown_secondary_jewel_stat_does_not_justify_nightwing_tier():
    captured = item("Nightwing's Veil", {'331:0': 20, '2:0': 20}, {'331:0': 5})
    child = dict(captured.socket_items[0])
    child['stats'] = {**child['stats'], '2:0': {'status': 'unresolved'}}
    assert assess_tier(replace(captured, socket_items=[child]))['tier'] is None


def test_socket_policy_cannot_leave_a_tier_dependent_stat_unadjusted():
    import json

    from pricing.knowledge.artifacts import read_artifact
    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(read_artifact(RULES))
    rule = next(p for p in document['policies'] if p['name'] == "Nightwing's Veil")
    rule['intrinsic_socket_stats'] = ['331:0']
    with pytest.raises(ValueError, match='tier-dependent'):
        _policies(json.dumps(document))

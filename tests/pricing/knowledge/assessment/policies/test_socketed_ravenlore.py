from dataclasses import replace

import pytest

from pricing.knowledge.assessment.policies.named_tiers import assess_tier
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def raven(total=25, contribution=5):
    child = {
        'name': 'Rainbow Facet',
        'item_type': 'jewl',
        'stats_complete': True,
        'stats': {'333:0': {'status': 'decoded', 'value': contribution}},
    }
    return replace(
        facts('Sky Spirit', 'unique', 'Ravenlore'),
        sockets=1,
        socket_contents='filled',
        socket_items=[child],
        stats={'333:0': {'status': 'decoded', 'value': total}},
    )


@pytest.mark.parametrize(('total', 'contribution', 'tier'), [(25, 5, 'high'), (23, 3, 'high'), (24, 5, 'low')])
def test_socketed_tier_uses_intrinsic_pierce_without_mutating_capture(total, contribution, tier):
    item = raven(total, contribution)
    result = assess_tier(item)
    assert result['tier'] == tier
    assert result['intrinsic_rolls']['333:0'] == {
        'observed': total,
        'socket': contribution,
        'intrinsic': total - contribution,
    }
    assert item.stats['333:0']['value'] == total
    assert item.socket_contents == 'filled'
    from inventory_tracking.appraisal.sections import tier_lines

    assert 'before socket additions' in tier_lines({'assessment': {'trade_tier': result}})[0]


@pytest.mark.parametrize(
    'change',
    [
        'missing-child',
        'unknown-occupancy',
        'incomplete-child',
        'unknown-type',
        'unresolved',
        'bad-total',
        'incomplete-parent',
    ],
)
def test_unverified_contribution_cannot_promote_the_item(change):
    item = raven()
    if change == 'missing-child':
        item = replace(item, socket_items=[])
    elif change == 'unknown-occupancy':
        item = replace(item, sockets=2)
    elif change == 'incomplete-parent':
        item = replace(item, capture_complete=False)
    elif change == 'bad-total':
        item = raven(30)
    else:
        child = dict(item.socket_items[0])
        if change == 'incomplete-child':
            child.update(stats_complete=False)
        elif change == 'unknown-type':
            child.pop('item_type')
        else:
            child['stats'] = {'333:0': {'status': 'unresolved', 'value': 5}}
        item = replace(item, socket_items=[child])
    assert assess_tier(item)['tier'] is None


def test_complete_jewel_without_fire_pierce_contributes_zero():
    item = raven(20)
    child = {**item.socket_items[0], 'name': 'Other Jewel', 'stats': {}}
    result = assess_tier(replace(item, socket_items=[child]))
    assert result['tier'] == 'high'
    assert result['intrinsic_rolls']['333:0']['socket'] == 0


@pytest.mark.parametrize('kind', ['rune', 'gem'])
def test_recipient_dependent_payloads_are_not_treated_as_jewels(kind):
    item = raven(20)
    child = {**item.socket_items[0], 'item_type': kind, 'stats': {}}
    assert assess_tier(replace(item, socket_items=[child]))['tier'] is None

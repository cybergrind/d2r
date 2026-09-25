from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def diamond_shield():
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Perfect Diamond')
    return replace(
        facts('Large Shield'),
        sockets=3,
        socket_contents='filled',
        socket_items=[
            {'name': gem['name'], 'base_code': gem['code'], 'unit_id': i + 1, 'position': i} for i in range(3)
        ],
        stats={f'{s}:0': {'status': 'decoded', 'value': 57} for s in (39, 41, 43, 45)},
    )


def test_three_perfect_diamonds_are_conditional_resistance_alternative():
    uses = assess_leveling(diamond_shield())
    assert len(uses) == 1
    assert uses[0]['source']['locator'] == '/generic_patterns/7'
    assert uses[0]['status'] == 'conditional'
    assert "Ancient's Pledge" in uses[0]['conditions'][0]
    assert uses[0]['requirements_fit']['status'] == 'unknown'


@pytest.mark.parametrize(
    'change',
    ['partial', 'wrong_gem', 'duplicate', 'wrong_slot', 'word', 'low_resist', 'unknown_resist', 'conflict', 'empty'],
)
def test_incomplete_or_conflicting_diamond_setup_does_not_claim_use(change):
    item = diamond_shield()
    if change == 'partial':
        item = replace(item, socket_items=item.socket_items[:2])
    elif change == 'wrong_gem':
        item = replace(item, socket_items=[{**c, 'base_code': 'unverified'} for c in item.socket_items])
    elif change == 'duplicate':
        item = replace(item, socket_items=[{**c, 'unit_id': 1} for c in item.socket_items])
    elif change == 'wrong_slot':
        item = replace(item, item_type='tors')
    elif change == 'word':
        item = replace(item, runeword="Ancient's Pledge")
    elif change == 'low_resist':
        item = replace(item, stats={**item.stats, '39:0': {'status': 'decoded', 'value': 56}})
    elif change == 'unknown_resist':
        item = replace(item, stats={k: v for k, v in item.stats.items() if k != '39:0'})
    elif change == 'conflict':
        item = replace(item, gaps=['Duplicate native stat 39:0.'])
    else:
        item = replace(item, socket_contents='empty')
    assert not assess_leveling(item)

"""Layer 2 of the loot design (inventory_tracking/loot/value.py): worth, tiers, the rolls that matter, copies."""

from dataclasses import replace

import pytest

from inventory_tracking.identify import service
from inventory_tracking.loot import value
from inventory_tracking.loot.facts import Owner
from inventory_tracking.loot.value import CollectionCopies, RollSpec, better_than, tier_of
from tests.inventory_tracking.loot.test_valuables import GOBLIN, facts_of


def test_value_ist_moved_to_the_loot_layers_and_the_old_import_still_works():
    assert service.value_ist is value.value_ist


@pytest.mark.parametrize(
    ('worth', 'verdict', 'tier'),
    [(1.0, 'slow', 'expensive'), (0.65, 'slow', 'cheap'), (0.2, 'sell', 'worthless'), (None, 'vendor', 'worthless'),
     (0.6, 'vendor', 'worthless'), (None, None, 'unknown'), (None, 'check', 'unknown')],
)  # fmt: skip
def test_the_tiers(worth, verdict, tier):
    assert tier_of(worth, verdict) == tier


def test_better_is_better_than_every_copy_and_a_tie_on_mixed_rolls_is_not():
    andy = {'base': 'Demonhead', 'code': 'usk', 'quality': 'unique', 'name': "Andariel's Visage"}
    specs = (RollSpec('0:0', 'Strength', 25, 30), RollSpec('60:0', 'Life stolen', 8, 10))
    new = facts_of({**andy, 'rolls': {'0:0': 30, '60:0': 8}})
    tie = facts_of({**andy, 'rolls': {'0:0': 25, '60:0': 10}}, 2, owner=Owner.PLAYER)
    worse = facts_of({**andy, 'rolls': {'0:0': 26, '60:0': 8}}, 3, owner=Owner.PLAYER)
    assert better_than(new, [worse], specs).better
    found = better_than(new, [worse, tie], specs)
    assert not found.better
    assert found.lines == ('Strength 30 vs 25, 26', 'Life stolen 8 vs 8, 10')
    eth = facts_of({**andy, 'ethereal': True, 'rolls': {'0:0': 25, '60:0': 8}}, 4, owner=Owner.PLAYER)
    assert better_than(new, [eth], specs).copies == 0  # another item


def test_the_rolls_that_matter_come_from_the_read_without_a_want():
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    found = value.matters_for(toe, ())
    assert [(spec.key, spec.low, spec.high) for spec in found] == [('16:0', 50, 60)]


def test_owned_copies_cannot_be_told_without_a_read():
    facts = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    assert CollectionCopies().copies(replace(facts, observation=None)) is None

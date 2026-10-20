"""The ground judge (inventory_tracking/loot/ground_judge.py) on the cases where its shadow left what today's GOOD
pickup (macros/pickmode.py `sure`) picks, 2026-10-20 (inventory_tracking/runs/alt-d/20261020T*/probe.log, `loot:
shadow: ground`): the Worldstone Shards, Wirt's Leg and a unique whose quality was not read yet (Waterwalk,
14:35:22). The acceptance cases with a ground aspect run in test_valuables.py."""

import pytest

from inventory_tracking.game.records import NAMED, VALUABLE, Drop, Rolls, prized
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import ground_judge
from inventory_tracking.loot.facts import from_drop
from inventory_tracking.loot.ground_judge import Then, base_verdict, judge, material
from inventory_tracking.loot.today import judge as today_judge
from inventory_tracking.macros.pickmode import sure


def class_of(code: str) -> int:
    return next(int(txt) for txt, row in metadata()['bases'].items() if row.get('code') == code)


def drop(code: str, source: str, quality: int, *, marked: bool = True, rolls: Rolls | None = None) -> Drop:
    txt = class_of(code)
    name = metadata()['bases'][str(txt)]['name']
    return Drop(1, 0.0, 0.0, name, VALUABLE, (1, 1), prized(source, marked=marked), source, txt, quality, rolls)


@pytest.mark.parametrize('code', ['xa1', 'xa2', 'xa3', 'xa4', 'xa5'])
def test_every_worldstone_shard_is_picked_as_the_good_pickup_picks_it(code):
    found = drop(code, 'material', 2)
    verdict = judge(from_drop(found))
    assert sure(found)
    assert (verdict.pick, verdict.klass, verdict.then) == (True, 'G1', Then.KEEP)
    assert verdict.must_have  # marked: the guard holds the game for it, as for today's prized drop
    assert material(from_drop(found).code) == 'shards'


def test_wirts_leg_is_picked_and_a_second_left_while_one_is_had():
    found = drop('leg', 'material', 2)
    facts = from_drop(found)
    assert sure(found)
    assert judge(facts).pick
    assert judge(facts).reason == 'a material (leg)'
    left = judge(facts, had=frozenset({found.txt}))
    assert not left.pick
    assert left.reason == 'one is had already: the game takes no second'


def test_a_unique_whose_quality_is_not_read_is_picked_to_identify():
    # 14:35:22: "unique Sharkskin Boots "Waterwalk" ... taken (unique)" / shadow "unread Sharkskin Boots: new leave"
    found = drop('xvb', 'unique', 0)
    verdict = judge(from_drop(found))
    assert sure(found)
    assert (verdict.pick, verdict.klass, verdict.then, verdict.must_have) == (True, 'G2', Then.IDENTIFY, True)


def test_an_unmarked_unread_item_is_still_left():
    found = drop('xvb', 'shown', 0, marked=False)
    assert not sure(found)
    assert not judge(from_drop(found)).pick


def test_the_marks_catch_all_is_not_in_the_live_base_verdict():
    # macros/pickmode.py `ground_base` (M5) asks `base_verdict`: a white base no row picks stays left, marked or not
    white = drop('uit', 'shown', 2, rolls=Rolls(3, ()))
    marked = Drop(white.unit_id, 0.0, 0.0, white.label, VALUABLE, white.size, True, NAMED, white.txt, 2, white.rolls)
    for found in (white, marked):
        verdict = base_verdict(from_drop(found))
        assert verdict is None or not verdict.pick


def test_todays_judge_and_the_new_one_agree_on_the_logged_materials(monkeypatch):
    # (the unread unique's 'unique' source is not in ItemFacts, so loot/today.py cannot tell it: `sure` is asked above)
    monkeypatch.setattr(ground_judge, 'BASES', True)
    for found in (drop('xa4', 'material', 2), drop('leg', 'material', 2)):
        facts = from_drop(found)
        assert judge(facts).pick == today_judge(facts).pick, found.label

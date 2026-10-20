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


def claw(code: str, skills: tuple[tuple[int, int], ...], sockets: int = 0, quality: int = 2) -> Drop:
    """A white claw as the ground read gives it (game/records.py Rolls: skills as (skill id, level))."""
    return drop(code, 'shown', quality, marked=False, rolls=Rolls(sockets, skills))


@pytest.mark.parametrize(
    ('found', 'label'),
    [
        (claw('9tw', ((280, 3),), 3), 'White Greater / Runic Talons 3os/0os +3 Phoenix Strike'),  # W1
        (claw('7tw', ((271, 3), (263, 3))), 'White Greater / Runic Talons 3os/0os +3 Lightning Sentry'),  # W2
        (claw('9tw', ((269, 3),), 3, quality=3), 'White Greater / Runic Talons 3os/0os +3 Claws of Thunder'),  # W3
    ],
)
def test_a_fast_white_claw_with_a_paid_plus3_is_picked_off_the_ground(found, label):
    # The player, 2026-10-20 ~21:05: "look up only elite claws with a specific base, not just random +3 skill"
    verdict = base_verdict(from_drop(found), owned=lambda _facts: 0)
    assert verdict is not None
    assert (verdict.pick, verdict.klass, verdict.then, verdict.must_have) == (True, 'G20', Then.KEEP, False)
    assert verdict.reason == label


@pytest.mark.parametrize(
    'found',
    [
        claw('9tw', ((267, 3),), 3),  # +3 Fade alone (was claw-elite-plus3-paid)
        claw('7tw', ((273, 3), (278, 2))),  # +3 Mind Blast, +2 Venom
        claw('9tw', ((272, 3),)),  # +3 Wake of Inferno alone
        claw('9tw', ((264, 3),)),  # 20:39:33 "normal Greater Talons 0os +3 Cloak of Shadows ... taken (shown)"
        claw('9tw', ((276, 2),)),  # +2 Death Sentry: under the own-use row's +3
        claw('9tw', ((280, 3),), 2),  # +3 Phoenix Strike in 2 sockets: never 3 (Larzuk takes only 0os)
    ],
)
def test_a_fast_white_claw_without_a_paid_plus3_is_left(found):
    verdict = base_verdict(from_drop(found), owned=lambda _facts: 0)
    assert verdict is not None
    assert not verdict.pick
    assert verdict.reason == 'no class takes it'


def test_the_own_use_trap_claws_are_picked_until_two_are_owned():
    # O1 (own-claw-white-plus3-traps; the player, 2026-10-20 ~21:05: "yes" to two trap claws): the owned count is
    # loot/value.py owned_bases (same base code, ethereal flag and sockets)
    death, wake = from_drop(claw('9tw', ((276, 3),))), from_drop(claw('7tw', ((262, 3),), 3))
    for facts in (death, wake):
        for owned in (0, 1):
            verdict = base_verdict(facts, owned=lambda _facts, owned=owned: owned)
            assert verdict is not None
            assert verdict.pick, (facts.code, owned)
            assert verdict.reason.startswith('Trap claws (own use, 2 kept)')
        full = base_verdict(facts, owned=lambda _facts: 2)
        assert full is not None
        assert not full.pick
        assert full.reason.startswith('2 owned, 2 kept at most: Trap claws')
    # unknown count (S8): the cap does not hold
    unknown = base_verdict(death, owned=lambda _facts: None)
    assert unknown is not None
    assert unknown.pick


def test_a_lightning_sentry_claw_over_the_own_use_cap_is_still_the_markets():
    verdict = base_verdict(from_drop(claw('9tw', ((271, 3),))), owned=lambda _facts: 5)
    assert verdict is not None
    assert verdict.pick
    assert verdict.reason == 'White Greater / Runic Talons 3os/0os +3 Lightning Sentry'


def test_only_the_fast_talons_take_the_staff_mod_rows():
    # Greater Claws / Feral Claws (-20) and the slow h2h2 elites have no claw row yet: no fills (claws-findings.md §5)
    for code in ('9lw', '7lw', '7ar', '7qr'):
        verdict = base_verdict(from_drop(claw(code, ((271, 3),))), owned=lambda _facts: 0)
        assert verdict is None or not verdict.pick, code

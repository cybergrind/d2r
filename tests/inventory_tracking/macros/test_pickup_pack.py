"""PACK_GOLD_WAIT (macros/pickup.py, 2026-10-24; rca/2026-10-24/pickup-pack-findings.md): game 5 of 2026-10-23, the
pickup Blade Warped back into a tier 5 Herald pack for 5648 gold and clicked 6210 gold 8.7 s among it (2
Rejuvenations, the merc). A press's gold waits while a tier 4-5 pack member or GOLD_CROWD hostiles stand within
GATHER_CLEAR of the character or the pile; valuables are taken as before."""

from dataclasses import replace

import pytest

from inventory_tracking.game.layout import NO_OWNER
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import pickup
from inventory_tracking.macros.pickup import GOLD_CROWD, pick_up
from tests.inventory_tracking.macros.test_pickup import LEVEL, PILE, RUNE, game, keys, nothing


def hostile(unit: int, x: float, tier: int = 0) -> Monster:
    """A Returned (monstats 1) at (x, 5000), of a tier `tier` Herald's pack (0: none)."""
    return Monster(unit, 1, 1, x, 5000.0, NO_OWNER, life=128, max_life=128, tier=tier)


def among(*drops, monsters=()):
    play = game(*drops)
    play.world = replace(play.world, monsters=tuple(monsters))
    return play


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(pickup, 'PACK_GOLD_WAIT', True)


def test_gold_by_a_tier_5_pack_member_waits_and_the_press_goes_to_the_fight(on) -> None:
    stepped = []
    play = among(PILE, monsters=(hostile(900, 5021.0, tier=5),))  # 6 past the pile, 21 from the character
    assert not pick_up(play.run(), LEVEL, keys, lambda: stepped.append(True), threat=lambda here, spot: 1)
    assert stepped == [True]
    assert play.picked == []
    assert play.said[-1] == '7200 gold waits: the fight first'


def test_a_crowd_of_plain_hostiles_holds_gold_only_from_gold_crowd_on(on) -> None:
    few = [hostile(900 + i, 5018.0 + i) for i in range(GOLD_CROWD - 1)]
    play = among(PILE, monsters=few)
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: len(few))
    assert play.picked == ['7200 gold']
    crowd = [hostile(900 + i, 5018.0 + i) for i in range(GOLD_CROWD)]
    play = among(PILE, monsters=crowd)
    assert not pick_up(play.run(), LEVEL, keys, lambda: None, threat=lambda here, spot: len(crowd))
    assert play.picked == []


def test_a_pack_member_out_of_reach_a_valuable_a_goals_gold_or_the_switch_off_take_as_before(on, monkeypatch) -> None:
    play = among(PILE, monsters=(hostile(900, 5040.0, tier=5),))  # 25 past the pile
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 0)
    assert play.picked == ['7200 gold']
    play = among(RUNE, monsters=(hostile(900, 5010.0, tier=5),))
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 1)  # the player's rule
    assert play.picked == [RUNE.label]
    play = among(PILE, monsters=(hostile(900, 5021.0, tier=5),))
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 1, unit=PILE.unit_id)  # the hunt's
    assert play.picked == ['7200 gold']
    play = among(PILE, monsters=(hostile(900, 5021.0, tier=5),))
    assert pick_up(play.run(), LEVEL, keys, nothing)  # no guarded site: no threat given
    monkeypatch.setattr(pickup, 'PACK_GOLD_WAIT', False)
    play = among(PILE, monsters=(hostile(900, 5021.0, tier=5),))
    assert pick_up(play.run(), LEVEL, keys, nothing, threat=lambda here, spot: 1)
    assert play.picked == ['7200 gold']

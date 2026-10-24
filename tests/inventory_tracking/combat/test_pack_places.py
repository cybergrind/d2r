"""The fight's places judged by the keep range's own model (combat/pack.py PLACES_KEEP_RANGE; the player, 2026-10-23:
"try to push exp/hour more"; rca/2026-10-23/keep-range-findings.md): a place the hop (macros/safety.py
`Safety.pack_back`, `why_back`) would leave at once is not chosen by the fight (macros/hunting/moves.py
`better_stand`). Off: as before."""

import math

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.combat.pack import PACK_BACK, breaks_range, range_kept, why_back
from inventory_tracking.levels.model import Ground
from tests.inventory_tracking.macros.test_hunt import ASPECT, foe, game, hostiles, hunter


HORROR_ARCHER = 174


@pytest.fixture(autouse=True)
def switched_on(monkeypatch):
    monkeypatch.setattr(pack, 'PLACES_KEEP_RANGE', True)


def archers(*places, tier=5):
    return [foe(11 + k, x, y, txt_id=HORROR_ARCHER, tier=tier) for k, (x, y) in enumerate(places)]


# Take 20261022T235532Z-51, 02:57:12: the better place (10071.5, 5623.5), three of the pack 6-8 units off it.
BETTER = (10071.5, 5623.5)
THREE = archers((10077.5, 5619.5), (10078.0, 5626.5), (10065.5, 5629.0), (10095.0, 5610.0))


def test_a_place_with_the_pack_on_it_within_the_back_range_breaks_it_as_the_hop_says(monkeypatch):
    monkeypatch.setattr(pack, 'RANGE_LEAD', False)  # the hop's own words: no lead (test_pack_lead.py)
    why = breaks_range(BETTER, THREE, [])
    assert why == why_back(BETTER, pack.members(THREE), [])
    assert why is not None
    assert why.startswith('3 of the pack on the character within 10')
    assert not range_kept(THREE, [])(BETTER)


def test_a_place_at_the_range_keeps_it():
    away = (10071.5, 5643.5)
    assert all(math.dist(away, m.at) >= PACK_BACK for m in pack.members(THREE))
    assert breaks_range(away, THREE, []) is None
    assert range_kept(THREE, [])(away)


def test_a_pack_held_by_a_demon_is_not_on_the_place():
    demon = (10077.8, 5623.0)  # 3.5 from each of the two, 6.3 from the place: they are on it, not on the character
    assert breaks_range(BETTER, THREE[:2], [demon]) is None
    assert breaks_range(BETTER, THREE[:2], []) is not None


def test_under_tier_4_or_with_the_switch_off_every_place_keeps_it(monkeypatch):
    assert breaks_range(BETTER, archers((10077.5, 5619.5), (10078.0, 5626.5), tier=3), []) is None
    monkeypatch.setattr(pack, 'PLACES_KEEP_RANGE', False)
    assert breaks_range(BETTER, THREE, []) is None
    assert range_kept(THREE, [])(BETTER)


# The character at (5000, 5000); three archers of a tier 5 pack 26-31 off: the fight's place would stand 7.9 from one.
PACK = ((5026.0, 5004.0), (5028.0, 4996.0), (5031.0, 5001.0))


def chosen(*monsters):
    play = game(*monsters)
    hunt, run = hunter(play), play.run()
    place = hunt.better_stand(play.world, hostiles(play.world), Ground(()), ASPECT, run=run, landed=True)
    assert place is not None
    return place.spot


def test_the_fight_s_place_is_one_the_hop_would_not_leave():
    spot = chosen(*archers(*PACK))
    assert why_back(spot, pack.members(archers(*PACK)), []) is None
    assert min(math.dist(spot, p) for p in PACK) >= PACK_BACK


def test_without_the_switch_the_fight_s_place_is_inside_the_back_range(monkeypatch):
    monkeypatch.setattr(pack, 'PLACES_KEEP_RANGE', False)
    spot = chosen(*archers(*PACK))
    assert why_back(spot, pack.members(archers(*PACK)), []) is not None


def test_a_pack_under_tier_4_is_fought_from_the_place_as_before(monkeypatch):
    on = chosen(*archers(*PACK, tier=3))
    monkeypatch.setattr(pack, 'PLACES_KEEP_RANGE', False)
    assert on == chosen(*archers(*PACK, tier=3))

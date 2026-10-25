"""ALONG_ALL (combat/pack.py; rca/2026-10-25/tactics/teleports.md §3.1, apply-0a.md): every Teleport and Blade Warp
brings every demon and the mercenary along, whatever their distance, so a landing by a jump is judged with no demon
holding the pack there; a walk leaves them where they stand. Off: the allies within TAKEN_ALONG alone, as before.

The shape of take 20261025T001331Z-66, 03:14:12.57 (teleports.md §4.3): a better place 9 units into a tier 5 pack,
the bound demon 3 off the member nearest it; the Teleport brought the demon beside the character, the member was on
the character and the keep range hopped out at once."""

import math

import pytest

from inventory_tracking.combat import bolts, pack
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros.safety import lands_in_range
from tests.inventory_tracking.combat.test_pack_places import archers
from tests.inventory_tracking.scenarios.arena import game


HERE = (10000.0, 5000.0)
PLACE = (10009.0, 5000.0)  # the better place, 9 into the pack
MEMBER = (10016.0, 5000.0)  # 7 beyond the place, under PACK_BACK of it
DEMON = (10018.0, 5002.0)  # 2.8 off the member: it holds it, 9.2 from the place
PACK = archers(MEMBER, (10030.0, 5010.0))


@pytest.fixture(autouse=True)
def places_kept(monkeypatch):
    monkeypatch.setattr(pack, 'PLACES_KEEP_RANGE', True)
    monkeypatch.setattr(pack, 'RANGE_LEAD', False)


@pytest.mark.parametrize('on', [False, True])
def test_a_place_jumped_to_is_judged_with_the_demons_along(monkeypatch, on):
    monkeypatch.setattr(pack, 'ALONG_ALL', on)
    assert pack.breaks_range(PLACE, PACK, [DEMON]) is None  # walked: the demon stays on the member
    jumped = pack.breaks_range(PLACE, PACK, [DEMON], jumped=True)
    assert (jumped is not None) is on
    if on:
        assert jumped is not None
        assert jumped.startswith('1 of the pack on the character')


@pytest.mark.parametrize('on', [False, True])
def test_the_places_filter_jumps_beyond_the_jumps_least_reach(monkeypatch, on):
    monkeypatch.setattr(pack, 'ALONG_ALL', on)
    near = (10011.0, 5000.0)  # 11 from HERE: a jump of least 8 reaches it
    kept = pack.range_kept(PACK, [DEMON], HERE, 8.0)
    assert kept(near) is not on
    walked = pack.range_kept(PACK, [DEMON], HERE, 12.0)  # a jump only from 12: the place is walked to
    assert walked(near)
    assert pack.range_kept(PACK, [DEMON])(near)  # no `here`: as before


@pytest.mark.parametrize('on', [False, True])
def test_the_safetys_landing_bar_by_a_jump_and_by_a_walk(monkeypatch, on):
    monkeypatch.setattr(pack, 'ALONG_ALL', on)
    monkeypatch.setattr('inventory_tracking.macros.safety.PACK_RANGE_LANDING', True)
    assert not lands_in_range(HERE, PLACE, PACK, [DEMON])
    assert lands_in_range(HERE, PLACE, PACK, [DEMON], jumped=True) is on


def test_the_hop_back_is_not_aimed_through_demons_it_brings(monkeypatch):
    members = pack.members(archers((10010.0, 5000.0), (10012.0, 5003.0), (10012.0, 4997.0)))
    demon = [(10006.0, 5010.0)]  # off to the side of the pack
    middle = pack.centre(HERE, members)
    heading = lambda spot: math.degrees(math.atan2(spot[1] - middle[1], spot[0] - middle[0]))  # ruff: ignore[lambda-assignment]
    monkeypatch.setattr(pack, 'ALONG_ALL', False)
    through = pack.hop_spots(HERE, members, demon)[0]
    monkeypatch.setattr(pack, 'ALONG_ALL', True)
    away = pack.hop_spots(HERE, members, demon)[0]
    assert abs(heading(away)) > 150  # straight back from the pack through the character (west)
    assert abs(heading(through)) < 150  # turned toward the demon


def test_the_burn_hop_is_not_aimed_through_demons_it_brings(monkeypatch):
    burner = manaburn.Burner(unit=1, at=(10010.0, 5000.0), keep=18.0, kind='burn', herald=True)
    demon = [(10004.0, 5012.0)]
    monkeypatch.setattr(pack, 'ALONG_ALL', False)
    through = manaburn.hop_spots(HERE, [burner], demon)[0]
    monkeypatch.setattr(pack, 'ALONG_ALL', True)
    away = manaburn.hop_spots(HERE, [burner], demon)[0]
    assert away[1] == pytest.approx(HERE[1], abs=1e-6)
    assert away[0] < HERE[0]
    assert through[1] != pytest.approx(HERE[1], abs=1.0)


@pytest.mark.parametrize('on', [False, True])
def test_a_far_companion_comes_along(monkeypatch, on):
    monkeypatch.setattr(pack, 'ALONG_ALL', on)
    far = (10025.0, 5000.0)  # 25 off: past TAKEN_ALONG
    assert pack.along(HERE, far) is on
    assert pack.along(HERE, (10005.0, 5000.0))
    moved = bolts.cover_at([far], HERE, (9990.0, 5000.0))
    assert (moved[0] == (10015.0, 5000.0)) is on


@pytest.mark.parametrize('on', [False, True])
def test_the_arena_takes_every_companion_along(monkeypatch, on):
    monkeypatch.setattr(game, 'ALONG_ALL', on)
    ally = game.Monster(unit_id=7, txt_id=361, mode=1, x=10040.0, y=5000.0)
    assert game.Arena.taken_along(HERE, ally) is on
    assert game.Arena.taken_along(HERE, game.Monster(unit_id=8, txt_id=361, mode=1, x=10004.0, y=5000.0))

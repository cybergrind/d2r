"""A sigil goes only at a spot the character sees (builds/warlock/casters.py SIGIL_SIGHT, `sighted_disc`): the game lays
none behind a wall, and the LONG_FIGHT of the take 20261024T075426Z-51 (Harem Level 2, 2026-10-24 10:55) pressed the
key 13 times in 34 s for 3 sigils, each miss read rightly as "no sigil of the character lies" and pressed again."""

import math
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock import casters
from tests.inventory_tracking.builds.warlock import test_pack_sigil as packs, test_sigil_keep as keeps
from tests.inventory_tracking.macros.moves import walled


def across_the_bunch(x: float, y: float) -> bool:
    """A wall between the character (5000, 5000) and the bunch south-east of it, open toward the Herald (north-east)."""
    return not (5003 <= x < 5005 and y > 5003)


def shut_in(x: float, y: float) -> bool:
    """A wall all round the east of the character: nothing of the pack in sight."""
    return x < 5003


def fight(walkable) -> packs.Fight:
    found = packs.Fight(packs.HERALD, *packs.BUNCH, *packs.BY_ME)
    ground = walled(walkable)
    found.run.ground = lambda: ground
    return found


def test_with_the_bunch_behind_a_wall_the_sigil_goes_at_the_disc_in_sight():
    found = fight(across_the_bunch)
    assert found.look(100.0)
    laid = found.play.sigils[0]
    assert math.dist(laid, (packs.HERALD.x, packs.HERALD.y)) < 1.0  # the Herald's disc, not the bunch's
    assert math.dist(laid, packs.centre(*packs.BUNCH)) > packs.SIGIL_RADIUS


def missiles(found, lying: dict) -> None:
    """The character's sigil in flight where `lying['at']` says (None: none, the key refused)."""
    me = found.play.world.player.unit_id

    def flights(kinds: frozenset[int]) -> tuple[tuple[int, int, float, float], ...]:
        at = lying['at']
        return ((me, 686, *at),) if at is not None else ()

    found.run.flights = flights


def test_with_no_disc_in_sight_one_key_tries_and_a_refused_one_waits_the_skip():
    found = fight(shut_in)
    missiles(found, {'at': None})  # the game lays none behind the wall
    keys, at = [], 100.0
    while at <= 110.0:
        if found.look(at):
            keys.append(casters.watch_of(found.buffs).at)
        at = round(at + 0.1, 3)
    assert len(keys) == 3  # the first try, then one a SIGIL_REFUSED_SKIP (13 keys in 10 s before, Harem 2)
    assert all(casters.SIGIL_REFUSED_SKIP <= b - a <= casters.SIGIL_REFUSED_SKIP + 1.0 for a, b in pairwise(keys))
    ground = walled(lambda x, y: True)  # the pack comes round the wall
    found.run.ground = lambda: ground
    assert len(found.looks(110.1, 111.1)) == 1  # in sight: at once, the skip aside
    assert math.dist(found.play.sigils[-1], packs.centre(*packs.BUNCH)) < 2.5


def test_the_skip_runs_from_the_refused_key():
    found = fight(shut_in)
    missiles(found, {'at': None})
    assert found.look(100.0)
    first = casters.watch_of(found.buffs).at
    assert first is not None
    assert found.looks(100.1, first + casters.SIGIL_REFUSED_SKIP - 0.05) == []
    assert len(found.looks(first + casters.SIGIL_REFUSED_SKIP, first + casters.SIGIL_REFUSED_SKIP + 1.0)) == 1


def test_a_try_through_the_wall_that_lands_is_kept():
    found = fight(shut_in)
    lying: dict = {'at': None}
    missiles(found, lying)
    assert found.look(100.0)
    lying['at'] = found.play.sigils[0]  # it landed
    assert found.looks(100.1, 104.0) == []  # it covers the bunch: kept as any other


def test_with_the_switch_off_it_goes_through_the_wall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(casters, 'SIGIL_SIGHT', False)
    found = fight(across_the_bunch)
    assert found.look(100.0)
    assert math.dist(found.play.sigils[0], packs.centre(*packs.BUNCH)) < 2.5


def test_a_dangerous_monster_behind_a_wall_gets_one_try_then_waits_the_skip():
    found = keeps.Fight(keeps.DIABLO)  # 8 east of the character
    ground = walled(shut_in)
    found.run.ground = lambda: ground
    missiles(found, {'at': None})
    assert len(found.looks(100.0, 102.9)) == 1  # the one try at 100
    found.move(5002.0)  # he comes round to this side of it
    assert found.looks(103.0, 104.0) != []
    assert found.play.sigils[-1] == pytest.approx((5002.0, 5000.0), abs=1.5)


def test_the_disc_in_sight_is_the_best_of_those_in_sight():
    pack = [packs.pack.Member(k, at) for k, at in enumerate(((10.0, 0.0), (11.0, 0.0), (10.0, 1.0), (-10.0, 0.0)))]
    spot, why = casters.sighted_disc((0.0, 0.0), pack, 5.5, lambda spot: True) or ((0.0, 0.0), '')
    assert spot[0] > 9.0
    assert why.endswith('3 of 4')
    found = casters.sighted_disc((0.0, 0.0), pack, 5.5, lambda spot: spot[0] < 0)
    assert found is not None
    assert found[0] == (-10.0, 0.0)
    assert casters.sighted_disc((0.0, 0.0), pack, 5.5, lambda spot: False) is None

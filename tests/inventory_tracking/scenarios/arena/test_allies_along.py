"""ALLIES_ALONG and MERC_HURT (game.py; rca/2026-10-23/death-canyon-findings.md): a Teleport takes the companions
within 10 along, as the game does (312 Teleports of rca/2026-10-21/herald-gloam-findings.md §3), and the mercenary
takes the blows that land on it."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Monster
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.game import Landing
from tests.inventory_tracking.scenarios.arena.test_moves import empty


def with_mates(arena, *places):
    player = arena.world.player
    assert player is not None
    mates = tuple(
        Monster(900 + index, HIRELING_CLASS_ID, 1, x, y, owner=player.unit_id, ally=True, life=128, max_life=128)
        for index, (x, y) in enumerate(places)
    )
    arena.world = replace(arena.world, monsters=(*arena.world.monsters, *mates))
    return arena


def landed(arena, spot, teleport=True):
    arena.landing = Landing(arena.time.ticks, spot, teleport)
    arena.move()


@pytest.mark.parametrize('on', [False, True])
def test_a_teleport_takes_the_companions_within_10_along(monkeypatch, on):
    monkeypatch.setattr(game, 'ALLIES_ALONG', on)
    arena = empty()
    here = arena.here
    with_mates(arena, (here[0] + 3, here[1]), (here[0] + 15, here[1]))
    spot = (here[0] - 20, here[1])
    landed(arena, spot)
    near, far = [m for m in arena.world.monsters if m.unit_id in (900, 901)]
    assert ((abs(near.x - spot[0]) <= game.ALONG_GAP + 1e-6) and abs(near.y - spot[1]) <= game.ALONG_GAP + 1e-6) == on
    assert (far.x, far.y) == (here[0] + 15, here[1])  # 15 off: left where it stood


def test_a_blade_warp_takes_none_along(monkeypatch):
    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    arena = empty()
    here = arena.here
    with_mates(arena, (here[0] + 3, here[1]))
    landed(arena, (here[0] - 20, here[1]), teleport=False)
    mate = next(m for m in arena.world.monsters if m.unit_id == 900)
    assert (mate.x, mate.y) == (here[0] + 3, here[1])


@pytest.mark.parametrize('on', [False, True])
def test_the_mercenary_takes_its_blows_with_merc_hurt(monkeypatch, on):
    monkeypatch.setattr(game, 'MERC_HURT', on)
    arena = empty()
    with_mates(arena, arena.here)
    merc = next(m for m in arena.world.monsters if m.unit_id == 900)
    assert arena.hurts(merc) == on


@pytest.mark.parametrize('on', [False, True])
def test_with_warp_along_a_blade_warp_takes_them_as_a_teleport(monkeypatch, on):
    # take 20261024T171736Z-71, 20:18:41.539: the Blade Warp of 15 put both demons 0.1 off the character (WARP_ALONG)
    monkeypatch.setattr(game, 'ALLIES_ALONG', True)
    monkeypatch.setattr(game, 'WARP_ALONG', on)
    arena = empty()
    here = arena.here
    with_mates(arena, (here[0] + 3, here[1]))
    spot = (here[0] - 20, here[1])
    landed(arena, spot, teleport=False)
    mate = next(m for m in arena.world.monsters if m.unit_id == 900)
    assert (math.dist((mate.x, mate.y), spot) <= game.ALONG_GAP + 1e-6) == on


def test_pets_as_game_turns_on_the_four_and_the_test_puts_them_back(monkeypatch):
    with monkeypatch.context() as patched:
        game.pets_as_game(patched.setattr)
        assert all(getattr(game, name) is True for name in game.PETS_AS_GAME)
    assert not any(getattr(game, name) for name in game.PETS_AS_GAME)

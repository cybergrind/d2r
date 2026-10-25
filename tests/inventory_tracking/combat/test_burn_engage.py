"""BURN_ENGAGE (combat/threats/manaburn.py; rca/2026-10-25/tactics/apply-burn.md): the keep range's hop and the
pursuit's jump in undid each other round a Mana Burn pack (take 20261025T110846Z-131, the Throne 14:10:40-51: 7
jumps, 0 kills), and every drainer seen waived the mark's hold. On: a drainer waives the hold only within its keep
range of the character (or with the mana leaving); the demons on a burner bar the jump into its keep range."""

from types import SimpleNamespace

import pytest

from inventory_tracking.combat.harm import Hostile
from inventory_tracking.combat.threats import manaburn
from inventory_tracking.macros.safety import Safety


HERE = (15087.0, 5018.0)
BURNER = manaburn.Burner(unit=1, at=(15107.0, 5018.0), keep=18.0, kind=manaburn.BURN_SAID)  # 20 off: beyond its keep
NEAR = manaburn.Burner(unit=2, at=(15097.0, 5018.0), keep=18.0, kind=manaburn.BURN_SAID)  # 10 off: within it
FAST = manaburn.Burner(unit=3, at=(15097.0, 5018.0), keep=18.0, drains=False, kind=manaburn.FAST_SAID)


def threat(burning, leaving=None):
    p = SimpleNamespace(
        here=HERE, look=SimpleNamespace(hostiles=(Hostile(unit=9, txt=7, at=(15140.0, 5018.0)),), life=2900.0),
        burning=tuple(burning), close=False, reach_blows=lambda spot: 0.0,
    )  # fmt: skip
    stub = SimpleNamespace(alarmed=False)
    said = Safety.real_threat(stub, p, SimpleNamespace(burst=0.0), 100.0, leaving)  # pyrefly: ignore[bad-argument-type]
    return said or ''


@pytest.mark.parametrize('on', [False, True])
def test_a_drainer_waives_the_hold_only_within_its_keep_range(monkeypatch, on):
    monkeypatch.setattr(manaburn, 'BURN_ENGAGE', on)
    assert (threat([BURNER]) == 'a drainer') is not on  # seen, 20 off: the hold stands with the switch
    assert threat([NEAR]) == 'a drainer'
    assert threat([FAST]) == ''  # an Extra Fast member that does not drain
    assert threat([], leaving='mana: leaving') == 'a drainer'


def test_the_demons_hold_a_burner_within_demon_holds():
    assert manaburn.burn_held([(15109.0, 5019.0)], [BURNER])
    assert not manaburn.burn_held([(15090.0, 5018.0)], [BURNER])  # by the character
    assert not manaburn.burn_held([(15098.0, 5019.0)], [FAST])  # on a member that does not drain


def test_a_drainer_close_is_one_within_its_keep_range():
    assert manaburn.drainer_close(HERE, [NEAR])
    assert not manaburn.drainer_close(HERE, [BURNER])
    assert not manaburn.drainer_close(HERE, [FAST])


@pytest.mark.parametrize('on', [False, True])
def test_the_mark_s_aim_moves_once_with_a_burner_closing(monkeypatch, on):
    """manaburn seed 35 (d2r-f3's arena, 2026-10-25): two moves under the pack while 14 members closed in."""
    from inventory_tracking.game.records import Monster
    from inventory_tracking.macros import buffs
    from tests.inventory_tracking.macros.fakes import player, world

    monkeypatch.setattr(manaburn, 'BURN_ENGAGE', True)
    monkeypatch.setattr(buffs, 'BURN_AIM_ONCE', on)
    burner = Monster(5, 23, 1, HERE[0] + 10.0, HERE[1], modifiers=(min(manaburn.DRAINING),))
    far = Monster(6, 23, 1, HERE[0] + 30.0, HERE[1], modifiers=(min(manaburn.DRAINING),))
    plain = Monster(7, 23, 1, HERE[0] + 5.0, HERE[1])
    seen = lambda *ms: world(131, player=player(131, x=HERE[0], y=HERE[1]), monsters=ms)  # ruff: ignore[lambda-assignment]
    assert buffs.burn_closing(seen(burner)) is on
    assert not buffs.burn_closing(seen(far, plain))

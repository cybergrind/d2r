"""Engorge only where it does some good and can land (builds/warlock/buffs.py ENGORGE_LIFE_SHARE, ENGORGE_SPARE_ENDS;
casters.py ENGORGE_HOVER_FIRST; rca/2026-10-20/lazy-work-findings.md §2). Each switch off gives the old behaviour."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan, casters
from inventory_tracking.builds.warlock.buffs import (
    BUFFS,
    ENGORGE_HURT_SECONDS,
    ENGORGE_RETRY,
    ENGORGE_SECONDS,
    Rotation,
    demon_hurt,
    engorge_due,
)
from inventory_tracking.builds.warlock.casters import ENGORGE_HOVER_RETRY
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ENGORGE
from inventory_tracking.game.layout import CHAMPION_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


ROW = next(row for row in BUFFS if row.skill == ENGORGE and row.due is plan.engorge_on_a_key)  # the lazy row
# CybergrindAA's Defiler as the client reads it (the takes 20261020T2*): life in 128ths, its maximum in whole points
FULL = Monster(20, 744, 1, 5004.0, 5000.0, 1, ally=True, life=128, max_life=230)
HURT = replace(FULL, life=60)  # 47%
FOE = Monster(10, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF)
CORPSE = (91, 5006.0, 5004.0)


@pytest.fixture(autouse=True)
def switched_on(monkeypatch):
    """The three switches on (a test of one off sets it so)."""
    monkeypatch.setattr(plan, 'ENGORGE_LIFE_SHARE', True)
    monkeypatch.setattr(plan, 'ENGORGE_SPARE_ENDS', True)
    monkeypatch.setattr(casters, 'ENGORGE_HOVER_FIRST', True)


def game(*monsters):
    play = Game(world(area=101, slots=HUNT_SLOTS))
    play.world = replace(play.world, monsters=monsters)
    return play


def facts(play, *, foes=(), prey=None, since=None):
    """The fight's facts for Engorge, the last one `since` seconds ago (None: never)."""
    cast_at: dict[tuple[int, int | None], float] = {} if since is None else {(ENGORGE, None): play.clock.now - since}
    return BuffFacts(play.world, play.clock.now, foes=foes, prey=prey, cast_at=cast_at, corpses=lambda: (CORPSE,))


# --- ENGORGE_LIFE_SHARE: hurt by the client's 128ths ---


def test_a_defiler_at_full_life_is_not_hurt_and_gets_engorge_for_the_buff_alone():
    play = game(FULL, FOE, replace(FOE, unit_id=11), replace(FOE, unit_id=12))
    foes = tuple(m for m in play.world.monsters if m.txt_id == 19)
    assert not demon_hurt(play.world)
    assert not engorge_due(facts(play, foes=foes, prey=FOE, since=ENGORGE_HURT_SECONDS + 1.0))
    assert engorge_due(facts(play, foes=foes, prey=FOE, since=ENGORGE_SECONDS + 0.1))
    hurt = game(HURT, *play.world.monsters[1:])
    assert demon_hurt(hurt.world)
    assert engorge_due(facts(hurt, foes=foes, prey=FOE, since=ENGORGE_HURT_SECONDS + 0.1))


def test_without_the_life_share_a_full_defiler_reads_hurt_as_before(monkeypatch):
    monkeypatch.setattr(plan, 'ENGORGE_LIFE_SHARE', False)
    play = game(FULL, FOE)
    assert demon_hurt(play.world)  # 128 < 0.7 * 230
    assert engorge_due(facts(play, foes=(FOE,), prey=FOE, since=ENGORGE_HURT_SECONDS + 0.1))
    assert plan.engorge_every(play.world) == ENGORGE_HURT_SECONDS


# --- ENGORGE_SPARE_ENDS: no buff cast as a fight ends ---


@pytest.mark.parametrize(
    ('left', 'due'),
    [
        ((FOE,), False),
        ((FOE, replace(FOE, unit_id=11)), False),
        ((FOE, replace(FOE, unit_id=11), replace(FOE, unit_id=12)), True),  # the fight goes on
        ((replace(FOE, flags=CHAMPION_FLAG),), True),  # a leader: its fight is worth the buff
        ((replace(FOE, txt_id=243),), True),  # Diablo
    ],
)
def test_the_buff_is_not_cast_while_a_fight_ends(left, due):
    play = game(FULL, *left)
    assert engorge_due(facts(play, foes=left, prey=left[0])) is due


def test_a_hurt_demon_gets_engorge_as_the_fight_ends_and_outside_a_fight_the_buff_is_cast():
    play = game(HURT, FOE)
    assert engorge_due(facts(play, foes=(FOE,), prey=FOE))
    play = game(FULL)
    assert engorge_due(facts(play))  # no prey: no fight to end (the tests' and replays' Rotation)


def test_without_spare_ends_the_buff_is_cast_whatever_is_left(monkeypatch):
    monkeypatch.setattr(plan, 'ENGORGE_SPARE_ENDS', False)
    play = game(FULL, FOE)
    assert engorge_due(facts(play, foes=(FOE,), prey=FOE))


# --- ENGORGE_HOVER_FIRST: the record read before the pointer moves ---


class Strike:
    """A held strike's release, counted."""

    def __init__(self):
        self.released = 0

    def __call__(self):
        self.released += 1


def engorge_under(play, over, *, held=True, demon=FULL):
    """Engorge cast under the strike (held or not) with the record of the unit under the pointer naming `over`
    until the strike is let go, then nothing; (tried, the pointer moved, keys pressed, releases, buffs)."""
    play.world = replace(play.world, monsters=(demon, *play.world.monsters[1:]))
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    strike = Strike()
    buffs.let_go = strike if held else None
    run.corpses = lambda: (CORPSE,)
    run.hovered = lambda: over if strike.released == 0 else None
    play.clock.now = 50.0
    before = play.keys.pointer()
    due = buffs.due(run, ROW, buffs.facts(run, play.world))  # no prey: the fight's end is not asked here
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    return tried, play.keys.pointer() != before, play.pressed(), strike.released, buffs


def test_a_held_strike_on_a_live_monster_has_no_engorge_tried_and_nothing_touched():
    tried, moved, pressed, released, buffs = engorge_under(game(FULL, FOE), (1, FOE.unit_id))
    assert (tried.cast, tried.touched, moved, pressed, released) == (False, False, False, [], 0)
    # looked at again within ENGORGE_HOVER_RETRY
    assert Rotation(buffs).engorged_at == 50.0 - ENGORGE_SECONDS + ENGORGE_HOVER_RETRY
    tried, moved, pressed, released, _ = engorge_under(game(FULL, FOE), (4, 777))  # an item's label
    assert (tried.cast, moved, pressed) == (False, False, [])


def test_without_hover_first_the_pointer_goes_to_the_corpses_as_before(monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_HOVER_FIRST', False)
    play = game(FULL, FOE)
    tried, moved, pressed, released, buffs = engorge_under(play, (1, FOE.unit_id))
    assert (tried.cast, tried.touched, moved, pressed, released) == (False, True, True, [], 0)
    # the next try ENGORGE_RETRY after this one, which took the pointer's travel
    assert Rotation(buffs).engorged_at == play.clock.now - ENGORGE_SECONDS + ENGORGE_RETRY


def test_a_strike_not_held_has_the_record_read_at_the_corpse():
    tried, moved, pressed, _, _ = engorge_under(game(FULL, FOE), None, held=False)
    assert (tried.cast, moved, pressed) == (True, True, ['e'])


def test_for_a_hurt_demon_the_strike_is_let_go_first_and_engorge_cast():
    tried, moved, pressed, released, _ = engorge_under(game(HURT, FOE), (1, FOE.unit_id), demon=HURT)
    assert (tried.cast, moved, pressed) == (True, True, ['e'])
    assert released >= 1


def test_a_record_naming_a_corpse_read_now_is_no_live_monster(monkeypatch):
    # 26 misses of the takes named a monster the strike had just killed: dead now, still in the look's monsters.
    killed = replace(FOE, unit_id=91)
    play = game(FULL, FOE, killed)
    tried, moved, pressed, _, _ = engorge_under(play, (1, 91))
    assert (tried.cast, moved, pressed) == (True, True, ['e'])
    monkeypatch.setattr(casters, 'ENGORGE_HOVER_FIRST', False)
    tried, moved, pressed, _, _ = engorge_under(game(FULL, FOE, killed), (1, 91))
    assert (tried.cast, pressed) == (False, [])

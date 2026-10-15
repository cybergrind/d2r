"""A Defiler kept out (builds/warlock/defiler.py; rca/2026-10-14/run-1932-findings.md issue 3)."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.buffs import BUFFS, CONSUME_RETRY, CONSUME_SOON
from inventory_tracking.builds.warlock.casters import CASTERS, consume_again, summon_defiler
from inventory_tracking.builds.warlock.defiler import DEFILER_RETRY, defiler_missing, price, worth_a_defiler
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import CONSUME, SUMMON_DEFILER
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, world


DEFILER = Monster(60, 744, 1, 5006.0, 4996.0, 0xFFFFFFFF)
CHAMPION = 0x0C


def field(**changes):
    return world(area=101, slots=HUNT_SLOTS, **changes)


TOOK = {CONSUME: 50.0}  # the macro's prebuff cast Consume and left a Defiler out


def test_a_defiler_is_due_only_with_none_alive_out_of_town_with_no_panel_and_the_window_in_front():
    out = field()
    assert defiler_missing(BuffFacts(out, 100.0, took=TOOK))
    assert not defiler_missing(BuffFacts(out, 100.0))  # never buffed by the macro: the player's to summon
    assert not defiler_missing(BuffFacts(replace(out, monsters=(DEFILER,)), 100.0, took=TOOK))  # never a second
    assert not defiler_missing(BuffFacts(replace(out, open_panels=('inventory',)), 100.0, took=TOOK))  # 22:45:01-07
    assert not defiler_missing(BuffFacts(world(area=109, slots=HUNT_SLOTS), 100.0, took=TOOK))  # Harrogath
    assert not defiler_missing(BuffFacts(replace(out, slots=()), 100.0, took=TOOK))  # not on a key
    assert not defiler_missing(BuffFacts(out, 100.0, focused=lambda: False, took=TOOK))
    tried = {(SUMMON_DEFILER, None): 100.0 - DEFILER_RETRY}
    assert not defiler_missing(BuffFacts(out, 100.0, cast_at=tried, took=TOOK))
    assert defiler_missing(BuffFacts(out, 100.0 + 0.01, cast_at=tried, took=TOOK))


def test_under_the_strike_a_summon_pays_in_a_long_fight_and_not_against_trash():
    out = field()
    # The Herald of 22:55 (13 times the life) and its pack: the fight in reach outlasts the Defiler's arrival
    herald = Monster(1, 595, 1, 5010.0, 5000.0, 0xFFFFFFFF, CHAMPION, life=128, max_life=128, tier=1)
    pack = tuple(
        Monster(10 + n, 595, 1, 5012.0, 5000.0 + n, 0xFFFFFFFF, CHAMPION, life=128, max_life=128) for n in range(8)
    )
    long = BuffFacts(out, 100.0, foes=(herald, *pack), reachable=(herald, *pack))
    found = price(long)
    assert found is not None
    assert found.worth > 0
    assert found.span > 1.0
    assert worth_a_defiler(long, None)
    trash = Monster(2, 19, 1, 5010.0, 5000.0, 0xFFFFFFFF, 0, life=10, max_life=128)
    short = BuffFacts(out, 100.0, foes=(trash,), reachable=(trash,))
    assert not worth_a_defiler(short, None)
    assert price(BuffFacts(out, 100.0)) is None  # nothing in reach: the upkeep's row


def casting(play: Game, phase: str) -> Casting:
    row = next(r for r in BUFFS if r.skill == SUMMON_DEFILER and r.phase == phase)
    run = play.run()
    return Casting(run, row, Buffs(ECHOING_STRIKE_BUILD), play.world, None, 16 / 9, lambda w, skills: {})


def test_the_quiet_summons_one_defiler_and_the_fight_presses_its_key_once_at_a_spot():
    play = Game(field())
    tried = CASTERS['defiler'](casting(play, 'upkeep'))
    assert tried.cast
    assert play.pressed() == ['q']
    assert [m.txt_id for m in play.world.monsters].count(744) == 1
    play = Game(field())
    tried = CASTERS['defiler'](casting(play, 'fight'))
    assert tried.cast
    assert tried.touched
    assert play.pressed() == ['q']


def test_no_summon_goes_into_a_panel_the_player_has_open():
    # 22:45:01-07 on 2026-10-14: four Summon Defiler keys into the inventory and the cube, no Defiler came
    play = Game(field(open_panels=('inventory',)))
    with pytest.raises(Abort, match='a panel is open'):
        summon_defiler(play.run())
    assert play.pressed() == []
    tried = CASTERS['defiler'](casting(play, 'upkeep'))
    assert not tried.cast
    assert play.pressed() == []


def test_consume_stopped_by_an_open_panel_is_tried_again_soon():
    play = Game(replace(field(open_panels=('inventory',)), player=replace(field().player, consume=False)))
    row = next(r for r in BUFFS if r.skill == CONSUME and r.phase == 'upkeep')
    run = play.run()
    tried = consume_again(Casting(run, row, Buffs(ECHOING_STRIKE_BUILD), play.world, None, 16 / 9, lambda w, s: {}))
    assert not tried.cast
    assert tried.at == pytest.approx(run.clock() - CONSUME_RETRY + CONSUME_SOON)

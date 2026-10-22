"""Consume's renewal kept out of a fight (rca/2026-10-21/consume-in-fight-findings.md; the player, 2026-10-21 ~21:02:
"also, T5 herald fight - we stood and do NOTHING under the fire, not damaging anything for solid 15 seconds")."""

from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan, casters
from inventory_tracking.builds.warlock.buffs import (
    BUFFS,
    CONSUME_OMEN_REACH,
    CONSUME_RETRY,
    CONSUME_SOON,
    consume_due,
)
from inventory_tracking.builds.warlock.casters import consume_again
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import CONSUME
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, character_of, world


FLAYER = 659  # the take's pack: 15 Flayers of a tier 5 Herald
CHAMPION = 0x0C


@pytest.fixture(autouse=True)
def no_omens():
    pack.saw_omens([])
    yield
    pack.saw_omens([])


def ran_out() -> Game:
    out = world(area=123, slots=HUNT_SLOTS)
    return Game(replace(out, player=replace(character_of(out), consume=False)))


def flayers(near: float = 12.0, count: int = 15) -> tuple[Monster, ...]:
    return tuple(
        Monster(
            900 + n, FLAYER, 1, 5000.0 + near, 5000.0 + n * 0.5, 0xFFFFFFFF, CHAMPION, life=128, max_life=128, tier=5
        )
        for n in range(count)
    )


def casting(play: Game) -> Casting:
    row = next(r for r in BUFFS if r.skill == CONSUME and r.phase == 'upkeep')
    return Casting(play.run(), row, Buffs(ECHOING_STRIKE_BUILD), play.world, None, 16 / 9, lambda w, s: {})


def test_consume_is_not_due_with_a_herald_coming_near():
    """20:59:03.66: Consume ran out 17 units from a pending omen (read at 20:58:59.68, the pack 5 s on); its renewal
    began with nothing within 30 and the pack showed 0.07 s later."""
    play = ran_out()
    out = play.world
    assert consume_due(BuffFacts(out, 100.0))
    pack.saw_omens([((5000.0, 5017.0), 105.0)])
    assert not consume_due(BuffFacts(out, 100.0))
    assert consume_due(BuffFacts(out, 105.5))  # the omen read out: the pack is within 30 by then, or never came
    pack.saw_omens([((5000.0, 5000.0 + CONSUME_OMEN_REACH + 1.0), 105.0)])
    assert consume_due(BuffFacts(out, 100.0))  # far off: the quiet holds here


def test_without_the_switch_an_omen_does_not_put_consume_off(monkeypatch):
    monkeypatch.setattr(plan, 'CONSUME_OMEN_DEFER', False)
    play = ran_out()
    pack.saw_omens([((5000.0, 5017.0), 105.0)])
    assert consume_due(BuffFacts(play.world, 100.0))


def test_a_pack_that_shows_during_the_renewal_stops_it_at_once_and_puts_it_off_to_the_quiet():
    """The take: the pack showed 0.07 s into the renewal, and two summons, a crowded Defiler summoned again and two
    Consume keys followed: 8.3 s with no strike. Now the renewal stops at the first look with a hostile within 30."""
    play = ran_out()
    cast = casting(play)
    run = cast.run
    started = run.clock()

    def comes():
        play.world = replace(play.world, monsters=(*play.world.monsters, *flayers()))

    play.later(0.05, comes)
    tried = consume_again(cast)
    assert not tried.cast
    assert '6' not in play.pressed()  # no Consume key under the pack
    assert run.clock() - started < 1.0
    assert tried.at == pytest.approx(run.clock() - CONSUME_RETRY + CONSUME_SOON)  # the first quiet 3 s on


def test_a_pack_after_the_consume_landed_is_a_consume_and_the_defiler_left_out_still_comes():
    # Else the upkeep's own Defiler row summons it by the same routine (golden loop_counts.json, walking into reach)
    play = ran_out()
    cast = casting(play)
    shown = []

    def comes():
        shown.append(True)
        play.world = replace(play.world, monsters=(*play.world.monsters, *flayers()))

    def watch(world_seen):
        # the pack shows the look the Consume's state does
        if character_of(world_seen).consume and not shown:
            play.later(0.0, comes)

    cast.run.observe = watch
    tried = consume_again(cast)
    assert tried.cast  # the state is on: a Consume
    assert play.pressed() == ['q', '6', 'q']


def test_without_the_switch_the_renewal_goes_on_under_the_pack(monkeypatch):
    monkeypatch.setattr(casters, 'CONSUME_BREAKS', False)
    play = ran_out()
    cast = casting(play)

    def comes():
        play.world = replace(play.world, monsters=(*play.world.monsters, *flayers(near=25.0)))

    play.later(0.05, comes)
    tried = consume_again(cast)
    assert tried.cast
    assert '6' in play.pressed()

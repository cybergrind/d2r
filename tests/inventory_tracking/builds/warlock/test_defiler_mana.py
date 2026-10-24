"""The Defiler's summon and Consume's renewal against the mana and the Defilers standing (the player, 2026-10-23: "push
exp/hour"; rca/2026-10-23/defiler-idle-findings.md): keys the mana does not pay for cast nothing, a refused spot is
known at once, and a Defiler standing still is consumed instead of a new one summoned."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan, casters, defiler as kept
from inventory_tracking.builds.warlock.buffs import BUFFS, CONSUME_RETRY, CONSUME_SOON, consume_due
from inventory_tracking.builds.warlock.casters import (
    SUMMON_REFUSED,
    SUMMON_SHOWS,
    NoMana,
    consume_again,
    renew_consume,
    summon_defiler,
)
from inventory_tracking.builds.warlock.defiler import CONSUME_MANA, DEFILER_MANA, defiler_missing
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import CONSUME
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, Game, character_of, world


POOL = 745  # CybergrindAA's mana pool tonight
TOOK = {CONSUME: 50.0}  # the macro's prebuff cast Consume and left a Defiler out
STILL_DEFILER = Monster(60, 744, 1, 5006.0, 4996.0, 0xFFFFFFFF)
BOUND_DEMON = Monster(50, 700, 1, 4995.0, 5003.0, 0xFFFFFFFF, ally=True)
ONE_SUMMON = 0.52  # seconds the fake's summon at the first spot takes, key and pauses


def field(*monsters: Monster, consume: bool = False) -> Game:
    out = world(area=101, slots=HUNT_SLOTS, monsters=monsters)
    return Game(replace(out, player=replace(character_of(out), consume=consume, stats_at=0x1000)))


def with_mana(game: Game, mana: float | None):
    """The game's run with the character's stat list reading `mana` (None: no stat reader)."""
    run = game.run()
    if mana is not None:
        run.unit_stats = lambda at: {8: int(mana * 256), 9: POOL * 256}
    return run


def facts(game: Game, mana: float | None, now: float = 100.0) -> BuffFacts:
    return BuffFacts(game.world, now, took=TOOK, mana=(lambda: mana) if mana is not None else None)


def casting(game: Game, run) -> Casting:
    row = next(r for r in BUFFS if r.skill == CONSUME and r.phase == 'upkeep')
    return Casting(run, row, Buffs(ECHOING_STRIKE_BUILD), game.world, None, 16 / 9, lambda w, s: {})


def test_the_mana_is_read_from_the_characters_stat_list():
    game = field()
    run = with_mana(game, 16.0)
    assert run.reads.mana(game.world) == pytest.approx(16.0)
    assert game.run().reads.mana(game.world) is None  # no stat reader: unread


def test_consume_waits_for_the_mana_of_the_summon_and_the_consume():
    """05:26:42 in the take 20261023T022539Z-76: Consume ran out with the mana at 16 of 745; Summon keyed at 16, 28, 40
    cast nothing, at 50 it cast, then Consume keyed at 14 and 34 cast nothing: 10.3 s with no strike."""
    game = field()
    assert not consume_due(facts(game, 16.0))
    assert not consume_due(facts(game, DEFILER_MANA + CONSUME_MANA - 1))
    assert consume_due(facts(game, DEFILER_MANA + CONSUME_MANA))
    assert consume_due(facts(game, None))  # unread: as before


def test_with_a_defiler_standing_consume_waits_only_for_its_own_mana():
    game = field(STILL_DEFILER)
    assert consume_due(facts(game, CONSUME_MANA + 1))
    assert not consume_due(facts(game, CONSUME_MANA - 1))


def test_without_the_switch_consume_is_due_whatever_the_mana(monkeypatch):
    monkeypatch.setattr(plan, 'CONSUME_PAYS', False)
    assert consume_due(facts(field(), 2.0))


def test_the_defiler_row_waits_for_its_mana(monkeypatch):
    game = field(consume=True)
    assert not defiler_missing(facts(game, DEFILER_MANA - 1))
    assert defiler_missing(facts(game, DEFILER_MANA))
    assert defiler_missing(facts(game, None))
    monkeypatch.setattr(kept, 'DEFILER_PAYS', False)
    assert defiler_missing(facts(game, 2.0))


def test_a_summon_the_mana_does_not_pay_for_is_not_keyed(monkeypatch):
    game = field()
    with pytest.raises(NoMana):
        summon_defiler(with_mana(game, DEFILER_MANA - 1))
    assert game.pressed() == []
    monkeypatch.setattr(casters, 'SUMMON_PAYS', False)
    summon_defiler(with_mana(game, DEFILER_MANA - 1))  # the fake summons whatever the mana
    assert game.pressed() == ['q']


@pytest.mark.parametrize('fast', [True, False])
def test_a_refused_spot_is_left_at_once(monkeypatch, fast):
    """03:57:59-58:18, the Plains of Despair's entry: full mana, 7 of 11 keys refused (no cast mode), each spot waited
    1.5 s for a Defiler that could not come: 18.6 s. A cast shows its mode 0.03 s after the key (p99 0.06 s)."""
    monkeypatch.setattr(casters, 'SUMMON_REFUSED_FAST', fast)
    game = field()
    refused = [True, True]
    game.blocked = lambda x, y: bool(refused) and refused.pop()
    run = with_mana(game, POOL)
    started = run.clock()
    summon_defiler(run)
    assert game.pressed() == ['q', 'q', 'q']
    refusals = run.clock() - started - ONE_SUMMON  # the two refused spots' time
    if fast:
        assert refusals < 2 * (SUMMON_REFUSED + 0.3)
    else:
        assert refusals >= 2 * SUMMON_SHOWS


def test_the_renewal_consumes_a_defiler_standing_still_and_summons_one_left_out():
    game = field(STILL_DEFILER)
    renew_consume(with_mana(game, POOL))
    assert game.pressed() == ['6', 'q']  # no summon for the Consume
    assert game.character.consume
    assert [m.unit_id for m in game.world.monsters if m.txt_id == 744] != [STILL_DEFILER.unit_id]


def test_with_two_standing_one_is_consumed_and_none_summoned():
    other = replace(STILL_DEFILER, unit_id=61, x=4996.0, y=5006.0)
    game = field(STILL_DEFILER, other)
    renew_consume(with_mana(game, POOL))
    assert game.pressed() == ['6']
    assert len([m for m in game.world.monsters if m.txt_id == 744]) == 1


@pytest.mark.parametrize(
    'scene',
    [
        (replace(STILL_DEFILER, x=BOUND_DEMON.x + 2.0, y=BOUND_DEMON.y), BOUND_DEMON),  # crowded by the bound demon
        (replace(STILL_DEFILER, mode=2),),  # walking after the character
    ],
)
def test_a_crowded_or_walking_defiler_is_not_the_one_consumed(scene):
    game = field(*scene)
    renew_consume(with_mana(game, POOL))
    assert game.pressed()[0] == 'q'


def test_without_the_switch_a_defiler_is_summoned_for_the_consume(monkeypatch):
    monkeypatch.setattr(plan, 'CONSUME_STANDING', False)
    game = field(STILL_DEFILER)
    renew_consume(with_mana(game, POOL))
    assert game.pressed() == ['q', '6', 'q']


def test_a_renewal_short_of_mana_for_its_summon_is_asked_again_soon():
    game = field()
    run = with_mana(game, DEFILER_MANA - 1)
    tried = consume_again(casting(game, run))
    assert not tried.cast
    assert game.pressed() == []
    assert tried.at == pytest.approx(run.clock() - CONSUME_RETRY + CONSUME_SOON)


def test_a_consume_made_stays_a_consume_when_the_defiler_left_out_waits_for_the_mana():
    game = field(STILL_DEFILER)
    run = with_mana(game, POOL)
    reads = [POOL]
    run.unit_stats = lambda at: {8: int(reads[0] * 256), 9: POOL * 256}

    def drained(world_seen):  # the Consume's cost takes the mana under a summon's
        if character_of(world_seen).consume:
            reads[0] = 10

    run.observe = drained
    tried = consume_again(casting(game, run))
    assert tried.cast
    assert game.pressed() == ['6']


def test_a_refused_spot_is_keyed_last_by_the_next_summon_of_the_renewal():
    """17:33:49-57 on 2026-10-23, Hole Level 2: three summons in one Consume renewal, each keyed the same two refused
    spots first again (0.7 s each time)."""
    game = field()
    bad: list[tuple[float, float]] = []  # the first two spots keyed are walls, for every summon

    def blocked(x: float, y: float) -> bool:
        if len(bad) < 2 and all(math.dist((x, y), b) > 0.05 for b in bad):
            bad.append((x, y))
        return any(math.dist((x, y), b) < 0.05 for b in bad)

    game.blocked = blocked
    run = with_mana(game, POOL)
    keyed: list[tuple[float, float]] = []
    react = game.keys.on_event

    def on_event(event):
        if event == ('key', 'q'):
            keyed.append(game.keys.fraction())
        react(event)

    game.keys.on_event = on_event
    tried: list[tuple[float, float]] = []
    summon_defiler(run, tried=tried)
    assert len(tried) == 3  # two refused, one taken
    first = len(keyed)
    summon_defiler(run, skip=1, tried=tried)
    assert len(keyed) == first + 1  # the next summon keys a spot not tried, once

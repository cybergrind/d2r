"""The buff executor (macros/buffs.py) with a plan of its own: two skills no build of the game has rows for."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import (
    STATE_DISTRUST,
    STATE_RETRY,
    STATE_TRIES,
    Buffs,
    keys_of,
    phase_keys,
)
from inventory_tracking.macros.build import Buff, Build, Casting, Tried, whenever
from inventory_tracking.macros.skills import ATTACK, SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.world import Monster
from tests.inventory_tracking.macros.fakes import OTHER_SET, PREBUFF_SET, WINDOW, Game, world


AURA, BOLT = ATTACK, TELEPORT  # two skills with a name (skills.py NAMES) that are no build's buffs
KEYS = {AURA: 'F5', BOLT: 'F6', SWAP_WEAPONS: 'c'}
ASPECT = WINDOW[2] / WINDOW[3]
NEAR = Monster(7, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0x0C, life=100, max_life=128)
FAR = Monster(8, 19, 1, 5200.0, 5000.0, 0xFFFFFFFF, 0, life=100, max_life=128)  # off the screen


def key_names(world, skills=tuple(KEYS)):
    return {skill: KEYS[skill] for skill in skills}


def shown(world):
    """The fake aura reads off the character's Consume flag: the one state the fakes' game changes."""
    return None if world.player is None else world.player.consume


def old(seconds: float):
    return lambda facts: facts.since(BOLT) > seconds


def first_foe(facts):
    return facts.foes[0] if facts.foes else None


def plan(*rows: Buff, **casters) -> Buffs:
    return Buffs(Build(name='fake', applies=lambda world: True, attack=None, movement=(), buffs=rows, casters=casters))


def game(*monsters, consume: bool | None = False):
    start = world(area=101, monsters=tuple(monsters))
    return Game(replace(start, player=replace(start.player, consume=consume)))


AURA_ROW = Buff(AURA, 'upkeep', whenever, state=shown)
BOLT_ROW = Buff(BOLT, 'upkeep', old(8.0), on='monster', target=first_foe)


def test_the_keys_of_a_row_are_its_casters_first_then_its_own_then_the_swap():
    row = Buff(AURA, 'prebuff', whenever, needs='prebuff', also=(BOLT,))
    assert keys_of(row) == (BOLT, AURA, SWAP_WEAPONS)
    assert keys_of(AURA_ROW) == (AURA,)
    rows = (row, Buff(BOLT, 'prebuff', whenever), Buff(9, 'fight', whenever), Buff(AURA, 'prebuff', whenever))
    assert phase_keys(rows, 'prebuff') == (BOLT, AURA, SWAP_WEAPONS)  # each once, the swap last
    assert phase_keys(rows, 'fight') == (9,)
    assert phase_keys(rows, 'upkeep') == ()


def test_the_rows_of_a_phase_come_in_the_plans_order():
    buffs = plan(BOLT_ROW, Buff(AURA, 'fight', whenever), AURA_ROW)
    assert buffs.rows('upkeep') == (BOLT_ROW, AURA_ROW)
    assert buffs.rows('opening') == ()


def test_a_row_with_a_state_is_due_only_while_the_state_reads_without_it():
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    assert buffs.due(run, AURA_ROW, buffs.facts(run, play.world)) is not None
    for state in (True, None):
        seen = replace(play.world, player=replace(play.world.player, consume=state))
        assert buffs.due(run, AURA_ROW, buffs.facts(run, seen)) is None


def test_a_cast_the_state_does_not_show_is_made_again_after_a_while_and_then_distrusted():
    play = game()
    buffs, run = plan(AURA_ROW), play.run()

    def due():
        return buffs.due(run, AURA_ROW, buffs.facts(run, play.world)) is not None

    buffs.cast_at[AURA, None], buffs.unseen[AURA] = play.clock.now, 1
    assert not due()
    play.clock.now += STATE_RETRY + 0.1
    assert due()
    buffs.cast_at[AURA, None], buffs.unseen[AURA] = play.clock.now, STATE_TRIES
    play.clock.now += STATE_RETRY + 0.1
    assert not due()  # cast and never seen: not every few seconds
    play.clock.now += STATE_DISTRUST
    assert due()
    seen = replace(play.world, player=replace(play.world.player, consume=True))
    assert buffs.due(run, AURA_ROW, buffs.facts(run, seen)) is None
    assert buffs.unseen[AURA] == 0  # it showed: the count starts anew
    unread = replace(play.world, player=replace(play.world.player, consume=None))
    buffs.unseen[AURA] = 1
    assert buffs.due(run, AURA_ROW, buffs.facts(run, unread)) is None
    assert buffs.unseen[AURA] == 1  # unreadable says nothing


def test_a_row_is_asked_its_own_due_then_its_target_then_its_worth():
    play = game(NEAR)
    run = play.run()
    asked = []

    def worth(facts, target):
        asked.append(target)
        return target is not None and target.leader

    row = replace(BOLT_ROW, worth=worth)
    buffs = plan(row)
    found = buffs.due(run, row, buffs.facts(run, play.world, foes=[NEAR]))
    assert found is not None
    assert (found.row, found.target) == (row, NEAR)
    assert buffs.due(run, row, buffs.facts(run, play.world)) is None  # nobody to cast it on
    assert asked == [NEAR]  # not asked what a cast on nobody is worth
    assert buffs.due(run, row, buffs.facts(run, play.world, foes=[FAR])) is None  # not worth it
    buffs.cast_at[BOLT, None] = play.clock.now
    assert buffs.due(run, row, buffs.facts(run, play.world, foes=[NEAR])) is None  # its own due says no
    assert asked == [NEAR, FAR]


def test_the_clock_is_read_anew_at_each_asking():
    play = game(NEAR)
    buffs, run = plan(BOLT_ROW), play.run()
    buffs.cast_at[BOLT, None] = play.clock.now
    facts = buffs.facts(run, play.world, foes=[NEAR])
    play.clock.now += 8.1  # a cast before it in the same look took its time
    found = buffs.due(run, BOLT_ROW, facts)
    assert found is not None
    assert found.facts.now == play.clock.now


def test_the_first_row_due_is_the_first_in_the_plans_order():
    play = game(NEAR)
    buffs, run = plan(AURA_ROW, BOLT_ROW), play.run()
    facts = buffs.facts(run, play.world, foes=[NEAR])
    assert buffs.first(run, 'upkeep', facts).row is AURA_ROW
    buffs.cast_at[AURA, None] = play.clock.now
    assert buffs.first(run, 'upkeep', facts).row is BOLT_ROW
    buffs.cast_at[BOLT, None] = play.clock.now
    assert buffs.first(run, 'upkeep', facts) is None
    assert buffs.first(run, 'fight', facts) is None


def test_a_cast_on_the_character_is_one_key_and_is_remembered_with_one_more_cast_to_show():
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    play.clock.now = 50.0
    tried = buffs.cast(run, buffs.due(run, AURA_ROW, buffs.facts(run, play.world)), key_names)
    assert play.pressed() == ['F5']
    assert (tried.cast, tried.touched) == (True, True)
    assert buffs.cast_at[AURA, None] == tried.at == play.clock.now
    assert buffs.unseen == {AURA: 1}


def test_the_cast_after_the_ones_the_state_did_not_show_is_made_with_a_warning(caplog):
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    buffs.unseen[AURA] = STATE_TRIES
    with caplog.at_level('WARNING'):
        buffs.cast(run, buffs.due(run, AURA_ROW, buffs.facts(run, play.world)), key_names)
    assert [record.getMessage() for record in caplog.records] == [
        f'Macro: Attack cast {STATE_TRIES} times and the state does not show it'
    ]
    assert buffs.unseen[AURA] == STATE_TRIES + 1


def test_a_cast_on_a_monster_puts_the_pointer_on_its_body_and_is_remembered_under_it_too():
    play = game(NEAR)
    buffs, run = plan(BOLT_ROW), play.run()
    due = buffs.due(run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
    tried = buffs.cast(run, due, key_names, ASPECT)
    assert play.pressed() == ['F6']
    assert play.keys.fraction()[0] > 0.5  # right of the character, where the monster stands
    assert tried.cast
    assert buffs.cast_at[BOLT, None] == buffs.cast_at[BOLT, NEAR.unit_id] == tried.at
    assert BOLT not in buffs.unseen  # no state to show it
    assert play.said[-1].startswith('Teleport on ')


def test_no_cast_on_a_monster_off_the_screen_or_gone_and_nothing_is_remembered():
    play = game(FAR)
    buffs, run = plan(BOLT_ROW), play.run()
    tried = buffs.cast(run, buffs.due(run, BOLT_ROW, buffs.facts(run, play.world, foes=[FAR])), key_names, ASPECT)
    assert tried == Tried()
    seen = buffs.facts(run, replace(play.world, monsters=(NEAR,)), foes=[NEAR])  # as it was a look ago
    assert buffs.cast(run, buffs.due(run, BOLT_ROW, seen), key_names, ASPECT) == Tried()  # dead since
    assert play.pressed() == []
    assert buffs.cast_at == {}


def test_a_cast_on_the_ground_puts_the_pointer_at_the_monsters_feet():
    row = replace(BOLT_ROW, on='ground')
    play = game(NEAR)
    buffs, run = plan(row), play.run()
    tried = buffs.cast(run, buffs.due(run, row, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert play.pressed() == ['F6']
    assert math.dist(play.ground_under_pointer(), (NEAR.x, NEAR.y)) < 1.5
    assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at
    far = buffs.facts(run, replace(play.world, monsters=(FAR,)), foes=[FAR])
    assert buffs.cast(run, buffs.due(run, replace(row, due=whenever), far), key_names, ASPECT) == Tried()
    assert play.pressed() == ['F6']


def test_a_row_on_a_corpse_has_no_shared_cast():
    row = Buff(AURA, 'fight', whenever, on='corpse')
    play = game()
    buffs, run = plan(row), play.run()
    with pytest.raises(ValueError, match='needs a caster'):
        buffs.cast(run, buffs.due(run, row, buffs.facts(run, play.world)), key_names)


def test_a_caster_is_called_with_the_row_and_what_it_answers_is_remembered():
    calls: list[Casting] = []

    def later(cast: Casting) -> Tried:
        calls.append(cast)
        return Tried.again(cast.run.clock(), 8.0, 2.0, touched=False)

    row = replace(BOLT_ROW, caster='later', state=shown)
    play = game(NEAR)
    buffs, run = plan(row, later=later), play.run()
    play.clock.now = 100.0
    due = buffs.due(run, row, buffs.facts(run, play.world, foes=[NEAR]))
    tried = buffs.cast(run, due, key_names, ASPECT)
    (cast,) = calls
    assert (cast.run, cast.row, cast.buffs, cast.world, cast.target) == (run, row, buffs, play.world, NEAR)
    assert (cast.aspect, cast.key_names, cast.fresh) == (ASPECT, key_names, None)
    assert not tried.touched
    assert play.pressed() == []
    assert buffs.cast_at[BOLT, None] == buffs.cast_at[BOLT, NEAR.unit_id] == 100.0 - 8.0 + 2.0
    assert BOLT not in buffs.unseen  # no cast was made: nothing for the state to show

    def asked():
        return buffs.due(run, replace(row, state=None), buffs.facts(run, play.world, foes=[NEAR])) is not None

    play.clock.now = 102.0
    assert not asked()
    play.clock.now = 102.01
    assert asked()  # again in the two seconds the caster said


def test_a_caster_may_have_the_try_counted_from_its_start_and_use_the_shared_cast():
    def stopped(cast: Casting) -> Tried:
        cast.buffs.remember(cast.row, cast.run.clock())
        raise Abort('stopped half way')

    def more(cast: Casting) -> Tried:
        tried = cast.buffs.shared(cast)
        cast.buffs.key(cast.run, AURA)
        return tried

    play = game(NEAR)
    stopping, adding = replace(BOLT_ROW, caster='stopped'), replace(BOLT_ROW, caster='more')
    buffs, run = plan(stopping, adding, stopped=stopped, more=more), play.run()
    run.keys.update(key_names(play.world))
    play.clock.now = 30.0
    with pytest.raises(Abort):
        buffs.cast(run, buffs.due(run, stopping, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert buffs.cast_at[BOLT, None] == 30.0
    play.clock.now = 40.0
    buffs.cast(run, buffs.due(run, adding, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert play.pressed() == ['F6', 'F5']


def test_a_key_under_a_held_strike_lets_it_go_first_and_resume_presses_it_again():
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    run.keys.update(key_names(play.world))
    order = []
    play.keys.on_event = lambda event: order.append(event[1])
    buffs.let_go = lambda: order.append('let go')
    buffs.key(run, AURA)
    assert order == ['let go', 'F5']
    buffs.resume(run, None)  # no strike is held: nothing to press
    before = play.clock.now
    buffs.resume(run, lambda: order.append('again'))
    assert order == ['let go', 'F5', 'again']
    assert play.clock.now > before  # the macro's own cast was waited for


def test_the_prebuff_casts_every_row_in_order_with_the_weapons_taken_once():
    calls: list[Casting] = []

    def dance(cast: Casting) -> Tried:
        calls.append(cast)
        cast.run.actuator.tap(cast.run.keys[BOLT])
        return Tried(cast.run.clock(), cast=True)

    never = Buff(BOLT, 'prebuff', lambda facts: False, needs='prebuff', caster='dance', state=shown)
    rows = (never, Buff(AURA, 'prebuff', whenever, needs='prebuff'), Buff(AURA, 'upkeep', whenever))
    play = game(consume=True)
    play.sets = [OTHER_SET, PREBUFF_SET]
    buffs, run = plan(*rows, dance=dance), play.run()
    run.keys.update(key_names(play.world))
    buffs.prebuff(run)
    assert play.pressed() == ['c', 'F6', 'F5']  # one swap; a row is cast whatever its due and state say
    (cast,) = calls
    assert (cast.row, cast.buffs, cast.world, cast.key_names, cast.fresh) == (never, buffs, None, None, None)
    assert buffs.cast_at == {}  # a game's start: nothing of it is the mode's memory

"""The buff executor (macros/buffs.py) with a plan of its own: two skills no build of the game has rows for."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Monster, Player, World
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import (
    STATE_DISTRUST,
    STATE_RETRY,
    STATE_TRIES,
    Buffs,
    Due,
    keys_of,
    lapsing,
    phase_keys,
)
from inventory_tracking.macros.build import Buff, BuffFacts, Build, Casting, Tried, whenever
from inventory_tracking.macros.skills import ATTACK, SWAP_WEAPONS, TELEPORT
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


def me(seen: World) -> Player:
    """The character of a world these tests always have one in."""
    assert seen.player is not None
    return seen.player


def due_now(buffs: Buffs, run, row: Buff, facts: BuffFacts) -> Due:
    """The row with its target, which the test expects to be due."""
    due = buffs.due(run, row, facts)
    assert due is not None
    return due


def first_due(buffs: Buffs, run, phase: str, facts: BuffFacts, *, renewing: bool = False) -> Due:
    """The first row due, which the test expects there to be."""
    due = buffs.first(run, phase, facts, renewing=renewing)
    assert due is not None
    return due


def plan(*rows: Buff, **casters) -> Buffs:
    return Buffs(Build(name='fake', applies=lambda world: True, attack=None, movement=(), buffs=rows, casters=casters))


def game(*monsters, consume: bool | None = False):
    start = world(area=101, monsters=tuple(monsters))
    return Game(replace(start, player=replace(me(start), consume=consume)))


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
        seen = replace(play.world, player=replace(me(play.world), consume=state))
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
    seen = replace(play.world, player=replace(me(play.world), consume=True))
    assert buffs.due(run, AURA_ROW, buffs.facts(run, seen)) is None
    assert buffs.unseen[AURA] == 0  # it showed: the count starts anew
    unread = replace(play.world, player=replace(me(play.world), consume=None))
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
    assert first_due(buffs, run, 'upkeep', facts).row is AURA_ROW
    buffs.cast_at[AURA, None] = play.clock.now
    assert first_due(buffs, run, 'upkeep', facts).row is BOLT_ROW
    buffs.cast_at[BOLT, None] = play.clock.now
    assert buffs.first(run, 'upkeep', facts) is None
    assert buffs.first(run, 'fight', facts) is None


def test_a_cast_on_the_character_is_one_key_and_is_remembered_with_one_more_cast_to_show():
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    play.clock.now = 50.0
    tried = buffs.cast(run, due_now(buffs, run, AURA_ROW, buffs.facts(run, play.world)), key_names)
    assert play.pressed() == ['F5']
    assert (tried.cast, tried.touched) == (True, True)
    assert buffs.cast_at[AURA, None] == tried.at == play.clock.now
    assert buffs.unseen == {AURA: 1}


def test_the_cast_after_the_ones_the_state_did_not_show_is_made_with_a_warning(caplog):
    play = game()
    buffs, run = plan(AURA_ROW), play.run()
    buffs.unseen[AURA] = STATE_TRIES
    with caplog.at_level('WARNING'):
        buffs.cast(run, due_now(buffs, run, AURA_ROW, buffs.facts(run, play.world)), key_names)
    assert [record.getMessage() for record in caplog.records] == [
        f'Macro: Attack cast {STATE_TRIES} times and the state does not show it'
    ]
    assert buffs.unseen[AURA] == STATE_TRIES + 1


def test_a_cast_on_a_monster_puts_the_pointer_on_its_body_and_is_remembered_under_it_too():
    play = game(NEAR)
    buffs, run = plan(BOLT_ROW), play.run()
    due = buffs.due(run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
    assert due is not None
    tried = buffs.cast(run, due, key_names, ASPECT)
    assert play.pressed() == ['F6']
    assert play.keys.fraction()[0] > 0.5  # right of the character, where the monster stands
    assert tried.cast
    assert buffs.cast_at[BOLT, None] == buffs.cast_at[BOLT, NEAR.unit_id] == tried.at
    assert BOLT not in buffs.unseen  # no state to show it
    assert play.said[-1].startswith('Teleport on ')


def test_a_casts_told_line_is_said_at_the_first_cast_on_a_monster_and_its_said_line_at_each(caplog):
    import logging

    row = replace(
        BOLT_ROW, due=whenever, said=lambda facts, m: f'said {m.unit_id}', told=lambda facts, m: f'told {m.unit_id}'
    )
    play = game(NEAR)
    buffs, run = plan(row), play.run()
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        for _ in range(2):
            seen = buffs.facts(run, play.world, foes=[NEAR])
            assert buffs.cast(run, due_now(buffs, run, row, seen), key_names, ASPECT).cast
    lines = [r.getMessage() for r in caplog.records if r.getMessage() in ('said 7', 'told 7')]
    assert lines == ['said 7', 'told 7', 'said 7']


def test_no_cast_on_a_monster_off_the_screen_or_gone_and_nothing_is_remembered(caplog):
    import logging

    play = game(FAR)
    buffs, run = plan(BOLT_ROW), play.run()
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        for _ in range(2):
            due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[FAR]))
            tried = buffs.cast(run, due, key_names, ASPECT)
            assert tried == Tried()
    # Said once a target (the player, 2026-10-20: "never death marked the leader")
    said = [r.getMessage() for r in caplog.records if 'off the screen' in r.getMessage()]
    assert len(said) == 1, said
    assert said[0].startswith('Macro: buff: no ')
    assert 'the monster 19 (8), 100/128: its body is off the screen at' in said[0]
    seen = buffs.facts(run, replace(play.world, monsters=(NEAR,)), foes=[NEAR])  # as it was a look ago
    assert buffs.cast(run, due_now(buffs, run, BOLT_ROW, seen), key_names, ASPECT) == Tried()  # dead since
    assert play.pressed() == []
    assert buffs.cast_at == {}


def test_a_cast_on_the_ground_puts_the_pointer_at_the_monsters_feet():
    row = replace(BOLT_ROW, on='ground')
    play = game(NEAR)
    buffs, run = plan(row), play.run()
    tried = buffs.cast(run, due_now(buffs, run, row, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert play.pressed() == ['F6']
    assert math.dist(play.ground_under_pointer(), (NEAR.x, NEAR.y)) < 1.5
    assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at
    far = buffs.facts(run, replace(play.world, monsters=(FAR,)), foes=[FAR])
    assert buffs.cast(run, due_now(buffs, run, replace(row, due=whenever), far), key_names, ASPECT) == Tried()
    assert play.pressed() == ['F6']


def test_a_row_on_a_corpse_has_no_shared_cast():
    row = Buff(AURA, 'fight', whenever, on='corpse')
    play = game()
    buffs, run = plan(row), play.run()
    with pytest.raises(ValueError, match='needs a caster'):
        buffs.cast(run, due_now(buffs, run, row, buffs.facts(run, play.world)), key_names)


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
    assert due is not None
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
        buffs.cast(run, due_now(buffs, run, stopping, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert buffs.cast_at[BOLT, None] == 30.0
    play.clock.now = 40.0
    buffs.cast(run, due_now(buffs, run, adding, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
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


# -- a buff that ends by itself (`Buff.lasts`): renewed before the fight ahead ------------------------------------

LASTING = Buff(AURA, 'upkeep', lambda facts: facts.lapsing, lasts=300.0)


def test_a_buff_that_ends_by_itself_is_lapsing_when_less_of_it_is_left_than_the_fight_ahead():
    play = game()
    facts = BuffFacts(play.world, 250.0, ahead=60.0, took={AURA: 0.0})
    assert lapsing(LASTING, facts)  # 50 s left
    assert not lapsing(LASTING, replace(facts, now=230.0))  # 70 s left
    assert not lapsing(LASTING, replace(facts, ahead=0.0))  # no fight ahead
    assert not lapsing(LASTING, replace(facts, took={}))  # no cast of it known: cast by hand
    assert not lapsing(replace(LASTING, lasts=None), facts)  # kept up by its state alone
    assert facts.left(AURA, 300.0) == 50.0
    assert facts.left(BOLT, 300.0) is None


def test_the_renewal_asks_only_a_lapsing_row_and_its_cast_says_so_and_counts_from_then(caplog):
    play = game()
    other = Buff(BOLT, 'upkeep', whenever)
    buffs, run = plan(other, LASTING), play.run()
    run.keys.update(key_names(play.world))
    buffs.took[AURA] = 0.0
    play.clock.now = 200.0  # 100 s left
    assert buffs.first(run, 'upkeep', buffs.facts(run, play.world, ahead=60.0), renewing=True) is None
    assert first_due(buffs, run, 'upkeep', buffs.facts(run, play.world, ahead=60.0)).row is other  # the plain upkeep
    play.clock.now = 250.0
    due = buffs.first(run, 'upkeep', buffs.facts(run, play.world, ahead=60.0), renewing=True)
    assert due is not None
    assert due.row is LASTING
    with caplog.at_level('INFO'):
        buffs.cast(run, due, key_names)
    assert 'Macro: buff: Attack has 50 s left of 300, under the 60 s fight ahead: cast again now' in caplog.text
    assert buffs.took[AURA] == play.clock.now
    assert buffs.first(run, 'upkeep', buffs.facts(run, play.world, ahead=60.0), renewing=True) is None


def test_the_prebuffs_casts_are_the_age_attack_mode_reads_through_the_runs_shared_record():
    """The prebuff is a run of its own with an executor of its own (routines.prebuff); attack mode's executor learns
    when its Consume was cast through the record the runner hands every run (`Run.lasting`)."""

    def dance(cast: Casting) -> Tried:
        return Tried(cast.run.clock(), cast=True)

    rows = (Buff(AURA, 'prebuff', whenever, caster='dance', lasts=300.0), LASTING)
    play = game()
    shared: dict[int, float] = {}
    prebuff = plan(*rows, dance=dance)
    run = play.run()
    run.lasting = shared
    play.clock.now = 10.0
    prebuff.prebuff(run)
    assert shared == {AURA: 10.0}
    mode, later = plan(*rows, dance=dance), play.run()
    later.lasting = shared
    play.clock.now = 260.0
    facts = mode.facts(later, play.world, ahead=60.0)
    assert facts.took[AURA] == 10.0
    assert lapsing(LASTING, facts)  # 50 s left of the prebuff's cast


# -- the life the rows may ask about (`Buffs.hurt`, BuffFacts.hurt): F3 of rca/2026-10-18/andariel-cadence-findings.md


def test_hurt_is_a_loss_of_life_within_hurt_seconds_as_the_hunt_counts_it():
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import buffs as executor, hunt

    assert executor.HURT_SECONDS == hunt.HURT_SECONDS  # the same rule as the hunt's `Facts.hurt`
    play = game()
    run = play.run()
    buffs = plan(AURA_ROW)
    play.loot = Loot(life=1800, max_life=1800)
    assert not buffs.hurt(run)
    play.clock.now += executor.LIFE_LOOK
    play.loot = Loot(life=1750, max_life=1800)
    assert buffs.hurt(run)
    play.clock.now += executor.HURT_SECONDS - 0.1
    assert buffs.hurt(run)  # no further loss, but the last within HURT_SECONDS
    play.clock.now += 0.2
    assert not buffs.hurt(run)
    # Read at most every LIFE_LOOK: a loss within it shows at the next read
    play.loot = Loot(life=1700, max_life=1800)
    assert not buffs.hurt(run)
    play.clock.now += executor.LIFE_LOOK
    assert buffs.hurt(run)


def test_hurt_is_not_known_better_than_hurt():
    from inventory_tracking.game.records import Loot

    play = game()
    run = play.run()
    play.loot = Loot()  # no life read
    assert plan(AURA_ROW).hurt(run)
    play.loot = Loot(life=1700, max_life=1800)  # a first read under the full life: hurt, as far as it shows
    assert plan(AURA_ROW).hurt(run)
    run.loot = None
    assert plan(AURA_ROW).hurt(run)


def test_the_facts_ask_the_life_only_when_a_row_does():
    from inventory_tracking.game.records import Loot

    play = game()
    run = play.run()
    reads: list[int] = []
    play.loot = Loot(life=1800, max_life=1800)
    run.loot = lambda: reads.append(1) or play.loot
    buffs = plan(AURA_ROW)
    facts = buffs.facts(run, play.world)
    assert reads == []
    assert facts.hurt is not None
    assert not facts.hurt()
    assert reads == [1]


# A cast checked on its target (`Buff.shows`, `Buffs.settle`; the player, 2026-10-20: "ok, recast"). The fake state:
# byte 0 of the words set.
CHECKED = replace(BOLT_ROW, due=whenever, shows=lambda words: words[:1] == b'\x01', shows_within=0.8, recasts=2)
MARKED, UNMARKED = b'\x01' + bytes(31), bytes(32)
BESIDE = Monster(9, 19, 1, 5010.0, 5000.0, 0xFFFFFFFF, 0, life=100, max_life=128)


def checked(*monsters: Monster, states=None):
    """A game with `monsters`, the checked row's executor and a run whose state words read `states` by unit (default:
    none shows the cast)."""
    play = game(*monsters)
    buffs, run = plan(CHECKED), play.run()
    words = states if states is not None else {}
    run.unit_states = lambda m: words.get(m.unit_id, UNMARKED)
    return play, buffs, run, words


def cast_on(play, buffs, run, target: Monster = NEAR):
    due = due_now(buffs, run, CHECKED, buffs.facts(run, play.world, foes=[target]))
    assert due.target == target
    tried = buffs.cast(run, due, key_names, ASPECT)
    assert tried.cast
    return tried


def ask(play, buffs, run, after: float, foes=(NEAR,)):
    """The row asked `after` s on (the look's facts then): its Due or None."""
    play.clock.now += after
    return buffs.due(run, CHECKED, buffs.facts(run, play.world, foes=list(foes)))


def said(caplog, words: str) -> list[str]:
    return [r.getMessage() for r in caplog.records if words in r.getMessage()]


def test_a_cast_that_shows_on_its_target_is_not_cast_again(caplog):
    import logging

    play, buffs, run, words = checked(NEAR)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        tried = cast_on(play, buffs, run)
        words[NEAR.unit_id] = MARKED
        ask(play, buffs, run, 0.4)
        assert buffs.watching == {}
        ask(play, buffs, run, 1.0)
    assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at  # its clock stands: the row's own rules decide
    assert said(caplog, 'did not take') == []


def test_a_cast_not_shown_within_its_window_is_cast_again_said_with_its_try(caplog):
    import logging

    play, buffs, run, _ = checked(NEAR)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        cast_on(play, buffs, run)
        ask(play, buffs, run, 0.5)  # not yet: a mark shows in 0.43 s at the median, 0.8 s at the latest
        assert (BOLT, NEAR.unit_id) in buffs.cast_at
        due = ask(play, buffs, run, 0.4)
        assert due is not None
        assert due.target == NEAR
    assert (BOLT, NEAR.unit_id) not in buffs.cast_at
    assert said(caplog, 'did not take') == [
        'Macro: buff: Teleport on the elite 19 (7), 100/128 did not take (it shows on no monster near it): cast '
        'again (try 2)'
    ]


def test_the_casts_again_are_bounded_then_said_once_and_the_clock_kept(caplog):
    import logging

    play, buffs, run, _ = checked(NEAR)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        for _ in range(3):
            cast_on(play, buffs, run)
            ask(play, buffs, run, 0.9)
    lines = said(caplog, 'did not take')
    assert [line.rsplit(' ', 1)[-1] for line in lines[:2]] == ['2)', '3)']
    assert lines[2].endswith('did not take (it shows on no monster near it), 3 casts: not cast again on it while the '
                             'last would last')  # fmt: skip
    assert (BOLT, NEAR.unit_id) in buffs.cast_at


def test_a_cast_again_that_shows_says_its_try_and_the_count_starts_anew(caplog):
    import logging

    play, buffs, run, words = checked(NEAR)
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        cast_on(play, buffs, run)
        ask(play, buffs, run, 0.9)
        cast_on(play, buffs, run)
        words[NEAR.unit_id] = MARKED
        ask(play, buffs, run, 0.5)
    assert said(caplog, 'took at') == ['Macro: buff: Teleport on the elite 19 (7), 100/128 took at try 2']
    assert buffs.missed == {}


def test_where_a_cast_went_instead_is_said(caplog):
    import logging

    play, buffs, run, words = checked(NEAR, BESIDE)
    words[BESIDE.unit_id] = MARKED
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        cast_on(play, buffs, run)
        ask(play, buffs, run, 0.9, foes=(NEAR, BESIDE))
    assert said(caplog, 'did not take') == [
        'Macro: buff: Teleport on the elite 19 (7), 100/128 did not take (it shows on the monster 19 (9)): cast '
        'again (try 2)'
    ]


def test_no_cast_again_on_a_monster_dead_or_gone_or_while_the_character_is_dead_or_with_the_words_unread(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        play, buffs, run, _ = checked(NEAR)
        tried = cast_on(play, buffs, run)
        play.world = replace(play.world, monsters=())  # dead and gone
        ask(play, buffs, run, 0.9, foes=())
        assert buffs.watching == {}
        assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at

        play, buffs, run, _ = checked(NEAR)
        tried = cast_on(play, buffs, run)
        play.world = replace(play.world, monsters=(replace(NEAR, mode=12),))  # lying dead
        ask(play, buffs, run, 0.9)
        assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at

        play, buffs, run, _ = checked(NEAR)
        tried = cast_on(play, buffs, run)
        play.world = replace(play.world, player=replace(me(play.world), mode=0))  # the character died
        ask(play, buffs, run, 0.9)
        assert buffs.watching == {}
        assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at

        play, buffs, run, _ = checked(NEAR)
        run.unit_states = lambda m: None
        tried = cast_on(play, buffs, run)
        ask(play, buffs, run, 0.9)
        assert buffs.watching == {}
        assert buffs.cast_at[BOLT, NEAR.unit_id] == tried.at
    assert said(caplog, 'did not take') == []


def test_a_row_with_no_check_is_never_watched():
    play = game(NEAR)
    buffs, run = plan(BOLT_ROW), play.run()
    run.unit_states = lambda m: UNMARKED
    buffs.cast(run, due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    assert buffs.watching == {}


# The pointer on the target before the key (AIM_CHECK): the cast goes on the unit under the pointer.
def hovering(run, *answers):
    """The hover record naming `answers` in turn, the last one after; the reads counted in the list returned."""
    reads: list[tuple[int, int] | None] = []

    def read():
        found = answers[min(len(reads), len(answers) - 1)]
        reads.append(found)
        return found

    run.hovered = read
    return reads


def test_the_pointer_is_moved_up_the_body_while_the_hover_names_another_monster(caplog):
    import logging

    from inventory_tracking.macros.buffs import NUDGE_UP

    play = game(NEAR, BESIDE)
    buffs, run = plan(BOLT_ROW), play.run()
    reads = hovering(run, (1, BESIDE.unit_id), (1, NEAR.unit_id))
    due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        aimed: list[tuple[float, float]] = []
        aim = run.actuator.aim

        def noted(x: float, y: float, *, scatter: tuple[int, int] = (4, 3), near: int = 0) -> None:
            aimed.append((x, y))
            aim(x, y, scatter=scatter, near=near)

        run.actuator.aim = noted
        assert buffs.cast(run, due, key_names, ASPECT).cast
    assert len(reads) == 2
    assert len(aimed) == 2
    assert aimed[1][1] == pytest.approx(aimed[0][1] - NUDGE_UP)
    assert play.pressed() == ['F6']
    assert said(caplog, 'the pointer named') == [
        'Macro: buff: Teleport on the elite 19 (7): the pointer named the monster 19 (9); moved 1 times, now on it'
    ]


def test_the_key_is_pressed_after_the_nudges_whatever_the_hover_names(caplog):
    import logging

    from inventory_tracking.macros.buffs import NUDGES

    play = game(NEAR, BESIDE)
    buffs, run = plan(BOLT_ROW), play.run()
    reads = hovering(run, (1, BESIDE.unit_id))
    due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        assert buffs.cast(run, due, key_names, ASPECT).cast
    assert len(reads) == NUDGES + 1
    assert play.pressed() == ['F6']
    assert said(caplog, 'pressed anyway') == [
        f'Macro: buff: Teleport on the elite 19 (7): the pointer names the monster 19 (9) after {NUDGES} moves (the '
        'cast goes on the unit under it): pressed anyway'
    ]


def test_the_pointer_is_left_where_the_hover_names_the_target_or_nothing(caplog):
    import logging

    for answer in ((1, NEAR.unit_id), None, (0, 0)):
        play = game(NEAR, BESIDE)
        buffs, run = plan(BOLT_ROW), play.run()
        reads = hovering(run, answer)
        due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
        with caplog.at_level(logging.INFO, logger='inventory_tracking'):
            assert buffs.cast(run, due, key_names, ASPECT).cast
        assert len(reads) == 1
    assert said(caplog, 'the pointer') == []


def test_the_pointer_follows_a_target_that_moved_since_the_look_and_none_of_it_with_the_check_off(monkeypatch):
    from inventory_tracking.macros import buffs as executor
    from inventory_tracking.macros.routines import screen_fraction

    for check in (True, False):
        monkeypatch.setattr(executor, 'AIM_CHECK', check)
        play = game(NEAR)
        buffs, run = plan(BOLT_ROW), play.run()
        due = due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR]))
        went = replace(NEAR, y=NEAR.y + 3.0)
        play.world = replace(play.world, monsters=(went,))
        assert buffs.cast(run, due, key_names, ASPECT).cast
        now = screen_fraction(me(play.world), went.x, went.y, ASPECT)
        before = screen_fraction(me(play.world), NEAR.x, NEAR.y, ASPECT)
        at = play.keys.fraction()
        assert math.dist(at, now if check else before) < math.dist(at, before if check else now)


@pytest.mark.parametrize('first', [True, False])
def test_a_cast_on_a_monster_lets_the_held_strike_go_before_the_pointer_leaves_its_line(monkeypatch, first):
    # LET_GO_FIRST (the player, 2026-10-21 ~20:15: "we need to do the best aiming when we're trying to focus mob";
    # rca/2026-10-21/herald-aiming-findings.md §1.1): a strike begun while the pointer was on the mark's target flew
    # there. The fake game says where the pointer stood as the strike's button went up.
    from inventory_tracking.macros import buffs as module

    monkeypatch.setattr(module, 'LET_GO_FIRST', first)
    play = game(NEAR)
    buffs, run = plan(BOLT_ROW), play.run()
    run.keys.update(key_names(play.world))
    on_line = play.keys.fraction()
    with run.actuator.hold('Button3') as again:
        buffs.let_go = getattr(again, 'release', None)  # actuator.hold's, read as hunt.py reads it
        buffs.cast(run, due_now(buffs, run, BOLT_ROW, buffs.facts(run, play.world, foes=[NEAR])), key_names, ASPECT)
    (released,) = [event for event in play.keys.events if event[0] == 'button' and event[1] == 3][:1]
    assert (released[2] == on_line) is first  # off: the strike was let go with the pointer on the target
    assert play.pressed()[-1] == 'F6'  # the key is pressed either way

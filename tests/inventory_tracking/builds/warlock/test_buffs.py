"""The Warlock's buff plan (builds/warlock/buffs.py): when each row is due, under the names the due-tests
had in macros/rotation.py (`Rotation`, the view of the executor's memory the hunt keeps for the tests)."""

from dataclasses import replace

from inventory_tracking.builds.warlock.buffs import (
    BUFFS,
    CONSUME_CLEAR,
    CONSUME_RETRY,
    CONSUME_SECONDS,
    CONSUME_SOON,
    ENGORGE_HURT_SECONDS,
    ENGORGE_REACH,
    ENGORGE_RETRY,
    SIGIL_LOOK,
    SIGIL_SECONDS,
    WARD_SECONDS,
    Rotation,
    consume_due,
    engorge_on_a_key,
    purge_shown,
    ward_shown,
)
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.mark import MARK_DELAY, mark_due, strongest
from inventory_tracking.builds.warlock.skills import (
    BIND_DEMON,
    CONSUME,
    DEATH_MARK,
    ENGORGE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SIGIL_LETHARGY,
    SUMMON_DEFILER,
)
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import (
    STATE_DISTRUST as HEX_DISTRUST,
    STATE_RETRY as HEX_RETRY,
    STATE_TRIES as HEX_TRIES,
    Buffs,
    keys_of,
    phase_keys,
)
from inventory_tracking.macros.build import BuffFacts
from inventory_tracking.macros.cta import BATTLE_ORDERS
from inventory_tracking.macros.skills import SWAP_WEAPONS
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, WINDOW, Game, character_of, world


def game():
    return Game(world(area=101, slots=HUNT_SLOTS))


def rotation_of():
    return Rotation(Buffs(ECHOING_STRIKE_BUILD))


def test_a_sigil_is_due_under_an_elite_once_the_last_one_under_it_is_old():
    play = game()
    rotation, run = rotation_of(), play.run()
    elite, plain = Monster(1, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0x0C), Monster(2, 19, 1, 5008.0, 5000.0, 0xFFFFFFFF, 0)
    assert rotation.sigil_due(run, elite)
    assert not rotation.sigil_due(run, plain)
    rotation.sigiled[1] = play.clock.now
    assert not rotation.sigil_due(run, elite)
    play.clock.now += SIGIL_SECONDS + 0.1
    assert rotation.sigil_due(run, elite)


def test_hex_purge_is_due_while_the_state_does_not_show_it_and_distrusted_after_unseen_casts():
    play = game()
    rotation, run = rotation_of(), play.run()
    shown = replace(play.world, player=replace(play.character, hex_purge=True))
    gone = replace(play.world, player=replace(play.character, hex_purge=False))
    assert not rotation.purge_due(run, shown)
    assert rotation.purge_due(run, gone)
    rotation.purged_at, rotation.purges_unseen = play.clock.now, 1
    assert not rotation.purge_due(run, gone)
    play.clock.now += HEX_RETRY + 0.1
    assert rotation.purge_due(run, gone)
    rotation.purged_at, rotation.purges_unseen = play.clock.now, HEX_TRIES
    play.clock.now += HEX_RETRY + 0.1
    assert not rotation.purge_due(run, gone)  # cast and never seen: not every few seconds
    play.clock.now += HEX_DISTRUST
    assert rotation.purge_due(run, gone)


def test_psychic_ward_is_due_while_the_state_does_not_show_it_and_in_a_fight_once_in_five_seconds():
    play = game()
    rotation, run = rotation_of(), play.run()
    shown = replace(play.world, player=replace(play.character, ward=True))
    gone = replace(play.world, player=replace(play.character, ward=False))
    unread = replace(play.world, player=replace(play.character, ward=None))
    assert not rotation.ward_due(run, shown)
    assert not rotation.ward_due(run, unread)
    assert rotation.ward_due(run, gone)
    assert rotation.ward_due(run, gone, fighting=True)
    rotation.warded_at, rotation.wards_unseen = play.clock.now, 1
    play.clock.now += HEX_RETRY + 0.1
    assert rotation.ward_due(run, gone)
    assert not rotation.ward_due(run, gone, fighting=True)  # a pack breaks it faster than it is cast
    play.clock.now += WARD_SECONDS
    assert rotation.ward_due(run, gone, fighting=True)
    assert not rotation.ward_due(run, replace(gone, slots=()))  # not on a key: never asked for


# --- the plan as rows (2026-10-12) ---


def test_the_plan_casts_each_phase_in_the_order_the_hunt_and_the_prebuff_had():
    by_phase = {phase: [row.skill for row in BUFFS if row.phase == phase] for phase in ('prebuff', 'upkeep', 'fight')}
    assert by_phase == {
        'prebuff': [CONSUME, HEX_PURGE, PSYCHIC_WARD],
        # A Defiler kept out (2026-10-14, run-1932-findings.md issue 3): after Consume in the quiet (its renewal
        # summons one of its own), before Death Mark under the strike (the mark sends it)
        # Battle Orders from a Call to Arms first, out of town (macros/cta.py, 2026-10-17)
        'upkeep': [BATTLE_ORDERS, HEX_PURGE, PSYCHIC_WARD, CONSUME, SUMMON_DEFILER],
        # Bind Demon again in a tier 4-5 Herald pack fight (builds/warlock/bind.py, 2026-10-21); Engorge first for a pet
        # in danger or among a dangerous pack (buffs.py `engorge_first`, 2026-10-21), the lazy one last
        'fight': [ENGORGE, HEX_PURGE, PSYCHIC_WARD, SUMMON_DEFILER, DEATH_MARK, BIND_DEMON, SIGIL_LETHARGY, ENGORGE],
    }
    assert [(row.skill, row.phase, row.caster) for row in BUFFS if row.caster] == [
        (CONSUME, 'prebuff', 'defiler dance'),
        (BATTLE_ORDERS, 'upkeep', 'cta'),
        (CONSUME, 'upkeep', 'consume'),
        (SUMMON_DEFILER, 'upkeep', 'defiler'),
        (ENGORGE, 'fight', 'engorge'),
        (SUMMON_DEFILER, 'fight', 'defiler'),
        (BIND_DEMON, 'fight', 'bind'),
        (SIGIL_LETHARGY, 'fight', 'sigil'),
        (ENGORGE, 'fight', 'engorge'),
    ]
    assert all(row.needs == 'prebuff' for row in BUFFS if row.phase == 'prebuff' or row.skill == CONSUME)
    assert all(row.needs is None for row in BUFFS if row.phase != 'prebuff' and row.skill != CONSUME)


def test_the_keys_the_prebuff_needs_are_the_ones_it_always_asked_for_in_that_order():
    from inventory_tracking.macros import routines

    assert phase_keys(BUFFS, 'prebuff') == (SUMMON_DEFILER, CONSUME, HEX_PURGE, PSYCHIC_WARD, SWAP_WEAPONS)
    assert routines.prebuff_keys(ECHOING_STRIKE_BUILD) == phase_keys(BUFFS, 'prebuff')
    assert keys_of(next(row for row in BUFFS if row.caster == 'consume')) == (SUMMON_DEFILER, CONSUME, SWAP_WEAPONS)


def test_only_hex_purge_psychic_ward_and_battle_orders_go_by_the_rule_for_a_state_that_reads_never_in_the_prebuff():
    assert {(row.skill, row.phase) for row in BUFFS if row.state is not None} == {
        (BATTLE_ORDERS, 'upkeep'),
        (HEX_PURGE, 'upkeep'),
        (PSYCHIC_WARD, 'upkeep'),
        (HEX_PURGE, 'fight'),
        (PSYCHIC_WARD, 'fight'),
    }


def test_a_buff_on_no_key_reads_as_unreadable_and_is_not_kept_up():
    play = game()
    assert purge_shown(play.world) is None  # the fakes' character: not read
    on = replace(play.world, player=replace(play.character, hex_purge=False, ward=True))
    assert (purge_shown(on), ward_shown(on)) == (False, True)
    off_keys = replace(on, slots=())
    assert (purge_shown(off_keys), ward_shown(off_keys)) == (None, None)
    assert purge_shown(replace(on, player=None)) is None


def test_death_mark_by_its_own_rule_is_for_the_strongest_in_reach_the_leader_first_then_the_nearer():
    # 2026-10-14: the gap between two marks is the skill's own delay (localdelay 20 frames), no more: a new mark is
    # for when the marked monster dies or its mark runs out (mark.py `target`), not a clock of 8 s.
    play = game()
    plain = Monster(1, 19, 1, 5004.0, 5000.0, 0xFFFFFFFF, 0, life=128, max_life=128)
    same = Monster(2, 19, 1, 5010.0, 5000.0, 0xFFFFFFFF, 0, life=128, max_life=128)
    elite = Monster(3, 19, 1, 5012.0, 5000.0, 0xFFFFFFFF, 0x0C, life=60, max_life=64)
    assert strongest(BuffFacts(play.world, 0.0, reachable=(same, plain))) is plain
    assert strongest(BuffFacts(play.world, 0.0, reachable=(plain, same, elite))) is elite
    assert strongest(BuffFacts(play.world, 0.0)) is None
    assert mark_due(BuffFacts(play.world, 100.0))
    assert not mark_due(BuffFacts(play.world, 100.0, cast_at={(DEATH_MARK, None): 100.0 - MARK_DELAY}))
    assert mark_due(BuffFacts(play.world, 100.0, cast_at={(DEATH_MARK, None): 100.0 - MARK_DELAY - 0.01}))
    assert not mark_due(BuffFacts(replace(play.world, slots=()), 100.0))


def test_consume_is_due_only_in_front_off_its_wait_and_with_nothing_hostile_near():
    play = game()
    out = replace(play.world, player=replace(play.character, consume=False))
    near = Monster(1, 19, 1, 5000.0 + CONSUME_CLEAR, 5000.0, 0xFFFFFFFF)
    asked = []

    def in_front():
        asked.append('focus')
        return True

    assert consume_due(BuffFacts(out, 100.0, focused=in_front))
    assert not consume_due(BuffFacts(out, 100.0, focused=lambda: False))
    assert not consume_due(BuffFacts(out, 100.0, foes=(near,)))
    assert not consume_due(BuffFacts(out, 100.0, cast_at={(CONSUME, None): 100.0 - CONSUME_RETRY}))
    asked.clear()
    for state in (True, None):  # on, or unreadable: not asked for
        shown = replace(out, player=replace(character_of(out), consume=state))
        assert not consume_due(BuffFacts(shown, 100.0, focused=in_front))
    assert not consume_due(BuffFacts(replace(out, slots=()), 100.0, focused=in_front))
    assert asked == []  # the display is asked only once the state and the keys say it could be cast


def test_consume_on_is_renewed_in_the_quiet_only_when_it_would_end_inside_the_boss_fight_ahead():
    """rca/2026-10-14/run-1214-findings.md §3.4: cast at the prebuff (15:14:47.9), it ran out 300.7 s later in
    Diablo's fight, max life 1818 -> 1580. With the boss ahead its row is told it is lapsing, and casts it again."""
    play = game()
    on = replace(play.world, player=replace(play.character, consume=True))
    near = Monster(1, 19, 1, 5000.0 + CONSUME_CLEAR, 5000.0, 0xFFFFFFFF)
    assert consume_due(BuffFacts(on, 100.0, lapsing=True))
    assert not consume_due(BuffFacts(on, 100.0))  # on, and no boss ahead: not cast
    assert not consume_due(BuffFacts(on, 100.0, lapsing=True, foes=(near,)))  # never with a hostile near
    unread = replace(on, player=replace(character_of(on), consume=None))
    assert not consume_due(BuffFacts(unread, 100.0, lapsing=True))
    (row,) = [row for row in BUFFS if row.skill == CONSUME and row.phase == 'upkeep']
    assert row.lasts == CONSUME_SECONDS == 300.0
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    buffs.took[CONSUME] = 0.0  # the prebuff's cast
    play.clock.now = 241.0  # 59 s left of it, under the 60 s of a boss's fight
    play.focused = True
    due = buffs.due(run, row, buffs.facts(run, on, ahead=60.0))
    assert due is not None
    assert due.facts.lapsing
    play.clock.now = 239.0  # 61 s left: it lasts through the fight
    assert buffs.due(run, row, buffs.facts(run, on, ahead=60.0)) is None


# --- the casters' answers (builds/warlock/casters.py) ---


def test_a_sigil_off_the_screen_is_asked_again_in_a_second():
    play = game()
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    row = next(row for row in BUFFS if row.skill == SIGIL_LETHARGY)
    elite = Monster(1, 19, 1, 5200.0, 5000.0, 0xFFFFFFFF, 0x0C)
    play.clock.now = 50.0
    due = buffs.due(run, row, buffs.facts(run, play.world, prey=elite))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: {skill: KEYS[skill] for skill in skills}, WINDOW[2] / WINDOW[3])
    assert (tried.cast, tried.touched) == (False, True)
    assert play.sigils == []
    # an elite is kept in its sigil (SIGIL_KEEPS): looked at every SIGIL_LOOK, the try again a second on
    assert buffs.cast_at[SIGIL_LETHARGY, 1] == 50.0 - SIGIL_LOOK + 1.0
    rotation = Rotation(buffs)
    assert rotation.sigiled[1] == buffs.cast_at[SIGIL_LETHARGY, 1]
    play.clock.now = 51.0
    assert not rotation.sigil_due(run, elite)
    play.clock.now = 51.01
    assert rotation.sigil_due(run, elite)


def test_engorge_with_no_corpse_in_reach_touches_nothing_and_looks_again_after_the_retry():
    play = game()
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    run.corpses = lambda: ((91, 5000.0 + ENGORGE_REACH + 1.0, 5000.0),)
    row = next(row for row in BUFFS if row.skill == ENGORGE and row.due is engorge_on_a_key)
    demon = Monster(20, 744, 1, 5004.0, 5000.0, 1, ally=True, life=60, max_life=100)
    seen = replace(play.world, monsters=(demon,))
    play.clock.now = 50.0
    before = play.keys.pointer()
    due = buffs.due(run, row, buffs.facts(run, seen))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    assert (tried.cast, tried.touched) == (False, False)
    assert (play.pressed(), play.keys.pointer()) == ([], before)
    assert Rotation(buffs).engorged_at == 50.0 - ENGORGE_HURT_SECONDS + ENGORGE_RETRY
    play.clock.now = 50.0 + ENGORGE_RETRY
    assert buffs.due(run, row, buffs.facts(run, seen)) is None
    play.clock.now += 0.01
    assert buffs.due(run, row, buffs.facts(run, seen)) is not None
    run.corpses = None
    assert buffs.due(run, row, buffs.facts(run, seen)) is None  # the corpses cannot be read: never


def test_a_consume_that_cannot_be_cast_counts_from_its_start_and_one_a_key_stopped_comes_again_soon(caplog):
    row = next(row for row in BUFFS if row.caster == 'consume')

    def tried_with(stop):
        play = game()
        buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
        out = replace(play.world, player=replace(play.character, consume=False))
        play.clock.now = 50.0

        def no_keys(world, skills):
            play.clock.now += 1.5  # the try took its time before it stopped
            raise stop

        due = buffs.due(run, row, buffs.facts(run, out))
        assert due is not None
        with caplog.at_level('INFO'):
            tried = buffs.cast(run, due, no_keys)
        assert play.said == ['Consume ran out: casting it again']
        return tried, Rotation(buffs).consumed_at

    tried, at = tried_with(Abort('Consume: not seen in 2.5s'))
    assert (tried.cast, at) == (False, 50.0)
    assert 'Macro: no Consume (Consume: not seen in 2.5s); again in 20s' in caplog.messages
    tried, at = tried_with(ValueError('Consume has no key the macro can press'))
    assert at == 50.0
    tried, at = tried_with(Abort('a key was pressed'))
    assert at == 51.5 - CONSUME_RETRY + CONSUME_SOON
    assert 'Macro: no Consume (a key was pressed); again in 3s' in caplog.messages

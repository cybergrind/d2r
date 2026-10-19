"""Attack mode and the seek step on a scripted level.

The character stands at world (5000, 5000), tile (1000, 1000), in an 8x8 room with a corridor east
(as test_teleport.py), on Durance of Hate Level 2 (101; the fakes' 109 is Harrogath, a town, where
there is nothing to hunt). Monsters are placed in world units; flags 0x0C make a champion. Attack mode
runs until cancelled: the game's `arrivals` script what happens meanwhile, cancelling included.
"""

import logging
import math
from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.builds.generic import GENERIC
from inventory_tracking.builds.warlock.buffs import CONSUME_RETRY, SIGIL_SECONDS, WARD_SECONDS, Rotation
from inventory_tracking.builds.warlock.casters import SUMMON_SPOTS
from inventory_tracking.builds.warlock.echoing_strike.attack import REACH
from inventory_tracking.builds.warlock.movement import WARP_DELAY
from inventory_tracking.builds.warlock.skills import BLADE_WARP, DEATH_MARK, ECHOING_STRIKE
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.combat.policy import Choice
from inventory_tracking.combat.stance import CAMP_REACH
from inventory_tracking.game.records import HEALING, VALUABLE, Drop, Monster, Player, Teleport, World
from inventory_tracking.levels.model import Ground, Level, Room, Walkable, pack_cells
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import STATE_DISTRUST as HEX_DISTRUST
from inventory_tracking.macros.hunt import (
    MISSES_IN_A_ROW,
    NEARING_SECONDS,
    QUIET_UNITS,
    RUN_IN_PLACE,
    STRIKE_REACH,
    TOUGH_POINTS,
    UNTOUCHABLE_SECONDS,
    UNTOUCHED_CASTS,
    Hunter,
    hostiles,
    strike_input,
)
from inventory_tracking.macros.hunting.base import FOLLOW_SECONDS, SWEEP_UNITS
from inventory_tracking.macros.skills import ATTACK, SWAP_WEAPONS, TELEPORT
from inventory_tracking.macros.travel import JUMP_REACH, Step, attackable, step_walk
from inventory_tracking.native.layout import HIRELING_CLASS_ID
from tests.inventory_tracking.macros.fakes import (
    BUILD,
    HUNT_SLOTS,
    KEYS,
    PREBUFF_SET,
    Game,
    patch_hunt,
    player,
    warlock,
    world,
)


@pytest.fixture
def marks_all(monkeypatch):
    """Death Mark on whatever is strongest, as before 2026-10-11: these tests are about the mark's timing. Since
    2026-10-14 its worth (mark.py `why_not`: a demon out, no trash, the price) is taken as nothing against it."""
    from inventory_tracking.builds.warlock import mark as mark_module

    monkeypatch.setattr(mark_module, 'why_not', lambda facts, monster: None)


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))
ROOMS = (HERE, *EAST)
STAFF = Teleport(10, 20, True)
CHAMPION, MINION, PLAIN = 0x0C, 0x10, 0
ASPECT = 2560 / 1418


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def me(seen: World) -> Player:
    """The character of a world these tests always have one in."""
    assert seen.player is not None
    return seen.player


def foe(unit_id, x, y, flags=PLAIN, txt_id=19, **changes):
    return Monster(unit_id, txt_id, 1, x, y, 0xFFFFFFFF, flags, **changes)


def game(*monsters, **changes):
    changes.setdefault('area', 101)
    changes.setdefault('slots', HUNT_SLOTS)
    start = world(monsters=tuple(monsters), **changes)
    # Consume on, as after the prebuff a run starts with: without it attack mode casts it first.
    play = Game(replace(start, player=replace(me(start), consume=True)))
    play.staff = STAFF
    return play


def hunter(play, *, ground=(), remembered=(), explored=None):
    def level():
        return Level(me(play.world).area, ROOMS, tuple(ground))

    return Hunter(
        level,
        lambda area: list(remembered),
        None if explored is None else lambda area: set(explored),
        build=warlock(play.world),
    )


def attack_mode(play, hunt, *, until=30.0, events=()):
    """Run attack mode with `events` ((seconds, callable)) happening meanwhile; cancelled at `until`."""
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False  # as the runner sets them for the mode
    for at, event in events:
        play.arrivals.append((at, event))
    play.arrivals.append((until, run.cancelled.set))
    play.arrivals.sort(key=lambda pair: pair[0])
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)


def appear(play, *monsters):
    return lambda: setattr(play, 'world', replace(play.world, monsters=(*play.world.monsters, *monsters)))


# --- attack mode: the kill ---


def test_the_aim_leaves_an_items_label_and_stays_on_the_line(caplog):
    # Drifter Cavern, 09:52 on 2026-10-12: a potion's label under the pointer and 21 casts flew to the potion.
    play = game(foe(10, 5008.0, 5000.0, life=90, max_life=90))
    play.toughness[10] = 2
    lift = play.pick_above / 16
    potion = Drop(77, 5008.0 + lift, 5000.0 + lift, 'a healing potion', HEALING)
    play.loot = replace(play.loot, drops=(potion,))
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=5.0)
    assert "an item's label under the aim at (5008.0, 5000.0)" in caplog.text
    # The first cast is out before the game has noted what is under the pointer; the next is off the label.
    assert [unit for unit, _ in play.strikes] == [10, 10]
    last = play.strikes[-1][1]
    assert last[0] > 5010.0  # further out along the line
    assert abs(last[1] - 5000.0) < 1.0


def test_attack_mode_strikes_a_monster_in_reach_by_the_skill_key_until_it_dies(marks_all):
    play = game(foe(10, 5008.0, 5000.0, life=90, max_life=90))
    play.toughness[10] = 2
    attack_mode(play, hunter(play), until=5.0)

    # The strike goes first and the mark under it (the logs of 2026-10-10: the mark and the sigil cast
    # first held the first strike back 0.3 to 0.7 s). The strike is let go and pressed again under the
    # mark's cast, so the game has it waiting when the mark is out; the last release ends the fight.
    # (A key reads as pressed at its release: the strike is let go for the mark, which is why it is first.)
    assert play.pressed() == ['7', 'd', '7']
    assert [unit for unit, _ in play.strikes] == [10, 10]
    # The blades meet at the pointer: the policy's focal point, on a lone monster where it stands; a
    # cast that flies while the pointer is on its body for the mark meets there.
    assert math.dist(play.strikes[0][1], (5008.0, 5000.0)) < 1.5
    assert all(math.dist(point, (5008.0, 5000.0)) < 3.0 for _, point in play.strikes)
    assert play.world.monsters == ()
    assert play.said == [
        'Attack mode on',
        'Echoing Strike (key 7) at the monster 19 (10), 90/90',
        'Death Mark',
        'Death Mark on the monster 19 (10), 89/90',
        play.said[4],
        play.said[-1],
    ]
    assert play.said[-1].startswith('Last minute: ')
    assert play.said[-1].endswith('of combat')


def test_the_right_mouse_button_is_held_when_it_holds_echoing_strike_as_the_player_does():
    play = game(foe(10, 5008.0, 5000.0))
    play.world = replace(play.world, player=player(101, consume=True, right_skill=ECHOING_STRIKE))
    attack_mode(play, hunter(play), until=5.0)
    assert play.pressed() == []  # the key stays unused, and the monster died before a mark
    assert [event[:2] for event in play.keys.events if event[0] == 'button'] == [('button', 3)]
    assert [unit for unit, _ in play.strikes] == [10]


def test_a_game_casting_once_per_press_gets_the_input_pressed_again(marks_all):
    play = game(foe(10, 5008.0, 5000.0))
    play.repeats = False
    play.toughness[10] = 3
    attack_mode(play, hunter(play), until=5.0)
    assert [unit for unit, _ in play.strikes] == [10, 10, 10]
    assert play.pressed().count('7') >= 2  # one hold, pressed again
    assert play.marks == [10]  # the mark under the held strike, once a cast was out


def test_without_a_key_the_mouse_button_holding_echoing_strike_is_used():
    play = game(foe(10, 5008.0, 5000.0), slots=(*HUNT_SLOTS[:13], None, *HUNT_SLOTS[14:]))
    play.world = replace(play.world, player=player(101, consume=True, right_skill=ECHOING_STRIKE))
    attack_mode(play, hunter(play), until=5.0)
    assert [event[:2] for event in play.keys.events if event[0] == 'button'] == [('button', 3)]
    assert 'Echoing Strike (right click) at the monster 19 (10), life unknown' in play.said

    play = game(foe(10, 5008.0, 5000.0), slots=(*HUNT_SLOTS[:13], None, *HUNT_SLOTS[14:]))
    play.world = replace(play.world, player=player(101, consume=True, left_skill=ECHOING_STRIKE))
    attack_mode(play, hunter(play), until=5.0)
    assert play.pressed() == ['Shift_L']  # Shift held for the click
    assert play.strikes[0][0] == 10


def test_a_plain_attack_on_the_left_button_is_not_echoing_strike_and_the_mode_gives_up(caplog):
    play = game(foe(10, 5008.0, 5000.0), slots=(*HUNT_SLOTS[:13], None, *HUNT_SLOTS[14:]))
    play.world = replace(play.world, player=player(101, consume=True, left_skill=ATTACK))
    with caplog.at_level('INFO'), pytest.raises(Abort, match=f'{MISSES_IN_A_ROW} fights stopped in a row'):
        hunter(play).attack_mode(play.run(), keys)
    assert play.keys.events == []
    assert sum('the fight stopped (Echoing Strike is on no skill key' in r.message for r in caplog.records) == 5


def test_a_fight_logs_its_line_and_its_casts(caplog):
    play = game(foe(10, 5008.0, 5000.0, life=100, max_life=100))
    play.toughness[10] = 3
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=5.0)
    lines = [r.message for r in caplog.records if r.message.startswith('Macro: line through')]
    assert len(lines) == 1
    assert lines[0].startswith(
        'Macro: line through the monster 19 (10), 100/100, 8.0 away, focal (5008.0, 5000.0), worth '
    )
    fights = [r.message for r in caplog.records if r.message.startswith('Macro: fight')]
    assert len(fights) == 1
    assert fights[0].startswith('Macro: fight (key 7): ')
    assert fights[0].endswith('1 down; Nothing left in reach')


def test_an_elite_in_reach_gets_the_sigil_under_the_strike_and_not_again_for_a_while(marks_all):
    play = game(foe(10, 5008.0, 5000.0, CHAMPION), foe(11, 5006.0, 5003.0))
    play.toughness[10] = 4
    hunt = hunter(play)
    attack_mode(play, hunt, until=8.0)

    assert 't' not in play.pressed()
    assert len(play.sigils) == 1
    assert math.dist(play.sigils[0], (5008.0, 5000.0)) < 1.5
    assert [unit for unit, _ in play.strikes] == [10, 10, 10, 10, 11]  # the elite before the plain monster
    assert play.said[1:5] == [
        'Echoing Strike (key 7) at the elite 19 (10), life unknown',  # the strike first
        'Death Mark',
        'Death Mark on the elite 19 (10), life unknown',
        'Sigil: Lethargy',
    ]

    play = game(foe(20, 5008.0, 5000.0, CHAMPION))  # another elite: the first one's sigil does not count
    play.toughness[20] = 1000
    attack_mode(play, hunt, until=1.5 * SIGIL_SECONDS)
    assert len(play.sigils) == 2  # at once, and again SIGIL_SECONDS later, within the one fight


def test_death_mark_goes_on_the_strongest_in_reach_now_and_then(marks_all):
    play = game(foe(10, 5008.0, 5000.0, life=50, max_life=50), foe(11, 5003.0, 5006.0, life=400, max_life=400))
    play.toughness[10], play.toughness[11] = 20, 60
    attack_mode(play, hunter(play), until=60.0)

    # the most life, and again when its mark runs out (mark.py MARK_SECONDS; before 2026-10-14 a clock of 8 s)
    assert play.marks[:2] == [11, 11]
    assert 'Death Mark on the monster 19 (11), 400/400' in play.said
    assert play.world.monsters == ()


def test_a_fight_takes_the_monsters_in_reach_one_after_another_and_leaves_the_far_one():
    play = game(foe(10, 5008.0, 5000.0), foe(11, 5003.0, 5006.0, CHAMPION), foe(12, 5040.0, 5000.0))
    play.toughness[10], play.toughness[11] = 2, 4
    attack_mode(play, hunter(play), until=10.0)

    assert [unit for unit, _ in play.strikes] == [11, 11, 11, 11, 10, 10]  # the elite first, then the rest
    assert [m.unit_id for m in play.world.monsters] == [12]  # out of reach: the seek step's business
    assert any(text.startswith('Nothing left in reach: 2 down in ') for text in play.said)


def test_a_monster_behind_a_wall_is_not_struck():
    rows = ['.' * 25 + '#' + '.' * 14] * 40  # a wall one sub-tile thick at world x = 5005
    wall = Walkable(996, 996, 8, 8, pack_cells(''.join('0' if c == '#' else '1' for row in rows for c in row)))
    play = game(foe(10, 5010.0, 5000.0))
    attack_mode(play, hunter(play, ground=(wall,)), until=3.0)
    assert play.strikes == []


def test_a_key_that_shows_no_cast_stops_the_fight_not_the_mode(caplog):
    play = game(foe(10, 5008.0, 5000.0))
    play.keys.on_event = lambda event: None  # the game ignores the key
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=3.0)
    assert any('the fight stopped (no cast seen after the key 7' in r.message for r in caplog.records)


# --- attack mode: living with the player ---


def test_attack_mode_fights_what_comes_into_reach_later_and_ignores_the_mouse_and_walks():
    play = game()
    hunt = hunter(play)

    def walk():
        play.keys.at = (play.keys.at[0] + 300, play.keys.at[1] + 100)
        play.world = replace(play.world, player=replace(me(play.world), x=5004.0, y=5001.0, mode=2))

    def stand():
        play.world = replace(play.world, player=replace(me(play.world), mode=5))

    attack_mode(
        play, hunt, until=30.0,
        events=[(5.0, walk), (6.0, stand), (12.0, appear(play, foe(11, 5010.0, 5004.0)))],
    )  # fmt: skip
    assert [unit for unit, _ in play.strikes] == [11]
    assert play.said[-2] == 'Nothing left in reach: 1 down in 1 casts'
    assert play.clock.now >= 30.0


def test_the_players_own_casts_and_teleports_never_end_attack_mode():
    # Twice on the host the mode ended "you attacked" seconds after the attack mode toggle, before any fight, while the
    # player only moved toward the monsters (21:17 on 2026-10-09).
    play = game()

    def cast():
        play.world = replace(play.world, player=replace(me(play.world), mode=10))

    def land():
        play.world = replace(play.world, player=replace(me(play.world), x=5030.0, y=5000.0, mode=5))

    def strike_by_hand():
        play.world = replace(play.world, player=replace(me(play.world), mode=10))

    def stand():
        play.world = replace(play.world, player=replace(me(play.world), mode=5))

    attack_mode(
        play, hunter(play), until=14.0,
        events=[
            (2.0, cast), (2.4, land), (4.0, strike_by_hand), (4.5, stand),
            (6.0, appear(play, foe(11, 5040.0, 5004.0))),
        ],
    )  # fmt: skip
    assert [unit for unit, _ in play.strikes] == [11]
    assert play.said[0] == 'Attack mode on'
    assert play.said[-2] == 'Nothing left in reach: 1 down in 1 casts'


def test_a_hand_working_the_mouse_does_not_stop_a_fight_in_attack_mode(caplog):
    # Four fights in a row stopped "the mouse is being moved" in the Chaos Sanctuary (host, 21:20 on
    # 2026-10-09): the re-aim of a hop (test_teleport.py) is not for a mode the player's hand works
    # the mouse through. Here the hand drags the pointer off after every move.
    play = game(foe(11, 5010.0, 5004.0))
    real_move = play.keys.move_pointer

    def move_pointer(x, y):
        return real_move(x + 120, y)

    play.keys.move_pointer = move_pointer
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=5.0)
    assert [unit for unit, _ in play.strikes] == [11]
    assert not [r.message for r in caplog.records if 'aiming again' in r.message or 'fight stopped' in r.message]


def test_a_key_the_player_holds_makes_attack_mode_wait_not_stop(caplog):
    play = game()

    def hold():
        play.keys.held = True

    def let_go():
        play.keys.held = False

    with caplog.at_level('INFO'):
        attack_mode(
            play, hunter(play), until=12.0,
            events=[(1.0, hold), (3.0, appear(play, foe(11, 5010.0, 5004.0))), (8.0, let_go)],
        )  # fmt: skip
    assert [unit for unit, _ in play.strikes] == [11]
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]
    assert play.said[-2] == 'Nothing left in reach: 1 down in 1 casts'


def test_a_key_the_player_taps_during_a_fight_leaves_the_strike_held(caplog):
    # Twenty taps of the player's own skill key in one Catacombs fight each let the strike go and
    # started the fight over (the runs of 18:01 and 18:05 on 2026-10-10).
    play = game(foe(11, 5010.0, 5004.0))
    play.toughness[11] = 1000
    taps = [(at, lambda held=held: setattr(play.keys, 'held', held)) for at, held in ((1.0, True), (1.1, False))]
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=3.0, events=taps)
    assert not [text for text in play.said if text.startswith('Yielded')]
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]
    assert sum(text.startswith('Echoing Strike') for text in play.said) == 1  # one hold through the tap


def test_a_step_waiting_for_the_fight_gets_its_turn_when_nothing_is_left_in_reach():
    # The pickup step during attack mode (runner): the mode goes on striking and pauses itself after the kill.
    play = game(foe(11, 5010.0, 5004.0))
    play.toughness[11] = 3
    hunt = hunter(play)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((0.05, hunt.after_fight.set))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    assert not run.cancelled.is_set()  # the mode's own pause, not the runner's cancel
    assert len(play.strikes) == 3  # the monster was killed first
    assert not hunt.after_fight.is_set()


def test_attack_mode_waits_through_town_panels_and_menus():
    play = game(area=109)  # Harrogath
    play.world = replace(play.world, open_panels=('inventory',))
    attack_mode(play, hunter(play), until=3.0)
    assert play.said == ['Attack mode on']


def test_leaving_the_game_ends_attack_mode_so_a_macro_request_in_the_lobby_runs_the_macro_at_once():
    # user, 2026-10-10: the mode idled on in the lobby (no player: wait) and the macro request there only turned it off.
    play = game()
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((2.0, lambda: setattr(play, 'world', replace(play.world, in_game=False, player=None))))
    with pytest.raises(Abort, match='attack mode off: the game was left'):
        hunter(play).attack_mode(run, keys)


def test_the_line_goes_through_two_monsters_rather_than_at_the_nearest():
    # The policy's line (combat/policy.py): two monsters on one line are worth more than the nearer lone one.
    play = game(foe(10, 5006.0, 5000.0), foe(11, 5000.0, 5009.0), foe(12, 5000.0, 5016.0))
    play.toughness[11] = 100
    attack_mode(play, hunter(play), until=1.0)
    assert play.strikes[0][0] == 11
    assert abs(play.strikes[0][1][0] - 5000.0) < 1.5  # aimed along the line through 11 and 12


def test_a_build_without_an_attack_stops_attack_mode_at_its_first_look_at_the_character():
    # Not before the look: the runner names the build by it (runner.py `choosing`).
    play = game(foe(10, 5008.0, 5000.0))
    play.build = GENERIC
    hunt = Hunter(lambda: Level(101, ROOMS, ()), None, None, build=GENERIC)
    with pytest.raises(Abort, match=r'attack mode off: the build \(generic\) has no attack of its own'):
        hunt.attack_mode(play.run(), keys)
    assert play.said == ['Attack mode on']
    assert not play.strikes
    assert not play.keys.events
    assert play.pressed() == []
    assert hunt.reach == 0.0  # and nothing is in reach of a build that does not fight


def test_the_strike_is_the_skill_of_the_builds_attack_on_whatever_input_has_it():
    play = game(foe(10, 5008.0, 5000.0))
    run, seen = play.run(), play.world
    assert strike_input(run, seen, keys, ECHOING_STRIKE) == (('7',), 'key 7')
    on_right = replace(seen, player=replace(me(seen), right_skill=TELEPORT))
    assert strike_input(run, on_right, keys, TELEPORT) == (('Button3',), 'right click')
    on_left = replace(seen, slots=(None,), player=replace(me(seen), left_skill=DEATH_MARK))
    assert strike_input(run, on_left, keys, DEATH_MARK) == (('Shift_L', 'Button1'), 'Shift+click')
    with pytest.raises(Abort, match='Echoing Strike is on no skill key and on neither mouse button'):
        strike_input(run, on_left, keys, ECHOING_STRIKE)
    with pytest.raises(Abort, match=r'Teleport is on no skill key and on neither mouse button \(left Death Mark'):
        strike_input(run, on_left, keys, TELEPORT)


def test_a_policy_set_in_place_of_the_attack_gives_the_aim_alone():
    hunt = hunter(game(foe(10, 5008.0, 5000.0)))
    assert hunt.policy is hunt.build.attack is hunt.attack

    def nothing(seen):
        return None

    hunt.policy = nothing
    assert hunt.policy is nothing
    assert hunt.attack is hunt.build.attack  # the reach, what is seen and what a cast deals stay the attack's
    assert Hunter(policy=nothing, build=BUILD).policy is nothing


def test_a_monster_in_reach_is_struck_by_the_old_rule_when_the_policy_finds_no_line():
    play = game(foe(10, 5008.0, 5000.0), foe(11, 5000.0, 5006.0, CHAMPION))
    hunt = hunter(play)
    hunt.policy = lambda seen: None
    attack_mode(play, hunt, until=3.0)
    assert [unit for unit, _ in play.strikes] == [11, 10]  # the elite first, then the nearest
    # AIM_BEYOND past it, or on its body where the pointer went for the mark under the held strike
    assert math.dist(play.strikes[1][1], (5009.0, 5000.0)) < 3.0


def test_a_fight_yields_the_moment_the_player_moves_and_goes_on_when_they_stand(caplog):
    # combat/plan.md stage 5, takeover with yield: the mode must never get in the way of moving.
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000

    def run_off():
        play.world = replace(play.world, player=replace(me(play.world), mode=2))

    def stand():
        play.world = replace(play.world, player=replace(me(play.world), mode=5))

    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=6.0, events=[(2.0, run_off), (4.0, stand)])
    yielded = [text for text in play.said if text.startswith('Yielded')]
    assert len(yielded) == 1
    assert yielded[0].startswith('Yielded (the character is on the move): 0 down in ')
    assert play.said.count('Echoing Strike (key 7) at the monster 19 (10), life unknown') == 2  # before and after
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]
    assert play.keys.down == []  # nothing is left held


def test_the_left_mouse_button_down_is_the_players_move():
    play = game(foe(10, 5008.0, 5000.0))
    play.keys.pointer_state = lambda: (*play.keys.at, 1 << 8)
    attack_mode(play, hunter(play), until=2.0)
    assert play.strikes == []


# --- the seek step ---


def test_seeking_hops_onto_a_firing_ring_around_the_nearest_elite_the_game_holds():
    play = game(foe(10, 5030.0, 5000.0, CHAMPION), foe(11, 5020.0, 5000.0))
    hunter(play).seek(play.run(), keys)

    assert play.pressed() == [KEYS[BLADE_WARP]]  # a clear line: no charge, no swap
    assert play.strikes == []
    landed = (me(play.world).x, me(play.world).y)
    assert STRIKE_REACH - 4 <= math.dist(landed, (5030.0, 5000.0)) <= STRIKE_REACH  # on a firing ring
    assert play.said[0].startswith('Blade Warp toward the elite 19 (10)')


def test_seeking_ignores_plain_monsters_and_takes_a_remembered_elite():
    play = game(foe(11, 5020.0, 5000.0))
    remembered = [(77, 5030.0, 5002.0, True), (78, 5010.0, 5000.0, False)]
    hunter(play, remembered=remembered).seek(play.run(), keys)

    assert play.pressed() == [KEYS[BLADE_WARP]]  # a clear line: no charge, no swap
    assert play.said[0].startswith('Blade Warp toward the remembered elite')


def test_a_firing_spot_a_few_units_away_is_walked_to_not_teleported_to():
    play = game(foe(10, 5025.0, 5000.0, CHAMPION))  # 25 away: the nearest firing ring is 8 from the character
    hunter(play).seek(play.run(), keys)

    assert play.pressed() == []
    assert len(play.walks) == 1
    assert math.dist(play.walks[0], (5008.0, 5000.0)) < 2.0
    assert play.said[0].startswith('Walking 8 toward the elite 19 (10)')


def test_a_walk_click_the_game_swallows_is_made_again():
    # Host, 19:40 on 2026-10-10: "Walking 7 toward the elite", "the character did not move".
    play = game(foe(10, 5025.0, 5000.0, CHAMPION))  # the firing ring 8 from the character: a walk
    real, heard = play.keys.on_event, []

    def deaf_once(event):
        if event[0] == 'click' and not heard:
            heard.append(event)
            return
        real(event)

    play.keys.on_event = deaf_once
    hunter(play).seek(play.run(), keys)
    assert play.pressed() == []
    assert len(play.walks) == 1  # the second click walked the character


def test_a_short_way_over_a_wall_is_still_a_teleport():
    rows = ['.' * 25 + '#' + '.' * 14] * 40  # a wall at world x = 5005
    wall = Walkable(996, 996, 8, 8, pack_cells(''.join('0' if c == '#' else '1' for row in rows for c in row)))
    play = game(foe(10, 5021.0, 5000.0, CHAMPION))
    hunter(play, ground=(wall,)).seek(play.run(), keys)

    assert play.walks == []
    assert play.pressed() == ['t']


def test_an_elite_already_in_reach_is_only_named():
    play = game(foe(10, 5008.0, 5000.0, CHAMPION))
    hunter(play).seek(play.run(), keys)  # no step: the attack mode the seek step leaves on takes it (runner.py)
    assert play.said == ['the elite 19 (10) is in reach: attack mode takes it']
    assert play.keys.events == []


def test_a_firing_spot_under_the_characters_feet_is_no_walk(monkeypatch):
    # The run of 18:38 on 2026-10-10: "Walking 1 toward the elite", a click under the feet, "the
    # character did not move". The shot read blocked from the exact place, clear from 0.6 units beside it.

    play = game(foe(10, 5014.0, 5000.0, CHAMPION))
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)
    patch_hunt(monkeypatch, 'firing_spots', lambda *args: [(5000.5, 5000.3)])
    hunter(play).seek(play.run(), keys)
    assert play.said == ['the elite 19 (10) is in reach: attack mode takes it']
    assert play.keys.events == []


def test_without_an_elite_the_hop_goes_to_the_nearest_unexplored_room():
    play = game(foe(11, 5020.0, 5000.0))  # a plain monster is not what the seek step seeks
    explored = {(HERE.x, HERE.y, 8, 8), (EAST[0].x, EAST[0].y, 8, 8)}
    hunter(play, explored=explored).seek(play.run(), keys)

    assert play.pressed() == [KEYS[BLADE_WARP]]  # a clear line: no charge, no swap
    assert me(play.world).x > 5015.0  # toward EAST[1], the nearest unexplored room
    assert play.said[0].startswith('Blade Warp toward an unexplored room')


def test_exploring_picks_the_room_nearest_by_the_way_not_the_nearest_lava_island():
    # Six small rooms lie south across eight tiles of void, nearer as the crow flies than the corridor's
    # next room, and no teleport chain reaches them (the Chaos Sanctuary entrance, host 20:49 on 2026-10-09).
    islands = tuple(Room(50 + i, 990 + 4 * i, 1012, 2, 2) for i in range(6))
    rooms = (HERE, *EAST, *islands)
    play = game()
    explored = {(HERE.x, HERE.y, 8, 8), (EAST[0].x, EAST[0].y, 8, 8)}
    Hunter(lambda: Level(101, rooms), None, lambda area: explored, build=BUILD).seek(play.run(), keys)

    assert play.pressed() == [KEYS[BLADE_WARP]]  # a clear line: no charge, no swap
    assert me(play.world).x > 5015.0  # east along the corridor, toward EAST[1]
    assert abs(me(play.world).y - 5000.0) < 10.0


def test_an_explored_level_with_no_elite_stops():
    play = game()
    explored = {(room.x, room.y, 8, 8) for room in ROOMS}
    with pytest.raises(Abort, match='the level is explored'):
        hunter(play, explored=explored).seek(play.run(), keys)
    assert play.keys.events == []


@pytest.mark.parametrize(('area', 'message'), [(109, 'in town'), (110, 'no level map for this level')])
def test_town_and_a_missing_level_map_stop_the_step(area, message):
    play = game(foe(10, 5008.0, 5000.0), area=area)
    hunt = Hunter(lambda: Level(101, ROOMS), None, None, build=BUILD)
    with pytest.raises(Abort, match=message):
        hunt.seek(play.run(), keys)


def test_hostiles_leave_out_allies_owned_units_townsfolk_and_the_unplaced():
    foes = (
        foe(1, 5001.0, 5001.0),
        foe(2, 5001.0, 5001.0, ally=True),
        Monster(3, 19, 1, 5001.0, 5001.0, 1),  # owned: the mercenary
        foe(4, 5001.0, 5001.0, txt_id=150),  # Kashya
        foe(5, 0.0, 0.0),
        foe(6, 5001.0, 5001.0, MINION),
        foe(7, 5001.0, 5001.0, txt_id=352),  # a Hydra the Council cast: it never dies
    )
    assert [m.unit_id for m in hostiles(world(monsters=foes))] == [1, 6]


def test_a_siege_door_or_wall_is_no_hostile_and_the_imps_hut_and_the_tower_are():
    # Frigid Highlands, 02:40 on 2026-10-11 (user: "too focused on killing doors ... we don't target
    # demon huts at all"): 432/433 barricade doors, 434 the prison door, 524/525 barricade walls;
    # 528 the Evil hut (it stood among the townsfolk by mistake), 435 the Barricade Tower.
    foes = tuple(
        foe(unit, 5001.0, 5001.0, txt_id=txt) for unit, txt in enumerate((432, 433, 434, 524, 525, 528, 435), 1)
    )
    assert [m.txt_id for m in hostiles(world(monsters=foes))] == [528, 435]


def test_a_water_watcher_under_the_water_is_no_hostile():
    # Great Marsh, 09:04 on 2026-10-19 (the player: "try to attack mobs that aren't visible and don't attack us at
    # all"): tentacle2 (259) and tentaclehead2 (262) struck 4 times each for nothing; a frog demon (247) is fought
    foes = tuple(foe(unit, 5001.0, 5001.0, txt_id=txt) for unit, txt in enumerate((258, 259, 263, 247), 1))
    assert [m.txt_id for m in hostiles(world(monsters=foes))] == [247]


def test_a_monster_behind_a_closed_door_is_not_struck_until_the_door_opens():
    from inventory_tracking.levels.doors import Door

    play = game(foe(10, 5010.0, 5000.0))
    play.world = replace(play.world, doors=(Door(50, 15, 0, 5005.0, 5000.0),))  # a closed wooden door between

    def opens():
        play.world = replace(play.world, doors=(Door(50, 15, 2, 5005.0, 5000.0),))

    attack_mode(play, hunter(play), until=6.0, events=[(3.0, opens)])
    assert play.strikes  # struck once the door stood open
    assert play.clock.now >= 3.0
    assert all(math.dist(point, (5011.0, 5000.0)) < 1.5 for _, point in play.strikes)


def test_a_line_whose_focal_point_is_off_the_screen_is_aimed_along_as_far_as_the_screen_goes(caplog):
    # Host, 16:57 on 2026-10-10: after the seek step five fights in a row stopped "is out of view", attack mode
    # ended and the character stood beside the monsters. The line is what matters: the pointer goes on it.
    play = game(foe(10, 5012.0, 5012.0))  # in reach (17 units), low on the screen
    hunt = hunter(play)
    hunt.policy = lambda seen: Choice((5016.0, 5016.0), 10, 1.0)  # the blades to meet past it, below the screen
    with caplog.at_level('INFO'):
        attack_mode(play, hunt, until=3.0)
    assert [unit for unit, _ in play.strikes] == [10]
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]
    aimed = play.strikes[0][1]
    assert abs((aimed[0] - 5000.0) - (aimed[1] - 5000.0)) < 1.5  # on the line through the monster
    assert math.dist(aimed, (5000.0, 5000.0)) < math.dist((5016.0, 5016.0), (5000.0, 5000.0))


def test_a_skill_still_on_the_button_after_a_hop_is_waited_out_not_a_stopped_fight(caplog):
    # Host, 2026-10-10: right after every seek hop the right button still held Teleport for a moment.
    play = game(foe(10, 5008.0, 5000.0), slots=(*HUNT_SLOTS[:13], None, *HUNT_SLOTS[14:]))
    play.world = replace(play.world, player=player(101, consume=True, right_skill=54))

    def back():
        play.world = replace(play.world, player=replace(me(play.world), right_skill=ECHOING_STRIKE))

    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=3.0, events=[(0.4, back)])
    assert [unit for unit, _ in play.strikes] == [10]
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]


def test_an_elite_off_the_screen_gets_no_sigil_and_the_fight_goes_on(caplog):
    # Host, 17:12 on 2026-10-10: "the fight stopped (the elite 7 is out of view)" four times in a row.
    play = game(foe(10, 5013.0, 5013.0, CHAMPION), foe(11, 5008.0, 5000.0))
    play.toughness[11] = 3
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=2.0)
    assert play.sigils == []  # its ground is below the screen
    assert play.strikes
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]


def test_an_elite_within_the_blades_reach_is_attack_modes_not_a_walk_toward_it():
    play = game(foe(10, 5021.0, 5000.0, CHAMPION))  # past the hunt's 20, within the blades' 22
    hunt = hunter(play)
    hunt.seek(play.run(), keys)
    assert play.said == ['the elite 19 (10) is in reach: attack mode takes it']
    assert play.keys.events == []
    attack_mode(play, hunt, until=3.0)  # and attack mode does take it
    assert [unit for unit, _ in play.strikes] == [10]


def tough_pack():
    """Enough monsters around (5008, 5000) for the main weapons: over TOUGH_POINTS of life in reach."""
    count = int(TOUGH_POINTS / points_of(19, 101)) + 1
    return [foe(100 + i, 5004.0 + i % 8, 4996.0 + i // 8) for i in range(count)]


def test_the_main_weapons_are_taken_for_a_fight_once_the_mode_has_run_a_second():
    # user, 2026-10-10: the main set has the skill levels and the damage; the other one is for teleporting.
    play = game()
    play.sets.reverse()  # the staff's set in hand, as after a teleport or seek step
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, *tough_pack()))])
    assert play.pressed()[0] == 'c'  # the swap before anything else
    assert play.pressed().count('c') == 1
    assert play.sets[0] == PREBUFF_SET
    assert 'Main weapons for the fight' in play.said
    assert play.strikes


def test_a_herald_in_reach_gets_the_main_weapons_whatever_the_life_counted():
    # Tower Cellar 5, 22:50 on 2026-10-11: a tier 2 Herald and eight minions counted under TOUGH_POINTS (its
    # 13 times the life is not in the tables' points), so the fight and the death were on the staff's set,
    # whose resistances are under the cap.
    play = game()
    play.sets.reverse()
    minion = replace(foe(100, 5006.0, 4998.0), flags=0x10, tier=2)
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, minion))])
    assert play.pressed()[0] == 'c'
    assert play.sets[0] == PREBUFF_SET
    assert 'Main weapons for the fight' in play.said


def test_a_pack_leader_in_reach_gets_the_main_weapons():
    # user, 2026-10-12: "we should swap to it against most of tough/hard-hitting enemies/bosses".
    play = game()
    play.sets.reverse()
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, foe(10, 5006.0, 5000.0, CHAMPION)))])
    assert play.pressed()[0] == 'c'
    assert play.sets[0] == PREBUFF_SET


def test_plain_monsters_that_hit_hard_together_get_the_main_weapons():
    # Two Gloams (txt 118): 4.75 on the threat score, over HARD_SCORE, at a few thousand points of life.
    play = game()
    play.sets.reverse()
    gloams = [replace(foe(10 + i, 5006.0 + 2 * i, 4998.0), txt_id=118) for i in range(2)]
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, *gloams))])
    assert play.pressed()[0] == 'c'


def test_one_plain_monster_in_reach_is_fought_with_what_is_held():
    play = game()
    play.sets.reverse()
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, foe(100, 5006.0, 4998.0)))])
    assert 'c' not in play.pressed()
    assert play.strikes


def test_a_fight_right_after_a_step_starts_with_what_is_held_and_stops_for_the_main_weapons_a_second_in(marks_all):
    # Host, 17:26 on 2026-10-10: a swap after every hop of a chain of seek steps, and the staff back for
    # the next one, left the character standing 63% of the frames it had a target.
    pack = tough_pack()
    play = game(*pack)
    for monster in pack:
        play.toughness[monster.unit_id] = 1000
    play.sets.reverse()
    attack_mode(play, hunter(play), until=4.0)
    keys_pressed = play.pressed()
    assert keys_pressed[:2] == ['7', 'd']  # the strike, let go for the mark under it: no swap first
    assert keys_pressed.count('c') == 1
    assert play.sets[0] == PREBUFF_SET
    stop = play.said.index(next(text for text in play.said if text.startswith('Stopping for the main weapons')))
    assert play.said.index('Main weapons for the fight') > stop
    assert sum(text.startswith('Echoing Strike (key 7)') for text in play.said) == 2  # before and after


def test_a_pack_no_longer_tough_when_the_swap_is_due_is_fought_on_without_a_stop():
    # The run of 18:21 on 2026-10-10: two fights stopped for the main weapons and no swap followed.
    pack = tough_pack()
    play = game(*pack)
    survivor = pack[0].unit_id
    play.toughness[survivor] = 1000
    play.sets.reverse()

    def thin_out():
        play.world = replace(play.world, monsters=tuple(m for m in play.world.monsters if m.unit_id == survivor))

    attack_mode(play, hunter(play), until=4.0, events=[(0.5, thin_out)])
    assert 'c' not in play.pressed()
    assert not [text for text in play.said if text.startswith('Stopping for the main weapons')]
    assert sum(text.startswith('Echoing Strike (key 7)') for text in play.said) == 1


def test_a_character_the_macros_do_not_know_keeps_what_it_holds():
    play = game(foe(10, 5008.0, 5000.0))
    play.sets.reverse()
    play.world = replace(play.world, player=replace(me(play.world), name='Somebody'))
    attack_mode(play, hunter(play), until=3.0)
    assert 'c' not in play.pressed()
    assert [unit for unit, _ in play.strikes] == [10]


def test_a_plain_pack_is_fought_with_what_is_held_and_a_big_one_gets_the_main_weapons():
    # user, 2026-10-10: the swap to the main weapons only for tougher packs. Since 2026-10-12 a pack leader
    # is one (the staff's set leaves the resistances under the cap); three plain monsters still are not.
    play = game()
    play.sets.reverse()
    few = [foe(10 + i, 5006.0 + i, 5000.0) for i in range(3)]
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, *few))])
    assert 'c' not in play.pressed()
    assert play.strikes

    play = game()
    play.sets.reverse()
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, appear(play, *tough_pack()))])
    assert play.pressed()[0] == 'c'


# --- the player's move before any strike (user, 2026-10-10 evening) ---


def left_click(play, at, seconds=0.08, pixel=(3400, 900)):
    """The player's own left click as an `attack_mode` event: the hand takes the pointer to `pixel` just
    before clock `at` and the button is down for `seconds`. The fake game takes none of it, as the real
    one takes no click while a cast runs."""

    def state():
        if at - 0.05 <= play.clock.now < at + seconds:
            play.keys.at = pixel  # the hand holds the pointer there
        down = at <= play.clock.now < at + seconds
        return (*play.keys.at, 1 << 8 if down else 0)

    play.keys.pointer_state = state
    play.keys.pointer = lambda: state()[:2]
    return (at, lambda: None)


def test_a_click_made_during_a_cast_stops_the_strike_and_is_made_again_when_the_character_is_free(caplog):
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=4.0, events=[left_click(play, 1.0)])
    assert len(play.walks) == 1  # the click the cast swallowed, made again once: the character walked
    assert math.dist(play.walks[0], (5000.0, 5000.0)) > 3  # where the player had clicked
    assert any('the click the cast swallowed made again at (3400, 900)' in r.message for r in caplog.records)
    assert not [r.message for r in caplog.records if 'fight stopped' in r.message]
    order = [text for text in play.said if text.startswith(('Echoing Strike', 'Yielded'))]
    assert order[0].startswith('Echoing Strike')
    assert order[1].startswith('Yielded (a move was asked for)')
    assert order[2].startswith('Echoing Strike')  # and on with the fight once the character stands again


@pytest.mark.parametrize('at', [1.0, 1.1, 1.2, 1.3, 1.37])
def test_no_strike_is_pressed_while_the_players_button_is_down(at):
    # review.md, finding 7: the idle hold was pressed again before the look at the player's click, so a
    # click could be answered with a new press. A game that casts once per press asks for one every 0.25 s.
    play = game(foe(10, 5008.0, 5000.0))
    play.repeats = False
    play.toughness[10] = 1000
    presses, press = [], play.keys.press

    def noting(key: int) -> bool:
        presses.append((play.clock.now, key))
        return press(key)

    play.keys.press = noting
    attack_mode(play, hunter(play), until=3.0, events=[left_click(play, at, seconds=0.3)])
    strike = play.keys.names['7']
    assert [when for when, code in presses if code == strike and when < at]  # it was striking before
    assert not [when for when, code in presses if code == strike and at + 0.02 <= when < at + 0.3]


def test_a_click_the_game_took_is_not_made_again():
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000

    def game_takes_it():  # the character starts running at once: the game had the click
        play.world = replace(play.world, player=replace(me(play.world), mode=2))

    def arrives():
        play.world = replace(play.world, player=replace(me(play.world), x=5003.0, y=5003.0, mode=5))

    attack_mode(play, hunter(play), until=4.0, events=[left_click(play, 1.0), (1.05, game_takes_it), (1.6, arrives)])
    assert play.walks == []  # no click of the macro's own
    assert play.said.count('Echoing Strike (key 7) at the monster 19 (10), life unknown') == 2  # before and after


def test_a_move_that_shows_nothing_is_given_two_clicks_and_dropped(caplog):
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000
    real = play.keys.on_event

    def deaf_to_clicks(event):
        if event[0] != 'click':
            real(event)

    play.keys.on_event = deaf_to_clicks
    with caplog.at_level('INFO'):
        attack_mode(play, hunter(play), until=5.0, events=[left_click(play, 1.0)])
    assert sum('made again' in r.message for r in caplog.records) == 2
    assert any('showed nothing after 2 clicks' in r.message for r in caplog.records)
    assert play.said.count('Echoing Strike (key 7) at the monster 19 (10), life unknown') == 2  # and on with the fight


def test_a_click_made_while_the_mode_is_busy_with_a_mark_is_still_seen(marks_all):
    # Host, 17:46 on 2026-10-10: a click made during Death Mark and a swap went unseen; the player clicked again.
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000
    hunt = hunter(play)
    looks = []
    sense = hunt.sense

    def counted(run):
        looks.append(play.clock.now)
        return sense(run)

    hunt.sense = counted
    attack_mode(play, hunt, until=3.0, events=[left_click(play, 0.12, seconds=0.06)])  # inside the mark's pauses
    assert len(play.marks) == 1  # the mark was being cast (the hand took the pointer off the monster)
    assert len(play.walks) == 1  # the move was seen, waited for, and made for the player
    assert max(b - a for a, b in pairwise(looks)) < 0.05  # never long without a look


def test_a_click_made_while_the_character_stood_free_is_the_games_and_is_not_made_again(caplog):
    # Host, 17:55 on 2026-10-10: four clicks beside the loot, each made twice more by the macro.
    play = game()
    with caplog.at_level('INFO'):
        attack_mode(
            play, hunter(play), until=4.0,
            events=[left_click(play, 1.0), (2.0, appear(play, foe(10, 5008.0, 5000.0)))],
        )  # fmt: skip
    assert play.walks == []
    assert not [r.message for r in caplog.records if 'made again' in r.message]
    assert [unit for unit, _ in play.strikes] == [10]  # and the strikes go on when something comes


# --- Engorge for the demons ---


def engorging(play, hunt, corpses, until=6.0, hovered=None):
    run = play.run()
    run.corpses = lambda: tuple(corpses)
    if hovered is not None:
        run.hovered = hovered
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((until, run.cancelled.set))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)


def test_a_hurt_demon_gets_engorge_on_the_nearest_corpse_under_the_held_strike():
    # user, 2026-10-10 night: Engorge (skills.txt 379, on a corpse) heals and buffs the demon.
    demon = Monster(50, 744, 1, 5003.0, 5003.0, 1, life=300, max_life=1000)
    play = game(foe(10, 5008.0, 5000.0), demon)
    play.toughness[10] = 1000
    engorging(play, hunter(play), [(90, 5030.0, 5000.0), (91, 5006.0, 5004.0), (92, 5200.0, 5000.0)])
    assert len(play.engorges) >= 1
    assert math.dist(play.engorges[0], (5006.0, 5004.0)) < 1.5  # the nearest one, not the one off the screen
    said = [text for text in play.said if text in ('Engorge',) or text.startswith('Echoing Strike')]
    assert said[0].startswith('Echoing Strike')  # the strike first, Engorge under it
    assert 'e' in play.pressed()


def test_no_engorge_without_a_demon_or_without_a_corpse():
    play = game(foe(10, 5008.0, 5000.0))
    play.toughness[10] = 1000
    engorging(play, hunter(play), [(91, 5006.0, 5004.0)])
    assert play.engorges == []

    demon = Monster(50, 744, 1, 5003.0, 5003.0, 1, life=300, max_life=1000)
    play = game(foe(10, 5008.0, 5000.0), demon)
    play.toughness[10] = 1000
    engorging(play, hunter(play), [])
    assert play.engorges == []


def test_a_healthy_demon_is_engorged_now_and_then_for_the_buff():
    from inventory_tracking.builds.warlock.buffs import ENGORGE_SECONDS

    demon = Monster(50, 744, 1, 5003.0, 5003.0, 1, life=1000, max_life=1000)
    play = game(foe(10, 5008.0, 5000.0), demon)
    play.toughness[10] = 10**6
    engorging(play, hunter(play), [(91, 5006.0, 5004.0)], until=ENGORGE_SECONDS + 5.0)
    assert len(play.engorges) == 2  # at the start of the fight, and ENGORGE_SECONDS later


def test_engorge_is_not_cast_with_a_live_monster_or_a_label_under_the_pointer():
    # Tower Cellar 5, 23:12 on 2026-10-10: the corpse lay 1.7 from the character, under the monster
    # being fought, and the record named that monster under the pointer.
    demon = Monster(50, 744, 1, 5003.0, 5003.0, 1, life=300, max_life=1000)
    for over in ((1, 10), (4, 777)):
        play = game(foe(10, 5008.0, 5000.0), demon)
        play.toughness[10] = 1000
        engorging(play, hunter(play), [(91, 5006.0, 5004.0)], hovered=lambda over=over: over)
        assert play.engorges == []
    play = game(foe(10, 5008.0, 5000.0), demon)
    play.toughness[10] = 1000
    engorging(play, hunter(play), [(91, 5006.0, 5004.0)], hovered=lambda: (1, 91))  # the corpse itself
    assert len(play.engorges) >= 1


# --- the step inside a fight: the pickup request asks for it (combat/stance.py decides where) ---


def row(*, tough=40):
    """One monster in reach and a pack of five past the blades: the pack is worth the walk."""
    pack = [foe(20 + k, 5030.0 + 2 * k, 5000.0) for k in range(5)]
    play = game(foe(11, 5012.0, 5000.0), *pack)
    play.toughness.update(dict.fromkeys((11, 20, 21, 22, 23, 24), tough))
    return play


def moves(play):
    """The places the character was taken to: walked, warped or teleported."""
    return [*play.walks, *play.warps]


def ask(hunt):
    """What the runner does for a pickup request during attack mode."""

    def asked():
        hunt.after_fight.set()
        hunt.step_asked.set()

    return asked


def test_a_step_asked_for_in_a_fight_walks_to_the_better_stand_and_the_fight_goes_on_there():
    play = row()
    hunt = hunter(play)
    dropped = []
    hunt.unwait = lambda: dropped.append(True)
    attack_mode(play, hunt, until=3.0, events=[(0.5, ask(hunt))])
    assert play.walks == []  # a step of over 8 units is a jump: a click in a pack meets a monster
    spot = play.warps[0]
    assert math.dist(spot, (5000.0, 5000.0)) <= CAMP_REACH + 1
    assert all(math.dist(spot, (5030.0 + 2 * k, 5000.0)) <= REACH for k in range(5))  # the whole pack in reach
    stepping = next(i for i, text in enumerate(play.said) if text.startswith('Stepping to a better place'))
    assert 'Blade Warp' in play.said[stepping:]
    assert any(text.startswith('Echoing Strike') for text in play.said[stepping:])  # struck again from there
    assert dropped == [True]  # nothing lay on the ground: the press picks up nothing after the fight
    assert not hunt.after_fight.is_set()


def test_a_step_asked_for_where_the_character_stands_well_moves_nothing():
    play = game(foe(11, 5012.0, 5000.0))
    play.toughness[11] = 40
    hunt = hunter(play)
    attack_mode(play, hunt, until=2.0, events=[(0.5, ask(hunt))])
    assert play.walks == []
    assert 'Standing well: no better place within 24' in play.said
    assert sum(text.startswith('Echoing Strike') for text in play.said) == 1  # the hold went on through it


def test_a_pickup_asked_for_in_a_fight_with_a_valuable_on_the_ground_stops_the_fight_for_it(caplog):
    # Halls of Vaught, 11:58:28 on 2026-10-11: the press with a Flawless Topaz 27 units away was three
    # Blade Warps to better places, 60 units from it, and the wait for the fight's end was lost on the way.
    caplog.set_level(logging.INFO)
    play = row(tough=1000)
    play.loot = replace(play.loot, drops=(Drop(50, 5003.0, 5003.0, 'Ist Rune', VALUABLE),))
    hunt = hunter(play)
    dropped = []
    hunt.unwait = lambda: dropped.append(True)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((0.5, ask(hunt)))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    assert not run.cancelled.is_set()  # the mode paused itself for the pickup step
    assert dropped == []  # the runner's pickup step stays wanted
    assert moves(play) == []  # no step to a better place first
    assert len(play.world.monsters) == 6  # the fight was not waited out
    assert 'Ist Rune first' in caplog.text


def test_a_pickup_asked_for_in_a_fight_with_gold_within_a_jump_stops_the_fight_for_it(caplog):
    # Halls of Vaught, 13:57:08 on 2026-10-11: 5221 gold 12 away waited for the fight's end through
    # three presses; the fourth and the sweep were two Blade Warps away from it, and it was left.
    caplog.set_level(logging.INFO)
    play = row(tough=1000)
    play.loot = replace(play.loot, drops=(Drop(60, 5010.0, 5006.0, '5221 gold', 'gold', (0, 0)),))
    hunt = hunter(play)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.arrivals.append((0.5, ask(hunt)))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    assert not run.cancelled.is_set()
    assert moves(play) == []  # no step to a better place first
    assert '5221 gold first' in caplog.text


def test_the_sweep_stops_for_something_to_pick_up_without_a_press(caplog, monkeypatch):
    # user, 2026-10-11: "when doing KP_1 auto-movement, we should also auto-pickup items/gold"

    patch_hunt(monkeypatch, 'GATHER_CLEAR', 0.0)  # the monsters here are not beside the drop (its own test)
    caplog.set_level(logging.INFO)
    play = row(tough=1000)
    hunt = hunter(play)
    asked = []
    hunt.pick = lambda: asked.append(True)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    hunt.sweep.start(run.clock())

    def drop():
        play.loot = replace(play.loot, drops=(Drop(60, 5010.0, 5006.0, '5221 gold', 'gold', (0, 0)),))

    play.arrivals.append((0.5, drop))
    with pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    assert not run.cancelled.is_set()  # the mode paused itself
    assert asked == [True]  # and asked the runner for the pickup step
    assert hunt.sweep.steps  # the sweep goes on after it
    assert hunt.sweep.until > run.clock()
    assert 'the sweep stops for 5221 gold' in caplog.text


def test_without_the_sweep_the_mode_does_not_stop_for_what_lies_on_the_ground():
    play = row(tough=1000)
    play.loot = replace(play.loot, drops=(Drop(60, 5010.0, 5006.0, '5221 gold', 'gold', (0, 0)),))
    hunt = hunter(play)
    asked = []
    hunt.pick = lambda: asked.append(True)
    attack_mode(play, hunt, until=2.0)
    assert asked == []


def test_the_sweep_stops_for_one_drop_twice_at_most(monkeypatch):

    patch_hunt(monkeypatch, 'GATHER_CLEAR', 0.0)  # the monsters here are not beside the drop (its own test)
    play = row(tough=1000)
    play.loot = replace(play.loot, drops=(Drop(60, 5010.0, 5006.0, '5221 gold', 'gold', (0, 0)),))
    hunt = hunter(play)
    asked = []
    hunt.pick = lambda: asked.append(True)
    for _ in range(3):
        run = play.run()
        run.actuator.drift, run.actuator.steady = 10**6, False
        hunt.sweep.start(run.clock())
        hunt.gather_looked = -math.inf
        if len(asked) < 2:
            with pytest.raises(Abort):
                hunt.gather(run, (5000.0, 5000.0))
        else:
            hunt.gather(run, (5000.0, 5000.0))
    assert asked == [True, True]


def test_a_step_left_over_from_the_last_run_of_the_mode_is_not_taken():
    # 11:58:20 on 2026-10-11: a step chosen on the level before, the mode stopped before taking it,
    # was a Teleport aimed 10,084 units away on arrival beside Nihlathak.
    play = game(foe(11, 5012.0, 5000.0))
    play.toughness[11] = 1000
    hunt = hunter(play)
    hunt.stepping = Step((9000.0, 9000.0))
    attack_mode(play, hunt, until=2.0)
    assert moves(play) == []


def test_a_boss_in_reach_has_the_line_laid_through_it_before_a_better_one():
    # user, 2026-10-11: Nihlathak first if he can be struck (he was, 5 s after the arrival beside him).
    play = game(foe(10, 5006.0, 5000.0, txt_id=526), foe(11, 5000.0, 5009.0), foe(12, 5000.0, 5016.0))
    play.toughness.update({10: 100, 11: 100, 12: 100})
    attack_mode(play, hunter(play), until=1.0)
    assert play.strikes[0][0] == 10


def test_a_boss_in_reach_gets_the_main_weapons_before_the_first_strike():
    play = game(foe(10, 5006.0, 5000.0, txt_id=526))
    play.toughness[10] = 1000
    play.sets.reverse()  # the staff's set in hand, as after the seek step that ended beside it
    attack_mode(play, hunter(play), until=3.0)
    assert play.pressed()[0] == 'c'
    assert play.sets[0] == PREBUFF_SET


def test_the_players_own_move_drops_the_step():
    play = row()
    hunt = hunter(play)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    hunt.stepping = Step((5008.5, 4991.5))
    play.keys.held = True  # a key of the player's is down
    hunt.sweep.steps = 2
    hunt.take_step(run, ASPECT)
    assert play.walks == []
    assert hunt.stepping is None
    assert hunt.sweep.steps == 0  # and no step of the mode's own after the player's


def test_the_pickup_request_with_hostiles_near_starts_the_sweep_and_moves_nothing_itself():
    # Black Marsh, 01:13 on 2026-10-11: the request walked, sought and explored by itself, press
    # after press, against the sweep's own walks.
    play = game(foe(11, 5027.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    assert moves(play) == []
    assert hunt.sweep.steps > 0
    attack_mode(play, hunt, until=4.0)
    assert len(moves(play)) >= 1
    assert play.world.monsters == ()


def test_the_pickup_request_with_no_hostile_near_is_the_seek_step(monkeypatch):
    play = game(foe(11, 5000.0 + SWEEP_UNITS + 15, 5000.0))
    hunt = hunter(play)
    sought = []
    monkeypatch.setattr(hunt, 'seek', lambda run, key_names, **how: sought.append(how))
    hunt.step(play.run(), keys)
    assert sought == [{'any_hostile': True}]  # a Terror Zone counts every kill: any known monster, or a room
    assert moves(play) == []
    assert hunt.sweep.steps == 0


def beside(play, unit, east):
    """A monster appearing `east` units east of where the character stands then."""

    def appear_there():
        at = me(play.world)
        play.world = replace(play.world, monsters=(*play.world.monsters, foe(unit, at.x + east, at.y)))

    return appear_there


def test_after_a_step_asked_for_the_mode_follows_on_to_what_is_near_and_out_of_reach():
    # user, 2026-10-11: one press should clear the group, not pick at it from where each step ended.
    play = game(foe(11, 5028.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    attack_mode(play, hunt, until=6.0, events=[(2.0, beside(play, 12, 27.0))])
    assert len(moves(play)) == 2  # toward the first, and one more toward the monster that came
    assert play.world.monsters == ()


def test_without_a_press_the_mode_never_steps():
    play = game(foe(11, 5028.0, 5000.0))
    attack_mode(play, hunter(play), until=4.0, events=[(2.0, beside(play, 12, 27.0))])
    assert moves(play) == []


def test_the_sweep_ends_some_seconds_after_its_last_step_and_after_its_steps(monkeypatch):

    play = game(foe(11, 5028.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    late = FOLLOW_SECONDS + 3.0
    attack_mode(play, hunt, until=late + 3.0, events=[(late, beside(play, 12, 27.0))])
    assert [m.unit_id for m in play.world.monsters] == [12]  # the first was gone to, the late one not
    patch_hunt(monkeypatch, 'FOLLOW_STEPS', 2)
    play = game(foe(11, 5028.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    comers = [(1.5 + 1.5 * k, beside(play, 12 + k, 27.0)) for k in range(5)]
    attack_mode(play, hunt, until=10.0, events=comers)
    assert len(moves(play)) == 2


def test_the_sweep_strides_toward_hostiles_further_than_any_place_reaches():
    # user, 2026-10-11, Black Marsh: 49 monsters in the open took 25 presses and a minute.
    play = game(foe(11, 5028.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    attack_mode(play, hunt, until=8.0, events=[(2.0, beside(play, 12, 55.0))])
    assert play.world.monsters == ()
    assert len(play.warps) >= 1  # the stride toward the far one is a Blade Warp
    assert me(play.world).x > 5030.0
    play = game(foe(11, 5028.0, 5000.0))
    hunt = hunter(play)
    hunt.step(play.run(), keys)
    attack_mode(play, hunt, until=8.0, events=[(2.0, beside(play, 12, SWEEP_UNITS + 10))])
    assert [m.unit_id for m in play.world.monsters] == [12]  # too far: the seek step's to go to


def test_a_step_that_fails_is_over_within_a_second_and_its_place_is_left_alone():
    # Black Marsh, 01:13:48 and 01:14:36 on 2026-10-11: a walk that did not come took 4 s to say so,
    # twice in a row for the same place, and nothing was cast meanwhile.
    play = game(foe(11, 5012.0, 5000.0))
    play.toughness[11] = 1000
    hunt = hunter(play)
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False
    play.keys.on_event = lambda event: None  # the game takes no click: nothing moves
    hunt.stepping = Step((5004.0, 4996.0))
    hunt.sweep.steps = 5
    before = play.clock.now
    hunt.take_step(run, ASPECT, keys)
    assert play.clock.now - before < 1.5
    assert [spot for spot, _ in hunt.sweep.shunned] == [(5004.0, 4996.0)]
    assert hunt.sweep.steps == 5  # one failure: the sweep goes on elsewhere
    hunt.stepping = Step((5004.0, 5006.0))
    hunt.take_step(run, ASPECT, keys)
    assert hunt.sweep.steps == 0  # two in a row: the sweep ends, the fight goes on where it stands
    assert any(text.startswith('No step') for text in play.said)


# --- Hex: Purge kept on, and Death Mark only where it pays (2026-10-11) ---


def purged(play, state):
    play.world = replace(play.world, player=replace(me(play.world), hex_purge=state))
    return play


def test_attack_mode_casts_hex_purge_when_the_characters_state_reads_without_it():
    # user, 2026-10-11: "if we don't have active hex-purge we should activate it: without it there is no damage".
    play = purged(game(), False)
    attack_mode(play, hunter(play), until=10.0)
    assert len(play.purges) == 1
    assert me(play.world).hex_purge is True
    assert 'Hex: Purge' in play.said


@pytest.mark.parametrize('state', [True, None], ids=['on', 'unreadable'])
def test_no_hex_purge_when_it_is_on_or_cannot_be_read(state):
    play = purged(game(foe(10, 5008.0, 5000.0)), state)
    attack_mode(play, hunter(play), until=5.0)
    assert play.purges == []


def test_hex_purge_runs_out_in_a_fight_and_is_cast_under_the_strike():
    play = purged(game(foe(10, 5008.0, 5000.0)), True)
    play.toughness[10] = 1000
    attack_mode(play, hunter(play), until=6.0, events=[(2.0, lambda: purged(play, False))])
    assert len(play.purges) == 1
    assert 2.0 <= play.purges[0] < 3.0
    assert len(play.strikes) > 6  # the strike went on after it


def test_a_hex_purge_the_state_never_shows_is_tried_twice_and_then_left_for_a_minute():
    play = purged(game(), False)
    play.purge_shows = False
    attack_mode(play, hunter(play), until=HEX_DISTRUST - 5)
    assert len(play.purges) == 2
    play = purged(game(), False)
    play.purge_shows = False
    attack_mode(play, hunter(play), until=HEX_DISTRUST + 15)
    assert len(play.purges) == 3


def warded(play, state):
    play.world = replace(play.world, player=replace(me(play.world), ward=state))
    return play


def test_attack_mode_casts_psychic_ward_when_the_characters_state_reads_without_it():
    # user, 2026-10-12: "we should keep psychic ward buff for the warlock: probably it will save us sometimes".
    play = warded(game(), False)
    attack_mode(play, hunter(play), until=10.0)
    assert len(play.wards) == 1
    assert me(play.world).ward is True


@pytest.mark.parametrize('state', [True, None], ids=['on', 'unreadable'])
def test_no_psychic_ward_when_it_is_on_or_cannot_be_read(state):
    play = warded(game(foe(10, 5008.0, 5000.0)), state)
    attack_mode(play, hunter(play), until=5.0)
    assert play.wards == []


def test_a_psychic_ward_broken_again_and_again_in_a_fight_is_cast_once_in_five_seconds():
    play = warded(game(foe(10, 5008.0, 5000.0)), True)
    play.toughness[10] = 1000
    breaks = [(at, lambda: warded(play, False)) for at in (2.0, 3.5, 5.0, 8.5)]
    attack_mode(play, hunter(play), until=10.0, events=breaks)
    # A key the fake game does not keep under a cast is pressed again at once (routines.press_through).
    casts = [at for before, at in zip([-math.inf, *play.wards], play.wards, strict=False) if at - before > 1.0]
    assert len(casts) == 2
    assert 2.0 <= casts[0] < 3.0
    assert casts[1] - casts[0] >= WARD_SECONDS
    assert len(play.strikes) > 10  # the strike went on between them


# --- Consume cast again when it has run out (2026-10-12) ---


def consumed(play, state):
    play.world = replace(play.world, player=replace(me(play.world), consume=state))
    return play


def test_attack_mode_casts_consume_again_when_it_has_run_out_and_nothing_is_near():
    # 02:40 on 2026-10-12: Consume ran out 300 s after its cast and the next five minutes were fought without it.
    play = consumed(game(), False)
    attack_mode(play, hunter(play), until=10.0)
    assert play.pressed().count('6') == 1
    assert me(play.world).consume is True
    assert len([m for m in play.world.monsters if m.txt_id == 744]) == 1
    assert 'Consume ran out: casting it again' in play.said


@pytest.mark.parametrize('state', [True, None], ids=['on', 'unreadable'])
def test_no_consume_while_it_is_on_or_cannot_be_read(state):
    play = consumed(game(), state)
    attack_mode(play, hunter(play), until=10.0)
    assert '6' not in play.pressed()
    assert 'q' not in play.pressed()


def test_no_consume_is_tried_while_the_game_is_in_the_background():
    play = consumed(game(), False)
    play.focused = False
    run = play.run()
    assert not Rotation(hunter(play).buffs).consume_due(run, play.world, [])
    play.focused = True
    assert Rotation(hunter(play).buffs).consume_due(run, play.world, [])


def test_no_consume_with_a_hostile_near_and_one_once_it_is_dead():
    play = consumed(game(foe(10, 5008.0, 5000.0)), False)
    play.toughness[10] = 30
    attack_mode(play, hunter(play), until=20.0)
    assert all(m.unit_id != 10 for m in play.world.monsters)
    assert play.pressed().count('6') == 1
    assert play.strikes
    assert play.pressed().index('6') > 0


def test_a_consume_that_cannot_be_cast_is_tried_again_only_after_a_while():
    play = consumed(game(), False)
    play.blocked = lambda x, y: True  # no ground takes a summon
    attack_mode(play, hunter(play), until=CONSUME_RETRY + 15)
    assert play.pressed().count('q') == 2 * len(SUMMON_SPOTS)  # two tries, each at every spot
    assert '6' not in play.pressed()


def demon(unit=60, x=4997.0, y=5000.0, txt=361):
    """A bound demon of the character's (a Pit Lord, as in the Chaos Sanctuary takes): an ally, no hostile."""
    return Monster(unit, txt, 1, x, y, 0xFFFFFFFF, 0, ally=True, life=128, max_life=128)


def test_death_mark_is_not_spent_on_a_monster_a_cast_or_two_kills():
    # 101 marks in the takes of 2026-10-10 cost about 0.9 s of casting each, on plain monsters too. Since 2026-10-14
    # (mark.py) with a demon out too: the plain one is trash, the champion's mark gains less than its cast.
    play = game(foe(10, 5008.0, 5000.0), foe(11, 5010.0, 5002.0, CHAMPION), demon())
    play.toughness.update({10: 1000, 11: 1000})
    attack_mode(play, hunter(play), until=10.0)
    assert play.marks == []


def test_a_death_mark_refused_on_an_elite_in_reach_is_said_once_with_its_worth_and_need(caplog):
    """The game of 00:25 on 2026-10-14 (rca/2026-10-14/run-0025-findings.md §4): one mark all game, on Diablo; the
    seal bosses and elites were refused by the worth rule, silently, and the player could not tell it was used.
    With no safety price fresh (the pursuit off here) the line gives the build's own price (mark.py `own_price`)."""
    elite = foe(11, 5010.0, 5002.0, CHAMPION, txt_id=312)  # a Venom Lord champion in the Chaos Sanctuary
    play = game(foe(10, 5008.0, 5000.0), elite, demon(), area=108)
    play.toughness.update({10: 1000, 11: 1000})
    with caplog.at_level(logging.INFO):
        attack_mode(play, hunter(play), until=10.0)
    assert play.marks == []
    refused = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: mark:')]
    assert len(refused) == 1  # once per target, and only for the elite
    assert 'no Death Mark on the elite 312 (11)' in refused[0]
    assert "by the build's rule (no safety price)" in refused[0]
    assert "against the cast's 0.37s" in refused[0]  # one volley of the strike (mark.py MARK_CAST_SECONDS)


def test_no_death_mark_with_no_demon_out_and_the_reason_is_said(caplog):
    # skills.txt 375 `requirespettype 1`: the skill needs a demon of the character's; the mercenary is none.
    merc = Monster(61, HIRELING_CLASS_ID, 1, 4997.0, 5000.0, 0xFFFFFFFF, 0, ally=True, life=128, max_life=128)
    play = game(foe(10, 5008.0, 5000.0, txt_id=243), merc, area=108)
    play.toughness[10] = 1000
    with caplog.at_level(logging.INFO):
        attack_mode(play, hunter(play), until=5.0)
    assert play.marks == []
    said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: mark:')]
    assert len(said) == 1
    assert "no demon of the character's is out (the skill needs one)" in said[0]


def test_death_mark_by_the_builds_own_rule_goes_on_diablo_once_while_it_lasts_and_says_why(caplog):
    # With no safety price (the pursuit off): Diablo's life is long enough that the demons sent onto him save more
    # of the fight than the cast costs (mark.py `gain`); not again while his mark lasts (MARK_SECONDS).
    play = game(foe(10, 5008.0, 5000.0, txt_id=243), demon(), area=108)
    play.toughness[10] = 1000
    with caplog.at_level(logging.INFO):
        attack_mode(play, hunter(play), until=8.0)
    assert play.marks == [10]
    cast = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: mark: Death Mark on')]
    assert len(cast) == 1
    assert 'the monster 243 (10)' in cast[0]
    assert "by the build's rule" in cast[0]


def test_the_sweep_goes_to_a_firing_spot_when_a_wall_stands_between(monkeypatch):
    # Tower Cellar 3, 2026-10-11 00:48:53: "sweeping with 14 hostiles near and none in reach: no better
    # place", the nearest 38 away behind a wall, and the sweep ended there.
    cells = ''.join('1' * 28 + '00' + '1' * 10 for _ in range(40))
    play = game(foe(11, 5016.0, 5000.0))
    play.staff = replace(STAFF, in_hand=False)  # no jump over the wall: a blade needs a clear line
    hunt = hunter(play, ground=(Walkable(996, 996, 8, 8, pack_cells(cells), pack_cells(cells)),))
    hunt.sweep.steps, hunt.sweep.until = 3, 100.0
    gone = []
    monkeypatch.setattr(
        hunt, 'go', lambda run, level, ground, player, rect, mob, name, doors, key_names: gone.append(mob)
    )
    attack_mode(play, hunt, until=0.5)
    assert gone[0] == (5016.0, 5000.0)
    assert play.walks == []
    assert hunt.sweep.steps < 3


def test_a_way_the_sweep_does_not_find_ends_it(monkeypatch):
    cells = ''.join('1' * 28 + '00' + '1' * 10 for _ in range(40))
    play = game(foe(11, 5016.0, 5000.0))
    play.staff = replace(STAFF, in_hand=False)  # no jump over the wall: a blade needs a clear line
    hunt = hunter(play, ground=(Walkable(996, 996, 8, 8, pack_cells(cells), pack_cells(cells)),))
    hunt.sweep.steps, hunt.sweep.until = 3, 100.0

    def no_way(*args):
        raise Abort('the character did not move')

    monkeypatch.setattr(hunt, 'go', no_way)
    attack_mode(play, hunt, until=2.0)
    assert hunt.sweep.steps == 0


# --- a stride is a jump: Blade Warp, else Teleport without a swap, else a walk (user, 2026-10-11) ---


def far_one(**changes):
    """A monster 50 units east in the open, nothing nearer: the sweep's to stride to."""
    play = game(foe(11, 5050.0, 5000.0), **changes)
    return play, hunter(play)


def swept(play, hunt, until=4.0):
    hunt.sweep.steps, hunt.sweep.until = 6, 100.0
    attack_mode(play, hunt, until=until)


def test_a_stride_is_a_blade_warp_onto_open_ground_short_of_the_monster():
    play, hunt = far_one()
    swept(play, hunt)
    assert play.world.monsters == ()
    first = play.warps[0]
    assert 16.0 < math.dist(first, (5000.0, 5000.0)) <= JUMP_REACH + 1  # the longest jump the window shows
    assert abs(first[1] - 5000.0) < 1.5  # straight toward it
    assert play.walks == [] or math.dist(play.walks[0], (5000.0, 5000.0)) > 20  # no walk before the warp
    assert play.pressed().count('c') == 0  # no weapon swap for it


def test_within_blade_warps_casting_delay_the_next_stride_goes_another_way():
    play, hunt = far_one()
    run = play.run()
    assert hunt.travel.jump_by(run, play.world) == BLADE_WARP
    hunt.travel.warped_at = play.clock.now
    assert hunt.travel.jump_by(run, play.world) == TELEPORT  # the staff is in hand: no swap
    play.staff = replace(STAFF, in_hand=False)
    assert hunt.travel.jump_by(run, play.world) is None  # walked
    play.clock.now += WARP_DELAY
    assert hunt.travel.jump_by(run, play.world) == BLADE_WARP
    play.staff = None  # Teleport as the character's own skill (Enigma)
    hunt.travel.warped_at = play.clock.now
    assert hunt.travel.jump_by(run, play.world) == TELEPORT


def test_a_blade_warp_that_moves_nothing_is_left_alone_and_the_stride_is_made_another_way():
    play, hunt = far_one()
    play.warp_lands = False
    swept(play, hunt, until=8.0)
    assert play.warps == []
    assert play.pressed().count('w') == 1  # tried once, then not for JUMP_DISTRUST
    assert play.world.monsters == ()  # by Teleport from the staff in hand, or on foot
    assert play.pressed().count('c') == 0


def test_without_blade_warp_the_stride_is_a_teleport_only_when_that_needs_no_swap():
    slots = tuple(None if skill == BLADE_WARP else skill for skill in HUNT_SLOTS)
    play, hunt = far_one(slots=slots)
    swept(play, hunt)
    assert play.pressed().count('t') >= 1
    assert play.pressed().count('c') == 0
    assert play.world.monsters == ()
    play, hunt = far_one(slots=slots)
    play.staff = replace(STAFF, in_hand=False)
    swept(play, hunt, until=8.0)
    assert play.pressed().count('t') == 0  # the staff is in the other set: walked
    assert len(play.walks) >= 2
    assert play.world.monsters == ()


def test_no_blade_warp_through_a_wall_and_none_onto_ground_without_footing():
    # A wall across the corridor between the character and the monster: the blade does not fly there.
    cells = ''.join('1' * 28 + '00' + '1' * 10 for _ in range(40))
    open_cells = '1' * 1600
    ground = (
        Walkable(996, 996, 8, 8, pack_cells(cells), pack_cells(cells)),
        *(Walkable(1004 + 8 * k, 996, 8, 8, pack_cells(open_cells), pack_cells(open_cells)) for k in range(3)),
    )
    play = game(foe(11, 5050.0, 5000.0))
    hunt = hunter(play, ground=ground)
    hunt.sweep.steps, hunt.sweep.until = 6, 100.0
    gone = []
    hunt.go = lambda run, level, ground, player, rect, mob, name, doors, key_names: gone.append(mob)
    attack_mode(play, hunt, until=1.0)
    assert play.warps == []
    assert gone  # the firing spot's to find


# --- the seek step for a Terror Zone: every kill and every room, in some order (user, 2026-10-11) ---


def test_the_pickup_requests_seek_goes_to_a_remembered_monster_of_any_kind_and_the_seek_steps_only_to_an_elite():
    play = game()
    hunt = hunter(play, remembered=[(31, 5050.0, 5000.0, False)], explored=[(1028, 996, 8, 8)])
    gone: list[object] = []
    hunt.go = lambda run, level, ground, player, rect, mob, name, doors, key_names: gone.append((mob, name))
    hunt.explore = lambda run, level, player, rect, key_names, frontier=None: gone.append('explore')
    hunt.seek(play.run(), keys, any_hostile=True)
    hunt.seek(play.run(), keys)
    assert gone == [((5050.0, 5000.0), 'the remembered monster'), 'explore']


def test_a_remembered_monster_much_further_than_the_nearest_unexplored_room_waits():
    play = game()
    hunt = hunter(play, remembered=[(31, 5000.0 + 5 * 60, 5000.0, False)], explored=[])
    gone = []
    hunt.go = lambda run, level, ground, player, rect, mob, name, doors, key_names: gone.append('go')
    hunt.explore = lambda run, level, player, rect, key_names, frontier=None: gone.append('explore')
    hunt.seek(play.run(), keys, any_hostile=True)
    assert gone == ['explore']


def test_a_remembered_monster_that_is_not_where_it_was_seen_is_not_gone_to_again():
    play = game()
    hunt = hunter(play, remembered=[(31, 5012.0, 5000.0, True)], explored=[])
    assert hunt.quarry(101, (5000.0, 5000.0), []) is None  # the character stands there and it is not
    assert hunt.vanished == {31}
    assert hunt.quarry(101, (5200.0, 5000.0), []) is None  # nor from afar later


def test_exploring_keeps_its_tour_when_a_step_makes_the_other_way_a_little_shorter():
    # The character in the middle room of a row of five, the middle three explored: an end to see
    # either way. The way chosen is kept from two tiles to the other side of the middle, where a
    # hunter that had chosen nothing yet goes the other way.
    play = game()
    explored = [(1004, 996, 8, 8), (1012, 996, 8, 8), (1020, 996, 8, 8)]
    hunt = hunter(play, explored=explored)
    assert hunt.level is not None
    level = hunt.level()
    assert level is not None
    rect = (1920, 0, 2560, 1418)
    first = hunt.frontier(level, replace(me(play.world), x=1016.0 * 5, y=5000.0), rect)
    assert first is not None
    side = 1 if first[2][0] > 1016 else -1
    across = replace(me(play.world), x=(1016.0 - 2 * side) * 5, y=5000.0)
    kept = hunt.frontier(level, across, rect)
    fresh = hunter(play, explored=explored).frontier(level, across, rect)
    assert kept is not None
    assert fresh is not None
    assert kept[1] == first[1]
    assert fresh[1] != first[1]


def test_with_the_staffs_charges_gone_the_seek_step_goes_by_blade_warp_and_else_walks():
    # Frigid Highlands, 02:55 on 2026-10-11: ten presses stopped with "no charges left".
    explored = {(HERE.x, HERE.y, 8, 8), (EAST[0].x, EAST[0].y, 8, 8)}
    play = game()
    play.staff = replace(STAFF, charges=0)
    hunter(play, explored=explored).seek(play.run(), keys)
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert me(play.world).x >= 5008.0
    assert any(said.startswith('Blade Warp toward an unexplored room') for said in play.said)

    slots = tuple(None if skill == BLADE_WARP else skill for skill in HUNT_SLOTS)
    play = game(slots=slots)
    play.staff = replace(STAFF, charges=0)
    hunter(play, explored=explored).seek(play.run(), keys)
    assert play.pressed() == []
    assert me(play.world).x > 5000.0
    assert play.said[-1].startswith('Walking')


def test_low_on_charges_the_seek_step_spares_the_staff_and_still_hops_where_nothing_else_leads():
    # user, 2026-10-11: "leverage warp more when low on charges". A level cleared after Nihlathak took
    # the staff from 69 to 2 that day (15:10).
    explored = {(HERE.x, HERE.y, 8, 8), (EAST[0].x, EAST[0].y, 8, 8)}
    play = game()
    play.staff = replace(STAFF, charges=5)
    hunter(play, explored=explored).seek(play.run(), keys)
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert play.staff.charges == 5
    assert any('the Teleport staff has 5 charges left' in said for said in play.said)

    play = game()
    play.staff = replace(STAFF, charges=5)
    hunt = hunter(play, explored=explored)
    hunt.travel.stride = lambda *args, **kwargs: None  # a wall: no Blade Warp, no walk
    hunt.seek(play.run(), keys)
    assert KEYS[TELEPORT] in play.pressed()
    assert play.staff.charges == 4


def test_a_seek_step_waits_out_the_blade_warps_delay_over_a_clear_line_and_spends_no_charge():
    # The game of 15:27 on 2026-10-11: presses came 0.5 s apart, under the 0.8 s delay, and 8 seek
    # hops went by Teleport to 4 by Blade Warp before the staff ran low.
    explored = {(HERE.x, HERE.y, 8, 8), (EAST[0].x, EAST[0].y, 8, 8)}
    play = game()
    hunt = hunter(play, explored=explored)
    run = play.run()
    hunt.travel.warped_at = run.clock() - 0.3
    began = run.clock()
    hunt.seek(run, keys)
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert play.staff is not None
    assert play.staff.charges == STAFF.charges
    assert 0.5 <= run.clock() - began < 2.0


def test_a_walk_step_minds_only_a_monster_a_click_attacks_that_stands_where_it_is_aimed():
    # Frigid Highlands, 03:00 on 2026-10-11: walks refused with the pointer on the Defiler, and with
    # nothing alive near the aim (the game still named the unit hovered before).
    near, far = foe(11, 5013.0, 5000.0), foe(12, 5060.0, 5000.0)
    pet = foe(13, 5011.0, 5000.0, ally=True)
    for over, refused in (((1, 11), True), ((1, 12), False), ((1, 13), False), ((0, 0), False)):
        play = game(near, far, pet)
        run = play.run()
        run.hovered = lambda over=over: over
        if refused:
            with pytest.raises(Abort, match='is under the pointer there'):
                step_walk(run, (5010.0, 5000.0), me(play.world), ASPECT, attackable(play.world))
            assert play.walks == []
        else:
            step_walk(run, (5010.0, 5000.0), me(play.world), ASPECT, attackable(play.world))
            assert len(play.walks) == 1


def test_a_character_running_in_place_is_not_waited_for():
    # Durance of Hate 2, 03:09 on 2026-10-11: 22 s in the running mode on one spot, and the mode,
    # which yields to a character on the move, cast nothing.
    play = game(foe(11, 5010.0, 5000.0))
    play.world = replace(play.world, player=replace(me(play.world), mode=3))
    hunt, run = hunter(play), play.run()
    assert hunt.moving(run, play.world) == 'the character is on the move'
    play.clock.now += RUN_IN_PLACE / 2
    assert hunt.moving(run, play.world) == 'the character is on the move'
    play.clock.now += RUN_IN_PLACE
    assert hunt.moving(run, play.world) is None
    going = replace(play.world, player=replace(me(play.world), x=5004.0))
    assert hunt.moving(run, going) == 'the character is on the move'  # it got somewhere: a move again
    standing = replace(play.world, player=replace(me(play.world), mode=1))
    assert hunt.moving(run, standing) is None
    assert hunt.moving(run, play.world) == 'the character is on the move'  # and anew after a stop


# --- one travel: the way a step was chosen for is the way it is made (review of 2026-10-11) ---


def test_a_place_is_chosen_with_the_jump_that_reaches_it_and_gone_to_by_it():
    play = game(foe(11, 5032.0, 5000.0))
    hunt, run = hunter(play), play.run()
    place = hunt.better_stand(play.world, hostiles(play.world), Ground(()), ASPECT, run=run)
    assert place is not None
    assert place.skill == BLADE_WARP
    assert hunt.better_stand(play.world, hostiles(play.world), Ground(()), ASPECT) is not None  # on foot, without
    hunt.stepping = Step.to(place)
    hunt.take_step(run, ASPECT, keys, Ground(()))
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert math.dist((me(play.world).x, me(play.world).y), place.spot) < 2


def test_a_step_chosen_as_a_walk_is_walked_however_far():
    # `take_step` turned any walk of 8 units or more into a jump, whatever the place was chosen for.
    play = game()
    hunt, run = hunter(play), play.run()
    hunt.stepping = Step((5012.0, 5000.0))
    hunt.take_step(run, ASPECT, keys, Ground(()))
    assert play.pressed() == []
    assert len(play.walks) == 1


def test_a_jump_that_cannot_be_made_any_more_is_made_by_the_next_skill_or_walked():
    slots = tuple(None if skill == BLADE_WARP else skill for skill in HUNT_SLOTS)
    play = game(slots=slots)
    hunt, run = hunter(play), play.run()
    hunt.stepping = Step((5012.0, 5000.0), BLADE_WARP)
    hunt.take_step(run, ASPECT, keys, Ground(()))
    assert play.pressed() == [KEYS[TELEPORT]]  # the staff is in hand: no swap

    play = game(slots=slots)
    play.staff = replace(STAFF, in_hand=False)
    hunt, run = hunter(play), play.run()
    hunt.stepping = Step((5012.0, 5000.0), BLADE_WARP)
    hunt.take_step(run, ASPECT, keys, Ground(()))
    assert play.pressed() == []
    assert len(play.walks) == 1


def test_the_sweeps_one_look_strides_only_when_nothing_is_in_reach():
    # A monster past any place worth going to: with nothing in reach the look is a stride toward
    # it; in a fight (something else in reach) there is no place worth twice this one, and no stride.
    play = game(foe(11, 5055.0, 5000.0))
    hunt, run = hunter(play), play.run()
    foes = hostiles(play.world)
    stride = hunt.next_step(run, play.world, foes, Ground(()), ASPECT, fighting=False)
    assert stride is not None
    assert stride.camp is None
    assert stride.skill == BLADE_WARP
    assert hunt.next_step(run, play.world, foes, Ground(()), ASPECT, fighting=True) is None


def test_exploring_goes_to_stand_beside_a_room_no_teleport_lands_in():
    # The last room of the row has no footing at all: it is seen from the room before it.
    ground = tuple(Walkable(room.x, room.y, 8, 8, pack_cells('1' * 1600)) for room in ROOMS[:-1])
    ground += (Walkable(ROOMS[-1].x, ROOMS[-1].y, 8, 8, pack_cells('0' * 1600)),)
    play = game()
    hunt = hunter(play, ground=ground, explored=[(room.x, room.y, 8, 8) for room in ROOMS[:3]])
    assert hunt.level is not None
    level = hunt.level()
    assert level is not None
    found = hunt.frontier(level, me(play.world), (1920, 0, 2560, 1418))
    assert found is not None
    assert found[1] == ROOMS[3]


# --- what the strikes do nothing to is left alone (user, 2026-10-11: the birds of Far Oasis) ---


def test_a_monster_that_takes_no_damage_is_left_alone_and_the_rest_is_fought():
    bird = foe(10, 5008.0, 5000.0, life=128, max_life=128)
    other = foe(11, 4992.0, 5000.0, life=128, max_life=128)
    play = game(bird, other)
    play.toughness.update({10: 1000, 11: 6})
    play.unhurt.add(10)  # in the air: the blades pass through
    attack_mode(play, hunter(play), until=6.0)
    struck = [unit for unit, _ in play.strikes]
    assert struck.count(10) <= UNTOUCHED_CASTS + 1
    assert [m.unit_id for m in play.world.monsters] == [10]  # the other one died meanwhile
    assert 'the monster 19 (10) takes no damage: left alone' in play.said
    assert any(text.startswith('Nothing left in reach') for text in play.said)  # the fight ended with it alive


def test_a_boss_that_takes_no_damage_is_never_left_alone():
    # The player, 2026-10-14: Baal's random teleports made "takes no damage after 4 casts" leave him alone 20 s; 2 of 10
    # arena seeds did not kill him in 60 s (rca/2026-10-14/baal-sim.md). Ordinary elites keep the rule (above).
    baal = foe(10, 5008.0, 5000.0, txt_id=544, life=128, max_life=128)
    play = game(baal)
    play.toughness[10] = 1000
    play.unhurt.add(10)
    hunt = hunter(play)
    attack_mode(play, hunt, until=6.0)
    assert hunt.untouchable == {}
    assert not any('left alone' in text for text in play.said)
    assert any('takes no damage: getting nearer' in text for text in play.said)
    struck = [unit for unit, _ in play.strikes]
    assert struck.count(10) > 2 * UNTOUCHED_CASTS  # the strikes go on at him


def test_a_boss_the_strikes_did_nothing_to_is_in_reach_only_within_the_engage_ring_for_a_while():
    from inventory_tracking.levels.model import Ground

    here = (5000.0, 5000.0)
    baal = foe(10, 5020.0, 5000.0, txt_id=544, life=128, max_life=128)  # 20 away: in the blades' reach
    play = game(baal)
    hunt, ground = hunter(play), Ground(())
    assert hunt.boss(baal)
    assert not hunt.boss(foe(11, 5020.0, 5000.0, flags=0x0A))  # a champion is no boss
    assert hunt.nearing_only(play.world, [baal], ground, here, 0.0) is False
    hunt.nearing[10] = NEARING_SECONDS
    assert hunt.nearing_only(play.world, [baal], ground, here, 0.0) is True  # beyond the engage ring: get nearer
    near = replace(baal, x=5000.0 + hunt.attack.engage - 1)
    assert hunt.nearing_only(play.world, [near], ground, here, 0.0) is False  # within it: the fight
    other = foe(12, 5010.0, 5000.0, life=128, max_life=128)
    assert hunt.nearing_only(play.world, [baal, other], ground, here, 0.0) is False  # something else to strike here
    assert hunt.nearing_only(play.world, [baal], ground, here, NEARING_SECONDS + 1) is False  # the while is over
    assert hunt.nearing == {}


@pytest.mark.parametrize(('away', 'renewing'), [(QUIET_UNITS + 5, False), (QUIET_UNITS - 5, True)])
def test_a_level_run_asks_its_whole_upkeep_between_its_moves_only_in_the_quiet(monkeypatch, away, renewing):
    # 2026-10-14 (run-1932-findings.md issue 3): `pursue` came first at every look of a level run and the upkeep only
    # at its end: Consume was down 59 s and 121 s of two full clears, a dead Defiler stayed dead. In the quiet the
    # whole upkeep goes between the run's moves; with a hostile near, only a buff that would end in a boss's fight.
    from inventory_tracking.config import with_overrides
    from inventory_tracking.macros.pursuit import FULL, Pursuit

    play = game(foe(10, 5000.0 + away, 5000.0, life=128, max_life=128))
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=with_overrides(hunt.build.settings, pursuit=True))
    hunt.pursuit = Pursuit('pickup', -100.0, advance=False, leash=FULL)
    order: list[object] = []

    def spent():
        # Each stub takes game time, and the test stops after a few looks whatever the loop does (bounded)
        play.clock.now += 0.1
        if len(order) > 20:
            raise Abort('cancelled: the test has seen enough looks')

    def pursue(*_, **__):
        order.append('pursue')
        spent()
        return True

    monkeypatch.setattr(hunt, 'pursue', pursue)

    def upkeep(run, world, foes, key_names, *, renewing=False):
        order.append(('upkeep', renewing))
        spent()
        return False

    monkeypatch.setattr(hunt, 'upkeep', upkeep)
    attack_mode(play, hunt, until=0.3)
    assert order[:2] == [('upkeep', renewing), 'pursue']


def test_a_monster_left_alone_is_tried_again_later():
    play = game(foe(10, 5008.0, 5000.0, life=128, max_life=128))
    play.toughness[10] = 1000
    play.unhurt.add(10)
    attack_mode(
        play, hunter(play), until=UNTOUCHABLE_SECONDS + 8, events=[(UNTOUCHABLE_SECONDS - 1, play.unhurt.clear)]
    )
    assert play.world.monsters[0].life < 128  # the bird landed: struck again once the time was over
    assert sum('takes no damage' in text for text in play.said) == 1


def test_a_monster_whose_life_goes_down_is_never_left_alone_and_one_whose_life_cannot_be_read_neither():
    play = game(foe(10, 5008.0, 5000.0, life=128, max_life=128), foe(11, 4992.0, 5000.0))
    play.toughness.update({10: 1000, 11: 1000})
    hunt = hunter(play)
    attack_mode(play, hunt, until=8.0)
    assert not any('takes no damage' in text for text in play.said)
    assert hunt.untouchable == {}


def test_the_sweep_and_the_seek_do_not_go_to_what_is_left_alone():
    play = game(foe(10, 5040.0, 5000.0, life=128, max_life=128))
    hunt = hunter(play)
    hunt.untouchable[10] = 100.0
    hunt.sweep.steps, hunt.sweep.until = 5, 100.0
    attack_mode(play, hunt, until=3.0)
    assert moves(play) == []
    assert hunt.quarry(101, (5000.0, 5000.0), hunt.foes(play.world, play.clock.now), any_hostile=True) is None


def test_a_bird_in_the_air_is_no_hostile_and_one_on_the_ground_is():
    # Far Oasis, take 20261010T224210Z-43: 33 Undead Scavengers, 73 hits; of the hits 55 came with the
    # bird walking or attacking (modes 2, 3, 4, 9: 1,797 frames) and 12 in modes 1 and 8 (8,807 frames).
    flying, gliding, walking = (
        replace(foe(n, 5008.0, 5000.0 + n, txt_id=111), mode=mode) for n, mode in ((1, 8), (2, 1), (3, 2))
    )
    other = replace(foe(4, 5010.0, 5000.0), mode=1)  # any other monster standing: a hostile
    assert [m.unit_id for m in hostiles(world(monsters=(flying, gliding, walking, other), slots=HUNT_SLOTS))] == [3, 4]


def open_step(play, hunt):
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros.teleport import step_toward

    run = play.run()
    target = Target(101, ROOMS, (1012.5, 1000.5), 'the mark', 'poi', False, ())
    step_toward(run, target, keys, None, lambda t, player, spot: hunt.warp_hop(run, t, player, spot, keys))


def test_with_few_charges_left_the_teleport_step_hops_by_blade_warp_over_open_ground():
    # user, 2026-10-11: "prefer tp for longer distances, until around 15 charges, then blade warp in priority".
    play = game()  # the staff of these tests holds 10 charges
    open_step(play, hunter(play))
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert me(play.world).x >= 5000.0 + 15.0
    assert play.staff is not None
    assert play.staff.charges == STAFF.charges
    assert any(said.startswith('Blade Warp toward the mark') for said in play.said)


def test_with_charges_to_spare_the_teleport_step_is_a_teleport():
    # user, 2026-10-11 evening: "KP_4 when forcing blade warp is way too slow".
    from inventory_tracking.macros.travel import WARP_CHARGES

    for charges, key in ((WARP_CHARGES, KEYS[TELEPORT]), (WARP_CHARGES - 1, KEYS[BLADE_WARP])):
        play = game()
        play.staff = replace(STAFF, charges=charges)
        open_step(play, hunter(play))
        assert play.pressed() == [key]


def test_with_few_charges_left_the_teleport_step_waits_out_blade_warps_whole_delay():
    play = game()
    hunt = hunter(play)
    hunt.travel.warped_at = play.clock.now  # just warped: presses come faster than the delay
    began = play.clock.now
    open_step(play, hunt)
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert play.clock.now - began >= WARP_DELAY


def test_without_blade_warp_on_the_bar_the_teleport_step_is_a_teleport():
    slots = tuple(None if skill == BLADE_WARP else skill for skill in HUNT_SLOTS)
    play = game(slots=slots)
    open_step(play, hunter(play))
    assert play.pressed() == [KEYS[TELEPORT]]


def test_the_sweep_stays_by_a_valuable_it_cannot_take_and_says_so(caplog):
    # The Tower, 17:56:14 on 2026-10-11: a Grand Charm came down 20 away, the sweep jumped twice and
    # stood 31 from it without a word (user: "we shouldn't move away from valuable drops", "stay in
    # radius, clear around").
    caplog.set_level(logging.INFO)
    play, hunt = far_one()
    charm = Drop(60, 4990.0, 5000.0, 'Grand Charm', 'valuable', (1, 3))
    play.loot = replace(play.loot, drops=(charm,), room=('####', '####'))
    hunt.pick = lambda: None
    swept(play, hunt)
    assert math.dist((me(play.world).x, me(play.world).y), (charm.x, charm.y)) <= 25.0
    assert play.warps == []
    assert 'Staying by Grand Charm: the inventory has no room for it' in play.said
    assert 'the sweep stays by Grand Charm' in caplog.text


def test_the_sweep_does_not_stay_by_gear_it_has_no_room_for():
    # Drifter Cavern, 19:59:52 on 2026-10-12: "the sweep stays by Magic Kriss ...: no step", 13 hostiles 39
    # away and attack mode idle (user: "allow moving when the item isn't very valuable").
    play, hunt = far_one()
    kriss = Drop(60, 4990.0, 5000.0, 'Magic Kriss', 'valuable', (1, 3), prized=False)
    play.loot = replace(play.loot, drops=(kriss,), room=('####', '####'))
    hunt.pick = lambda: None
    swept(play, hunt)
    assert math.dist((me(play.world).x, me(play.world).y), (kriss.x, kriss.y)) > 25.0
    assert not any(line.startswith('Staying by') for line in play.said)


def test_by_hand_the_sweep_goes_on_from_a_low_rune_with_no_room():
    # macros/lootpolicy.py (rca/2026-10-18/arch-level-behaviour.md §2.1, Q1): by hand the sweep sweeps on as before the
    # player's ruling (not prized)
    play, hunt = far_one()
    rune = Drop(61, 4990.0, 5000.0, 'El Rune', 'valuable', (1, 1), prized=False, source='rune')
    play.loot = replace(play.loot, drops=(rune,), room=('####', '####'))
    hunt.pick = lambda: None
    swept(play, hunt)
    assert math.dist((me(play.world).x, me(play.world).y), (rune.x, rune.y)) > 25.0


def test_in_the_loop_the_sweep_stays_by_a_chipped_gem_with_no_room():
    # The player, 2026-10-18 17:50, on Q1: "we should stop and clear inventory with our designated town routine": with
    # the KP_6 loop on the sweep holds a plain valuable it has no room for, as the loop's press does
    play, hunt = far_one()
    gem = Drop(63, 4990.0, 5000.0, 'Chipped Amethyst', 'valuable', (1, 1), prized=False, source='material')
    play.loot = replace(play.loot, drops=(gem,), room=('####', '####'))
    hunt.pick = lambda: None
    hunt.looping = lambda: True
    swept(play, hunt)
    assert math.dist((me(play.world).x, me(play.world).y), (gem.x, gem.y)) <= 25.0
    assert 'Staying by Chipped Amethyst: the inventory has no room for it' in play.said


def test_the_level_run_stands_by_a_low_rune_with_no_room():
    play, hunt = far_one()
    rune = Drop(62, 5010.0, 5000.0, 'El Rune', 'valuable', (1, 1), prized=False, source='rune')
    play.loot = replace(play.loot, drops=(rune,), room=('####', '####'))
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) == rune
    assert hunt.stay_by(play.run(), (5000.0, 5000.0)) == rune


def test_the_sweep_still_steps_within_the_radius_of_the_valuable_it_stays_by():
    play, hunt = far_one()
    charm = Drop(60, 5012.0, 5000.0, 'Grand Charm', 'valuable', (1, 3))
    play.loot = replace(play.loot, drops=(charm,), room=('####', '####'))
    hunt.pick = lambda: None
    swept(play, hunt)
    assert play.warps
    assert math.dist(play.warps[0], (charm.x, charm.y)) <= 25.0


def test_a_warp_that_moved_nobody_keeps_the_teleport_step_off_blade_warp_for_a_moment_only():
    # Black Marsh, 18:07:38 on 2026-10-11: the third hop's warp failed and the 43 after it were Teleports.
    play = game()
    hunt = hunter(play)
    hunt.travel.jump_failed[BLADE_WARP] = play.clock.now - 1.0
    open_step(play, hunt)
    assert play.pressed() == [KEYS[TELEPORT]]

    play = game()
    hunt = hunter(play)
    hunt.travel.jump_failed[BLADE_WARP] = play.clock.now - 5.0  # the sweep leaves it alone for 30 s
    open_step(play, hunt)
    assert play.pressed() == [KEYS[BLADE_WARP]]


def test_with_the_staff_empty_the_teleport_step_goes_along_the_way_by_blade_warp_or_stops():
    # Black Marsh, 18:59:44 on 2026-10-11: straight toward the tower nothing led, and the step stopped. The step with
    # the staff empty is the navigation class's (rca/2026-10-14/navigation-classes.md): the walked way to the mark,
    # a Blade Warp over a clear line, never toward a Teleport landing (the pocket of 22:54:28 on 2026-10-14).
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros.teleport import step_toward

    play = game()
    play.staff = replace(STAFF, charges=0)
    hunt = hunter(play)
    hunt.travel.warped_at = play.clock.now  # its delay is waited out: no Teleport can take the hop
    run = play.run()
    target = Target(101, ROOMS, (1012.5, 1000.5), 'the mark', 'poi', False, ())
    step_toward(
        run, target, keys, lambda t: hunt.foot_step(run, t, keys),
        lambda t, player, spot: hunt.warp_hop(run, t, player, spot, keys),
    )  # fmt: skip
    assert play.pressed() == [KEYS[BLADE_WARP]]
    assert 'Blade Warp toward the mark' in play.said


def seal(point=(1006.0, 1000.0), *, use=None, warp=False):
    from inventory_tracking.levels.model import WIRTS_BODY, Target

    return Target(101, ROOMS, point, 'the seal', 'target', warp, use=WIRTS_BODY if use is None else use)


def pack(count, x=5030.0, y=5000.0):
    return [foe(10 + n, x + 2.0 * (n % 3), y + 2.0 * (n // 3)) for n in range(count)]


def test_with_the_staff_empty_and_in_hand_the_step_takes_the_main_weapons_first():
    # Chaos Sanctuary, 23:16:26 on 2026-10-12: the last charge spent, and the staff stayed in hand for 17 s of
    # Blade Warps and a fight (user: "no reason to really do this": lower resistances and skill levels).
    from inventory_tracking.levels.model import Target
    from inventory_tracking.macros.teleport import step_toward

    play = game()
    play.sets.reverse()  # the staff's set in hand
    play.staff = replace(STAFF, charges=0, in_hand=True)
    hunt = hunter(play)
    hunt.travel.warped_at = play.clock.now
    run = play.run()
    target = Target(101, ROOMS, (1012.5, 1000.5), 'the mark', 'poi', False, ())
    step_toward(
        run, target, keys, lambda t: hunt.foot_step(run, t, keys),
        lambda t, player, spot: hunt.warp_hop(run, t, player, spot, keys),
    )  # fmt: skip
    assert play.pressed() == [KEYS[SWAP_WEAPONS], KEYS[BLADE_WARP]]
    assert play.staff.in_hand is False


def test_a_seek_step_with_the_staff_empty_and_in_hand_takes_the_main_weapons_first(monkeypatch):

    play = game(foe(10, 5040.0, 5000.0, CHAMPION))
    play.sets.reverse()
    play.staff = replace(STAFF, charges=0, in_hand=True)
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)
    hunter(play).seek(play.run(), keys)
    assert play.pressed()[0] == KEYS[SWAP_WEAPONS]
    assert play.staff.in_hand is False


def test_a_firing_spot_a_few_units_off_behind_a_corner_is_still_gone_to(monkeypatch):
    # Tower Cellar 5, 20:14:45 on 2026-10-11: the firing spot 4.1 from the character, no clear line
    # to it and no shot from where it stood. Seven seek presses said "the character is beside it"
    # and moved nothing, while attack mode went on with "none in reach".

    play = game(foe(10, 5012.0, 5000.0, CHAMPION))
    play.staff = replace(STAFF, charges=40)
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)
    patch_hunt(monkeypatch, 'clear_shot', lambda *args: False)
    patch_hunt(monkeypatch, 'firing_spots', lambda *args: [(5004.0, 5001.0)])
    start = (me(play.world).x, me(play.world).y)
    hunter(play).seek(play.run(), keys)
    assert play.pressed() == [KEYS[TELEPORT]]
    assert math.dist((me(play.world).x, me(play.world).y), start) >= 2.0
    assert not any(said.startswith('At ') for said in play.said)


def test_a_seek_step_that_moves_nothing_says_so(monkeypatch):

    play = game(foe(10, 5012.0, 5000.0, CHAMPION))
    play.staff = replace(STAFF, charges=40)
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)
    patch_hunt(monkeypatch, 'clear_shot', lambda *args: False)
    patch_hunt(monkeypatch, 'firing_spots', lambda *args: [(5004.0, 5001.0)])
    patch_hunt(monkeypatch, 'hop_toward', lambda *args: None)  # a hop that does nothing, whatever the cause
    hunter(play).seek(play.run(), keys)
    assert play.said[-1] == 'No move toward the elite 19 (10): 4 from its firing spot'


def boss_card(play, mark=(1010.5, 1000.5)):
    from inventory_tracking.levels.model import Target

    return Target(me(play.world).area, ROOMS, mark, 'Countess', 'target', False, ())


def test_the_teleport_step_goes_for_a_boss_its_mark_has_no_shot_at(monkeypatch):
    # Tower Cellar 5, 20:14:33 on 2026-10-11: the Countess 29 from her mark, behind a wall.

    countess = foe(10, 5025.0, 5030.0, 0x02, txt_id=45)  # a super unique, 32 from the mark at (5052.5, 5002.5)
    play = game(countess)
    play.staff = replace(STAFF, charges=40)
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)  # no shot from the mark, none from here
    patch_hunt(monkeypatch, 'firing_spots', lambda *args: [(5020.0, 5012.0)])
    hunt = hunter(play)
    assert hunt.boss_step(play.run(), boss_card(play), keys)
    assert play.pressed()  # a jump toward the firing spot at her
    assert math.dist((me(play.world).x, me(play.world).y), (5020.0, 5012.0)) < 12.0


def test_the_teleport_step_stays_when_the_boss_is_in_reach_and_the_mark_has_no_shot(monkeypatch):

    play = game(foe(10, 5015.0, 5000.0, 0x02, txt_id=45))
    marks = iter([False, True])  # no shot from the mark; one from where the character stands
    patch_hunt(monkeypatch, 'in_reach', lambda *args: next(marks))
    assert hunter(play).boss_step(play.run(), boss_card(play), keys)
    assert play.keys.events == []
    assert play.said[-1].endswith('is in reach: attack mode takes it')


def test_the_teleport_step_goes_to_a_mark_with_a_shot_at_its_boss_and_to_any_other_mark_as_ever(monkeypatch):
    from inventory_tracking.levels.model import Target

    play = game(foe(10, 5060.0, 5000.0, 0x02, txt_id=45))
    patch_hunt(monkeypatch, 'in_reach', lambda *args: True)  # the stand has the shot
    hunt = hunter(play)
    assert not hunt.boss_step(play.run(), boss_card(play), keys)
    patch_hunt(monkeypatch, 'in_reach', lambda *args: False)
    stairs = Target(me(play.world).area, ROOMS, (1010.5, 1000.5), 'Next level', 'stairs', True, ())
    assert not hunt.boss_step(play.run(), stairs, keys)
    assert not hunter(game()).boss_step(game().run(), boss_card(play), keys)  # no boss in sight
    far = game(foe(10, 5200.0, 5000.0, 0x02, txt_id=45))  # a super unique far from the mark is not its boss
    assert not hunter(far).boss_step(far.run(), boss_card(far), keys)


def test_the_sweep_does_not_stop_for_a_drop_with_a_hostile_beside_it_or_the_character(caplog):
    # Tower Cellar 5, 22:50:55 on 2026-10-11: the sweep stopped for a potion 15 away with four hostiles
    # within 10 units; the clicks took nothing for 5 s with a monster over the label, no strike was
    # made meanwhile, and the character died there.
    caplog.set_level(logging.INFO)
    play = row(tough=1000)
    play.loot = replace(play.loot, drops=(Drop(60, 5010.0, 5006.0, '5221 gold', 'gold', (0, 0)),))
    hunt = hunter(play)
    asked = []
    hunt.pick = lambda: asked.append(True)
    run = play.run()
    hunt.sweep.start(run.clock())
    here = (5000.0, 5000.0)
    foe = play.world.monsters[0]
    for at in ((5004.0, 5003.0), (5014.0, 5010.0)):  # beside the character, beside the drop
        hunt.gather_looked = -math.inf
        hunt.gather(run, here, [replace(foe, x=at[0], y=at[1])])
    assert asked == []
    assert 'the sweep leaves 5221 gold for later: 1 hostiles within 12' in caplog.text
    hunt.gather_looked = -math.inf
    with pytest.raises(Abort, match='cancelled'):
        hunt.gather(run, here, [replace(foe, x=5040.0, y=5040.0)])  # the place is clear: stopped for
    assert asked == [True]


def test_a_hostile_that_dies_with_its_summoner_is_no_target_while_anything_else_is_in_reach():
    """rca/2026-10-14/baal-sim.md fix 2: Baal's clone (combat/threats `bound`) is not aimed at while Baal or anything
    else is in reach; with nothing else in reach the mode alone strikes it, and the pursuit loop's look does not hold
    for it (`only_bound`)."""
    from inventory_tracking.macros.view import Viewport

    baal = foe(1, 5015.0, 5000.0, txt_id=544)
    clone = foe(2, 5006.0, 5000.0, txt_id=570, life=129882, max_life=129882)
    tentacle = foe(3, 5003.0, 5004.0, txt_id=564)
    play = game(baal, clone, tentacle)
    hunt = hunter(play)
    ground = Ground(())
    assert hunt.bound_lost([baal, clone, tentacle], [clone, tentacle]) == {2: (1,)}
    assert hunt.bound_lost([baal, clone], [clone]) == {}  # nothing else in reach: struck as it is
    assert hunt.bound_lost([clone, tentacle], [clone, tentacle]) == {}  # no summoner about: a monster as any
    assert hunt.choose(play.world, [baal, clone], [baal, clone], ground, Viewport(ASPECT)).unit == 1
    far = replace(baal, x=5040.0)  # out of reach
    assert hunt.choose(play.world, [far, clone, tentacle], [clone, tentacle], ground, Viewport(ASPECT)).unit == 3
    here = (5000.0, 5000.0)
    assert hunt.only_bound(play.world, [baal, clone], ground, here) is False  # Baal himself in reach
    assert hunt.only_bound(play.world, [far, clone], ground, here) is True
    assert hunt.only_bound(play.world, [far, clone, tentacle], ground, here) is False


def test_a_walk_the_look_chose_in_blade_warps_delay_is_not_made_once_the_warp_counts_ready():
    # 22:51:10 on 2026-10-16, Lower Kurast: the look priced the chest's move with 0.3 s of Blade Warp's delay left (more
    # than PLAN_AHEAD: no jump offered, a walk of 16); by the move, 0.2 s were left and `pause` saw the warp as ready,
    # so waited nothing, and the walk was made: 1.2 s on foot, the warp held back 0.9 s past its delay. Of the
    # session's 41 walks between two warps, 17 were chosen 0.80-0.90 s after the warp's key.
    from inventory_tracking.macros.goals import USE, Goal
    from inventory_tracking.macros.pursuit import Move
    from inventory_tracking.macros.travel import LOOPED, PLAN_AHEAD

    play = game()
    play.staff = replace(STAFF, charges=0)  # as that evening's: every hop a Blade Warp or a walk
    hunt = hunter(play)
    run = play.run()
    here = me(play.world)
    goal = Goal('Super chests', (here.x + 56.0, here.y), USE, 4.0, LOOPED)
    hunt.travel.warped_at = run.clock() - (WARP_DELAY - PLAN_AHEAD + 0.05)  # 0.2 s of the delay left
    walk = Step((here.x + 16.0, here.y))

    hunt.advance(run, play.world, Ground(()), Move(walk, goal), goal.place, keys)

    assert play.walks == []  # the next look prices the move again: the warp
    found = hunt.travel.toward(run, play.world, Ground(()), ASPECT, goal.place, LOOPED, ROOMS)
    assert isinstance(found, Step)
    assert found.skill == BLADE_WARP


def test_a_walk_the_look_chose_with_no_casting_delay_running_is_made():
    # Only a delay that ended since the look sends the move back to it: a walk priced over a ready warp (the safety's
    # choice, a shorter way round) is made as it was chosen
    from inventory_tracking.macros.goals import USE, Goal
    from inventory_tracking.macros.pursuit import Move
    from inventory_tracking.macros.travel import LOOPED

    play = game()
    play.staff = replace(STAFF, charges=0)
    hunt = hunter(play)
    run = play.run()
    here = me(play.world)
    goal = Goal('Super chests', (here.x + 56.0, here.y), USE, 4.0, LOOPED)
    hunt.travel.warped_at = run.clock() - 5.0

    hunt.advance(run, play.world, Ground(()), Move(Step((here.x + 16.0, here.y)), goal), goal.place, keys)

    assert len(play.walks) == 1


def test_the_hold_that_began_a_fight_is_not_judged_again_before_the_strike_is_pressed(monkeypatch):
    # 2026-10-18: a second look and price before the press held the first strike after a landing on Catacombs 4
    # 0.48 s, 44 of 61 landings (rca/2026-10-18/andariel-cadence-findings.md F2); a fresh press is still judged
    from types import SimpleNamespace

    play = game(foe(10, 5008.0, 5000.0))
    hunted = hunter(play)
    monkeypatch.setattr(type(hunted), 'pursuing', property(lambda _self: True))
    run = play.run()
    looks = []
    monkeypatch.setattr(
        hunted, 'judge', lambda *_a, **_k: looks.append(1) or SimpleNamespace(act=None, pressed=False, goal=None)
    )
    monkeypatch.setattr(hunted, 'pursuit', SimpleNamespace(pressed_at=1.0))
    hunted.judged = (1.0, run.clock() - 1.0, False)  # the Hold's, a second old
    assert not hunted.key_asks(run, play.world, [], Ground(()))  # (the fakes' ground: unread)
    assert len(looks) == 1  # struck: judged again, as every DECIDE_SECONDS
    hunted.judged = (1.0, run.clock() - 1.0, False)
    assert not hunted.key_asks(run, play.world, [], Ground(()), unstruck=True)
    assert len(looks) == 1  # not before the press
    monkeypatch.setattr(hunted, 'pursuit', SimpleNamespace(pressed_at=2.0))  # a fresh press of the key
    hunted.key_asks(run, play.world, [], Ground(()), unstruck=True)
    assert len(looks) == 2


def test_the_loops_fight_lets_go_when_its_run_is_over(monkeypatch):
    # 13:26:39-13:26:51 on 2026-10-18: Andariel dead, her pack fought 11.5 s; the run's end now yields the fight (the
    # loop's run only: a level run of the player's hand fights on as before)
    from types import SimpleNamespace

    from inventory_tracking.macros.pursuit import Ended

    play = game(foe(10, 5008.0, 5000.0))
    hunted = hunter(play)
    monkeypatch.setattr(type(hunted), 'pursuing', property(lambda _self: True))
    run = play.run()
    monkeypatch.setattr(hunted, 'pursuit', SimpleNamespace(pressed_at=1.0))
    for looped, yields in ((True, True), (False, False)):
        posted = SimpleNamespace(looped=looped)
        monkeypatch.setattr(
            hunted,
            'judge',
            lambda *_a, p=posted, **_k: SimpleNamespace(act=Ended('over'), pressed=False, goal=None, posted=p),
        )
        hunted.judged = (0.0, -10.0, False)
        assert hunted.key_asks(run, play.world, [], Ground(())) is yields


# --- the Gheed's swap (macros/pickup.py `Refused`): the level run ends for it ---


def gheeds_run(*, gheeds: bool = True, swap: bool = True):
    """A level run by a unique Grand Charm 4 units off, the player's Gheed's Fortune carried (`gheeds`), the runner's
    answer to a refusal `swap`; the refusals asked and the run's ends."""
    from inventory_tracking.builds import pursuing
    from inventory_tracking.game.records import Carried, Loot, Pack
    from inventory_tracking.macros.charms import GHEEDS_FORTUNE, UNIQUE, grand_charm
    from inventory_tracking.macros.pursuit import FULL, Pursuit

    play = game()
    charm = Drop(60, 5004.0, 5000.0, "Unique Grand Charm (Gheed's Fortune?)", VALUABLE, (1, 3), txt=grand_charm(),
                 quality=UNIQUE)  # fmt: skip
    play.loot = Loot((charm,), room=('..........',) * 4)
    theirs = Carried(1, grand_charm(), 0, 0, (1, 3), quality=UNIQUE, unique=GHEEDS_FORTUNE)
    play.pack = Pack((theirs,) if gheeds else ())
    hunt = hunter(play)
    hunt.build = pursuing(hunt.build)
    hunt.post(Pursuit('pickup', 0.0, advance=False, leash=FULL, area=101))
    asked: list = []
    ended: list[str] = []
    hunt.carry_one = lambda refused: asked.append(refused) or swap
    hunt.run_over = ended.append
    return play, hunt, charm, asked, ended


def test_a_unique_grand_charm_the_level_run_gives_up_with_a_gheeds_carried_is_the_gheeds_swap():
    # 13:56:41.578 on 2026-10-18: the run gave the charm up after 2 tries ("priced act expired"), went on, and only the
    # 45 s stand reached the swap (13:57:26)
    from inventory_tracking.macros.drop_ledger import GATHER_TRIES

    play, hunt, charm, asked, ended = gheeds_run()
    run = play.run()
    hunt.drops.gathered[charm.unit_id] = GATHER_TRIES
    hunt.drops.retried.add(charm.unit_id)  # (its one more try from near made: `again`)
    hunt.drops.tried[charm.unit_id] = 'priced act expired: look again before continuing'
    assert hunt.side_drop(run, (5000.0, 5000.0), [], play.world) is None
    assert [refused.drop for refused in asked] == [charm]
    assert 'given up after 2 tries' in str(asked[0])
    assert len(ended) == 1
    assert "the Gheed's swap" in ended[0]
    hunt.side_drop(run, (5000.0, 5000.0), [], play.world)
    assert len(asked) == 1  # asked once a drop


@pytest.mark.parametrize('which', ['a rune', 'no gheeds carried', 'no swap'])
def test_a_drop_given_up_with_no_gheeds_swap_is_left_as_before(which):
    from inventory_tracking.macros.drop_ledger import GATHER_TRIES

    play, hunt, charm, asked, ended = gheeds_run(gheeds=which != 'no gheeds carried', swap=which != 'no swap')
    if which == 'a rune':
        charm = Drop(61, 5004.0, 5000.0, 'Ist Rune', VALUABLE)
        play.loot = replace(play.loot, drops=(charm,))
    run = play.run()
    hunt.drops.gathered[charm.unit_id] = GATHER_TRIES
    hunt.drops.retried.add(charm.unit_id)
    assert hunt.side_drop(run, (5000.0, 5000.0), [], play.world) is None
    assert len(asked) == (1 if which == 'no swap' else 0)
    assert ended == []


def test_a_refused_click_of_the_level_run_ends_it_for_the_gheeds_swap_at_once():
    # The level run's pickup (hunting/moves.py `operate`) met the refusal at its first click: no try counted toward
    # giving up
    from inventory_tracking.macros.goals import PICK_UP, Goal
    from inventory_tracking.macros.hunting.base import Judged
    from inventory_tracking.macros.pickup import Refused
    from inventory_tracking.macros.pursuit import Operate
    from inventory_tracking.macros.travel import PRESSED

    play, hunt, charm, asked, ended = gheeds_run()
    play.deaf_picks = 999
    run = play.run()
    goal = Goal(charm.label, (charm.x, charm.y), PICK_UP, 4.0, PRESSED, unit=charm.unit_id)
    hunt.judge = lambda *_, **__: Judged(Operate(goal), goal, (charm.x, charm.y), hunt.pursuit)  # type: ignore[method-assign]
    assert hunt.pursue(run, play.world, [], Ground(()), None, in_reach=False)
    assert 999 - play.deaf_picks == 1
    assert len(asked) == 1
    assert isinstance(asked[0], Refused)
    assert len(ended) == 1
    assert charm.unit_id not in hunt.drops.tried  # not a failed try


def test_the_level_runs_give_up_memory_is_forgotten_for_the_new_gheeds():
    # 13:57:50 on 2026-10-18: back for the new one after the player's went onto a shared page, the level run never
    # tried it (the same unit, still given up); macros/loop.py GHEED_STASH forgets it (runner.py `_forget_given_up`)
    from inventory_tracking.macros.drop_ledger import GATHER_TRIES

    play, hunt, charm, _, _ = gheeds_run(gheeds=False)  # the player's on a shared page now
    run = play.run()
    hunt.drops.gathered[charm.unit_id] = GATHER_TRIES
    hunt.drops.retried.add(charm.unit_id)
    hunt.drops.swap_asked.add(charm.unit_id)
    assert hunt.side_drop(run, (5000.0, 5000.0), [], play.world) is None
    hunt.forget_given_up()
    assert hunt.side_drop(run, (5000.0, 5000.0), [], play.world) == charm


# --- F3 (rca/2026-10-18/andariel-cadence-findings.md §5): no side drop but a potion with the run's boss in reach ---


@pytest.mark.parametrize('quiet', [True, False])
def test_no_side_drop_but_a_potion_while_the_runs_boss_is_in_reach(monkeypatch, quiet):
    # 11:49:03 on 2026-10-18 (084856Z-37): one strike at Andariel, then "pursuit: Teleport toward Dol Rune ... 32 away";
    # back in reach at 11:49:09.6, dead at 11:49:11.56: 9.3 s in her window against a 3.6 s median
    from inventory_tracking.game.layout import SUPER_HEALING
    from inventory_tracking.game.records import Loot
    from inventory_tracking.macros import buffs

    monkeypatch.setattr(buffs, 'QUIET_BY_THE_BOSS', quiet)
    play = game()
    hunt = hunter(play)
    run = play.run()
    here = (5000.0, 5000.0)
    rune = Drop(80, 5006.0, 5000.0, 'Dol Rune', VALUABLE)
    play.loot = Loot((rune,), room=('..........',) * 4)
    her = foe(81, 5015.0, 5000.0, txt_id=156)
    assert hunt.side_drop(run, here, [her], play.world) == (None if quiet else rune)
    assert hunt.side_drop(run, here, [replace(her, x=5060.0)], play.world) == rune  # out of the strike's reach
    assert hunt.side_drop(run, here, [foe(82, 5015.0, 5000.0)], play.world) == rune  # no boss
    # A potion the belt wants is still a side goal by her (supply)
    potion = Drop(83, 5004.0, 5000.0, 'Super Healing Potion', HEALING, txt=SUPER_HEALING)
    play.loot = replace(play.loot, drops=(potion,))
    assert hunt.side_drop(run, here, [her], play.world) == potion

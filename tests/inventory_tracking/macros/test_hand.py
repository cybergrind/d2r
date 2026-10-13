"""The player's hand during a level run (rca/2026-10-13/run-2110-findings.md, moments M2 and M3).

- **Sorting** (21:13:55-21:14:22, take 20261013T181240Z-108): the player clicked during the run, opened the
  inventory and the cube, sorted and walked back by hand. The click ended the run ("the player moves by hand;
  KP_1 runs the level again") and a click the cast had swallowed was made again into the open inventory
  (21:13:59.93). The ruling (2026-10-13): the run is paused, not ended, and goes on by itself once the hand
  rests ("yes"); nothing is clicked into an open panel.
- **The stale pointer mark** (21:15:34-43, and 21:14:11.9-20.2): the hand left the pointer at (2459, 440); the
  guard's mark was the macro's last aim (2102, 305), seconds old; every priced move aborted "the mouse was moved"
  before any input, said once and then silenced, for 9.3 s.

The level is test_hunt's (the character at (5000, 5000), rooms east); the run's goal is a place 30 units east, as
the route's stage would name it, so that the run's own moves are walks.
"""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.actuator import Abort, Actuator
from inventory_tracking.macros.goals import PLACE_NEAR, REACH, Goal
from inventory_tracking.macros.pursuit import FULL, NONE, PAUSED, SETTLE, Hold, Pursuit, decide, settled
from inventory_tracking.macros.travel import PRESSED
from tests.inventory_tracking.macros.test_hunt import game, hunter, keys
from tests.inventory_tracking.macros.test_level_run import STEP, Level, facts, unasked


AREA = 101  # test_hunt's level
MARK = Goal('the mark', (5030.0, 5000.0), REACH, PLACE_NEAR, PRESSED, route='a route')
FAR = replace(MARK, label='the far mark', place=(5170.0, 5000.0))  # the east end of test_hunt's rooms
LEFT_AT, HAND = (2102, 305), (2459, 440)  # the macro's last aim and where the hand left the pointer (M3)
LEFT_BUTTON = 1 << 8  # XQueryPointer's mask for the left button (actuator.py `button_held`)


def running(play, *, goal: Goal = MARK):
    """A hunter on a level run of test_hunt's level whose goal is `goal`, with the pursuit loop on."""
    hunt = hunter(play)
    hunt.build = replace(hunt.build, settings=hunt.build.settings.model_copy(update={'pursuit': True}))
    hunt.post(Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA))
    hunt.goal = lambda run, world, foes, pressed, posted: goal  # the route's stage, as goals.goal_of names it
    return hunt


def ground(hunt, play) -> Ground:
    return Ground(hunt.known_level(play.world.player).ground)


# -- the pause, pure ----------------------------------------------------------------------------------------


def test_a_paused_run_strikes_what_is_in_reach_and_makes_no_move_of_its_own() -> None:
    goal = Level().goal()
    paused = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=108, paused=True)
    assert paused.leashed
    assert not paused.runs  # the loop and its pricing go by `runs`: no move, no insistence of the run's
    assert decide(facts(goal, way=unasked), paused).reason == PAUSED
    assert decide(facts(goal, in_reach=True, way=unasked), paused) == Hold(goal)
    # the level left ends it all the same
    assert decide(facts(goal, area=107, way=unasked), paused).reason == 'the level was left'
    # a fresh teleport press during the pause still asks for its goal now
    pressed = replace(paused, key='teleport', pressed_at=100.0, advance=True)
    assert decide(facts(goal), pressed).step == STEP


def test_the_hand_rests_settle_seconds_with_no_panel_open_before_the_run_goes_on() -> None:
    assert not settled(10.0, 10.0 + SETTLE - 0.01, panels=False)
    assert settled(10.0, 10.0 + SETTLE, panels=False)
    assert not settled(10.0, 60.0, panels=True)  # never with a panel open (I7)


def test_a_press_during_the_pause_keeps_it_a_fresh_pickup_press_ends_it_and_the_toggle_ends_the_run() -> None:
    play = game()
    hunt = running(play)
    run = play.run()
    hunt.pause_run(run, 'a click')
    hunt.post(Pursuit('teleport', 5.0))
    assert (hunt.pursuit.leash, hunt.pursuit.paused, hunt.pursuit.area) == (FULL, True, AREA)
    hunt.post(Pursuit('pickup', 6.0, advance=False, leash=FULL))
    assert (hunt.pursuit.leash, hunt.pursuit.paused, hunt.pursuit.area) == (FULL, False, AREA)
    hunt.pause_run(run, 'a click')
    hunt.end_run(run, 'attack mode off')  # KP_3 off, Mod+X: a paused run ends too
    assert hunt.pursuit is None or hunt.pursuit.leash == NONE
    assert 'Level run over: attack mode off' in play.said


# -- the sorting moment, 21:13:55-21:14:22 --------------------------------------------------------------------


def test_the_players_sorting_pauses_the_run_clicks_nothing_into_the_panel_and_the_run_goes_on_after(caplog):
    """The recorded order, on the arena's clock: the hand clicks at 0.5 s (a cast running: the click is one the
    game may have swallowed), opens the inventory and the cube at 1.0 s, sorts until 3.0 s and closes them; the
    run goes on by itself SETTLE seconds after, with no press. As it ran: the click ended the run, the swallowed
    click was made again into the open inventory, and only a fresh KP_1 moved the character again."""
    play = game()
    hunt = running(play, goal=FAR)
    clicks = (0.5, 0.62)
    play.keys.pointer_state = lambda: (*play.keys.at, LEFT_BUTTON if clicks[0] <= play.clock.now < clicks[1] else 0)
    hunt.casting = True
    placed: list[tuple[float, float]] = []

    def panels(*names):
        return lambda: setattr(play, 'world', replace(play.world, open_panels=names))

    def where():
        placed.append((play.clock.now, play.world.player.x))

    events = [
        (0.45, where), (1.0, panels('inventory', 'cube')), (2.9, where), (3.0, panels()), (3.0 + SETTLE - 0.1, where),
    ]  # fmt: skip
    run = play.run()
    run.actuator.drift, run.actuator.steady = 10**6, False  # as the runner sets them for attack mode
    for at, event in [*events, (9.0, run.cancelled.set)]:
        play.arrivals.append((at, event))
    play.arrivals.sort(key=lambda pair: pair[0])
    with caplog.at_level(logging.INFO), pytest.raises(Abort, match='cancelled'):
        hunt.attack_mode(run, keys)
    said = '\n'.join(play.said)
    assert 'Level run over' not in said
    assert "Level run paused: the player's hand (a click)" in said
    assert 'Level run resumed' in said
    # the character stood still from the click until the hand had rested: no move of the run's while paused
    still = [x for at, x in placed if at > 0.5]
    assert len(set(still)) == 1
    assert play.world.player.x > still[0] + 5  # and the run walked on to its goal after, with no press
    assert 'not made again: inventory, cube open' in caplog.text or 'made again' not in caplog.text


def test_a_swallowed_click_is_never_made_again_into_an_open_panel(caplog) -> None:
    """21:13:59.93: "the click the cast swallowed made again at (3093, 548)" with the inventory and the cube open."""
    from inventory_tracking.combat.controller import Move

    play = game()
    hunt = hunter(play)
    play.world = replace(play.world, open_panels=('inventory', 'cube'))
    hunt.move = Move(0.0, (3093, 548), swallowed=True)
    run = play.run()
    play.clock.now = 2.0
    with caplog.at_level(logging.INFO):
        hunt.serve_move(run, play.world)
    assert not [event for event in play.keys.events if event[0] == 'click']
    assert hunt.move is None
    assert 'not made again: inventory, cube open' in caplog.text


# -- the stale pointer mark, 21:15:34-43 ---------------------------------------------------------------------


def test_a_priced_move_after_the_hand_has_let_go_of_the_mouse_makes_its_click_at_the_first_look() -> None:
    """M3 as recorded: the hand left the pointer at (2459, 440), the mark was the macro's aim of 14 s before at
    (2102, 305). As it ran every look aborted "the mouse was moved" before any input, for 9.3 s."""
    play = game()
    hunt = running(play)
    run = play.run()
    play.keys.at, run.actuator.left_at = HAND, LEFT_AT
    hunt.pursue(run, play.world, [], ground(hunt, play), keys, in_reach=False)
    assert play.walks or play.warps, play.said  # the move's input was made (the fakes' build warps where it can)
    assert play.world.player.x > 5010.0
    assert not any('the mouse was moved' in line for line in play.said)


def test_a_hand_that_carries_the_pointer_off_during_the_move_still_stops_it_and_each_stop_is_said() -> None:
    """I7 kept: a hand moving the mouse during the act aborts it; I1/I6: the same abort for the same goal is said
    every time, with its count (as it ran it was said once and then silenced)."""
    play = game()
    hunt = running(play)
    run = play.run()
    sweep = iter(range(10_000))
    play.keys.pointer = lambda: (2200 + 7 * next(sweep), 400)  # a hand sweeping: never twice the same place
    for _ in range(3):
        hunt.pursue(run, play.world, [], ground(hunt, play), keys, in_reach=False)
    assert not play.walks
    assert not play.warps
    stops = [line for line in play.said if line.startswith('No move toward the mark')]
    assert stops == [
        'No move toward the mark: the mouse was moved',
        'No move toward the mark: the mouse was moved (x2)',
        'No move toward the mark: the mouse was moved (x3)',
    ]


def test_an_act_rebases_the_guards_mark_and_puts_back_the_runs_drift() -> None:
    play = game()
    actuator = Actuator(play.keys, lambda: True, play.run().pace)
    actuator.drift, actuator.steady, actuator.left_at = 10**6, False, LEFT_AT
    play.keys.at = HAND
    with actuator.held_act():
        assert (actuator.drift, actuator.steady, actuator.left_at) == (4, True, HAND)
        actuator.guard()  # the hand let go before the act: nothing stops it
        play.keys.at = (HAND[0] + 30, HAND[1])
        with pytest.raises(Abort, match='the mouse was moved'):
            actuator.guard()  # the hand moves during it: stopped
    assert (actuator.drift, actuator.steady) == (10**6, False)

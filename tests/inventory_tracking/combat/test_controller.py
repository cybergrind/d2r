"""Trace tests for the attack controller's decisions (combat/controller.py): the held strike input, the aim, the
player's move, and the aim as a policy."""

import math

from inventory_tracking.combat.controller import (
    CLICK,
    DONE,
    GAVE_UP,
    HAND_REST,
    MOVE_CLICKS,
    MOVE_QUIET,
    MOVE_RETRY,
    MOVE_SECONDS,
    MOVE_SETTLE,
    MOVED_UNITS,
    NO_CAST,
    PENDING,
    REAIM_UNITS,
    RETAP,
    STRAY_PIXELS,
    Aim,
    CastWatch,
    LiveAim,
    Move,
    aim_choice,
    serve,
)
from inventory_tracking.combat.policy import AIM_BEYOND, Choice, Foe, LinePolicy, Observation


ORIGIN = (5000.0, 5000.0)
HERE = (5000.0, 5000.0)
FOCAL = (5010.0, 5000.0)
PIXEL = (500, 400)


def test_a_cast_seen_right_after_the_press_counts_once_however_long_it_lasts():
    # One press can run several cast steps; each cast must count once, a second press counts again.
    watch = CastWatch(began=0.0)
    assert [watch.step(t, True) for t in (0.04, 0.08, 0.12)] == [None, None, None]
    assert watch.casts == 1
    assert watch.step(0.16, False) is None
    assert watch.step(0.2, True) is None
    assert watch.casts == 2


def test_no_cast_at_all_is_reported_once_the_cast_time_has_passed():
    # Idle steps are spaced under RETAP_SECONDS so only the cast time decides here.
    watch = CastWatch(began=0.0)
    assert watch.step(0.5, False) is None
    assert watch.step(0.7, False) is None
    assert watch.step(0.9, False) == NO_CAST  # 0.9 - 0.0 > CAST_SECONDS


def test_an_idle_hold_is_retapped_once_per_idle_spell():
    # The game casts once per press: an idle hold is released and pressed again, once per RETAP_SECONDS.
    watch = CastWatch(began=0.0)
    assert watch.step(0.0, True) is None
    assert watch.step(0.0, False) is None
    results = {}
    for k in range(1, 31):
        now = round(0.04 * k, 2)
        answer = watch.step(now, False)
        if answer is not None:
            results[now] = answer
    assert results == {0.28: RETAP, 0.6: RETAP, 0.92: RETAP}


def test_an_excuse_restarts_the_wait_for_the_first_cast_only_while_none_was_seen():
    # A cast of the macro's own is no missing strike: the wait restarts, but not after a strike cast.
    watch = CastWatch(began=0.0)
    watch.excuse(0.7)
    assert watch.began == 0.7
    assert watch.step(0.9, False) is None  # 0.2 s since the excuse, not NO_CAST

    cast = CastWatch(began=0.0, casts=1)
    cast.excuse(0.7)
    assert cast.began == 0.0


def test_an_aim_never_put_is_due():
    # Nothing has been aimed yet, so the pointer must be put on the line.
    aim = Aim(hand=((100, 100), -math.inf))
    assert aim.due(1.0, (100, 100), None, ORIGIN, HERE) is True


def test_an_aim_put_where_the_macro_left_it_is_not_due_until_the_focal_point_or_place_moves():
    # Only a focal point moved more than REAIM_UNITS, or a new place for the character, aims it again.
    aim = Aim(hand=((100, 100), -math.inf))
    aim.put(FOCAL, HERE, (100, 100))
    assert aim.due(1.0, (100, 100), (100, 100), FOCAL, HERE) is False
    moved_far = (FOCAL[0] + REAIM_UNITS + 0.5, FOCAL[1])
    assert aim.due(1.1, (100, 100), (100, 100), moved_far, HERE) is True
    moved_little = (FOCAL[0] + REAIM_UNITS * 0.5, FOCAL[1])
    assert aim.due(1.2, (100, 100), (100, 100), moved_little, HERE) is False
    moved_here = (HERE[0] + 1.0, HERE[1])
    assert aim.due(1.3, (100, 100), (100, 100), FOCAL, moved_here) is True


def test_a_pointer_the_players_hand_is_taking_somewhere_is_left_alone_until_it_rests():
    # (time, pointer) pairs: the hand keeps moving the pointer to new places, then rests for HAND_REST.
    aim = Aim(hand=((100, 100), -math.inf))
    aim.put(FOCAL, HERE, (100, 100))
    trace = [
        (1.0, (200, 100)),
        (1.1, (250, 100)),
        (1.2, (300, 120)),
        (1.3, (300, 120)),
        (1.5, (300, 120)),
    ]
    answers = [aim.due(now, pointer, (100, 100), FOCAL, HERE) for now, pointer in trace]
    assert answers == [False, False, False, False, True]  # 1.5 - 1.2 is well past HAND_REST
    assert HAND_REST == 0.2


def test_a_stray_of_at_most_stray_pixels_is_not_a_stray():
    # A few pixels off where the macro put the pointer is no reason to aim it again.
    aim = Aim(hand=((100, 100), -math.inf))
    aim.put(FOCAL, HERE, (100, 100))
    assert aim.due(1.0, (110, 100), (100, 100), FOCAL, HERE) is False
    assert aim.due(1.1, (100 + STRAY_PIXELS, 100), (100, 100), FOCAL, HERE) is False


def test_forget_makes_the_next_aim_due_even_with_the_pointer_in_place():
    # Another aim of the macro took the pointer: the line is aimed again whatever the pointer says.
    aim = Aim(hand=((100, 100), -math.inf))
    aim.put(FOCAL, HERE, (100, 100))
    assert aim.due(1.0, (100, 100), (100, 100), FOCAL, HERE) is False
    aim.forget()
    assert aim.due(1.1, (100, 100), (100, 100), FOCAL, HERE) is True


def test_a_click_the_game_took_that_moves_nothing_is_done_after_the_quiet_time_never_clicked():
    # The game took the click and the character stood still: the strikes wait MOVE_QUIET, then go on.
    move = Move(at=0.0, pixel=PIXEL)
    answers = [serve(move, now, HERE, running=False, acting=False, left_down=False) for now in (0.1, 0.2, 0.3)]
    assert answers == [PENDING, PENDING, PENDING]
    assert serve(move, MOVE_QUIET, HERE, running=False, acting=False, left_down=False) == DONE


def test_a_click_the_game_took_is_done_once_the_character_walks_and_stands_again():
    # While the character walks the move is PENDING; standing with the button up it is DONE.
    move = Move(at=0.0, pixel=PIXEL)
    assert serve(move, 0.1, HERE, running=True, acting=False, left_down=False) == PENDING
    assert serve(move, 0.2, HERE, running=True, acting=False, left_down=False) == PENDING
    assert serve(move, 0.3, HERE, running=False, acting=False, left_down=False) == DONE


def test_a_swallowed_click_is_made_again_after_the_cast_and_at_most_move_clicks_times():
    # A cast swallowed the click: wait for the character to stand free, click again, retry, then give up.
    move = Move(at=0.0, pixel=PIXEL, swallowed=True)
    freed = 0.5  # the cast ends and the character stands free
    answers = [
        serve(move, 0.0, HERE, running=False, acting=True, left_down=False),
        serve(move, 0.4, HERE, running=False, acting=True, left_down=False),
        serve(move, freed, HERE, running=False, acting=False, left_down=False),
        serve(move, freed + MOVE_SETTLE / 2, HERE, running=False, acting=False, left_down=False),
        serve(move, freed + MOVE_SETTLE + 0.05, HERE, running=False, acting=False, left_down=False),
    ]
    assert answers == [PENDING, PENDING, PENDING, PENDING, CLICK]
    first = freed + MOVE_SETTLE + 0.05
    move.clicked(first)
    assert serve(move, first + MOVE_RETRY / 2, HERE, running=False, acting=False, left_down=False) == PENDING
    second = first + MOVE_RETRY + 0.01
    assert serve(move, second, HERE, running=False, acting=False, left_down=False) == CLICK
    move.clicked(second)
    assert MOVE_CLICKS == 2
    assert serve(move, second + MOVE_RETRY / 2, HERE, running=False, acting=False, left_down=False) == PENDING
    assert serve(move, second + MOVE_RETRY + 0.01, HERE, running=False, acting=False, left_down=False) == GAVE_UP


def test_a_swallowed_click_that_moved_the_character_by_position_is_done_when_it_stands():
    # The character moved a unit or more from where it first stood, though not seen running: under way.
    moved = Move(at=0.0, pixel=PIXEL, swallowed=True)
    assert serve(moved, 0.0, HERE, running=False, acting=False, left_down=False) == PENDING
    far = (HERE[0] + MOVED_UNITS + 0.5, HERE[1])
    assert serve(moved, 0.2, far, running=False, acting=False, left_down=False) == DONE

    barely = Move(at=0.0, pixel=PIXEL, swallowed=True)
    assert serve(barely, 0.0, HERE, running=False, acting=False, left_down=False) == PENDING
    short = (HERE[0] + MOVED_UNITS * 0.5, HERE[1])
    assert serve(barely, 0.2, short, running=False, acting=False, left_down=False) == CLICK


def test_a_button_still_held_keeps_the_move_pending_past_every_limit():
    # The button down keeps the move pending for ever (3 s is past MOVE_SECONDS); a cast alone does not.
    move = Move(at=0.0, pixel=PIXEL, swallowed=True)
    for k in range(7):
        now = round(0.5 * k, 2)
        assert serve(move, now, HERE, running=False, acting=False, left_down=True) == PENDING
    assert MOVE_SECONDS == 2.0
    assert serve(move, 3.0, HERE, running=False, acting=False, left_down=True) == PENDING
    assert serve(move, 3.0, HERE, running=False, acting=True, left_down=False) == DONE

    cast_only = Move(at=0.0, pixel=PIXEL, swallowed=True)
    assert serve(cast_only, 1.9, HERE, running=False, acting=True, left_down=False) == PENDING
    assert serve(cast_only, 2.1, HERE, running=False, acting=True, left_down=False) == DONE


def test_a_swallowed_click_with_no_pixel_known_gives_up_when_it_would_have_clicked():
    # Without the pointer's place there is nothing to click again.
    move = Move(at=0.0, pixel=None, swallowed=True)
    assert serve(move, 0.0, HERE, running=False, acting=False, left_down=False) == PENDING
    assert serve(move, 0.2, HERE, running=False, acting=False, left_down=False) == GAVE_UP


def test_the_policy_answer_wins_whatever_is_reachable():
    # When the policy finds a line, that line is the answer, reachable monsters or not.
    choice = Choice((1.0, 2.0), 7, 5.0)
    seen = Observation(origin=ORIGIN, foes={})
    assert aim_choice(lambda _: choice, seen, []) == choice
    assert aim_choice(lambda _: choice, seen, [1]) == choice


def test_without_a_policy_line_the_elite_in_reach_is_aimed_at_just_past_it():
    # The elite is chosen over the nearer normal monster, the focal point AIM_BEYOND past it on the line.
    foes = {1: Foe(310, (5010.0, 5000.0), 100.0), 2: Foe(310, (5000.0, 5015.0), 100.0, elite=True)}
    seen = Observation(origin=ORIGIN, foes=foes)
    assert aim_choice(lambda _: None, seen, [1, 2]) == Choice((5000.0, 5015.0 + AIM_BEYOND), 2, 0.0)


def test_without_a_policy_line_the_nearest_reachable_monster_is_aimed_at_just_past_it():
    # Only unit 1 is in reach: it is aimed at just past it; nothing reachable means no cast.
    foes = {1: Foe(310, (5010.0, 5000.0), 100.0), 2: Foe(310, (5000.0, 5015.0), 100.0, elite=True)}
    seen = Observation(origin=ORIGIN, foes=foes)
    assert aim_choice(lambda _: None, seen, [1]) == Choice((5010.0 + AIM_BEYOND, 5000.0), 1, 0.0)
    assert aim_choice(lambda _: None, seen, []) is None


def test_the_fallback_focal_point_is_moved_by_the_window_aimable_function():
    # The focal point the fallback returns is the one the window lets the pointer reach.
    foes = {1: Foe(310, (5010.0, 5000.0), 100.0)}
    shifted = Observation(origin=ORIGIN, foes=foes, aimable=lambda focal: (focal[0] - 2.0, focal[1]))
    assert aim_choice(lambda _: None, shifted, [1]) == Choice((5010.0 + AIM_BEYOND - 2.0, 5000.0), 1, 0.0)
    unseen = Observation(origin=ORIGIN, foes=foes, aimable=lambda focal: None)
    assert aim_choice(lambda _: None, unseen, [1]) == Choice((5010.0 + AIM_BEYOND, 5000.0), 1, 0.0)


def test_the_line_policy_scores_only_the_focal_point_the_window_can_reach():
    # With no reachable focal point for any line there is no cast; with no window function it casts.
    foes = {1: Foe(310, (5010.0, 5000.0), 100.0)}
    policy = LinePolicy(damage_of=lambda txt: 1000.0)
    blind = Observation(origin=ORIGIN, foes=foes, aimable=lambda focal: None)
    assert policy(blind) is None
    open_window = Observation(origin=ORIGIN, foes=foes, aimable=None)
    assert policy(open_window) is not None


def test_live_aim_yields_while_the_player_moves():
    # The fight's aim leaves the pointer to the player while they move, whatever the policy says.
    live = LiveAim(policy=lambda seen: Choice((1.0, 2.0), 7, 5.0))
    moving = Observation(origin=ORIGIN, foes={1: Foe(310, (5010.0, 5000.0), 100.0)}, moving=True)
    assert live(moving) is None


def test_live_aim_falls_back_only_to_monsters_within_its_reach_with_a_clear_line():
    # A monster 30 units off is beyond the blades (REACH is about 22); 10 units is in reach.
    live = LiveAim(policy=lambda seen: None)
    far = Observation(origin=ORIGIN, foes={1: Foe(310, (5030.0, 5000.0), 100.0)})
    assert live(far) is None
    near = Observation(origin=ORIGIN, foes={1: Foe(310, (5010.0, 5000.0), 100.0)})
    assert live(near) == Choice((5010.0 + AIM_BEYOND, 5000.0), 1, 0.0)
    walled = Observation(origin=ORIGIN, foes={1: Foe(310, (5010.0, 5000.0), 100.0)}, blocked=lambda point: True)
    assert live(walled) is None


def test_live_aim_hands_the_policy_an_aimable_mapped_through_the_origin():
    # The policy sees the window function with the character's place bound in: (origin, focal) -> focal.
    got = []

    def record(seen):
        got.append(seen.aimable((1.0, 1.0)))
        return None

    def through(origin, focal):
        return (origin[0] + focal[0], origin[1] + focal[1])

    LiveAim(policy=record, aimable=through)(Observation(origin=ORIGIN, foes={}))
    assert got == [(5001.0, 5001.0)]

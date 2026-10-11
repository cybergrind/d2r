"""The last stretch before a level's door: the final hops, the click, and the first moment in the next level.

Each test is a situation cut from a recorded Catacombs level (`stage.py` says how the faked game walks,
teleports and takes a door) and asserts what is WANTED, in hops (a Teleport charge each), presses (one
teleport step each), seconds by the faked clock, clicks and stops. Where today's code does otherwise the
test is a strict xfail whose reason carries the measured numbers. The player taps the action with THINK
seconds from a step's end to the next one (the quarter of the 1782 logged gaps that were queued presses;
the median was 0.48 s).

From `evidence.py` over the logs of 2026-10-09 and 10, read at 22:20 on the 10th (116 exits in 37 logs):
- hops inside the last 60 units: 2 for 66 exits, 3 for 30, 4 or more for 10; the last hop was under 16 units
  for 51 of 111.
- the last landing to the next level: 1.03 s the median, 1.95 s the 90th percentile; 0.52 s of the median
  is the wait for the next press, 0.27 s the click (0.21 s with nothing to walk).
- the spot remembered: 0.22 s a click (53 exits, 2 misses); not known: 1.70 s (9 exits, 8 misses).
- stops right after an arrival: "the level card is for another level" 15, "the only way marked is back" 3.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.macros import teleport
from tests.inventory_tracking.scenarios.exits import evidence
from tests.inventory_tracking.scenarios.exits.stage import (
    SPOT,
    Card,
    LevelGame,
    Outcome,
    hostile,
    press,
    stage,
    to_the_door,
    walk_path,
)


THINK = 0.2


def remembered(level, offset=SPOT):
    """The door's spot as a run before this one left it."""
    teleport.ENTRIES.learn(level.target, offset)


def from_mark(level, points):
    return [(round(x - level.mark[0], 1), round(y - level.mark[1], 1)) for x, y in points]


def approach(name: str, start, *, spot=SPOT, limit: int = 8, **changes) -> tuple[LevelGame, Outcome]:
    """The player taps the action from `start` (world units from the mark) until the next level."""
    level = stage(name)
    if spot is not None:
        remembered(level, spot)
    play = LevelGame(level, level.off(*start), **changes)
    return play, to_the_door(play, limit, think=THINK)


# --- the stage itself ---


def test_the_card_marks_the_stairs_where_the_log_did_and_the_recorded_hops_come_out_again():
    # Host, 17:26 on 2026-10-10 (log 20261010T142454Z): "door Next level marked at (22532.5, 6897.5)", then
    # landings at (22542.5, 6872.5), (22535.5, 6891.5) and on the spot (22532.5, 6900.5).
    level = stage('catacombs2_stairs294')
    assert level.target.label == 'Next level'
    assert level.target.warp
    assert level.mark == (22532.5, 6897.5)
    assert teleport.Entries.key(level.target) == 'preset 294:stairs'
    _, outcome = approach('catacombs2_stairs294', (16, -50))
    logged = [(10.0, -25.0), (3.0, -6.0), (0.0, 3.0)]
    assert len(outcome.landings) == len(logged)
    assert all(math.dist(a, b) < 1.6 for a, b in zip(from_mark(level, outcome.landings), logged, strict=True))
    assert outcome.entered
    assert outcome.stops == []


def test_the_log_reader_counts_an_exit_as_the_log_tells_it(tmp_path):
    # Host, 21:44 on 2026-10-10: two hops, a click from 7.1 away that walked 7.2, and the next step stopped.
    lines = [
        '2026-10-10 21:44:04,700 INFO Macro: Teleport toward Next level: 26 left after this, 18 charges',
        '2026-10-10 21:44:04,894 INFO Macro: door Next level marked at (22647.5, 8027.5), entry (22647.5, 8030.5); '
        'this hop aims 25.9 from the mark',
        '2026-10-10 21:44:05,113 INFO Macro: teleport aimed at (22667.5, 8043.9), 28.6 from (22672.6, 8072.1), 25.7 '
        'off the way, footing True, 16 grids, pointer (4067, 71) in (1920, 0, 2560, 1418); landed at (22667.6, '
        '8044.1), off by 0.2 (+0.1, +0.2)',
        '2026-10-10 21:44:05,289 INFO Macro: Teleport toward Next level: 7 left after this, 17 charges',
        '2026-10-10 21:44:05,459 INFO Macro: door Next level marked at (22647.5, 8027.5), entry (22647.5, 8030.5); '
        'this hop aims 7.4 from the mark',
        '2026-10-10 21:44:05,678 INFO Macro: teleport aimed at (22653.7, 8031.5), 18.8 from (22667.6, 8044.1), 18.1 '
        'off the way, footing True, 16 grids, pointer (3148, 196) in (1920, 0, 2560, 1418); landed at (22653.6, '
        '8031.1), off by 0.4 (-0.0, -0.4)',
        '2026-10-10 21:44:05,681 INFO Macro: Walking into Next level, 7 away',
        '2026-10-10 21:44:05,681 INFO Macro: door Next level marked at (22647.5, 8027.5); the character at (22653.6, '
        '8031.1), 7.1 from the mark; entry remembered -0.0, +3.0 from the mark',
        '2026-10-10 21:44:06,225 INFO Macro: the door took the click (0, 0) pixels from its tiles; under the pointer '
        '(5, 1961049836)',
        '2026-10-10 21:44:06,226 INFO Macro: door Next level: in after 0.54s, walked 7.2 from (22653.6, 8031.1) to '
        '(22646.8, 8030.8); the entry at -0.7, +3.3 from the mark, 3.4 away (remembered)',
        '2026-10-10 21:44:06,226 INFO Macro: Next level: there',
        '2026-10-10 21:44:06,229 INFO Macro stopped: the level card is for another level',
    ]
    log = tmp_path / 'probe.log'
    log.write_text('\n'.join(lines))
    [exit_], [stop] = evidence.read(log)
    assert (exit_.hops, exit_.fewest, exit_.misses, exit_.entry) == (2, 2, 0, 'remembered')
    assert (exit_.walk_from, exit_.walk_seconds, exit_.walked) == (7.1, 0.54, 7.2)
    assert exit_.landing_to_click == 0.0  # the press was queued
    assert stop[2:4] == ('the level card is for another level', 0.0)


# --- the landing before the door ---


@pytest.mark.xfail(
    strict=True,
    reason='today 2 hops, 3 presses, 1.60 s: the hop lands at (+2.9, -6.3), nearest the MARK and 9.7 from the '
    'spot, 0.7 past ENTRY_WALK, then a hop of 9.7 onto the spot. (+3, -3) is in view from the start and an open '
    'walk of 6.7 from the spot. landing() ranks by the way to the mark, not by where the click can be made from',
)
def test_a_spot_on_the_far_side_of_the_stairs_walls_is_one_hop_and_the_click():
    # Host, 17:26, 18:01, 18:33 and 19:32 on 2026-10-10: the stairs' mark sits in the east edge of a block of
    # walls 8 x 9 units, the spot is 3 south of it. Coming from the north the character is 27 from the mark.
    _, outcome = approach('catacombs2_stairs294', (10, -25))
    assert outcome.entered
    assert outcome.hops == 1
    assert outcome.presses == 2
    assert outcome.seconds <= 1.45


@pytest.mark.xfail(
    strict=True,
    reason='today 3 hops, 4 presses, 2.17 s: landings at (+4.3, -26.8) and (+2.7, -6.7), then 9.9 onto the spot. '
    'Two hops reach a place the click walks in from (replayed over 42 recorded exits: 99 hops made, 91 needed)',
)
def test_the_same_door_from_54_units_is_two_hops_and_the_click():
    _, outcome = approach('catacombs2_stairs294', (10, -53))
    assert outcome.entered
    assert outcome.hops == 2
    assert outcome.presses == 3
    assert outcome.seconds <= 2.0


@pytest.mark.xfail(
    strict=True,
    reason='today 2 hops, 3 presses, 1.60 s: the spot is 45 units up the screen from the start, out of view; the '
    'hop lands at (+10.7, +6.1), 11.1 from the spot, and a hop of 11 follows. A landing within ENTRY_WALK of the '
    'spot over open ground is in view from the start',
)
def test_a_spot_off_the_screen_from_the_start_gets_the_one_hop_that_leaves_a_walk():
    _, outcome = approach('catacombs3_stairs292', (24, 24))
    assert outcome.entered
    assert outcome.hops == 1
    assert outcome.presses == 2
    assert outcome.seconds <= 1.45


# Until 2026-10-11: 7 hops, 8 presses, 4.50 s, through the gap at the wall's west end 50 units off (Way gave
# no hop of 5 tiles straight down the screen: hop_in_view counts any point of both tiles). The far potential
# counts tile centres and 6 tiles (teleport.FAR_TILES). The recorded run made 4 hops, 3 are enough.
def test_a_wall_21_units_thick_before_the_stairs_room_is_hopped_over_not_gone_round():
    # Host, 18:37 on 2026-10-10: hops of 25.0, 6.3 (to line up), 25.5 over the wall and 12.0 onto the spot.
    play, outcome = approach('catacombs2_wall_band', (25, -50), limit=10)
    assert outcome.entered
    assert outcome.hops <= 4
    assert outcome.seconds <= 2.8
    assert min(x for x, _ in from_mark(play.level, outcome.landings)) > -20  # never out by the west end


def test_a_charge_is_not_spent_on_a_few_open_steps():
    # Host, 18:22 on 2026-10-10: a hop to 5 units west of the spot, then a hop of 5 onto it ("we have jumped
    # twice around the entrance"). Since ENTRY_WALK the click walks them.
    play, outcome = approach('catacombs3_stairs291', (-21, -5))
    assert outcome.entered
    assert (outcome.hops, outcome.presses, outcome.clicks) == (1, 2, 1)
    assert 5.0 < outcome.walked < 8.0
    assert outcome.seconds <= 1.5
    assert play.staff.charges == 39


@pytest.mark.xfail(
    strict=True,
    reason='today 2 hops, 3 presses, 1.59 s against 1 hop, 1.01 s with the spot at (0, +3): the hop lands at '
    '(+7.3, 0.0), 12.6 from the remembered place, and a second one crosses to it. walk_into keeps where the '
    'character STOOD when the first click took (host, 21:36 on 2026-10-10: preset 291 went from (0, +3) to '
    '(-5, +3), a place west of the stairs)',
)
def test_a_spot_learnt_standing_west_of_the_stairs_costs_no_hop_from_the_east():
    _, outcome = approach('catacombs2_stairs291', (25, 0), spot=(-5.0, 3.0))
    assert outcome.entered
    assert outcome.hops == 1
    assert outcome.seconds <= 1.1


# --- a spot remembered, and not yet known ---


def test_a_door_not_met_before_is_walked_into_round_its_walls_and_its_spot_is_kept():
    # The character comes from the north-west; 10 from the mark, north of the block of walls, the step clicks
    # the door and the game walks 14 units round the block (0.94 s: less than a hop and the next press).
    play, first = approach('catacombs3_stairs291', (-11, -39), spot=None)
    level = play.level
    assert first.entered
    assert first.stops == []
    assert (first.hops, first.clicks, first.strays) == (2, 1, 0)
    assert 12.0 < first.walked < 16.0
    learnt = teleport.ENTRIES.offset(level.target)
    assert learnt is not None
    assert math.dist(learnt, SPOT) < 1.0
    # The next run through the same preset lands on the spot and walks nothing.
    again = LevelGame(level, level.off(-11, -39))
    second = to_the_door(again, think=THINK)
    assert second.entered
    assert second.walked < 1.0
    assert second.seconds <= first.seconds


# --- the click ---


@pytest.mark.xfail(
    strict=True,
    reason='today the hop ends the step and the door waits for the next press: 0.52 s the median over 111 logged '
    'exits, 1.27 s the 90th percentile (attack mode comes back on in between); here '
    'one press leaves the character on the spot, not in the next level',
)
def test_the_hop_that_lands_on_the_doors_spot_goes_on_to_the_click():
    level = stage('catacombs2_stairs294')
    remembered(level)
    play = LevelGame(level, level.off(12, 10))
    outcome = press(play, lambda: level.target)
    assert outcome.hops == 1
    assert outcome.entered
    assert outcome.seconds <= 0.9


def test_a_pointer_the_hand_jerks_away_before_the_click_is_put_back_on_the_door():
    level = stage('catacombs2_stairs294')
    remembered(level)
    play = LevelGame(level, level.spot)
    sleep, jerked = play.clock.sleep, []

    def hand(seconds):
        if not jerked and seconds == teleport.HOVER_SECONDS:  # once, while the step looks under the pointer
            jerked.append(play.keys.at)
            play.keys.at = (play.keys.at[0] + 300, play.keys.at[1] - 80)
        sleep(seconds)

    play.clock.sleep = hand
    outcome = to_the_door(play, think=THINK)
    assert jerked
    assert outcome.entered
    assert outcome.strays == 0
    assert outcome.walked < 1.0
    assert outcome.seconds <= 1.0


def test_a_doorway_drawn_above_its_tiles_is_found_by_what_is_under_the_pointer():
    level = stage('catacombs2_stairs294')
    remembered(level)
    play = LevelGame(level, level.spot)
    play.door_above = 60  # classic pixels: the box takes the second aim, not the ground
    outcome = to_the_door(play, think=THINK)
    assert outcome.entered
    assert (outcome.clicks, outcome.strays) == (1, 0)
    assert outcome.seconds <= 0.8


def test_monsters_at_the_door_do_not_keep_the_step_from_leaving():
    # The step is the player's "go on": attack mode is paused for it (runner) and comes back in the next
    # level. A monster on the first aim leaves that aim for last; the next one takes the door.
    level = stage('catacombs2_stairs294')
    remembered(level)
    play = LevelGame(level, level.off(12, 10))
    pack = (hostile(50, level.mark), hostile(51, level.off(4, 6)), hostile(52, level.off(-3, 7)))
    play.world = replace(play.world, monsters=pack)
    outcome = to_the_door(play, think=THINK)
    assert outcome.entered
    assert outcome.stops == []
    assert (outcome.hops, outcome.clicks, outcome.strays) == (1, 1, 0)
    assert outcome.seconds <= 1.4
    assert play.strikes == []
    assert play.sigils == []


@pytest.mark.parametrize('spot', [SPOT, None])
def test_a_closed_door_between_the_character_and_the_stairs_is_hopped_over(spot):
    # The stairs room's east wall has two doors, both closed in the take; the character stands 5 units
    # outside the southern one. No walk leads in (the faked game would stand at the door), a hop does.
    level = stage('catacombs3_stairs292_doors')
    start = level.off(18, 12.5)
    assert any(door.closed and math.dist((door.x, door.y), level.off(12.5, 12.5)) < 1 for door in level.doors)
    assert walk_path(level.ground, level.doors, start, level.spot) is None
    _, outcome = approach('catacombs3_stairs292_doors', (18, 12.5), spot=spot)
    assert outcome.entered
    assert outcome.stops == []
    assert (outcome.hops, outcome.clicks) == (1, 1)
    assert outcome.walked < 6.0
    assert outcome.seconds <= 1.5


# --- the first moment in the next level ---


def test_the_action_asked_for_again_on_arrival_waits_for_the_new_levels_card():
    here, beyond = stage('catacombs2_stairs294'), stage('catacombs3_stairs292')
    remembered(here)
    play = LevelGame(here, here.spot, beyond=beyond)
    card = Card(play)
    outcome = press(play, card)
    assert outcome.entered
    assert play.world.player.area == 36
    outcome = press(play, card, outcome)  # queued during the walk-in: it runs at once
    assert outcome.stops == []
    assert outcome.hops == 1  # toward the next stairs
    assert play.clock.now - play.entered_at <= 1.5


@pytest.mark.xfail(
    strict=True,
    reason='today "Macro stopped: the only way marked is back to Catacombs 3" (3 logged: Catacombs 4 once, Tower '
    'Cellar 5 twice); each time the player went on with the pickup or seek step toward the boss',
)
def test_a_level_whose_only_marked_way_is_back_is_no_stop():
    here, last = stage('catacombs3_stairs292'), stage('catacombs4')
    assert last.target.kind == 'previous'
    remembered(here)
    play = LevelGame(here, here.spot, beyond=last)
    card = Card(play, lag=0.0)
    outcome = press(play, card)
    assert outcome.entered
    outcome = press(play, card, outcome)
    assert outcome.stops == []
    assert play.world.player.area == 37  # and never back up the stairs

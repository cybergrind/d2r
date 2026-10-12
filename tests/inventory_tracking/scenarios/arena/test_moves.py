"""A move takes its time in the arena (game.py): a walk is run, a hop is cast, a Blade Warp is cast and
flown, the character can be struck on the way, and the production code's own waits for a move are met.

The first part plays no macro (the inputs are made as in test_game.py); the second plays the production
macro (driver.py), with `instant_moves=True` beside it for what the same play was before.
"""

import math
from dataclasses import replace
from itertools import pairwise

import pytest

from inventory_tracking.builds.warlock.movement import WARP_SECONDS, WARP_SPEED
from inventory_tracking.builds.warlock.skills import BLADE_WARP
from inventory_tracking.combat.policy import RUN_MODES
from inventory_tracking.combat.timeline import GAME_RATE
from inventory_tracking.config import PLAYER_HEALING
from inventory_tracking.macros.movement import TELEPORT_SECONDS
from inventory_tracking.macros.routines import ACTING
from inventory_tracking.macros.runner import ATTACK, PICKUP
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.teleport import MOVED, WALKING
from tests.inventory_tracking.macros.fakes import KEYS
from tests.inventory_tracking.scenarios.arena.driver import Press, play
from tests.inventory_tracking.scenarios.arena.evidence.sure import sure
from tests.inventory_tracking.scenarios.arena.game import RUN_SPEED, Arena
from tests.inventory_tracking.scenarios.arena.scenes_basic import (
    HERE,
    afoot,
    archer_at_a_gap,
    archer_behind_a_wall,
    bovine_behind_a_wall,
    hero,
    one_in_the_open,
    one_out_of_reach,
    potion_on_the_ground,
)
from tests.inventory_tracking.scenarios.arena.test_game import RIGHT_BUTTON, click, frames, point_at, tap
from tests.inventory_tracking.scenarios.threat.harness import RUN


STRIDE = RUN_SPEED / GAME_RATE  # units of one tick's run
# What the macro says when a wait of its own for a move ran out (macros/travel.py `step_walk` and
# `Travel.jump`, macros/hunt.py `take_step` and `go`).
TIMED_OUT = ('did not move', 'No step', 'No move toward')


def empty(scene=None, **changes) -> Arena:
    """An arena with nobody to fight: `scene` (one in the open) without its monsters."""
    scene = one_in_the_open() if scene is None else scene
    scene.mobs = []
    return Arena(scene, **changes)


def mode(arena: Arena) -> int:
    return arena.world.player.mode


def run_out(arena: Arena, limit: int = 400) -> list[tuple[float, float]]:
    """The frames of a walk under way, to its end: where the character was at each look."""
    seen = []
    while mode(arena) in RUN_MODES:
        seen.append(arena.here)
        frames(arena, 1)
        assert len(seen) < limit
    return seen


def lines(result) -> list[str]:
    return [text for _, text in result.said]


def step_scenes():
    """The three plays in which the macro has to move, each by another way: (scene, the way's line)."""
    staffed = one_out_of_reach()
    staffed.hero = replace(hero(hand=1), slots=tuple(None if s == BLADE_WARP else s for s in staffed.hero.slots))
    return [
        (afoot(one_out_of_reach()), 'Macro: Walking 7 toward a better place'),
        (one_out_of_reach(), 'Macro: Blade Warp'),
        (staffed, 'Macro: Teleport'),
    ]


# --- a walk ---------------------------------------------------------------------------------------------


def test_the_run_is_the_one_measured_from_a_take():
    assert RUN_SPEED == RUN == 18.75  # scenarios/threat/harness.py: the take 20261010T162810Z-35
    assert STRIDE == 0.75


def test_a_walk_takes_its_length_at_the_run_and_the_character_runs_meanwhile():
    arena = empty()
    point_at(arena, (HERE[0] + 15.0, HERE[1]))
    click(arena)
    goal = arena.walks[-1]
    away = math.dist(HERE, goal)
    assert arena.here == HERE  # not there in the instant of the click
    assert mode(arena) in WALKING  # what the macro reads as going somewhere on foot
    seen = run_out(arena)
    assert len(seen) == pytest.approx(away / RUN_SPEED * GAME_RATE, abs=1)  # away / speed seconds, a tick either way
    assert arena.clock.now == pytest.approx(away / RUN_SPEED, abs=1 / GAME_RATE)
    assert all(math.dist(a, b) == pytest.approx(STRIDE) for a, b in pairwise(seen))
    assert arena.here == goal
    assert mode(arena) not in RUN_MODES | ACTING  # it stands
    assert arena.result().moved == pytest.approx(away)


def test_with_instant_moves_the_walk_is_over_at_its_click():
    arena = empty(instant_moves=True)
    point_at(arena, (HERE[0] + 15.0, HERE[1]))
    click(arena)
    assert arena.here == arena.walks[-1]
    assert mode(arena) not in RUN_MODES
    assert arena.clock.now == 0.0


def test_a_walk_round_a_wall_follows_the_way():
    arena = empty(archer_behind_a_wall())  # the wall at x = HERE + 7, down to y = HERE + 10
    point_at(arena, (HERE[0] + 10.0, HERE[1] - 5.0))  # beyond it
    click(arena)
    goal = arena.walks[-1]
    seen = [*run_out(arena), arena.here]
    assert arena.here == goal
    assert all(arena.footing(at) for at in seen)  # never in the wall
    assert max(y for _, y in seen) >= HERE[1] + 10.0  # round its end
    gone = arena.result().moved
    assert gone > 2 * math.dist(HERE, goal)
    assert len(seen) - 1 == pytest.approx(gone / RUN_SPEED * GAME_RATE, abs=1)


def test_a_click_during_a_walk_redirects_it():
    arena = empty()
    point_at(arena, (HERE[0] + 20.0, HERE[1]))
    click(arena)
    first = arena.walks[-1]
    frames(arena, 10)
    turned = arena.here
    assert turned == pytest.approx((HERE[0] + 10 * STRIDE, HERE[1]), abs=0.01)
    point_at(arena, (turned[0], turned[1] - 9.0))
    click(arena)
    second = arena.walks[-1]
    seen = [*run_out(arena), arena.here]
    assert arena.here == second
    assert all(x == pytest.approx(turned[0], abs=0.05) for x, _ in seen)  # not a step further toward the first
    assert first not in seen
    assert arena.result().moved == pytest.approx(10 * STRIDE + math.dist(turned, second))


def test_a_cast_ends_a_walk_where_the_character_is():
    arena = empty()
    point_at(arena, (HERE[0] + 20.0, HERE[1]))
    click(arena)
    frames(arena, 8)
    arena.keys.button(RIGHT_BUTTON, True)  # the strike held: the game casts it at the next look
    frames(arena, 1)
    stopped = arena.here
    assert arena.casts == 1
    assert mode(arena) in ACTING
    frames(arena, 40)
    arena.keys.button(RIGHT_BUTTON, False)
    assert arena.here == stopped
    assert math.dist(HERE, stopped) == pytest.approx(8 * STRIDE, abs=STRIDE)
    frames(arena, 20)
    assert arena.here == stopped  # the walk does not come back when the casts are over
    assert mode(arena) not in RUN_MODES | ACTING


def test_a_click_during_a_cast_walks_when_the_cast_is_over():
    arena = empty()
    arena.keys.button(RIGHT_BUTTON, True)
    frames(arena, 1)
    arena.keys.button(RIGHT_BUTTON, False)
    cast_ends = arena.acting_until
    assert mode(arena) in ACTING
    point_at(arena, (HERE[0] + 6.0, HERE[1]))
    click(arena)
    goal = arena.walks[-1]
    while arena.clock.now < cast_ends:
        assert arena.here == HERE
        assert mode(arena) in ACTING
        frames(arena, 1)
    arena.read()  # the look that finds the cast over: the walk begins
    assert mode(arena) in WALKING
    seen = run_out(arena)
    assert seen[0] == HERE
    assert arena.here == goal


def test_a_drop_is_taken_when_the_character_stands_on_it():
    arena = Arena(potion_on_the_ground())
    arena.pick_above = 0.0
    at = arena.scene.drops[0].at
    point_at(arena, at)
    click(arena)
    ticks = math.ceil(math.dist(HERE, at) / STRIDE)
    frames(arena, ticks - 1)
    assert arena.picked == []
    assert mode(arena) in RUN_MODES
    frames(arena, 1)
    assert arena.picked == ['a super healing potion']
    assert arena.here == at
    assert arena.loot.drops == ()


# --- struck on the way ----------------------------------------------------------------------------------


def crossing(instant_moves: bool, seed: int = 1) -> Arena:
    """The character walked past the gap an archer stands at (`archer_at_a_gap`: cover at both ends
    of the walk, the archer's line on the way), the archer kept where it is, for ten seconds."""
    arena = Arena(archer_at_a_gap(), seed=seed, instant_moves=instant_moves)
    arena.mobs.pack.walkers[1].traits = replace(arena.mobs.pack.walkers[1].traits, speed=0.0)
    point_at(arena, (HERE[0], HERE[1] + 15.0))
    click(arena)
    frames(arena, round(10 * GAME_RATE))
    return arena


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_a_monster_with_the_path_in_reach_strikes_a_character_walking_past(seed, monkeypatch):
    # Of the arena giving the monsters the character's place on the way, not of the fitted chances:
    # every shot lands, and at once (with the fitted flight an arrow sent at a character that walks
    # on ends behind it: tests/inventory_tracking/scenarios/arena/test_mobs.py has that).
    sure(monkeypatch, instant=True)
    walked, jumped = crossing(False, seed), crossing(True, seed)
    assert walked.here == jumped.here == walked.walks[-1]  # the same walk, to its end
    assert jumped.taken == 0.0  # in cover at both ends: the walk made in an instant passes no line
    assert walked.taken > 0.0  # run, it crosses the archer's line


def test_the_monsters_are_given_the_place_of_each_tick():
    arena = empty(one_in_the_open())
    given = []
    arena.mobs.tick = lambda here, *more: given.append(here) or 0.0
    point_at(arena, (HERE[0] + 9.0, HERE[1]))
    click(arena)
    frames(arena, 6)
    assert [round(x - HERE[0], 2) for x, _ in given] == [0.75, 1.5, 2.25, 3.0, 3.75, 4.5]


# --- a hop and a Blade Warp -----------------------------------------------------------------------------


def staffed() -> Arena:
    scene = one_in_the_open()
    scene.hero.hand = 1  # the staff in hand: a hop needs it
    return empty(scene)


def test_a_hop_places_the_character_after_its_cast_not_before():
    arena = staffed()
    spot = (HERE[0] + 12.5, HERE[1] + 3.5)
    point_at(arena, spot)
    charges = arena.staff.charges
    tap(arena, KEYS[TELEPORT])
    assert arena.here == HERE
    assert mode(arena) in ACTING  # the cast, from the key
    assert arena.staff.charges == charges - 1  # spent with the cast
    assert arena.result().charges == 1
    ticks = math.ceil(TELEPORT_SECONDS * GAME_RATE)  # 0.31 s: the eighth tick
    assert ticks == 8
    for _ in range(ticks - 1):
        frames(arena, 1)
        assert arena.here == HERE
        assert mode(arena) in ACTING
    frames(arena, 1)
    assert arena.here == spot  # the sub-tile's centre
    assert arena.clock.now == pytest.approx(ticks / GAME_RATE)
    frames(arena, 1)
    assert mode(arena) not in ACTING | RUN_MODES  # free at the landing
    assert arena.result().moved == pytest.approx(math.dist(HERE, spot))


def test_with_instant_moves_a_hop_lands_at_its_key():
    scene = one_in_the_open()
    scene.hero.hand = 1
    arena = empty(scene, instant_moves=True)
    point_at(arena, (HERE[0] + 12.5, HERE[1] + 3.5))
    tap(arena, KEYS[TELEPORT])
    assert arena.here == (HERE[0] + 12.5, HERE[1] + 3.5)
    assert mode(arena) not in ACTING


def test_a_hop_key_during_a_cast_is_cast_when_that_cast_is_over():
    arena = staffed()
    arena.keys.button(RIGHT_BUTTON, True)
    frames(arena, 1)
    arena.keys.button(RIGHT_BUTTON, False)
    cast_ends = arena.acting_until
    point_at(arena, (HERE[0] + 12.5, HERE[1] + 3.5))
    tap(arena, KEYS[TELEPORT])
    assert arena.landing is None  # kept, not cast
    assert arena.result().charges == 0
    while arena.here == HERE:
        frames(arena, 1)
        assert arena.clock.now < 2.0
    assert arena.here == (HERE[0] + 12.5, HERE[1] + 3.5)
    assert arena.result().charges == 1
    assert arena.clock.now >= cast_ends + TELEPORT_SECONDS
    assert arena.clock.now <= cast_ends + TELEPORT_SECONDS + 2 / GAME_RATE


def test_a_blade_warp_places_the_character_after_its_cast_and_the_blades_flight():
    arena = empty()
    point_at(arena, (HERE[0] + 18.0, HERE[1]))
    tap(arena, KEYS[BLADE_WARP])
    spot = arena.warps[-1]
    away = math.dist(HERE, spot)
    takes = WARP_SECONDS + away / WARP_SPEED  # 0.35 s and 18 units at 45 a second: 0.75 s
    ticks = math.ceil(takes * GAME_RATE - 1e-6)
    assert ticks == 19
    assert mode(arena) in ACTING
    for _ in range(ticks - 1):
        frames(arena, 1)
        assert arena.here == HERE
        assert mode(arena) in ACTING
    frames(arena, 1)
    assert arena.here == spot
    frames(arena, 1)
    assert mode(arena) not in ACTING | RUN_MODES
    assert arena.result().moved == pytest.approx(away)
    assert arena.result().charges == 0


def test_a_longer_blade_warp_flies_longer():
    def landed_after(away: float) -> int:
        arena = empty()
        point_at(arena, (HERE[0] + away, HERE[1]))
        tap(arena, KEYS[BLADE_WARP])
        ticks = 0
        while arena.here == HERE:
            frames(arena, 1)
            ticks += 1
        return ticks

    assert landed_after(9.0) == math.ceil((WARP_SECONDS + 9.0 / WARP_SPEED) * GAME_RATE - 0.01)
    assert landed_after(24.0) > landed_after(9.0) + 7  # 15 units more at 45 a second: 8 ticks


def test_a_hop_and_a_warp_into_a_wall_move_nobody_and_cost_nothing():
    scene = archer_behind_a_wall()
    scene.hero.hand = 1
    arena = empty(scene)
    point_at(arena, (HERE[0] + 7.5, HERE[1] - 5.0))  # in the wall
    tap(arena, KEYS[TELEPORT])
    tap(arena, KEYS[BLADE_WARP])
    frames(arena, 30)
    assert arena.here == HERE
    assert len(arena.refused) == 2
    assert arena.result().charges == 0
    assert mode(arena) not in ACTING


def test_a_click_during_a_hop_walks_from_the_landing():
    arena = staffed()
    spot = (HERE[0] + 12.5, HERE[1] + 3.5)
    point_at(arena, spot)
    tap(arena, KEYS[TELEPORT])
    point_at(arena, (HERE[0], HERE[1] - 6.0))
    click(arena)  # during the hop's cast
    while arena.here == HERE:
        assert mode(arena) in ACTING
        frames(arena, 1)
    assert arena.here == spot  # the hop first, whole
    arena.read()  # the look that finds the cast over
    seen = [*run_out(arena), arena.here]
    assert seen[0] == spot  # the walk is from the landing
    assert seen[-1] == arena.walks[-1] == pytest.approx((HERE[0], HERE[1] - 6.0), abs=0.05)
    assert arena.result().moved == pytest.approx(math.dist(HERE, spot) + math.dist(spot, seen[-1]))


# --- the production macro's own waits ---------------------------------------------------------------------


@pytest.mark.parametrize(('scene', 'way'), step_scenes(), ids=['walk', 'blade warp', 'teleport'])
def test_the_step_toward_a_monster_out_of_reach_is_made_and_the_monster_killed(scene, way):
    """Attack mode never moves by itself (macros/hunt.py: the mode's own moves follow a pickup request);
    the pickup press with nothing to pick up is the step. Each wait of the production code for its move
    is met: `step_walk` sees the character going, `Travel.jump` sees it somewhere else, and neither
    before the move is real."""
    result = play(scene, [Press(0, ATTACK), Press(0.5, PICKUP)], 20.0)
    before = play(scene, [Press(0, ATTACK), Press(0.5, PICKUP)], 20.0, instant_moves=True)
    said = lines(result)
    assert way in said
    assert not [line for line in said if any(text in line for text in TIMED_OUT)]
    assert result.kills == [1]
    assert result.alive
    assert result.moved == pytest.approx(before.moved)  # the same step
    assert result.moved >= MOVED
    struck, struck_before = (
        next(at for at, text in found.said if text.startswith('Macro: Echoing Strike')) for found in (result, before)
    )
    stepped = next(at for at, text in result.said if text == way)
    # The first strike waits for the move: it comes later than with the move made in an instant, by
    # about the move's own time.
    assert struck - stepped > 0.3
    assert struck > struck_before + 0.2
    assert result.cleared_at > before.cleared_at


def test_the_step_round_a_wall_is_walked_and_the_monster_killed(monkeypatch):
    sure(monkeypatch)  # the bovine's swings all land: the test is of the walk, not of the fitted chances
    result = play(bovine_behind_a_wall(), [Press(0, PICKUP)], 20.0)
    before = play(bovine_behind_a_wall(), [Press(0, PICKUP)], 20.0, instant_moves=True)
    said = lines(result)
    assert 'Macro: Walking 13 toward a better place' in said
    assert not [line for line in said if any(text in line for text in TIMED_OUT)]
    assert result.kills == [1]
    assert result.moved > before.moved + 2.0  # the way round, not the line through the wall the click was made over
    assert result.cleared_at > before.cleared_at
    # The monster comes for a character it sees walking up; one that is there in an instant has killed it first.
    assert before.taken == 0.0
    assert result.taken > 0.0


def test_the_pickup_step_waits_for_the_walk_to_the_drop():
    result = play(potion_on_the_ground(), [Press(0, PICKUP)], 5.0)
    before = play(potion_on_the_ground(), [Press(0, PICKUP)], 5.0, instant_moves=True)
    assert lines(result) == lines(before)
    assert lines(result)[-1] == 'Macro: a super healing potion: picked up'
    assert result.said[-1][0] >= before.said[-1][0] + 7.0 / RUN_SPEED - 1 / GAME_RATE  # seven units away


def test_ten_plays_with_moves_in_them_are_equal():
    scene = bovine_behind_a_wall()
    scene.drops = potion_on_the_ground().drops
    presses = [Press(0, ATTACK), Press(0.4, PICKUP), Press(1.5, PICKUP), Press(4.0, PICKUP)]
    results = [play(scene, presses, 9.0, osd=PLAYER_HEALING, seed=3) for _ in range(10)]
    assert all(result == results[0] for result in results)
    assert results[0].moved > 10.0
    assert results[0].casts > 0
    warped = [play(one_out_of_reach(), [Press(0, PICKUP)], 6.0, seed=3) for _ in range(10)]
    assert all(result == warped[0] for result in warped)
    assert warped[0].moved > 10.0

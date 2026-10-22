"""hunting/moves.py: the last leg's walk where a Teleport moves nothing, and the hands' time at a drop (2026-10-21,
rca/2026-10-21/priced-act-expired-findings.md)."""

import pytest

from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.macros import teleport
from inventory_tracking.macros.goals import PICK_UP, REACH, Goal
from inventory_tracking.macros.hunting import moves
from inventory_tracking.macros.pursuit import Move
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED, Step
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER
from tests.inventory_tracking.macros.test_hunt import game, hunter, keys, me


AREA = 101


def stairs(at: tuple[float, float], *, passage=None) -> Goal:
    """The way out by stairs marked at `at` (world units), as goals.py `way_out` makes it with no entry known."""
    mark = Target(AREA, (), (at[0] / TILE_UNITS, at[1] / TILE_UNITS), 'Sewers 2', 'stairs', True, passage=passage)
    return Goal('Sewers 2', at, ENTER, 5.0, PRESSED, mark=mark)


@pytest.mark.parametrize('on', [True, False])
def test_a_hop_onto_stairs_from_near_them_is_a_walk_short_of_the_mark(monkeypatch, on):
    # 02:49:37.93 on 2026-10-21: the hop onto Sewers 2's mark from 11.2 away landed 7.1 off (the stairs are no ground),
    # three more from there moved nothing ("priced act expired" x3), then a walk of 4 took the stairs.
    monkeypatch.setattr(moves, 'PASSAGE_WALK', on)
    mark = (12832.5, 5097.5)
    here = (12827.5, 5092.5)
    found = moves.last_leg(stairs(mark), Step(mark, TELEPORT), here, AREA)
    if not on:
        assert found == Step(mark, TELEPORT)
        return
    assert found.skill is None
    assert found.spot == pytest.approx((mark[0] - 3.5 / 2**0.5, mark[1] - 3.5 / 2**0.5))


def test_far_stairs_an_open_passage_and_a_hop_short_of_the_mark_stay_hops():
    mark = (12832.5, 5097.5)
    hop = Step(mark, TELEPORT)
    assert moves.last_leg(stairs(mark), hop, (mark[0] - 30.0, mark[1]), AREA) == hop  # beyond PASSAGE_WALK_UNITS
    passage = stairs(mark, passage=(mark[0] / TILE_UNITS + 1, mark[1] / TILE_UNITS))
    assert passage.crossed
    assert moves.last_leg(passage, hop, (mark[0] - 8.0, mark[1]), AREA) == hop  # walked across by `through`
    short = Step((mark[0] - 4.0, mark[1]), TELEPORT)
    assert moves.last_leg(stairs(mark), short, (mark[0] - 8.0, mark[1]), AREA) == short  # not the last leg


def test_a_door_whose_entry_is_the_goal_is_walked_onto_the_entry_itself():
    mark, entry = (1000.0, 1000.0), (1006.0, 998.5)
    goal = Goal('Crypt', entry, ENTER, 2.0, PRESSED, mark=stairs(mark).mark)
    found = moves.last_leg(goal, Step(entry, TELEPORT), (1012.0, 998.5), AREA)
    assert found == Step(entry)


@pytest.mark.parametrize('on', [True, False])
def test_a_hop_again_at_the_spot_the_last_one_missed_from_its_landing_is_a_walk(monkeypatch, on):
    # 05:00:59.71 on 2026-10-21: a hop aimed at (5759.5, 5593.5) landed 8.1 off; the next from there to the same spot
    # moved nothing and the act ran out 1.4 s later. 33 of 48 such hops within 10 did the same on 2026-10-20/21.
    monkeypatch.setattr(moves, 'REHOP_WALK', on)
    aim, landed = (5759.5, 5593.5), (5767.5, 5594.5)
    monkeypatch.setattr(teleport, 'MISSED', [(aim, landed, AREA)])
    room = Goal('full clear: a group of 20', aim, REACH, 5.0, PRESSED)
    found = moves.last_leg(room, Step(aim, TELEPORT), landed, AREA)
    assert found == (Step(aim) if on else Step(aim, TELEPORT))


def test_a_hop_the_last_miss_says_nothing_of_stays_a_hop(monkeypatch):
    aim, landed = (5759.5, 5593.5), (5767.5, 5594.5)
    room = Goal('full clear: a group of 20', aim, REACH, 5.0, PRESSED)
    hop = Step(aim, TELEPORT)
    monkeypatch.setattr(teleport, 'MISSED', [(aim, landed, AREA)])
    assert moves.last_leg(room, hop, (5770.0, 5600.0), AREA) == hop  # not where that hop landed
    assert moves.last_leg(room, hop, landed, AREA + 1) == hop  # another level
    other = Step((aim[0] - 3.0, aim[1]), TELEPORT)
    assert moves.last_leg(room, other, landed, AREA) == other  # another spot
    far = (aim[0] + 20.0, aim[1])
    monkeypatch.setattr(teleport, 'MISSED', [(aim, far, AREA)])
    assert moves.last_leg(room, hop, far, AREA) == hop  # 20 away: such hops land (35 of 35 beyond 10)
    monkeypatch.setattr(teleport, 'MISSED', [])
    assert moves.last_leg(room, hop, landed, AREA) == hop


def test_the_pursuits_hop_onto_near_stairs_is_made_as_a_walk(monkeypatch):
    monkeypatch.setattr(moves, 'PASSAGE_WALK', True)
    play = game()
    play.staff = None
    hunt = hunter(play)
    run = play.run()
    here = me(play.world)
    mark = (here.x + 8.0, here.y)
    goal = stairs(mark)
    hunt.advance(run, play.world, Ground(()), Move(Step(mark, TELEPORT), goal), goal.place, keys)
    assert 't' not in play.pressed()
    assert play.walks == [pytest.approx((mark[0] - 3.5, mark[1]), abs=1.0)]


@pytest.mark.parametrize('on', [True, False])
def test_the_hands_at_a_drop_are_given_the_way_there(monkeypatch, on):
    # 05:13:18.83 on 2026-10-21: "Going for 7193 gold, 20 away", a Blade Warp of 1.09 s, the click made at 20.344 and
    # the act's 1.5 s ran out at 20.345; two such run-outs give a drop up.
    monkeypatch.setattr(moves, 'PICK_WALK_PRICED', on)
    gold = Goal('7193 gold', (7581.0, 5105.0), PICK_UP, 2.0, PRESSED, unit=7)
    window = moves.hands_window(1.5, (7561.5, 5101.5), gold)
    if not on:
        assert window == 1.5
        return
    assert window == pytest.approx(1.5 + 19.9 / moves.RUN_SPEED + moves.STILL_SECONDS, abs=0.01)
    assert moves.hands_window(1.5, (7481.0, 5105.0), gold) == 1.5 + moves.PICK_WALK_MOST  # bounded
    seal = Goal('seal', (7581.0, 5105.0), REACH, 2.0, PRESSED)
    assert moves.hands_window(1.5, (7561.5, 5101.5), seal) == moves.operate_window(1.5, (7561.5, 5101.5), seal)


@pytest.mark.parametrize('on', [True, False])
def test_a_level_runs_walk_onto_its_way_out_that_does_not_move_ends_the_run_at_the_door(monkeypatch, on):
    # 23:18:59-23:19:45 on 2026-10-21 (rca/2026-10-21/tower-stall-findings.md): the Forgotten Tower's way back to the
    # Black Marsh in the wall, the character 3.0 from it on the nearest ground, "no move toward Black Marsh: the
    # character did not move" x16 until the 45 s still watchdog left the game. The run ends there: the press clicks
    # the door
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.hunting.base import Judged
    from inventory_tracking.macros.pursuit import FULL, Pursuit

    monkeypatch.setattr(moves, 'DOOR_WALK_PRESS', on)
    play = game()
    hunt = hunter(play)
    posted = Pursuit('pickup', 0.0, advance=False, leash=FULL, area=AREA)
    hunt.post(posted)
    here = me(play.world)
    goal = stairs((here.x - 3.0, here.y))
    walk = Move(Step(goal.place), goal)
    monkeypatch.setattr(hunt, 'judge', lambda *args, **kwargs: Judged(walk, goal, goal.place, posted))

    def stuck(*args, **kwargs):
        raise Abort('the character did not move')

    monkeypatch.setattr(hunt, 'advance', stuck)
    ended: list[str] = []
    hunt.run_over = ended.append
    hunt.pursue(play.run(), play.world, [], Ground(()), keys, in_reach=False)
    if not on:
        assert ended == []
        assert hunt.pursuit is posted  # the run goes on: the walk again at the next look
        return
    assert len(ended) == 1
    assert ended[0].endswith('going through takes a press')
    assert 'Sewers 2, 3.0 away' in ended[0]
    assert hunt.ended_area == AREA


def test_a_stuck_move_far_from_the_door_or_across_an_open_passage_does_not_end_the_run():
    from inventory_tracking.macros.actuator import Abort

    here = (5000.0, 5000.0)
    near = stairs((here[0] - 3.0, here[1]))
    stop = Abort('the character did not move')
    assert moves.door_stuck(Move(Step(near.place), near), here, True, stop)
    assert not moves.door_stuck(Move(Step(near.place), near), here, False, stop)  # not a level run (a press)
    far = stairs((here[0] - 20.0, here[1]))
    assert not moves.door_stuck(Move(Step(far.place), far), here, True, stop)  # beyond ENTRY_REACH
    passage = stairs((here[0] - 3.0, here[1]), passage=(here[0] / TILE_UNITS - 1, here[1] / TILE_UNITS))
    assert not moves.door_stuck(Move(Step(passage.place), passage), here, True, stop)  # walked across (`through`)
    other = Abort('Teleport: the casting delay')
    assert not moves.door_stuck(Move(Step(near.place), near), here, True, other)

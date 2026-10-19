"""Echoing Strike's emulation (mechanics.py, hits.py) against one recorded cast (fixtures/cast_706.json:
42 frames of the second Chaos Sanctuary take, 2026-10-09, trimmed to the player, the pointer and
the five blades)."""

import copy
import json
import math
from pathlib import Path

from inventory_tracking.builds.warlock.echoing_strike.hits import full_casts
from inventory_tracking.builds.warlock.echoing_strike.mechanics import (
    LIFE,
    OUT_FRAMES,
    RANGE,
    cast,
    errors,
    focal_point,
)


FIXTURE = json.loads((Path(__file__).parent / 'fixtures' / 'cast_706.json').read_text())


def test_the_blades_spawn_ahead_converge_at_the_focal_point_turn_at_the_range_and_come_home():
    origin, focal = (5000.0, 5000.0), (5000.0, 5012.0)
    blades = cast(origin, focal, lambda frame: origin)
    assert len(blades) == 5
    starts = [b[0] for b in blades]
    assert all(abs(y - 5000.8) < 1e-9 for _, y in starts)  # AHEAD along the aim
    assert [round(x - 5000.0, 2) for x, _ in starts] == [1.9, 0.95, 0.0, -0.95, -1.9]  # across (left to right)
    at_focal = [min(math.dist(p, focal) for p in b) for b in blades]
    assert max(at_focal) < 0.6
    furthest = [max(math.dist(p, origin) for p in b) for b in blades]
    assert all(abs(f - RANGE) < 0.5 for f in furthest)  # the outer blades fly a little slanted
    assert all(math.dist(b[OUT_FRAMES], origin) == max(math.dist(p, origin) for p in b) for b in blades)
    assert all(len(b) == LIFE for b in blades)  # the return takes the whole life: they vanish beside the caster
    assert all(math.dist(b[-1], origin) < 2.0 for b in blades)


def test_the_focal_point_of_recorded_blades_is_where_they_converge():
    frames = FIXTURE['frames']
    (_, blades), *_ = full_casts(frames)
    focal = focal_point(blades)
    origin = (frames[8]['p'][3], frames[8]['p'][4])  # the cast frame: eight frames of pointer lead the fixture
    assert 8 < math.dist(focal, origin) < 20
    nearest = [min(math.dist(p, focal) for p in b[:OUT_FRAMES]) for b in blades]
    assert max(nearest) < 1.5


def test_the_emulation_follows_the_recorded_cast_within_a_unit_or_two():
    frames = FIXTURE['frames']
    (n, blades), *_ = full_casts(frames)
    by_n = {f['n']: f for f in frames}
    origin = (by_n[n]['p'][3], by_n[n]['p'][4])

    def player_at(k):
        later = by_n.get(n + k)
        return (later['p'][3], later['p'][4]) if later and later['p'] else origin

    out, back = errors(blades, origin, focal_point(blades), player_at)
    assert out < 1.3
    assert back < 2.5


def test_a_blade_stops_at_a_wall_and_does_not_come_back():
    origin, focal = (5000.0, 5000.0), (5000.0, 5012.0)
    free = cast(origin, focal, lambda frame: origin)
    walled = cast(origin, focal, lambda frame: origin, blocked=lambda p: p[1] >= 5010.0)
    assert all(len(b) == LIFE for b in free)
    assert all(len(b) < 10 for b in walled)  # about nine units of flight before the wall
    assert all(max(p[1] for p in b) < 5010.0 for b in walled)


def test_a_blade_does_not_step_over_a_wall_one_cell_thick():
    # Catacombs 3, 2026-10-10 21:43: a blade flies 1.12 units a frame, and frame positions alone
    # missed a wall one cell deep, so the fight aimed at a monster behind it.
    origin, focal = (5000.5, 5000.5), (5000.5, 5015.5)
    for wall in (5005, 5006, 5007, 5008, 5009):
        thin = cast(origin, focal, lambda frame: origin, blocked=lambda p, wall=wall: int(p[1]) == wall)
        assert all(point[1] < wall for path in thin for point in path), wall


def test_a_missile_whose_path_was_not_read_in_a_frame_is_left_out_of_that_frame():
    """Four of the 129,466 missile rows of the take 20261011T231408Z-39 hold an empty path (a read that failed):
    the gate over every take ended there with a struct.error (2026-10-12)."""
    frames = copy.deepcopy(FIXTURE['frames'])
    (_, whole), *_ = full_casts(frames)
    unread = next(frame for frame in frames[12:] if frame.get('x'))
    unread['x'][0][5] = ''
    (_, blades), *_ = full_casts(frames)
    assert sorted(len(blade) for blade in blades) == sorted([len(whole[0]) - 1, *(len(blade) for blade in whole[1:])])

"""The moments chosen blind to the outcome: the times, the fight at them, the spread."""

from pathlib import Path
from typing import Any

from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.world import NO_OWNER
from tests.inventory_tracking.scenarios.arena.fixed import fixed, spread, strides


def frame(
    t: float, *, life: int | None = 1000, mode: int = 1, hostile: int = 3, far: int = 0, ally: int = 0
) -> dict[str, Any]:
    """The character at the origin; `hostile` monsters 10 units off, `far` 100 units off, `ally` allied."""
    player: list[Any] = [1, mode, 1, 0.0, 0.0, None, None, life, None if life is None else 1200, None, None]
    near = [[100 + i, 1, 8, 10.0, 0.0, 128, 128, 0, NO_OWNER, 0] for i in range(hostile)]
    away = [[200 + i, 1, 8, 100.0, 0.0, 128, 128, 0, NO_OWNER, 0] for i in range(far)]
    friends = [[300 + i, 1, 8, 5.0, 0.0, 128, 128, 0, NO_OWNER, 1] for i in range(ally)]
    return {'t': t, 'p': player, 'm': near + away + friends}


def take(frames: list[dict[str, Any]]) -> Take:
    return Take(directory=Path('x'), manifest={'schema': 2}, frames=frames)


def second_by_second(count: int, **kwargs: Any) -> list[dict[str, Any]]:
    return [frame(100.0 + i, **kwargs) for i in range(count)]


def test_the_times_are_a_grid_and_each_is_the_frame_at_it():
    found = fixed(take(second_by_second(60)))
    assert [(m.kind, m.at, m.frame) for m in found] == [('fixed', 5.0, 5), ('fixed', 25.0, 25), ('fixed', 45.0, 45)]
    assert found[0].note == '3 hostiles within 30, life 1000/1200'
    assert [m.at for m in fixed(take(second_by_second(60)), every=10.0, offset=0.0)] == [
        0.0,
        10.0,
        20.0,
        30.0,
        40.0,
        50.0,
    ]
    # Between two frames it is the earlier one; a pause of the recorder leaves no frame at the time.
    frames = [frame(0.0), frame(4.5), frame(7.0), frame(26.0)]
    assert [(m.at, m.frame) for m in fixed(take(frames))] == [(5.0, 1)]


def test_only_a_frame_of_a_fight_counts():
    def kept(**kwargs: Any) -> int:
        return len(fixed(take(second_by_second(10, **kwargs))))

    assert kept() == 1
    assert kept(hostile=2) == 0
    assert kept(hostile=2, far=5) == 0  # beyond the reach
    assert kept(hostile=2, ally=5) == 0  # allies are not hostiles
    assert kept(life=None) == 0  # vitals not read
    assert kept(life=0) == 0
    assert kept(mode=17) == 0  # dead mode
    assert len(fixed(take(second_by_second(10, hostile=2, far=5)), reach=200.0)) == 1


def test_nothing_after_the_frame_is_read():
    frames = second_by_second(70)
    whole = fixed(take(frames))
    assert [m.at for m in whole] == [5.0, 25.0, 45.0, 65.0]
    # The take cut short at a moment's frame gives the moments up to it; a rewritten future (a death, an empty
    # screen) leaves the earlier ones alone.
    for cut in (25, 45, 65):
        assert fixed(take(frames[: cut + 1])) == [m for m in whole if m.at <= cut]
    future = [frame(100.0 + i, life=0 if i > 30 else 1000, hostile=0 if i > 30 else 3) for i in range(70)]
    assert fixed(take(future))[:2] == whole[:2]


def test_spread_takes_the_middle_ones_evenly():
    assert spread(9, 2) == [2, 5]  # the 3rd and the 6th
    assert spread(9, 1) == [3]
    assert spread(3, 5) == [0, 1, 2]
    assert spread(5, 0) == []
    assert strides(80, 40) == [1 + 2 * i for i in range(40)]
    assert strides(3, 5) == [0, 1, 2]
    picked = strides(754, 40)
    assert len(set(picked)) == 40
    assert picked[0] < 754 // 40
    assert picked[-1] >= 754 - 754 // 40

"""The rules that find the moments of a take: each kind, its limits, merging and placement."""

from pathlib import Path
from typing import Any

from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.game.layout import NO_OWNER
from tests.inventory_tracking.scenarios.arena.moments import Moment, moments


def frame(
    t: float,
    *,
    life: int | None = None,
    max_life: int | None = None,
    mode: int = 1,
    hostile: tuple[tuple[float, float], ...] = (),
    vitals: bool = True,
) -> dict[str, Any]:
    """A frame with the character at the origin (`p`) and monsters at `hostile` (`m`)."""
    player: list[Any] = [1, mode, 1, 0.0, 0.0]
    if vitals:
        player += [None, None, life, max_life, None, None]
    monsters = [[100 + i, 1, 8, x, y, 128, 128, 0, NO_OWNER, 0] for i, (x, y) in enumerate(hostile)]
    return {'t': t, 'p': player, 'm': monsters}


def lives(values: list[int], *, max_life: int = 1000, step: float = 1.0) -> list[dict[str, Any]]:
    return [frame(i * step, life=life, max_life=max_life) for i, life in enumerate(values)]


def keys(t: float, *down: int) -> dict[str, Any]:
    return {'t': t, 'event': 'keys', 'down': list(down)}


def take(
    frames: list[dict[str, Any]], events: list[dict[str, Any]] | None = None, manifest: dict[str, Any] | None = None
) -> Take:
    return Take(
        directory=Path('x'),
        manifest={'schema': 2} if manifest is None else manifest,
        frames=frames,
        events=events or [],
    )


def of_kind(found: list[Moment], kind: str) -> list[Moment]:
    return [m for m in found if m.kind == kind]


BELT = frozenset({101, 102})
HOSTILE_NEAR = ((10.0, 0.0),)


def test_death_by_mode_is_placed_lead_before() -> None:
    frames = [frame(float(t), mode=17 if t == 10 else 1, vitals=False) for t in range(11)]
    found = moments(take(frames, manifest={}))
    assert found == [Moment(frame=7, kind='death', at=10.0, note='dead at 10.0 s')]


def test_death_by_life_zero_is_the_first_dead_frame() -> None:
    found = moments(take(lives([100, 100, 100, 100, 100, 0, 0])))
    assert of_kind(found, 'death') == [Moment(frame=2, kind='death', at=5.0, note='dead at 5.0 s')]


def test_burst_is_placed_lead_before_the_drop() -> None:
    found = moments(take(lives([1000] * 6 + [500] * 5)))
    assert found == [
        Moment(frame=3, kind='burst', at=6.0, note='life 1000 -> 500 of 1000 within 1.00 s'),
    ]


def test_burst_just_under_the_share_is_none() -> None:
    assert moments(take(lives([1000] * 5 + [701] * 5))) == []


def test_burst_spread_over_more_than_the_window_is_none() -> None:
    frames = [frame(0.0, life=1000, max_life=1000), frame(1.2, life=500, max_life=1000)]
    assert moments(take(frames)) == []


def test_bursts_two_seconds_apart_merge_and_six_apart_stay_two() -> None:
    merged = moments(take(lives([1000] * 4 + [500] + [1000] + [500] * 6)))
    assert of_kind(merged, 'burst') == [
        Moment(frame=1, kind='burst', at=4.0, note='life 1000 -> 500 of 1000 within 1.00 s'),
    ]
    apart = moments(take(lives([1000] * 4 + [500] + [1000] * 5 + [500] * 2)))
    assert of_kind(apart, 'burst') == [
        Moment(frame=1, kind='burst', at=4.0, note='life 1000 -> 500 of 1000 within 1.00 s'),
        Moment(frame=7, kind='burst', at=10.0, note='life 1000 -> 500 of 1000 within 1.00 s'),
    ]


def test_potions_with_no_belt_keys_are_none() -> None:
    frames = [frame(float(t)) for t in range(11)]
    events = [keys(6.0, 101), keys(7.0, 101), keys(8.0, 101)]
    assert moments(take(frames, events)) == []


def test_potions_are_placed_at_the_first_key_of_the_run() -> None:
    frames = [frame(float(t)) for t in range(11)]
    events = [keys(6.0, 101), keys(7.0, 101), keys(8.0, 101)]
    found = moments(take(frames, events), belt_keys=BELT)
    assert found == [Moment(frame=3, kind='potions', at=6.0, note='3 potions within 2.0 s')]


def test_potions_ignore_other_keys_and_release_only_events() -> None:
    frames = [frame(float(t)) for t in range(11)]
    events = [
        keys(2.0, 101, 999),
        keys(3.0, 999),
        keys(4.0, 101, 999),
        {'t': 4.5, 'event': 'keys', 'up': [101]},
        keys(5.0, 102),
    ]
    found = moments(take(frames, events), belt_keys=BELT)
    assert found == [Moment(frame=0, kind='potions', at=2.0, note='3 potions within 3.0 s')]


def test_long_fight_broken_by_a_1_5_second_gap_is_none() -> None:
    times = [float(t) for t in range(13)] + [13.5 + i for i in range(13)]
    frames = [frame(t, hostile=HOSTILE_NEAR) for t in times]
    assert moments(take(frames)) == []


def test_long_fight_of_exactly_20_seconds_is_placed_at_its_start() -> None:
    frames = [frame(float(t), hostile=HOSTILE_NEAR if 5 <= t <= 25 else ()) for t in range(31)]
    found = moments(take(frames))
    assert found == [Moment(frame=5, kind='long', at=5.0, note='hostiles within 30 for 20.0 s')]


def test_take_without_life_values_gives_no_burst() -> None:
    frames = [frame(float(t), vitals=False) for t in range(11)]
    assert moments(take(frames, manifest={})) == []


def test_lead_is_clamped_to_the_first_frame() -> None:
    frames = [frame(100.0), frame(101.0, mode=17, vitals=False)]
    found = moments(take(frames, manifest={}))
    assert found == [Moment(frame=0, kind='death', at=1.0, note='dead at 1.0 s')]


def test_result_is_sorted_by_time_then_kind() -> None:
    frames = [frame(float(t), mode=17 if t == 14 else 1, vitals=False) for t in range(15)]
    events = [keys(2.0, 101), keys(3.0, 101), keys(4.0, 101), keys(14.0, 101), keys(15.0, 101), keys(16.0, 101)]
    found = moments(take(frames, events, manifest={}), belt_keys=BELT)
    assert found == [
        Moment(frame=0, kind='potions', at=2.0, note='3 potions within 2.0 s'),
        Moment(frame=11, kind='death', at=14.0, note='dead at 14.0 s'),
        Moment(frame=11, kind='potions', at=14.0, note='3 potions within 2.0 s'),
    ]


def test_a_frame_whose_vitals_were_not_read_is_not_a_death():
    """Life 0 of 0 is a failed read (takes of 2026-10-11 and 12 hold such frames), the character alive in mode 1."""
    frames = [frame(0.0, life=1500, max_life=1800), frame(1.0, life=0, max_life=0)]
    assert [m.kind for m in moments(take(frames))] == []


def test_a_take_that_opens_on_the_corpse_holds_no_death():
    """The walk back to the body (20261011T195359Z-25): dead mode from the first frame on."""
    frames = [frame(0.0, life=0, max_life=0, mode=17), frame(1.0, life=0, max_life=0, mode=17)]
    assert [m.kind for m in moments(take(frames))] == []


def test_a_lighter_share_finds_a_lighter_burst():
    frames = lives([1000, 800])
    assert [m.kind for m in moments(take(frames))] == []
    assert [m.kind for m in moments(take(frames), burst_share=0.15)] == ['burst']

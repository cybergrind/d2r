"""The loop's bound legs (macros/running/legs.py)."""

from types import SimpleNamespace

from inventory_tracking.macros.agenda import COVER, TRANSIT, ZONE_LEFT
from inventory_tracking.macros.running import legs
from inventory_tracking.macros.tzroutine import itinerary


SPIDER_FOREST, ARACHNID_LAIR, SPIDER_CAVERN = 76, 84, 85


def runner(terrorized: bool | None) -> SimpleNamespace:
    plan = itinerary(frozenset((SPIDER_FOREST, ARACHNID_LAIR, SPIDER_CAVERN)))
    loop = SimpleNamespace(agenda=SimpleNamespace(plan=plan, finished=set()), kind=SimpleNamespace(full_clear=False))
    return SimpleNamespace(loop=loop, progress=SimpleNamespace(wanted=lambda _: terrorized))


def test_a_level_the_zone_left_under_the_run_ends_it() -> None:
    """23:30 on 2026-10-19: the zone went to Dry Hills while Spider Forest was explored for 1.5 min more."""
    assert legs._agenda_policy(runner(True), SPIDER_FOREST) == COVER  # type: ignore[arg-type]
    assert legs._agenda_policy(runner(False), SPIDER_FOREST) == ZONE_LEFT  # type: ignore[arg-type]


def test_a_level_crossed_on_the_way_is_never_a_zone_left() -> None:
    # Not in the plan's zone (crossed, never terrorized): TRANSIT as before
    assert legs._agenda_policy(runner(False), 1) == TRANSIT  # type: ignore[arg-type]


def test_an_unread_zone_leaves_the_plan_to_decide() -> None:
    assert legs._agenda_policy(runner(None), SPIDER_FOREST) == COVER  # type: ignore[arg-type]

"""The loop's bound legs (macros/running/legs.py)."""

import time
from types import SimpleNamespace

from inventory_tracking.macros import zonenav
from inventory_tracking.macros.agenda import PLUS, SKIPPED, TRANSIT, ZONE_LEFT
from inventory_tracking.macros.experience import Ledger
from inventory_tracking.macros.running import legs
from inventory_tracking.macros.tzroutine import itinerary


SPIDER_FOREST, ARACHNID_LAIR, SPIDER_CAVERN = 76, 84, 85


def runner(terrorized: bool | None, stalled: float | None = None) -> SimpleNamespace:
    plan = itinerary(frozenset((SPIDER_FOREST, ARACHNID_LAIR, SPIDER_CAVERN)))
    agenda = SimpleNamespace(plan=plan, finished=set(), blocked={}, bosses=SimpleNamespace(alive_in=lambda area: []))
    # The watchdog's clock (loop.py `progressed`): `stalled` seconds with no progress on Spider Forest, None not known
    progressed = None if stalled is None else ('g', time.monotonic() - stalled, (0, 0, 0, SPIDER_FOREST))
    loop = SimpleNamespace(
        agenda=agenda,
        kind=SimpleNamespace(full_clear=False),
        on=True,
        progressed=progressed,
        cooling=0.0,
        abandon=False,
        experience=Ledger(),
    )
    return SimpleNamespace(loop=loop, progress=SimpleNamespace(wanted=lambda _: terrorized), valuable_left=lambda: None)


def test_a_level_the_zone_left_under_the_run_ends_it() -> None:
    """23:30 on 2026-10-19: the zone went to Dry Hills while Spider Forest was explored for 1.5 min more."""
    # Worked as the level's policy says (TZ+ since 2026-10-20: COVER's rooms, a big level's big groups)
    assert legs._agenda_policy(runner(True), SPIDER_FOREST) == PLUS  # type: ignore[arg-type]
    assert legs._agenda_policy(runner(False), SPIDER_FOREST) == ZONE_LEFT  # type: ignore[arg-type]


def test_a_level_crossed_on_the_way_is_never_a_zone_left() -> None:
    # Not in the plan's zone (crossed, never terrorized): TRANSIT as before
    assert legs._agenda_policy(runner(False), 1) == TRANSIT  # type: ignore[arg-type]


def test_an_unread_zone_leaves_the_plan_to_decide() -> None:
    assert legs._agenda_policy(runner(None), SPIDER_FOREST) == PLUS  # type: ignore[arg-type]


def test_a_level_with_no_progress_is_skipped_by_its_policy_only_under_the_switch(monkeypatch) -> None:
    # zonenav.py STALLED_SKIP (rca/2026-10-23/exp-hour-levels-findings.md): the run ends, the zone goes on
    monkeypatch.setattr(zonenav, 'ROTATION', True)  # the rotation played by the zone's graph, as served
    monkeypatch.setattr(zonenav, 'STALLED_SKIP', False)
    assert legs._agenda_policy(runner(True, stalled=120.0), SPIDER_FOREST) == PLUS  # type: ignore[arg-type]
    monkeypatch.setattr(zonenav, 'STALLED_SKIP', True)
    assert legs._agenda_policy(runner(True, stalled=30.0), SPIDER_FOREST) == PLUS  # type: ignore[arg-type]
    skipped = runner(True, stalled=120.0)
    assert legs._agenda_policy(skipped, SPIDER_FOREST) == SKIPPED  # type: ignore[arg-type]
    assert skipped.loop.agenda.blocked[SPIDER_FOREST].startswith('skipped: no kill and no level done for 120 s')
    assert legs._agenda_policy(runner(False, stalled=120.0), SPIDER_FOREST) == ZONE_LEFT  # type: ignore[arg-type]

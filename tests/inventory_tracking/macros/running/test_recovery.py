"""The room rules' trip for a field item the cube can make no room for (macros/running/recovery.py `_field_trip`,
loot/api.py FIELD_AT_ONCE). The player, 2026-10-20 ~14:58: "we need to optimize space (move to cube) and identify items
during games / if we have no room for optimization to keep picking up items - we need to do town routine"."""

import logging
import threading
from pathlib import Path

import pytest

from inventory_tracking.macros.loop import ANDARIEL, TRIPS_A_GAME, TZ
from inventory_tracking.macros.runner import MacroRunner


GAME = 'cyberg4'
KRISS = 'rare Kriss'


def runner(kind=TZ, *, on: bool = True, carrying: bool = True, area: int | None = 63) -> MacroRunner:
    found = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda lines: None,
        place=lambda: (GAME, 63),
    )  # fmt: skip
    found.loop.on, found.loop.kind, found.loop.carrying = on, kind, carrying
    found.loop.seen = (GAME, 0.0)
    found.area_seen = area
    found.attack_mode, found.working = True, True
    return found


def test_a_terror_zone_kind_pushes_the_room_package_and_ends_the_level_run(caplog):
    found = runner()
    with caplog.at_level(logging.INFO):
        assert found._field_trip(KRISS)
    assert found.loop.trips_in(GAME) == 1  # the trip's bookkeeping (tzloop.py `trip`)
    assert found.loop.agenda.package() is not None
    assert not found.attack_mode
    assert found.cancelled.is_set()
    assert found.stand_answered > 0  # watch.py `stood_after_cube` stays the backstop only
    assert "rare Kriss lies on the ground with no room in the inventory or the cube: a trip to town for room (the " \
           "agenda's package)" in caplog.text  # fmt: skip


def test_the_andariel_kind_takes_its_trip_and_back_through_the_portal():
    found = runner(ANDARIEL)
    assert found._field_trip(KRISS)
    assert found.loop.trip_due


@pytest.mark.parametrize(
    ('why', 'changes'),
    [('the loop off', {'on': False}), ('nothing a visit takes away', {'carrying': False})],
)
def test_no_trip_is_made_when_the_room_rules_would_make_none(why, changes):
    found = runner(**changes)
    assert not found._field_trip(KRISS), why
    assert not found.cancelled.is_set(), why
    assert found.attack_mode, why


def test_the_trips_of_a_game_are_bounded():
    found = runner(ANDARIEL)
    for _ in range(TRIPS_A_GAME):
        found.loop.begin_trip(GAME)
    assert not found.loop.may_trip(GAME)
    assert not found._field_trip(KRISS)
    assert not found.loop.trip_due

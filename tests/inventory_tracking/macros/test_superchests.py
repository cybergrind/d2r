"""The super chests a level run opens (macros/superchests.py; rca/2026-10-20/superchest-findings.md)."""

from inventory_tracking.game.records import Thing
from inventory_tracking.levels.model import SUPER_CHEST, UNIQUE_CHEST, Room
from inventory_tracking.macros import superchests
from inventory_tracking.macros.superchests import is_super, mark_use, super_chests, unique_spots


LAIR = 505  # Act 2 - Lair Treasure W, one layout: PlaceUniqueChest at (35, 21) and (26, 34) units from its origin
SPOTS = frozenset(((4980 + 35, 5020 + 21), (4980 + 26, 5020 + 34)))


def test_a_presets_spots_come_once_from_its_origin_whatever_its_chunks():
    whole = Room(LAIR, 996, 1004, 10, 10, 0, (996, 1004, 10, 10))
    chunks = (Room(LAIR, 996, 1004, 8, 8, 0, (996, 1004, 10, 10)), Room(LAIR, 1004, 1004, 2, 8, 0, (996, 1004, 10, 10)))
    assert unique_spots((whole,)) == SPOTS
    assert unique_spots(chunks) == SPOTS
    assert unique_spots((Room(1, 996, 1004, 8, 8),)) == frozenset()  # a preset with no unique chest


def test_the_glowing_chests_and_a_container_at_a_spot_are_super_chests_and_a_plain_one_is_not(monkeypatch):
    spot = next(iter(SPOTS))
    rolled = Thing(1, 88, 0, *spot)  # TombChest2, the Maggot Lair's
    off = Thing(2, 88, 0, spot[0] + 5.0, spot[1])
    glowing, special = Thing(3, SUPER_CHEST, 0, 0.0, 0.0), Thing(4, 455, 0, 0.0, 0.0)
    assert [is_super(t, SPOTS) for t in (rolled, off, glowing, special)] == [True, False, True, True]
    rooms = (Room(LAIR, 996, 1004, 10, 10, 0, (996, 1004, 10, 10)),)
    assert super_chests((rolled, off, glowing), rooms) == [rolled, glowing]
    assert (mark_use(glowing), mark_use(rolled), mark_use(None)) == (SUPER_CHEST, UNIQUE_CHEST, UNIQUE_CHEST)
    monkeypatch.setattr(superchests, 'ENABLED', False)  # the switch off: the 397 one alone, as before 2026-10-20
    assert super_chests((rolled, off, glowing, special), rooms) == [glowing]
    assert mark_use(None) == SUPER_CHEST


def test_the_glowing_chests_are_the_data_rows_with_an_overlay_over_a_chests_drops():
    import json
    from pathlib import Path

    from inventory_tracking.game.decode import glowing_chests
    from inventory_tracking.macros.superchests import GLOWING, build_glowing

    source = Path(__file__).parents[3] / 'third-parties' / 'd2data' / 'json' / 'objects.json'
    if source.exists():
        rows = json.loads(source.read_text())
        assert build_glowing(rows.values() if isinstance(rows, dict) else rows) == glowing_chests()
    # ConsolationChest, SpecialChest100, the Horadric Cube's, Scroll's, Staff of Kings', Khalim's three
    assert frozenset((354, 355, 356, 397, 405, 406, 407, 455)) == GLOWING


def test_the_super_tries_are_the_hunts():
    from inventory_tracking.macros.hunting.base import SUPER_TRIES

    assert SUPER_TRIES == superchests.SUPER_TRIES


def level_goal_at(here, things=(), tries=None, passed=lambda place, unit: False, now=0.0, book=None):
    from inventory_tracking.macros.superchests import Book, level_goal
    from inventory_tracking.macros.travel import PRESSED

    rooms = (Room(LAIR, 996, 1004, 10, 10, 0, (996, 1004, 10, 10)),)
    book = book if book is not None else Book()
    return level_goal('g', 64, here, rooms, things, tries or {}, passed, now, PRESSED, book=book), book


def test_each_spot_is_left_once_opened_tried_out_passed_or_out_of_time():
    from inventory_tracking.macros.superchests import SPOT_SECONDS, SUPER_TRIES

    near, far = sorted(SPOTS, key=lambda spot: spot[1])  # (5015, 5041) first from the north
    here = (5000.0, 4900.0)
    goal, book = level_goal_at(here)
    assert goal is not None
    assert goal.place == near
    chest = Thing(7, 88, 0, *near)
    goal, _ = level_goal_at(here, (replace_mode(chest, 2),), book=book)
    assert goal is not None
    assert goal.place == far  # the near one is open
    goal, _ = level_goal_at(here, (Thing(8, 87, 0, *far),), tries={8: SUPER_TRIES}, book=book)
    assert goal is None  # the far one tried out: none left
    goal, _ = level_goal_at(here, passed=lambda place, unit: place == near)
    assert goal is not None
    assert goal.place == far
    goal, book = level_goal_at(here, now=0.0)
    assert goal is not None
    goal, _ = level_goal_at(here, now=SPOT_SECONDS + 1.0, book=book)
    assert goal is not None
    assert goal.place == far  # the first one gone for too long: left
    level_goal_at(here, book=book)
    book.begin('another game')
    assert not book.done


def replace_mode(thing, mode):
    from dataclasses import replace

    return replace(thing, mode=mode)

"""One colour per POI kind, shared by arrow rows, arrows and map dots (user, 2026-09-30):
next level green, previous level purple, waypoint blue, POI (boss, chest, rune, shrine) bright yellow."""

import pytest

from inventory_tracking.levels.geometry import Pointer
from inventory_tracking.levels.guide import pointer_lines
from inventory_tracking.levels.registry import handler_for
from inventory_tracking.osd.level_map import KIND_COLOURS, KIND_TONES
from inventory_tracking.presentation import Tone, tone_rgb


def test_arrow_rows_take_the_tone_of_their_kind():
    pointers = [
        Pointer('Next level', None, 10, 0, kind='stairs'),
        Pointer('Barracks', None, 0, 10, kind='previous'),
        Pointer('Waypoint', None, 5, 5, here=True, kind='waypoint'),
        Pointer('Summoner', None, -5, 0),
    ]

    assert [line.tone for line in pointer_lines(pointers)] == [
        Tone.LEVEL_NEXT,
        Tone.LEVEL_PREVIOUS,
        Tone.WAYPOINT,
        Tone.POI,
    ]


def test_map_dots_use_the_row_colours():
    assert KIND_TONES == {
        'stairs': Tone.LEVEL_NEXT,
        'previous': Tone.LEVEL_PREVIOUS,
        'waypoint': Tone.WAYPOINT,
        'target': Tone.POI,
        'exit': Tone.EXIT,  # an exit whose destination is not known yet
        'herald': Tone.HERALD,  # a live Terror Zone Herald
        'mob': Tone.MOB,  # a hostile monster alive
        'leader': Tone.MOB_LEADER,  # a unique, champion or super unique alive
        'danger': Tone.MOB_DANGER,  # a monster of a deadly pack
        'caution': Tone.MOB_CAUTION,  # a monster of a pack to be careful with
        'pack': Tone.MOB_DANGER,  # a deadly pack's centre: only a ground arrow
    }
    assert {kind: tone_rgb(tone) for kind, tone in KIND_TONES.items()} == KIND_COLOURS


def test_the_colours_are_green_purple_blue_and_bright_yellow():
    r, g, b = tone_rgb(Tone.LEVEL_NEXT)
    assert g > max(r, b) + 0.3
    r, g, b = tone_rgb(Tone.LEVEL_PREVIOUS)
    assert min(r, b) > g + 0.2
    r, g, b = tone_rgb(Tone.WAYPOINT)
    assert b > max(r, g) + 0.2
    r, g, b = tone_rgb(Tone.POI)
    assert min(r, g) > 0.9 > 0.4 > b


@pytest.mark.parametrize(
    ('area', 'label'),
    [(6, 'Forgotten Tower'), (7, 'Pit'), (41, 'Stony Tomb'), (31, 'Inner Cloister'), (122, 'Next level')],
)
def test_level_entrances_are_the_next_level(area, label):
    [spec] = [s for s in handler_for(area).pois if s.label == label]

    assert spec.kind == 'stairs'


@pytest.mark.parametrize(
    ('area', 'label'), [(74, 'Summoner'), (124, 'Nihlathak'), (59, 'Treasure'), (59, 'Creeping Feature')]
)
def test_bosses_and_chests_are_pois(area, label):
    [spec] = [s for s in handler_for(area).pois if s.label == label]

    assert spec.kind == 'target'

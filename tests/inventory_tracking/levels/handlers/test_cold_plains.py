"""Cold Plains: every open border gap is marked; named by the level behind it when known.

Act 1 wilderness exits are 'Wild Border 1-4' rooms in their open DS1 variant (Bord*o.ds1 = file
3, Bord*oe.ds1 = 4; D2MOO DrlgOutPlace). Real evidence 2026-09-30: three variant-3 gaps, Blood
Moor at (1136, 1016), Stony Field at (1080, 1040), Burial Grounds at (1152, 1072). The level behind
a gap (Room.leads_to) is readable only after the player has been near that edge, so unknown gaps
are shown as 'Exit', and the last unknown one is named by elimination.
"""

import pytest

from inventory_tracking.levels.model import LevelSnapshot, Location, Room
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


BLOOD_MOOR, STONY_FIELD, BURIAL_GROUNDS = (1136, 1016), (1080, 1040), (1152, 1072)


def gap(preset, x, y, leads_to=(), variant=3):
    return Room(preset, x, y, 8, 8, variant, (x, y, 8, 8), leads_to)


def found(guidance):
    return [(p.label, p.kind, (p.room.x, p.room.y)) for p in guidance.pois]


@pytest.mark.parametrize(
    ('fixture', 'expected'),
    [
        (
            'cold_plains_entry',  # only the Blood Moor edge was near: two unknown gaps
            [
                ('Blood Moor', 'previous', BLOOD_MOOR),
                ('Exit', 'exit', BURIAL_GROUNDS),
                ('Exit', 'exit', STONY_FIELD),
            ],
        ),
        (
            'cold_plains_two_known',  # the third is named by elimination
            [
                ('Stony Field', 'stairs', STONY_FIELD),
                ('Burial Grounds', 'target', BURIAL_GROUNDS),
                ('Blood Moor', 'previous', BLOOD_MOOR),
            ],
        ),
        (
            'cold_plains_all_known',
            [
                ('Stony Field', 'stairs', STONY_FIELD),
                ('Burial Grounds', 'target', BURIAL_GROUNDS),
                ('Blood Moor', 'previous', BLOOD_MOOR),
            ],
        ),
    ],
)
def test_real_cold_plains_gaps(fixture, expected):
    snapshot = replay(fixture)

    guidance = handler_for(3).guide(snapshot)

    assert sorted(found(guidance)) == sorted([*expected, ('Cave', 'stairs', (1120, 1032))])
    assert guidance.problems == ()


def test_named_exits_come_first_in_handler_order():
    rooms = (gap(5, 0, 8, (2,)), gap(6, 16, 0, (4,)), gap(7, 16, 16, (17,)))
    guidance = handler_for(3).guide(LevelSnapshot(Location(3, 0, 60, 60), rooms))

    assert [p.label for p in guidance.pois] == ['Stony Field', 'Burial Grounds', 'Blood Moor']
    assert guidance.problems == ('Cave: no room matches',)


def test_closed_borders_are_not_exits_and_nothing_known_means_plain_exits():
    rooms = (Room(0, 8, 8, 8, 8), gap(5, 0, 8), gap(6, 16, 0), gap(4, 8, 0, variant=0))
    guidance = handler_for(3).guide(LevelSnapshot(Location(3, 0, 60, 60), rooms))

    assert [(p.label, p.kind) for p in guidance.pois] == [('Exit', 'exit'), ('Exit', 'exit')]
    assert guidance.problems == ('Cave: no room matches',)
    assert not handler_for(3).confirmed


@pytest.mark.parametrize('fixture', ['cold_plains_entry', 'cold_plains_all_known'])
def test_the_cave_entrance_is_marked_after_the_exits(fixture):
    guidance = handler_for(3).guide(replay(fixture))

    assert found(guidance)[-1] == ('Cave', 'stairs', (1120, 1032))

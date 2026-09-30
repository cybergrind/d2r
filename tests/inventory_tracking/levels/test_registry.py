"""Handler discovery and offline validation of every handler against the bundled preset table."""

import pytest

from inventory_tracking.levels.handler import Handler, PoiSpec, target
from inventory_tracking.levels.presets import PRESET_NAMES
from inventory_tracking.levels.registry import HANDLERS, handler_for, validate


def test_every_discovered_handler_passes_offline_validation():
    assert validate(HANDLERS) == []


def test_discovery_finds_one_handler_per_level_file():
    assert {h.name for h in HANDLERS} >= {
        'Arcane Sanctuary',
        'Black Marsh',
        'Tower Cellar 1-4',
        'Tower Cellar 5',
        'Durance of Hate 1-2',
        'Halls of Anguish/Pain',
        'Halls of Vaught',
    }


def test_unguided_area_has_no_handler():
    assert handler_for(1) is None  # Rogue Encampment
    assert handler_for(None) is None


@pytest.mark.parametrize(
    ('area', 'label', 'presets'),
    [
        (74, 'Summoner', {525, 526, 527, 528}),
        (6, 'Forgotten Tower', {163}),
        *((area, 'Next level', {143, 144, 145, 146}) for area in (21, 22, 23, 24)),
        (25, 'Countess', {159}),
        *((area, 'Next level', {788, 789, 790, 791}) for area in (100, 101)),
        *((area, 'Waypoint', {792, 793, 794, 795}) for area in (100, 101)),
        *((area, 'Next level', {1046, 1047, 1048}) for area in (122, 123)),
        (124, 'Nihlathak', {864}),
        (28, 'Next level', {198, 199, 200, 201}),
        *((area, 'Next level', {240, 241, 242, 243}) for area in (29, 30)),
        *((area, 'Waypoint', {248, 249, 250, 251}) for area in (29, 30)),
        (31, 'Inner Cloister', {244, 245, 246, 247}),
        (29, 'Barracks', {236, 237, 238, 239}),
        (30, 'Jail 1', {236, 237, 238, 239}),
        (31, 'Jail 2', {236, 237, 238, 239}),
        *((area, 'Next level', {291, 292, 293, 294}) for area in (34, 35, 36)),
        (34, 'Cathedral', {288, 289, 290}),
        (35, 'Waypoint', {295, 296, 297, 298}),
        (35, 'Catacombs 1', {288, 289, 290}),
        (36, 'Catacombs 2', {288, 289, 290}),
        *((area, 'Next level', {1078, 1079, 1080, 1081}) for area in (128, 129, 130)),
        (128, 'Arreat Summit', {1074, 1075, 1076, 1077}),
        (129, 'Waypoint', {1082, 1083, 1084, 1085}),
        (129, 'Worldstone Keep 1', {1074, 1075, 1076, 1077}),
        (130, 'Worldstone Keep 2', {1074, 1075, 1076, 1077}),
        (7, 'Pit', {24, 25, 51}),
        (12, 'Next level', {91, 92, 93, 94}),
        (12, 'Tamoe Highland', {83, 84, 85, 86}),
        (41, 'Stony Tomb', {388}),
        (55, 'Next level', {448, 449, 450, 451}),
        (55, 'Rocky Waste', {444, 445, 446, 447}),
        (59, 'Treasure', {452, 453, 454, 455}),
        (59, 'Creeping Feature', {464, 465, 466, 467}),
        (59, 'Stony Tomb 1', {444, 445, 446, 447}),
    ],
)
def test_handler_pois_resolve_to_the_expected_presets(area, label, presets):
    [spec] = [s for s in handler_for(area).pois if s.label == label]

    assert {d for d, name in PRESET_NAMES.items() if spec.matches(name)} == presets


def test_validation_reports_duplicates_unknown_areas_typos_and_family_mismatch():
    handlers = [
        target('A', areas={74}, label='Summoner', preset=r'Act 2 - Arcane Summoner [NSEW]'),
        Handler(
            'B',
            frozenset({74, 9999}),
            (
                PoiSpec('Typo', r'Act 2 - Arcane Sumoner [NSEW]'),
                PoiSpec('Stairs', r'Act 1 - Crypt Next N', family='Act 5'),
            ),
        ),
    ]

    problems = validate(handlers)

    assert 'area 74 has 2 handlers: A, B' in problems
    assert 'B: area 9999 is not in the levels table' in problems
    assert "B: Typo pattern 'Act 2 - Arcane Sumoner [NSEW]' matches no preset" in problems
    assert "B: Stairs matches 'Act 1 - Crypt Next N' outside family 'Act 5'" in problems

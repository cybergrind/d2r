"""The bundled object table: which objects a preset's files place, per layout variant."""

import json

import pytest

from inventory_tracking.levels.build_objects import build
from inventory_tracking.levels.model import BRAIN_CHEST, FROZEN_ANYA, HELL_GATE, SEALS, SUPER_CHEST, THRONE_PORTAL
from inventory_tracking.levels.presets import PRESET_NAMES, object_spots, object_variants
from tests.inventory_tracking.levels.test_ds1 import ds1


def test_each_variant_lists_its_wanted_objects_and_the_preset_counts_its_files(tmp_path):
    (tmp_path / 'json').mkdir()
    presets = {
        'a': {'Def': 107, 'Name': 'chest room', 'File1': 'Act1/Caves/A.ds1', 'File2': 'Act1/Caves/B.ds1', 'File3': '0'},
        'b': {'Def': 108, 'Name': 'nothing wanted', 'File1': 'Act1/Caves/B.ds1'},
    }
    (tmp_path / 'json' / 'lvlprest.json').write_text(json.dumps(presets))
    objects = {
        '397': {'Class': 'ConsolationChest', '*ID': 397},
        '1': {'Class': 'Fountain', '*ID': 1},
    }
    (tmp_path / 'json' / 'objects.json').write_text(json.dumps(objects))
    rows = {
        '0': {'Index': 0, 'Act': 1, 'ObjectClass': 'Fountain'},
        '9': {'Index': 9, 'Act': 1, 'ObjectClass': 'ConsolationChest'},
        '200': {'Index': 9, 'Act': 2, 'ObjectClass': 'Fountain'},  # another act's row 9
    }
    (tmp_path / 'json' / 'objpreset.json').write_text(json.dumps(rows))
    blank = ([0] * 9, [0] * 9)
    files = {
        # A fountain (row 0) and the chest (row 9) at sub-tiles (110, 59).
        'data/global/tiles/act1/caves/a.ds1': ds1(2, 2, [blank], objects=[(2, 0, 5, 5, 0), (2, 9, 110, 59, 0)]),
        'data/global/tiles/act1/caves/b.ds1': ds1(2, 2, [blank], objects=[(2, 0, 5, 5, 0)]),
    }

    table = build(tmp_path, files.__getitem__, wanted=frozenset({397}))

    assert table['objects'] == {'107': {'0': [[397, 110, 59]]}}
    assert table['variants'] == {'107': 2}


def named(name: str) -> int:
    [found] = [preset for preset, known in PRESET_NAMES.items() if known == name]
    return found


# Read by hand from the installed game's files on 2026-10-12 (levels/routes.md).
@pytest.mark.parametrize(
    ('preset', 'variant', 'thing', 'spot'),
    [
        ('Act 1 - Cave Treasure 2', 0, SUPER_CHEST, (112, 22)),
        ('Act 1 - Cave Treasure 5', 0, SUPER_CHEST, (110, 59)),  # Pit 2
        ('Act 1 - Crypt Chest W', 0, SUPER_CHEST, (21, 11)),
        ('Act 2 - Sewer Chest N', 0, SUPER_CHEST, (11, 39)),
        ('Act 3 - Spider Chest NE', 2, SUPER_CHEST, (34, 68)),
        ('Act 3 - Dungeon Treasure 1', 1, SUPER_CHEST, (145, 90)),
        ('Act 3 - Dungeon Treasure 2', 4, BRAIN_CHEST, (97, 97)),
        ('Act 5 - Ice Pool A', 0, SUPER_CHEST, (143, 119)),
        ('Act 5 - Ice Pool B', 5, SUPER_CHEST, (10, 135)),
        ('Act 5 - Ice River A', 1, FROZEN_ANYA, (181, 56)),
        ('Act 5 - Lava W', 1, SUPER_CHEST, (55, 49)),
        ('Act 3 - Mephisto Complex', 0, HELL_GATE, (102, 69)),
        ('Act 5 - ThroneRoom', 0, THRONE_PORTAL, (90, 5)),
        ('Act 4 - Diablo Arm N', 1, SEALS[2], (75, 35)),
        ('Act 4 - Diablo Arm W', 0, SEALS[4], (35, 35)),
        ('Act 4 - Diablo Arm E', 1, SEALS[0], (33, 73)),
    ],
)
def test_the_bundled_table_holds_the_spots_read_from_the_install(preset, variant, thing, spot):
    assert object_spots(named(preset), variant, thing) == (spot,)


def test_a_layout_without_the_object_and_an_unread_layout_have_no_spot():
    lava = named('Act 5 - Lava W')

    assert object_spots(lava, 0, SUPER_CHEST) == ()  # the chest is in the second layout only
    assert object_spots(lava, None, SUPER_CHEST) == ()
    assert object_spots(named('Act 5 - Ice Pool A'), 0, HELL_GATE) == ()
    assert object_variants(lava) == 2
    assert object_variants(named('Act 5 - Ice Pool A')) == 6
    assert object_variants(named('Act 4 - Diablo Entry')) == 0  # places nothing a mark sits on

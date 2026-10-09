"""The bundled warp table: lvlprest names -> the game's DS1 paths -> warp centres per variant."""

import json

from inventory_tracking.levels.build_warps import build, game_path
from tests.inventory_tracking.levels.test_ds1 import cell, ds1


def test_game_paths_are_lowercase_under_the_tiles_folder():
    assert game_path('Act1/Caves/CaveDr1.ds1') == 'data/global/tiles/act1/caves/cavedr1.ds1'


def test_each_variant_gets_the_centre_of_its_warp_tiles(tmp_path):
    (tmp_path / 'json').mkdir()
    presets = {
        'a': {'Def': 51, 'Name': 'Act 1 - Cave Entrance', 'File1': 'Act1/Caves/W.ds1', 'File2': 'Act1/Caves/N.ds1'},
        'b': {'Def': 52, 'Name': 'no warps', 'File1': 'Act1/Caves/N.ds1', 'File2': '0'},
    }
    (tmp_path / 'json' / 'lvlprest.json').write_text(json.dumps(presets))
    objects = {'119': {'Class': 'WaypointOutsideAct1', 'OperateFn': 23}, '1': {'Class': 'Fountain', 'OperateFn': 0}}
    (tmp_path / 'json' / 'objects.json').write_text(json.dumps(objects))
    rows = {
        '0': {'Index': 0, 'Act': 1, 'ObjectClass': 'Fountain'},
        '37': {'Index': 37, 'Act': 1, 'ObjectClass': 'WaypointOutsideAct1'},
        '200': {'Index': 0, 'Act': 2, 'ObjectClass': 'WaypointOutsideAct1'},  # another act's row 0
    }
    (tmp_path / 'json' / 'objpreset.json').write_text(json.dumps(rows))
    w = 3
    cells, orientations = [0] * (w * w), [0] * (w * w)
    for index in (3, 4):  # tiles (0, 1) and (1, 1)
        cells[index], orientations[index] = cell(5), 10
    files = {
        'data/global/tiles/act1/caves/w.ds1': ds1(2, 2, [(cells, orientations)]),
        # A fountain (row 0) and a waypoint (row 37) at sub-tiles (19, 24).
        'data/global/tiles/act1/caves/n.ds1': ds1(
            2, 2, [([0] * 9, [0] * 9)], objects=[(2, 0, 5, 5, 0), (2, 37, 19, 24, 0)]
        ),
    }

    table = build(tmp_path, files.__getitem__)

    assert table['warps'] == {'51': {'0': {'5': [1.0, 1.5]}}}
    assert table['waypoints'] == {'51': {'1': [3.8, 4.8]}, '52': {'0': [3.8, 4.8]}}

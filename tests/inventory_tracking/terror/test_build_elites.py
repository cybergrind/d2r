"""elites.json from the game's tables and map pieces: random groups per level, fixed ones per preset."""

from inventory_tracking.terror.build_elites import build


TABLES = {
    'levels': [
        {'Id': '2', 'MonUMin(H)': '7', 'MonUMax(H)': '9'},
        {'Id': '1', 'MonUMin(H)': '', 'MonUMax(H)': ''},  # a town
        {'Id': '', 'MonUMin(H)': '', 'MonUMax(H)': ''},  # the table's separator rows
    ],
    # The map pieces name their monsters by row of this table, per act (1-based here, 0-based in the file).
    'monpreset': [
        {'Act': '1', 'Place': 'fallen1'},
        {'Act': '1', 'Place': 'place_unique_pack'},
        {'Act': '3', 'Place': 'place_champion'},
        {'Act': '3', 'Place': 'Toorc Icefist'},
        {'Act': '3', 'Place': 'place_group100'},
    ],
    'superuniques': [
        {'Superunique': 'Toorc Icefist', 'Name': 'key', 'hcIdx': '27'},
        {'Superunique': 'Infector of Souls', 'Name': 'other', 'hcIdx': '38'},
    ],
}


def test_levels_keep_their_hell_range_of_random_groups():
    assert build(TABLES, {}, {}, 'test')['levels'] == {'2': [7, 9]}


def test_presets_keep_their_fixed_groups_by_kind_with_the_spot_in_the_piece():
    pieces = {
        ('103', 0): (0, [(0, 3, 4), (1, 40, 50)]),  # act 1: a plain Fallen, then a unique pack
        ('654', 1): (2, [(0, 8, 9), (1, 63, 88), (2, 6, 101)]),  # act 3: champions, Toorc, a plain group
        ('655', 0): (2, [(2, 1, 1)]),
    }

    built = build(TABLES, pieces, {'key': 'Toorc Icefist'}, 'test')

    assert built['presets'] == {
        '103': {'0': [['unique', '', 40, 50]]},
        '654': {'1': [['champion', '', 8, 9], ['super', 'Toorc Icefist', 63, 88]]},
    }


def test_super_uniques_are_named_by_their_id_and_scripted_ones_by_level():
    built = build(TABLES, {}, {'key': 'Toorc Icefist', 'other': 'Infector of Souls'}, 'test')

    assert built['supers'] == {'27': 'Toorc Icefist', '38': 'Infector of Souls'}
    assert built['scripted']['108'] == ['Infector of Souls']  # the seal bosses the table here knows

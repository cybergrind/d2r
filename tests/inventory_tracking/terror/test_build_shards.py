"""shards.json from the game's tables: each elite class's shard rolls and the act table it rolls on."""

import pytest

from inventory_tracking.terror.build_shards import build, shard_rolls


def tc(name, picks, *entries, group='', level='', nodrop='', condition=''):
    row = {'Treasure Class': name, 'group': group, 'level': level, 'Picks': str(picks), 'NoDrop': nodrop}
    row['ConditionCalc'] = condition
    for index in range(1, 11):
        item, prob = entries[index - 1] if index <= len(entries) else ('', '')
        row[f'Item{index}'], row[f'Prob{index}'] = item, str(prob)
    return row


SHARDS = (('xa1', 5), ('xa2', 3), ('xa3', 2), ('xa4', 2), ('xa5', 1))
TREASURE = [
    tc('Act 1 Terrorize Act Consumable', 1, *SHARDS),
    tc('Act 3 Terrorize Act Consumable', 1, ('xa1', 1), ('xa2', 2), ('xa3', 5), ('xa4', 3), ('xa5', 2)),
    tc('All Acts Terrorize Consumable', 1, *((code, 1) for code, _ in SHARDS)),
    tc('Parent 3', -2, ('Act 3 Terrorize Act Consumable', 1), ('All Acts Terrorize Consumable', 1), ('Junk', 1)),
    tc('Parent 1', -2, ('Act 1 Terrorize Act Consumable', 1), ('All Acts Terrorize Consumable', 1)),
    tc('Junk', 1, ('gld', 1)),
    tc('Citem 1', 1, ('gld', 130), ('Parent 3', 3)),
    tc('Citem 5', 1, ('gld', 130), ('Parent 1', 3)),
    tc('Champ 1', -3, ('Citem 1', 1), ('Junk', 1), group='13', level='63'),
    tc('Champ 5', -3, ('Citem 5', 1), ('Junk', 1), group='13', level='81'),
    tc('Uitem 1', 1, ('gld', 81), ('Parent 3', 2)),
    tc('Unique 1', -4, ('Uitem 1', 1), ('Junk', 2), group='15', level='63'),
    tc('Super 1', -5, ('Uitem 1', 2), ('Junk', 2), group='18', level='67'),
    tc('Boss', 5, ('gld', 9), ('Junk', 5)),
    tc('Herald Shard', -2, ('Junk', 1), ('All Acts Terrorize Consumable', 1)),
    tc('Herald Item', 1, ('gld', 392), ('Herald Shard', 15)),
    tc('Herald Extra 1', -1, ('Herald Item', 1), condition="(stat('heraldtier'.accr)>2)*(stat('heraldtier'.accr) <5)"),
    tc('Herald Extra 2', -2, ('Herald Item', 2), condition="(stat('heraldtier'.accr) >4)"),
    tc('Herald', -6, ('Herald Item', 2), ('Herald Extra 1', 1), ('Herald Extra 2', 1), ('Junk', 2), group='41'),
]
TABLES = {
    'treasureclassex': TREASURE,
    'monstats': [
        {'Id': 'zombie1', '*hcIdx': '5', 'boss': '', 'Level(H)': '67'}
        | {
            'TreasureClassChamp(H)': 'Champ 1',
            'TreasureClassUnique(H)': 'Unique 1',
            'TreasureClassHerald(H)': 'Herald',
        },
        {'Id': 'griswold', '*hcIdx': '365', 'boss': '1', 'Level(H)': '84'}
        | {'TreasureClassChamp(H)': 'Boss', 'TreasureClassUnique(H)': 'Boss', 'TreasureClassHerald(H)': ''},
        {'Id': 'dummy', '*hcIdx': '9', 'boss': '', 'Level(H)': '1'}
        | {'TreasureClassChamp(H)': '', 'TreasureClassUnique(H)': '', 'TreasureClassHerald(H)': ''},
    ],
    'levels': [
        {'Id': '35', 'Act': '0', 'MonLvlEx(H)': '73', 'LevelName': 'Catacombs Level 2'},
        {'Id': '1', 'Act': '0', 'MonLvlEx(H)': '', 'LevelName': 'Rogue Encampment'},
        {'Id': '', 'Act': '', 'MonLvlEx(H)': '', 'LevelName': ''},
    ],
    'superuniques': [
        {'Superunique': 'Bishibosh', 'Class': 'zombie1', 'hcIdx': '0', 'TC(H)': 'Super 1'},
        {'Superunique': 'Griswold', 'Class': 'griswold', 'hcIdx': '3', 'TC(H)': 'Boss'},
    ],
}
MISC = {code: {'classid': 674 + index, 'name': f'Shard {code}'} for index, (code, _) in enumerate(SHARDS)}


def rolls(name, tier=None):
    return shard_rolls({row['Treasure Class']: row for row in TREASURE}, name, tier)


def test_a_champion_rolls_its_shard_entry_once_and_the_act_table_and_the_even_one_both_get_it():
    assert rolls('Champ 1') == pytest.approx(
        {'Act 3 Terrorize Act Consumable': 3 / 133, 'All Acts Terrorize Consumable': 3 / 133}
    )


def test_negative_picks_take_each_entry_as_often_as_its_weight():
    assert rolls('Super 1')['All Acts Terrorize Consumable'] == pytest.approx(2 * 2 / 83)
    assert rolls('Boss') == {}


def test_a_heralds_extra_rolls_come_with_its_tier():
    chances = [rolls('Herald', tier)['All Acts Terrorize Consumable'] for tier in (1, 3, 5)]

    assert chances == pytest.approx([2 * 15 / 407, 3 * 15 / 407, 4 * 15 / 407])


def test_classes_keep_their_upgrade_group_level_chance_and_act_table():
    built = build(TABLES, MISC, 'test')

    assert built['classes']['Champ 1'] == [13, 63, pytest.approx(3 / 133), 3]
    assert built['classes']['Champ 5'] == [13, 81, pytest.approx(3 / 133), 1]  # in the group, though no monster's own
    assert built['classes']['Boss'] == [0, 0, 0, 0]
    assert built['groups'] == {'13': ['Champ 1', 'Champ 5'], '15': ['Unique 1'], '18': ['Super 1']}


def test_monsters_super_uniques_levels_and_shards_are_keyed_as_the_client_shows_them():
    built = build(TABLES, MISC, 'test')

    assert built['monsters'] == {'5': ['Champ 1', 'Unique 1', 0], '365': ['Boss', 'Boss', 84]}
    assert built['supers'] == {'0': ['Super 1', 5], '3': ['Boss', 365]}
    assert built['levels'] == {'35': [1, 73, 'Catacombs Level 2']}
    assert built['items']['674'] == ['xa1', 'Shard xa1']
    assert built['mixes'] == {'1': [5, 3, 2, 2, 1], '3': [1, 2, 5, 3, 2]}
    assert built['heralds'] == {str(tier): pytest.approx(n * 15 / 407) for tier, n in enumerate((2, 2, 3, 3, 4), 1)}

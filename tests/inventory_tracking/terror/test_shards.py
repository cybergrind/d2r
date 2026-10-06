"""Worldstone Shards: the act table an elite rolls on, its kills and the shards seen dropping."""

import pytest

from inventory_tracking.loot.ground import ItemSighting
from inventory_tracking.terror.shards import ShardWatch, expected, load, report, summarise, table


CHAMPION, UNIQUE, SUPER, MINION = '0c', '08', '0a', '10'
NAMES = ('Western', 'Eastern', 'Southern', 'Deep', 'Northern')
MODEL = load(
    {
        'items': {str(674 + index): [f'xa{index + 1}', f'{name} Worldstone Shard'] for index, name in enumerate(NAMES)},
        'mixes': {'1': [5, 3, 2, 2, 1], '3': [1, 2, 5, 3, 2], '5': [2, 2, 1, 2, 5]},
        'classes': {
            'Champ 1': [13, 63, 0.03, 3],
            'Champ 3': [13, 74, 0.03, 5],
            'Champ 5': [13, 81, 0.03, 1],
            'Unique 1': [15, 63, 0.02, 3],
            'Unique 5': [15, 81, 0.02, 1],
            'Super 1': [18, 67, 0.05, 3],
            'Smith': [0, 0, 0.02, 3],
            'Boss': [0, 0, 0, 0],
        },
        'groups': {'13': ['Champ 1', 'Champ 3', 'Champ 5'], '15': ['Unique 1', 'Unique 5'], '18': ['Super 1']},
        'monsters': {'5': ['Champ 1', 'Unique 1', 0], '23': ['Champ 5', 'Unique 5', 0], '400': ['Champ 1', 'Boss', 90]},
        'supers': {'0': ['Super 1', 5], '20': ['Smith', 5], '60': ['Boss', 400]},
        'heralds': {'1': 0.07, '5': 0.15},
        'levels': {'35': [1, 73, 'Catacombs Level 2'], '3': [1, 68, 'Cold Plains'], '120': [5, 78, 'Arreat Plateau']},
    }
)
EVEN = pytest.approx([0.2] * 5)


def test_a_champions_class_is_upgraded_to_the_last_of_its_group_its_level_reaches():
    # Catacombs 2 is level 73: a champion there is level 75 and drops from the Act 3 class, whose
    # shard table is Act 5's. The user got mostly Northern shards there (2026-10-07).
    chance, mix = expected(MODEL, 'champion', 5, 35)

    assert chance == 0.03
    assert mix == pytest.approx([2 / 12, 2 / 12, 1 / 12, 2 / 12, 5 / 12])


def test_a_low_level_keeps_the_monsters_own_class_and_a_unique_is_one_level_above_a_champion():
    assert expected(MODEL, 'champion', 5, 3)[1] == pytest.approx([1 / 13, 2 / 13, 5 / 13, 3 / 13, 2 / 13])
    assert expected(MODEL, 'champion', 5, 120)[1][4] == pytest.approx(5 / 12)  # level 80: still the Act 3 class
    assert expected(MODEL, 'unique', 5, 120) == (0.02, pytest.approx([5 / 13, 3 / 13, 2 / 13, 2 / 13, 1 / 13]))


def test_a_class_is_never_downgraded_and_a_boss_monster_has_its_own_level():
    assert expected(MODEL, 'champion', 23, 3)[1][0] == pytest.approx(5 / 13)  # an Act 5 monster in a level-68 area
    assert expected(MODEL, 'champion', 400, 3)[1][0] == pytest.approx(5 / 13)  # level 90 whatever the area


def test_a_super_unique_rolls_its_own_class_by_its_table_row():
    assert expected(MODEL, 'super', 5, 3, super_id=0) == (0.05, pytest.approx([1 / 13, 2 / 13, 5 / 13, 3 / 13, 2 / 13]))
    assert expected(MODEL, 'super', 5, 35, super_id=20)[0] == 0.02  # no group: nothing to upgrade to
    assert expected(MODEL, 'super', 400, 35, super_id=60) == (0, None)


def test_terror_zones_and_heralds_roll_the_even_table():
    assert expected(MODEL, 'champion', 5, 35, terrorized=True) == (0.03, EVEN)
    assert expected(MODEL, 'herald', 5, 35, tier=5, terrorized=True) == (0.15, EVEN)


def test_an_unknown_monster_or_level_has_no_expectation():
    assert expected(MODEL, 'champion', 999, 35) is None
    assert expected(MODEL, 'champion', 5, 999) is None


def test_the_bundled_table_sends_catacombs_champions_to_the_northern_table():
    model = table()
    zombie = next(txt_id for txt_id, (champion, _, level) in model.monsters.items() if champion.startswith('Act 1 (H)'))

    chance, mix = expected(model, 'champion', zombie, 35)

    assert chance == pytest.approx(3 / 133)
    assert mix.index(max(mix)) == 4  # Northern
    assert [name for _, name in model.items.values()][4] == 'Northern Worldstone Shard'


def seen(unit_id, flags, *, txt_id=5, stats=(), super_id=0, area=35):
    data = bytearray(0x80)
    data[0x1A] = int(flags, 16)
    data[0x2A:0x2C] = super_id.to_bytes(2, 'little')
    event = {'event': 'seen', 'unit_id': unit_id, 'txt_id': txt_id, 'mode': 1, 'x': 100, 'y': 100, 'area': area}
    return event | {'data_hex': data.hex(), 'stats': [list(stat) for stat in stats]}


def died(unit_id, *, x=100, y=100, area=35, txt_id=5):
    return {'event': 'died', 'unit_id': unit_id, 'txt_id': txt_id, 'area': area, 'x': x, 'y': y}


def test_an_elites_death_is_one_kill_with_its_kind_and_the_zones_state():
    watch = ShardWatch(MODEL, terrorized={35: False}.get)
    watch.update([seen(1, CHAMPION), seen(2, UNIQUE), seen(3, MINION), seen(4, '00'), seen(5, SUPER, super_id=20)], 1.0)

    kills = watch.update([died(1), died(2), died(3), died(4), died(5)], 2.0)

    assert [(k['event'], k['unit_id'], k['kind'], k['terrorized']) for k in kills] == [
        ('elite_kill', 1, 'champion', False),
        ('elite_kill', 2, 'unique', False),
        ('elite_kill', 5, 'super', False),
    ]
    assert kills[0] | {'t': 0} == {'event': 'elite_kill', 't': 0, 'unit_id': 1, 'txt_id': 5, 'area': 35} | {
        'kind': 'champion',
        'terrorized': False,
        'x': 100,
        'y': 100,
    }
    assert kills[2]['super'] == 20
    assert watch.update([died(1)], 3.0) == []  # revived and killed again: no second drop


def test_a_herald_is_a_kill_with_its_tier_and_allies_are_none():
    watch = ShardWatch(MODEL, terrorized=lambda area: True)
    watch.update([seen(1, UNIQUE, stats=[(0, 367, 3)]), seen(2, UNIQUE, stats=[(0, 172, 2)])], 1.0)

    kills = watch.update([died(1), died(2)], 2.0)

    assert [(k['unit_id'], k['kind'], k['tier'], k['terrorized']) for k in kills] == [(1, 'herald', 3, True)]


def shard(unit_id, class_id=678, mode=3, x=104, y=103):
    return ItemSighting(class_id, unit_id, mode, x, y)


def test_a_shard_first_seen_on_the_ground_is_a_drop_of_the_elite_killed_next_to_it():
    watch = ShardWatch(MODEL, terrorized={35: False}.get)
    watch.update([seen(1, CHAMPION), seen(2, UNIQUE)], 1.0, items=[shard(50, mode=0)], area=35)
    watch.update([died(1, x=400, y=400), died(2)], 2.0, items=[shard(50, mode=0)], area=35)

    found = watch.update([], 2.5, items=[shard(50, mode=0), shard(51, mode=5)], area=35)

    assert found == [
        {'event': 'shard', 't': 2.5, 'unit_id': 51, 'code': 'xa5', 'area': 35, 'terrorized': False}
        | {'x': 104, 'y': 103, 'from': 2, 'kind': 'unique'}
    ]
    assert watch.update([], 3.0, items=[shard(50, mode=3), shard(51, mode=0)], area=35) == []  # dropped by the player


def test_a_shard_with_no_fresh_kill_near_it_is_still_a_drop():
    watch = ShardWatch(MODEL)
    watch.update([seen(1, CHAMPION)], 1.0, items=[], area=35)
    watch.update([died(1)], 2.0, items=[], area=35)

    [found] = watch.update([], 60.0, items=[shard(51, class_id=674)], area=35)

    assert (found['code'], found['from'], found['kind'], found['terrorized']) == ('xa1', None, None, None)


def test_what_lies_on_the_ground_when_a_game_or_the_watch_starts_is_no_drop():
    watch = ShardWatch(MODEL)

    assert watch.update([], 1.0, items=[shard(51)], area=35) == []
    assert watch.update([], 2.0, items=[shard(51), shard(52)], area=35) != []
    assert watch.update([{'event': 'left_game'}], 3.0) == []
    assert watch.update([], 4.0, items=[shard(52), shard(53)], area=35) == []  # other units carry these ids now


def kill(kind, area, terrorized, txt_id=5, **extra):
    return {'event': 'elite_kill', 'unit_id': 1, 'txt_id': txt_id, 'area': area, 'kind': kind} | {
        'terrorized': terrorized,
        **extra,
    }


def test_the_summary_sets_drops_against_the_kills_by_act_and_zone():
    events = [
        kill('champion', 35, False),
        kill('champion', 35, False),
        kill('unique', 35, False),
        kill('herald', 35, True, tier=5),
        kill('champion', 120, None),
        {'event': 'shard', 'code': 'xa5', 'area': 35, 'terrorized': False},
        {'event': 'shard', 'code': 'xa1', 'area': 35, 'terrorized': True},
        {'event': 'seen', 'area': 35},
    ]

    rows = summarise(events, MODEL)

    assert list(rows) == [(1, 'regular'), (1, 'terror'), (5, 'unsure')]
    regular = rows[1, 'regular']
    assert regular.kills == {'champion': 2, 'unique': 1}
    assert regular.dropped == [0, 0, 0, 0, 1]
    assert sum(regular.expected) == pytest.approx(0.03 + 0.03 + 0.02)
    assert regular.expected[4] == pytest.approx(0.06 * 5 / 12 + 0.02 * 2 / 13)  # level 76: the unique's own class
    assert rows[1, 'terror'].dropped == [1, 0, 0, 0, 0]
    assert rows[1, 'terror'].expected == pytest.approx([0.03] * 5)
    assert sum(rows[5, 'unsure'].expected) == pytest.approx(0.03)  # counted as not terrorized


def test_the_summary_can_split_by_level():
    rows = summarise([kill('champion', 35, False), kill('champion', 3, False)], MODEL, by_level=True)

    assert list(rows) == [('Cold Plains', 'regular'), ('Catacombs Level 2', 'regular')]


def test_the_report_names_the_shards_and_totals_each_row():
    events = [kill('champion', 35, False), {'event': 'shard', 'code': 'xa5', 'area': 35, 'terrorized': False}]

    text = report(summarise(events, MODEL), MODEL)

    assert 'Act 1' in text
    assert 'regular' in text
    assert 'Northern' in text

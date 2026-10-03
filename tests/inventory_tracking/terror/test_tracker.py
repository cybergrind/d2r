"""Per-game Herald tracking from probe events: group kills, tiers, allies, and the card text."""

import pytest

from inventory_tracking.terror.monsters import Monster
from inventory_tracking.terror.tracker import ZoneTracker


HERALD_DATA = '00' * 0x18 + '462a0802' + '00' * 0x64  # monster data +0x1A: 0x08, as the Black Marsh Herald
MINION_DATA = '00' * 0x18 + '00001004' + '00' * 0x64  # +0x1A: 0x10, as its minions
PLAIN_DATA = '00' * 0x80  # +0x1A: 0, a plain monster
CHAMPION_DATA = '00' * 0x18 + '00000c00' + '00' * 0x64  # +0x1A: 0x0c, as champions in the probe logs


def seen(unit_id, area, *, stats=(), mode=1, data_hex=HERALD_DATA):
    stats = [[0, s, v] for s, v in stats]
    return {'event': 'seen', 'unit_id': unit_id, 'area': area, 'mode': mode, 'stats': stats, 'data_hex': data_hex}


def died(unit_id, area):
    return {'event': 'died', 'unit_id': unit_id, 'area': area}


def kill(tracker, area, count, start=1000):
    for unit_id in range(start, start + count):
        tracker.apply([seen(unit_id, area), died(unit_id, area)])


def test_kills_in_any_level_of_a_group_count_together():
    tracker = ZoneTracker()
    kill(tracker, 11, 3)  # Hole Level 1
    kill(tracker, 15, 2, start=2000)  # Hole Level 2
    kill(tracker, 6, 4, start=3000)  # Black Marsh: same Terror Zone, other group

    assert (tracker.count('Hole levels').killed, tracker.count('Black Marsh').killed) == (5, 4)


def test_allies_never_count():
    tracker = ZoneTracker()
    tracker.apply([seen(7, 6, stats=[(172, 2)]), died(7, 6)])

    assert tracker.count('Black Marsh').killed == 0
    assert tracker.count('Black Marsh').seen == set()


def test_a_revived_monster_counts_one_kill():
    # Fallen Shamans revive their Fallen: same unit id, dead again (Blood Moor, 2026-10-03 logs).
    tracker = ZoneTracker()
    tracker.apply([at(seen(7, 6, data_hex=PLAIN_DATA), 5000, 5000), died(7, 6)])
    tracker.track([Monster(7, 19, 1, 5000, 5000, 6, None)])  # revived

    assert [dot.kind for dot in tracker.map_dots(6)] == ['mob']

    tracker.apply([died(7, 6)])

    assert tracker.count('Black Marsh').killed == 1
    assert tracker.map_dots(6) == []


def test_a_herald_sets_the_next_tier_and_stores_its_group_completion():
    tracker = ZoneTracker()
    kill(tracker, 6, 10)
    kill(tracker, 11, 5, start=2000)

    tracker.apply([seen(9, 6, stats=[(367, 1)])])

    assert tracker.next_tier == 2
    assert tracker.heralds == [(1, 'Black Marsh')]
    assert tracker.offsets == {'Black Marsh': pytest.approx(100 * 10 / 199)}  # Hole levels untouched
    tracker.apply([died(9, 6)])  # the game counts the Herald's death like any other
    assert tracker.count('Black Marsh').killed == 11


def test_herald_minions_carry_the_tier_but_are_not_another_herald():
    tracker = ZoneTracker()
    minions = [seen(unit_id, 6, stats=[(367, 1)], data_hex=MINION_DATA) for unit_id in (20, 21, 22)]

    tracker.apply([*minions[:2], seen(9, 6, stats=[(367, 1)]), minions[2], died(20, 6), died(21, 6)])

    assert tracker.heralds == [(1, 'Black Marsh')]
    assert tracker.count('Black Marsh').killed == 2  # kills like any other (game code)


def test_tier_stays_at_five_and_leaving_the_game_resets_everything():
    tracker = ZoneTracker()
    tracker.apply([seen(9, 6, stats=[(367, 5)])])
    assert tracker.next_tier == 5

    tracker.apply([{'event': 'left_game'}])

    assert (tracker.next_tier, tracker.heralds, tracker.count('Black Marsh').killed) == (1, [], 0)


def text(lines):
    return [line if isinstance(line, str) else line.text for line in lines]


def test_card_before_the_breakpoint():
    tracker = ZoneTracker()
    kill(tracker, 6, 50)

    assert text(tracker.lines(6, terrorized=True)) == [
        'Terror · Black Marsh',
        'Next Herald: Tier 1 · none seen this game',
        'Killed 50 / 199 · 149 left',
        'Progress 25% · breakpoint 52% in 54 kills',  # the 54th kill makes 52.3%
    ]


def test_card_past_the_breakpoint_shows_next_kill_and_remaining_chances():
    tracker = ZoneTracker()
    kill(tracker, 6, 197)

    lines = text(tracker.lines(6, terrorized=True))

    assert lines[2:] == [
        'Killed 197 / 199 · 2 left',
        'Progress 98% · breakpoint 52% reached',
        'Next kill 3.91% · all 2 left 7.7%',  # rolls at 198/199 and 199/199
    ]


def test_card_marks_an_unknown_terror_status_and_hides_when_not_terrorized():
    tracker = ZoneTracker()
    kill(tracker, 6, 1)

    assert text(tracker.lines(6, terrorized=None))[0] == 'Terror · Black Marsh (unconfirmed)'
    assert tracker.lines(6, terrorized=False) == []
    assert tracker.lines(1, terrorized=True) == []  # town: no group


def test_population_grows_to_the_hostile_monsters_seen():
    tracker = ZoneTracker()
    tracker.apply([seen(unit_id, 8) for unit_id in range(80)])  # Den of Evil: article mean 67

    assert text(tracker.lines(8, terrorized=True))[2] == 'Killed 0 / 80 · 80 left'


def plain(mod):
    """Monster data of a plain monster (+0x1A type flags 0) with first special modifier `mod` (+0x20)."""
    return '00' * 0x20 + f'{mod:02x}' + '00' * 0x5F


def sightings(tracker, area, mods, *, start=500, data=plain):
    tracker.apply([seen(unit_id, area, data_hex=data(mod)) for unit_id, mod in enumerate(mods, start)])


def test_plain_monsters_with_a_forced_terror_modifier_mark_their_terror_zone():
    # Hell Terror Zones give every plain monster one modifier from desecratedzones.json's
    # always_unique_mod_pool: 'manahit' (25) in Black Marsh, 'fast' (6) in the sewers (2026-10-02).
    tracker = ZoneTracker()
    sightings(tracker, 6, [25, 25, 25])

    assert tracker.terrorized(6) is True
    assert tracker.terrorized(11) is True  # Hole: same Terror Zone (Act1-Tower)
    assert tracker.terrorized(2) is None  # Blood Moor: nothing seen there


def test_plain_monsters_without_a_modifier_mean_no_terror_zone():
    tracker = ZoneTracker()
    sightings(tracker, 35, [0, 0, 0])

    assert tracker.terrorized(35) is False


def test_the_latest_sightings_win_after_the_zone_rotates():
    tracker = ZoneTracker()
    sightings(tracker, 47, [6] * 10)
    sightings(tracker, 47, [0] * 6, start=600)

    assert tracker.terrorized(47) is False


def test_champions_uniques_and_minions_do_not_vote():
    tracker = ZoneTracker()
    sightings(tracker, 35, [9, 18, 5], data=lambda mod: '00' * 0x1A + '10' + '00' * 5 + f'{mod:02x}' + '00' * 0x5F)

    assert tracker.terrorized(35) is None


def test_a_herald_marks_its_terror_zone_when_no_plain_monster_was_seen():
    tracker = ZoneTracker()
    tracker.apply([seen(9, 6, stats=[(367, 1)])])

    assert tracker.terrorized(11) is True


def test_a_breakpoint_beyond_the_mobs_left_says_the_group_is_done():
    tracker = ZoneTracker()
    kill(tracker, 6, 186)
    tracker.apply([seen(9, 6, stats=[(367, 1)])])

    assert text(tracker.lines(6, terrorized=True))[3] == 'Progress 0% · breakpoint 43% out of reach: 13 left give 6%'


def test_visited_rooms_are_the_rooms_ever_loaded_in_that_level():
    tracker = ZoneTracker()
    tracker.apply([{'event': 'rooms', 'area': 6, 'bounds': [[0, 0, 8, 8], [8, 0, 8, 8]]}])

    assert tracker.visited_rooms(6) == {(0, 0, 8, 8), (8, 0, 8, 8)}
    assert tracker.visited_rooms(7) == set()


def at(event, x, y):
    return {**event, 'x': x, 'y': y}


def test_map_dots_put_each_live_hostile_at_its_last_seen_position():
    # Pack leaders by monster data +0x1A (probe logs 2026-10-02/03): 0x08 unique, 0x0c champion,
    # 0x0a super unique; minions (0x10) are plain dots. Mobs first, then leaders, then Heralds:
    # the drawing order, so the rarer marks stay on top.
    tracker = ZoneTracker()
    tracker.apply(
        [
            at(seen(1, 6, data_hex=PLAIN_DATA), 5000, 5000),
            at(seen(2, 6, data_hex=CHAMPION_DATA), 5010, 5000),
            at(seen(3, 6, data_hex=MINION_DATA), 5020, 5000),
            at(seen(4, 6, data_hex=MINION_DATA), 5025, 5000),
            at(seen(5, 6, stats=[(172, 2)]), 5030, 5000),  # an ally
            at(seen(6, 6, data_hex=PLAIN_DATA, mode=12), 5040, 5000),  # a corpse seen first
            at(seen(7, 11, data_hex=PLAIN_DATA), 5050, 5000),  # another level
            at(seen(8, 6, data_hex=HERALD_DATA[:0x34] + '0a' + HERALD_DATA[0x36:]), 5060, 5000),  # super unique
            herald(9, 6, 5100, 5200),
        ]
    )
    tracker.track([Monster(1, 1, 2, 5005, 5015, 6, None)])
    tracker.apply([died(3, 6)])

    assert [(dot.kind, dot.x, dot.y) for dot in tracker.map_dots(6)] == [
        ('mob', 1001.0, 1003.0),
        ('mob', 1005.0, 1000.0),
        ('leader', 1002.0, 1000.0),
        ('leader', 1012.0, 1000.0),
        ('herald', 1020.0, 1040.0),
    ]
    assert [dot.kind for dot in tracker.map_dots(11)] == ['mob']

    tracker.apply([died(2, 6), died(8, 6), died(9, 6)])
    assert [dot.kind for dot in tracker.map_dots(6)] == ['mob', 'mob']


def test_a_monster_followed_into_another_level_moves_its_dot_there():
    tracker = ZoneTracker()
    tracker.apply([at(seen(1, 6, data_hex=PLAIN_DATA), 5000, 5000)])

    tracker.track([Monster(1, 1, 2, 300, 400, 11, None)])

    assert tracker.map_dots(6) == []
    assert [(dot.x, dot.y) for dot in tracker.map_dots(11)] == [(60.0, 80.0)]


def explore(tracker, area, level_rooms, loaded):
    tracker.apply(
        [
            {'event': 'area', 'area': area, 'level_rooms': level_rooms},
            {'event': 'rooms', 'area': area, 'bounds': [[8 * index, 0, 8, 8] for index in range(loaded)]},
        ]
    )


def test_a_level_population_is_extrapolated_from_its_explored_rooms_as_the_game_does():
    # Ancients' Way (weight 3) and Icy Cellar (weight 1) share the article's 281: 70.25 for Icy Cellar.
    tracker = ZoneTracker()
    explore(tracker, 118, level_rooms=40, loaded=20)
    tracker.apply([seen(unit_id, 118) for unit_id in range(100)])

    # 100 seen in half the rooms: 200; the unvisited Icy Cellar keeps its article share.
    assert text(tracker.lines(118, terrorized=True))[2] == 'Killed 0 / 270 · 270 left'

    explore(tracker, 118, level_rooms=40, loaded=40)
    assert text(tracker.lines(118, terrorized=True))[2] == 'Killed 0 / 170 · 170 left'  # fully explored: 100 + 70


def test_progress_weighs_each_level_by_the_game_weight():
    tracker = ZoneTracker()
    explore(tracker, 118, level_rooms=40, loaded=40)
    explore(tracker, 119, level_rooms=10, loaded=10)
    kill(tracker, 119, 50)  # Icy Cellar cleared: weight 1 of 4
    assert text(tracker.lines(119, terrorized=True))[3].startswith('Progress 25% ')

    tracker.apply([seen(unit_id, 118) for unit_id in range(5000, 5100)])
    kill(tracker, 118, 100, start=6000)  # half of Ancients' Way: 3 x 0.5 of 4 more

    assert text(tracker.lines(118, terrorized=True))[3].startswith('Progress 62% ')


@pytest.mark.parametrize(
    ('rooms', 'population'),
    [(72, 390), (48, 270), (24, 124), (28, 124), (None, 124)],
)
def test_a_tal_rasha_tomb_is_sized_by_its_room_count(rooms, population):
    # Evidence 2026-10-02: the Orifice tomb had 72 Room2s, the Kaa tomb 48, chest tombs 24-28;
    # the article's real / big false / small false tombs hold 390 / 270 / 124.
    tracker = ZoneTracker()
    if rooms:
        tracker.apply([{'event': 'area', 'area': 70, 'level_rooms': rooms}])

    assert text(tracker.lines(70, terrorized=True))[2] == f'Killed 0 / {population} · {population} left'


def herald(unit_id, area, x, y, tier=1, **extra):
    return {**seen(unit_id, area, stats=[(367, tier)], **extra), 'x': x, 'y': y}


def test_a_live_herald_is_marked_until_it_dies_and_follows_its_position():
    tracker = ZoneTracker()
    tracker.apply([herald(9, 6, 5100, 5200), herald(20, 6, 5110, 5200, data_hex=MINION_DATA)])
    assert tracker.herald_marks(6) == [(1, 5100, 5200)]
    assert tracker.herald_marks(11) == []  # another level

    tracker.track([Monster(9, 1, 2, 5150, 5260, 6, None)])
    assert tracker.herald_marks(6) == [(1, 5150, 5260)]

    tracker.apply([died(9, 6)])
    assert tracker.herald_marks(6) == []


def test_a_herald_corpse_seen_first_is_not_marked():
    tracker = ZoneTracker()
    tracker.apply([herald(9, 6, 5100, 5200, mode=12)])

    assert tracker.herald_marks(6) == []
    assert tracker.next_tier == 2  # it still was this game's Tier 1


def test_the_card_points_at_a_live_herald():
    tracker = ZoneTracker()
    tracker.apply([herald(9, 6, 5100, 5000, tier=2)])

    lines = text(tracker.lines(6, terrorized=True, position=(5000, 5000)))

    assert lines[1] == '↘  Herald T2 alive: east'
    assert lines[2].startswith('Next Herald: Tier 3')
    assert text(tracker.lines(6, terrorized=True))[1].startswith('Next Herald')  # no position: no pointer


def test_herald_dots_for_the_map_are_in_tiles():
    tracker = ZoneTracker()
    tracker.apply([herald(9, 6, 5100, 5200, tier=3)])

    [dot] = tracker.herald_dots(6)

    assert (dot.label, dot.kind, dot.x, dot.y) == ('Herald T3', 'herald', 1020.0, 1040.0)


def test_rooms_loaded_count_from_logs_without_bounds():
    # Logs before 2026-10-02 18:00 carried only `loaded_ever`: still the populated rooms.
    tracker = ZoneTracker()
    tracker.apply([{'event': 'area', 'area': 6, 'level_rooms': 94}, {'event': 'rooms', 'area': 6, 'loaded_ever': 47}])
    tracker.apply([seen(unit_id, 6, data_hex='') for unit_id in range(100)])

    assert text(tracker.lines(6, terrorized=True))[2] == 'Killed 0 / 200 · 200 left'  # 100 in half the rooms

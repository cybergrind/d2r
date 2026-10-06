"""Per-game Herald tracking from probe events: group kills, tiers, allies, and the card text."""

import pytest

from inventory_tracking.levels.model import Location
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


def test_the_card_names_the_zone_modifier_and_the_terrorized_level():
    # The game's own lines under the area name, which the card covers (user, 2026-10-06):
    # 'Terrorized: 95' and 'Fire Enchanted' in the Lut Gholein sewers.
    tracker = ZoneTracker()
    sightings(tracker, 6, [9, 9, 25, 9])  # 9 = fire; one stray reading

    assert tracker.zone_modifier(6) == 'Fire Enchanted'
    assert tracker.lines(6, terrorized=True, player_level=93)[:2] == [
        'Terror · Black Marsh',
        'Level 95 · Fire Enchanted',
    ]
    assert tracker.lines(6, terrorized=True, player_level=98)[1] == 'Level 96 · Fire Enchanted'  # Hell cap
    assert tracker.lines(6, terrorized=True)[1] == 'Fire Enchanted'

    unknown = ZoneTracker()
    assert unknown.zone_modifier(6) is None
    assert unknown.lines(6, terrorized=None, player_level=93)[1].startswith('Next Herald')


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


def test_visited_rooms_are_the_players_room_and_the_rooms_touching_it():
    # The client loads rooms further out than it shows monsters in: of 589 monsters first seen with
    # the player's position known (probe logs, 2026-10-06), every one was in the player's room or
    # one of its eight neighbours. Only those count as visited (user, 2026-10-06: too wide an area
    # was coloured). Bounds are tiles; the player's position is world units, 5 to a tile.
    tracker = ZoneTracker()
    row = [[x, 0, 8, 8] for x in (0, 8, 16, 24)]
    tracker.apply([{'event': 'rooms', 'area': 6, 'bounds': [*row, [8, 8, 8, 8], [24, 16, 8, 8]]}])
    assert tracker.visited_rooms(6) == set()

    tracker.track([], Location(6, 0, 2 * 5, 3 * 5))  # in the first room

    assert tracker.visited_rooms(6) == {(0, 0, 8, 8), (8, 0, 8, 8), (8, 8, 8, 8)}  # the corner neighbour too
    assert tracker.visited_rooms(7) == set()

    tracker.track([], Location(6, 0, 20 * 5, 3 * 5))  # two rooms on

    assert tracker.visited_rooms(6) == {(x, 0, 8, 8) for x in (0, 8, 16, 24)} | {(8, 8, 8, 8)}


def test_visited_rooms_come_back_with_a_rejoined_game(tmp_path):
    store = tmp_path / 'games.json'
    tracker = ZoneTracker(store)
    tracker.apply([entered(6, 0xAAAA), {'event': 'rooms', 'area': 6, 'bounds': [[0, 0, 8, 8], [40, 0, 8, 8]]}])
    tracker.track([], Location(6, 0, 10, 10))
    tracker.save()

    again = ZoneTracker(store)
    again.apply([entered(6, 0xAAAA)])

    assert again.visited_rooms(6) == {(0, 0, 8, 8)}


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


def test_leader_and_herald_dots_carry_the_path_address_last_seen_and_plain_mobs_none():
    tracker = ZoneTracker()
    tracker.apply(
        [
            at(seen(1, 6, data_hex=PLAIN_DATA), 5000, 5000),
            at(seen(2, 6, data_hex=CHAMPION_DATA), 5010, 5000),
            herald(9, 6, 5100, 5200),
        ]
    )

    tracker.track(
        [
            Monster(1, 1, 2, 5000, 5000, 6, None, path=0x10),
            Monster(2, 1, 2, 5010, 5000, 6, None, path=0x20),
            Monster(9, 1, 2, 5100, 5200, 6, None, path=0x90),
        ]
    )

    assert [(dot.kind, dot.path) for dot in tracker.map_dots(6)] == [('mob', 0), ('leader', 0x20), ('herald', 0x90)]

    # The champion walks out of the client's range: its dot stays where it was last seen, but its
    # path is freed and reused (by another monster or a missile), so the address must not be followed.
    tracker.track([Monster(9, 1, 2, 5100, 5200, 6, None, path=0x90)])
    assert [(dot.kind, dot.path) for dot in tracker.map_dots(6)] == [('mob', 0), ('leader', 0), ('herald', 0x90)]

    tracker.apply([{'event': 'left_game'}])
    assert tracker.paths == {}


def test_a_unit_that_cannot_be_killed_is_no_monster_to_mark_or_count():
    # Durance of Hate 3, 2026-10-05: the Compelling Orb (monstats compellingorb 366, not killable)
    # carries the unique flag 0x08 and never dies; it got a pack-leader ring with no monster in it.
    tracker = ZoneTracker()

    tracker.apply([at({**seen(4, 6, data_hex=CHAMPION_DATA), 'txt_id': 366}, 5000, 5000)])

    assert tracker.map_dots(6) == []
    assert tracker.area_count(6).seen == set()


def test_a_remembered_monster_that_is_not_there_when_the_player_comes_close_loses_its_dot():
    # The client drops live monsters 8-24 tiles away (probe log 2026-10-05: 3 of 1233 nearer than
    # 40 units), keeping their dot at the last seen spot. Back within 40 units with the unit still
    # absent from a complete walk, it is not there any more (it moved, or died unseen).
    tracker = ZoneTracker()
    tracker.apply([at(seen(2, 6, data_hex=CHAMPION_DATA), 5000, 5000), herald(9, 6, 5010, 5000)])

    tracker.track([], Location(6, 0, 5100, 5000))  # far: out of the client's range, the dots stay
    tracker.track([], Location(6, 0, 5020, 5000), complete=False)  # a broken-off walk proves nothing
    tracker.track([], Location(11, 0, 5020, 5000))  # another level
    assert [dot.kind for dot in tracker.map_dots(6)] == ['leader', 'herald']

    tracker.track([], Location(6, 0, 5020, 5000))
    assert tracker.map_dots(6) == []
    assert tracker.herald_marks(6) == []

    tracker.track([Monster(2, 1, 2, 5300, 5300, 6, None), Monster(9, 1, 2, 5310, 5300, 6, None)])  # found again
    assert [(dot.kind, dot.x, dot.y) for dot in tracker.map_dots(6)] == [
        ('leader', 1060.0, 1060.0),
        ('herald', 1062.0, 1060.0),
    ]


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


def entered(area, seed):
    """An 'area' event with the level struct the probe reads on entering: its seed is at +0x1E4."""
    level = bytearray(0x400)
    level[0x1E4:0x1EC] = seed.to_bytes(8, 'little')
    return {'event': 'area', 'area': area, 'level_rooms': 30, 'level_hex': level.hex()}


def test_rejoining_the_same_game_after_a_restart_continues_its_heralds_and_kills(tmp_path):
    # The game restarted and the same server game rejoined showed Tier 1 again (user, 2026-10-06).
    # A level's seed (+0x1E4, 8 bytes) is the same whenever the same game is entered and differs
    # between games (probe logs: 516 area/seed pairs, shared only by rejoins and service restarts).
    store = tmp_path / 'terror-games.json'
    first = ZoneTracker(store)
    first.apply([entered(1, 0xAAAA), entered(6, 0xBBBB), herald(9, 6, 5100, 5200, tier=2), died(9, 6)])
    kill(first, 6, 3)
    assert first.next_tier == 3
    first.apply([{'event': 'left_game'}])
    assert first.next_tier == 1

    again = ZoneTracker(store)  # the service restarted with the game
    again.apply([entered(40, 0xCCCC)])  # a level the game was never seen in: not known yet
    assert again.next_tier == 1
    again.apply([entered(6, 0xBBBB)])
    assert again.next_tier == 3
    assert again.area_count(6).killed == 4
    assert again.visited_rooms(6) == first.visited_rooms(6)

    again.apply([herald(9, 6, 5100, 5200, tier=2)])  # seen again by a fresh client: the same Herald
    assert again.heralds == [(2, 'Black Marsh')]


def test_another_game_starts_from_nothing_and_both_are_kept(tmp_path):
    store = tmp_path / 'terror-games.json'
    first = ZoneTracker(store)
    first.apply([entered(6, 0xBBBB), herald(9, 6, 5100, 5200), {'event': 'left_game'}])

    first.apply([entered(6, 0xDDDD)])  # the same area with another seed: a new game
    assert first.next_tier == 1
    first.apply([herald(3, 6, 5100, 5200, tier=4), {'event': 'left_game'}])

    assert [tracker_for(store, seed).next_tier for seed in (0xBBBB, 0xDDDD, 0xEEEE)] == [2, 5, 1]


def tracker_for(store, seed):
    tracker = ZoneTracker(store)
    tracker.apply([entered(6, seed)])
    return tracker


def test_a_game_killed_without_leaving_is_still_saved_and_a_broken_store_is_ignored(tmp_path):
    store = tmp_path / 'terror-games.json'
    crashed = ZoneTracker(store, clock=lambda: 100.0)
    crashed.apply([entered(6, 0xBBBB), herald(9, 6, 5100, 5200)])  # no 'left_game' follows

    assert tracker_for(store, 0xBBBB).next_tier == 2

    store.write_text('{"games": [')
    assert tracker_for(store, 0xBBBB).next_tier == 1


def test_a_monster_without_a_position_yet_gets_no_dot_until_it_has_one():
    # Far Oasis probe log, 2026-10-06: a unit first seen at (0, 0), its path not filled in yet.
    tracker = ZoneTracker()
    tracker.apply([at(seen(1, 6, data_hex=PLAIN_DATA), 0, 0), at(seen(2, 6, data_hex=PLAIN_DATA), 5000, 5000)])
    assert [(dot.x, dot.y) for dot in tracker.map_dots(6)] == [(1000.0, 1000.0)]

    tracker.track([Monster(1, 1, 2, 5010, 5000, 6, None), Monster(2, 1, 2, 0, 0, 6, None)])
    assert [(dot.x, dot.y) for dot in tracker.map_dots(6)] == [(1000.0, 1000.0), (1002.0, 1000.0)]


def monster_data(flags=0, modifiers=()):
    """Monster data with the type flags at +0x1A and the modifier bytes from +0x20."""
    data = bytearray(0x80)
    data[0x1A] = flags
    data[0x20 : 0x20 + len(modifiers)] = bytes(modifiers)
    return data.hex()


def archers(count, *, start=100, x=5000, y=5000, stats=(), modifiers=()):
    """Dark Rangers (txt id 160) of Tamoe Highland (area 7), two units apart."""
    data = monster_data(0x10, modifiers)
    return [at({**seen(start + n, 7, stats=stats, data_hex=data), 'txt_id': 160}, x + 2 * n, y) for n in range(count)]


def test_archers_first_seen_under_fanaticism_are_danger_dots_with_a_pack_point_saying_why():
    # Stats 350/351: the aura's skill id and level, on every monster standing in it (probe logs).
    tracker = ZoneTracker()
    tracker.apply([*archers(8, stats=[(350, 122), (351, 9)]), at(seen(1, 7, data_hex=PLAIN_DATA), 6000, 6000)])
    tracker.track([Monster(100, 160, 1, 5000, 5000, 7, None, path=0x7000)])

    dots = tracker.map_dots(7)

    assert [dot.kind for dot in dots] == ['mob', *['danger'] * 8, 'pack']
    assert dots[1].path == 0x7000  # the HUD follows a deadly pack's monsters
    assert (dots[-1].label, dots[-1].x, dots[-1].y) == ('Dark Ranger x8 · Fanaticism', 1001.4, 1000.0)
    assert [dot.kind for dot in tracker.map_dots(7, danger=False)] == ['mob'] * 9


def test_plain_archers_stay_plain_dots_and_a_pack_to_be_careful_with_is_caution():
    tracker = ZoneTracker()
    tracker.apply(archers(4))
    assert [dot.kind for dot in tracker.map_dots(7)] == ['mob'] * 4

    tracker.apply(archers(6, start=200, x=7000, modifiers=(5,)))  # the zone's Extra Strong on each

    assert [dot.kind for dot in tracker.map_dots(7)] == [*['mob'] * 4, *['caution'] * 6]
    assert tracker.danger_lines(7) == []


def test_an_aura_enchanted_leader_makes_the_archers_around_it_deadly_until_it_dies():
    tracker = ZoneTracker()
    leader = {**seen(50, 7, stats=[(350, 98), (351, 12)], data_hex=monster_data(0x08, (30, 5, 6))), 'txt_id': 160}
    tracker.apply([at(leader, 5000, 5010), *archers(7)])

    # The leader stays told apart from its pack (user, 2026-10-06: the marks made elites look like the rest).
    dots = tracker.map_dots(7)
    assert [dot.kind for dot in dots] == ['danger'] * 7 + ['elite', 'pack']
    assert (dots[7].label, dots[7].x, dots[7].y) == ('unique', 1000.0, 1002.0)

    tracker.apply([died(50, 7)])

    assert [dot.kind for dot in tracker.map_dots(7)] == ['mob'] * 7


def test_the_warning_row_names_the_deadly_pack_and_points_at_it():
    tracker = ZoneTracker()
    tracker.apply(archers(8, stats=[(350, 122), (351, 9)]))

    assert tracker.danger_lines(7, (5007, 5100)) == ['↗  ⚠ Dark Ranger x8 · Fanaticism: north']
    assert tracker.danger_lines(6, (5007, 5100)) == []


def test_a_deadly_pack_stays_marked_while_it_is_killed_down_to_a_weak_one():
    tracker = ZoneTracker()
    tracker.apply(archers(8, stats=[(350, 122), (351, 9)]))
    assert tracker.danger_lines(7) == ['⚠ Dark Ranger x8 · Fanaticism']

    tracker.apply([died(100, 7)])

    assert tracker.danger_lines(7) == ['⚠ Dark Ranger x7 · Fanaticism']
    assert [dot.kind for dot in tracker.map_dots(7)] == ['danger'] * 7 + ['pack']

    tracker.apply([died(101, 7), died(102, 7), died(103, 7)])

    assert tracker.danger_lines(7) == []
    assert [dot.kind for dot in tracker.map_dots(7)] == ['mob'] * 4


def test_the_leader_of_a_pack_to_be_careful_with_stays_a_leader_dot():
    tracker = ZoneTracker()
    leader = {**seen(50, 7, data_hex=monster_data(0x08, (5,))), 'txt_id': 160}
    tracker.apply([at(leader, 5000, 5010), *archers(5, modifiers=(5,))])

    assert [dot.kind for dot in tracker.map_dots(7)] == ['caution'] * 5 + ['leader']


def elite(unit_id, x, y, *, flags=0x08, txt_id=160, area=7, super_id=0, stats=()):
    """A pack leader's first sight: type flags at +0x1A, the super unique's id (hcIdx) at +0x2A."""
    data = bytearray(0x80)
    data[0x1A] = flags
    data[0x2A:0x2C] = super_id.to_bytes(2, 'little')
    return at({**seen(unit_id, area, stats=stats, data_hex=data.hex()), 'txt_id': txt_id}, x, y)


def test_the_elite_line_counts_groups_killed_and_alive_against_the_levels_range():
    # Tamoe Highland (7) rolls 7-9 random groups in Hell (levels.txt, 2026-10-06).
    tracker = ZoneTracker()
    tracker.apply([
        elite(1, 5000, 5000),
        at({**seen(2, 7, data_hex=monster_data(0x10)), 'txt_id': 160}, 5002, 5000),  # its minion
        elite(3, 6000, 5000),
        *(elite(10 + n, 7000 + 3 * n, 5000, flags=0x0C) for n in range(3)),  # champions: one group
        elite(20, 8000, 5000, stats=[(367, 1)]),  # a Herald is no elite group of the level
        elite(30, 5000, 5000, area=6),  # another level's
    ])  # fmt: skip
    assert tracker.elite_line(7, []) == 'Elites: 0 killed · 3 alive of 7-9'

    tracker.apply([died(1, 7), died(10, 7), died(11, 7)])

    assert tracker.elite_line(7, []) == 'Elites: 1 killed · 2 alive of 7-9'

    tracker.apply([died(12, 7)])

    assert tracker.elite_line(7, []) == 'Elites: 2 killed · 1 alive of 7-9'


def test_the_elite_line_knows_the_fixed_groups_of_the_levels_pieces_before_they_are_seen():
    from inventory_tracking.levels.model import Room

    # Travincal (83): piece 654 places the three council super uniques (elites.json, 2026-10-06).
    rooms = [Room(654, 1140, 280, 8, 8, 0, (1140, 280, 32, 32))]
    tracker = ZoneTracker()
    assert tracker.elite_line(83, rooms) == 'Elites: 0 killed · 0 alive of 6-8 · fixed: 0 killed of 3'

    tracker.apply([elite(1, 5762, 1494, flags=0x0A, txt_id=346, area=83, super_id=27)])  # Geleb Flamefinger
    assert tracker.elite_line(83, rooms) == 'Elites: 0 killed · 0 alive of 6-8 · fixed: 0 killed · 1 alive of 3'

    tracker.apply([died(1, 83)])
    assert tracker.elite_line(83, rooms) == 'Elites: 0 killed · 0 alive of 6-8 · fixed: 1 killed of 3'


def test_a_rejoined_game_keeps_its_elite_groups(tmp_path):
    store = tmp_path / 'games.json'
    tracker = ZoneTracker(store)
    tracker.apply([entered(7, 0xAAAA), elite(1, 5000, 5000), died(1, 7), elite(2, 6000, 5000)])
    tracker.save()

    again = ZoneTracker(store)
    again.apply([entered(7, 0xAAAA)])

    assert again.elite_line(7, []) == 'Elites: 1 killed · 1 alive of 7-9'


def test_the_elite_line_uses_the_rooms_the_level_guide_read():
    from inventory_tracking.levels.model import Room

    tracker = ZoneTracker()
    assert tracker.elite_line(83) == 'Elites: 0 killed · 0 alive of 6-8'

    tracker.level_layout(83, [Room(654, 1140, 280, 8, 8, 0, (1140, 280, 32, 32))])

    assert tracker.elite_line(83) == 'Elites: 0 killed · 0 alive of 6-8 · fixed: 0 killed of 3'


def test_a_loading_screen_read_as_leaving_keeps_what_was_counted_on_the_trip(tmp_path):
    # A waypoint's loading screen reads as 'left_game' (terror-probe.jsonl 2026-10-06: town 103,
    # left_game, 0.3 s later level 79 of the same game, town 103 again with its seed). Coming back
    # to town restored the copy saved before the trip over the elites counted on it (user, 2026-10-06).
    tracker = ZoneTracker(tmp_path / 'terror-games.json')
    tracker.apply([entered(1, 0xAAAA), entered(6, 0xBBBB), elite(1, 5000, 5000, area=6), died(1, 6)])
    tracker.apply([entered(1, 0xAAAA), {'event': 'left_game'}, entered(7, 0xCCCC)])
    tracker.apply([elite(2, 5000, 5000), died(2, 7), elite(3, 6000, 5000)])

    assert tracker.elite_line(6, []).startswith('Elites: 1 killed · 0 alive')  # a level out of town: the same game

    tracker.apply([entered(1, 0xAAAA)])

    assert tracker.elite_line(7, []) == 'Elites: 1 killed · 1 alive of 7-9'
    assert tracker.elite_line(6, []).startswith('Elites: 1 killed · 0 alive')


def test_a_stored_game_joined_late_is_merged_into_what_was_counted_since(tmp_path):
    # The first level entered after a false leave can be a town not seen before (another act's).
    store = tmp_path / 'terror-games.json'
    tracker = ZoneTracker(store)
    tracker.apply([entered(1, 0xAAAA), entered(6, 0xBBBB), herald(9, 6, 5100, 5200), died(9, 6)])
    tracker.apply([{'event': 'left_game'}, entered(40, 0xDDDD), entered(7, 0xCCCC), elite(2, 5000, 5000), died(2, 7)])
    assert tracker.next_tier == 1  # a town first: it may be another game

    tracker.apply([entered(1, 0xAAAA)])

    assert tracker.next_tier == 2
    assert tracker.elite_line(7, []) == 'Elites: 1 killed · 0 alive of 7-9'
    assert tracker_for(store, 0xBBBB).elite_line(7, []) is not None  # saved as one game

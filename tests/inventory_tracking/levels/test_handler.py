"""Handler helpers: declarative POIs over preset names; problems instead of guesses."""

from inventory_tracking.levels.handler import Handler, PoiSpec, stairs_down, target, waypoint
from inventory_tracking.levels.model import SUPER_CHEST, LevelSnapshot, Location, Room


def snapshot(*presets):
    rooms = tuple(Room(preset, 100 + 12 * i, 100, 12, 12) for i, preset in enumerate(presets))
    return LevelSnapshot(Location(1, 0, 500, 500), rooms)


SUMMONER = target('Arcane Sanctuary', areas={74}, label='Summoner', preset=r'Act 2 - Arcane Summoner [NSEW]')


def test_target_finds_the_unique_matching_room():
    guidance = SUMMONER.guide(snapshot(524, 512, 525))

    assert [(p.label, p.room.preset, p.kind) for p in guidance.pois] == [('Summoner', 525, 'target')]
    assert guidance.problems == ()


def test_missing_target_is_a_problem():
    guidance = SUMMONER.guide(snapshot(524, 512))

    assert guidance.pois == ()
    assert guidance.problems == ('Summoner: no room matches',)


def test_two_matching_rooms_are_a_problem_not_a_guess():
    guidance = SUMMONER.guide(snapshot(525, 527))

    assert guidance.pois == ()
    assert guidance.problems == ('Summoner: 2 rooms match',)


def test_stairs_down_matches_the_family_next_rooms_only():
    handler = stairs_down('Tower Cellar 1-4', areas={21, 22, 23, 24}, family='Act 1 - Crypt')

    guidance = handler.guide(snapshot(123, 139, 146))  # NSEW, Prev W, Next N

    assert [(p.label, p.room.preset, p.kind) for p in guidance.pois] == [('Next level', 146, 'stairs')]


def test_optional_waypoint_is_shown_when_present_and_silent_when_absent():
    handler = stairs_down(
        'Durance of Hate 1-2', areas={100, 101}, family='Act 3 - Mephisto', extra=[waypoint('Act 3 - Mephisto')]
    )

    with_waypoint = handler.guide(snapshot(788, 792))
    without = handler.guide(snapshot(788))

    assert [(p.label, p.kind) for p in with_waypoint.pois] == [('Next level', 'stairs'), ('Waypoint', 'waypoint')]
    assert [p.label for p in without.pois] == ['Next level']
    assert without.problems == ()


def test_handlers_default_to_unconfirmed():
    assert not stairs_down('x', areas={1}, family='Act 1 - Crypt').confirmed
    assert target('x', areas={1}, label='y', preset='z', confirmed=True).confirmed


def chunks(preset, block, variant=0):
    """A large preset split into 8x8 Room2 chunks that all share one preset object."""
    bx, by, bw, bh = block
    return tuple(Room(preset, x, y, 8, 8, variant, block) for x in range(bx, bx + bw, 8) for y in range(by, by + bh, 8))


def test_chunks_of_one_preset_are_one_poi_at_the_preset_centre():
    rooms = chunks(1047, (2040, 2983, 40, 40)) + chunks(1042, (2000, 2983, 40, 40))
    handler = target('Halls', areas={123}, label='Next level', preset=r'Act 5 - Temple (NE|NW|SW) Down')

    guidance = handler.guide(LevelSnapshot(Location(123, 0, 0, 0), rooms))

    [poi] = guidance.pois
    assert poi.room.center == ((2040 + 20) * 5, (2983 + 20) * 5)
    assert guidance.problems == ()


def test_two_separate_preset_instances_are_still_ambiguous():
    rooms = chunks(1047, (2040, 2983, 16, 16)) + chunks(1047, (2100, 2983, 16, 16))
    handler = target('Halls', areas={123}, label='Next level', preset=r'Act 5 - Temple NW Down')

    guidance = handler.guide(LevelSnapshot(Location(123, 0, 0, 0), rooms))

    assert guidance.pois == ()
    assert guidance.problems == ('Next level: 2 areas match',)


def test_a_target_preset_covering_the_player_is_not_a_direction():
    # Tower Cellar 5: all 16 chunks are 'Crypt Countess X' (evidence 2026-09-30); pointing at the
    # middle of the level the player stands in would mislead.
    rooms = chunks(159, (2500, 1000, 32, 32), variant=1)
    handler = target('Tower Cellar 5', areas={25}, label='Countess', preset=r'Act 1 - Crypt Countess X')

    guidance = handler.guide(LevelSnapshot(Location(25, 0, 2510 * 5, 1010 * 5), rooms))

    assert guidance.pois == ()
    assert guidance.problems == ('Countess: the preset is the whole area around the player (variant 1)',)


def test_standing_in_a_small_multi_chunk_target_is_a_here_poi():
    # WSK stairs are 16x16 presets in four 8x8 chunks; the guard is for whole-level presets only.
    stairs = chunks(1074, (0, 0, 16, 16))  # Act 5 - Baal Prev NEW
    rest = tuple(Room(1073, x, y, 8, 8) for x in range(16, 64, 8) for y in range(0, 32, 8))
    handler = target('WSK 3', areas={130}, label='Worldstone Keep 2', preset=r'Act 5 - Baal Prev [NSEW]+')

    guidance = handler.guide(LevelSnapshot(Location(130, 0, 5 * 5, 5 * 5), stairs + rest))

    assert [p.label for p in guidance.pois] == ['Worldstone Keep 2']
    assert guidance.problems == ()


# A mark on an object the preset's files place (PoiSpec.thing; data/preset_objects.json).
POOL_A, LAVA_W, LAVA_E = 1040, 1056, 1055  # level_presets.json: Act 5 - Ice Pool A, Lava W, Lava E
CAVERN = target('Drifter Cavern', areas={116}, label='Super chest', preset=r'Act 5 - Ice Pool [AB]', thing=SUPER_CHEST)


def near(point):
    return round(point[0]), round(point[1])  # the spot is kept in tiles: a unit is a fifth of one


def pool(variants, *, at=(100, 200), player=(520, 1020)):
    """The 32x32 cavern as sixteen 8x8 chunks of one preset; `variants`: the layout each chunk has read."""
    block = (*at, 32, 32)
    rooms = tuple(
        Room(POOL_A, at[0] + 8 * (i % 4), at[1] + 8 * (i // 4), 8, 8, variants[i % len(variants)], block)
        for i in range(16)
    )
    return LevelSnapshot(Location(116, 0, *player), rooms)


def test_a_thing_mark_sits_where_the_layout_places_the_object_even_with_the_player_inside():
    guidance = CAVERN.guide(pool([4]))  # layout 4 puts the chest at (21, 21) units

    [poi] = guidance.pois
    assert (poi.label, poi.kind, near(poi.point)) == ('Super chest', 'target', (100 * 5 + 21, 200 * 5 + 21))
    assert guidance.problems == ()


def test_a_thing_mark_takes_the_layout_from_whichever_chunk_has_read_it():
    guidance = CAVERN.guide(pool([None, None, 5]))  # layout 5: (10, 135)

    assert [near(poi.point) for poi in guidance.pois] == [(100 * 5 + 10, 200 * 5 + 135)]


def test_a_thing_mark_with_no_layout_read_is_a_problem_not_a_guess():
    guidance = CAVERN.guide(pool([None]))

    assert guidance.pois == ()
    assert guidance.problems == ('Super chest: layout variant unknown',)


def test_a_thing_mark_in_a_room_not_read_yet_is_the_room_until_its_layout_is_known():
    handler = target('Pit', areas={125}, label='Super chest', preset=r'Act 5 - Lava W', thing=SUPER_CHEST)
    far = Room(LAVA_W, 300, 0, 24, 24)

    guidance = handler.guide(LevelSnapshot(Location(125, 0, 500, 500), (far, Room(0, 96, 96, 8, 8))))

    assert [(poi.room, poi.spot) for poi in guidance.pois] == [(far, None)]
    assert guidance.problems == ()


def test_a_thing_mark_in_a_layout_without_the_object_is_a_problem():
    handler = target('Pit', areas={125}, label='Super chest', preset=r'Act 5 - Lava W', thing=SUPER_CHEST)
    rooms = (Room(LAVA_W, 0, 0, 24, 24, 0),)

    guidance = handler.guide(LevelSnapshot(Location(125, 0, 500, 500), rooms))

    assert guidance.pois == ()
    assert guidance.problems == ('Super chest: the layout (variant 0) places 0 of object 397',)


def test_each_thing_mark_is_every_room_whose_layout_holds_the_object():
    spec = PoiSpec('Super chest', r'Act 5 - Lava [NSEW]', each=True, thing=SUPER_CHEST)
    handler = Handler('Abaddon', frozenset({125}), (spec,))
    rooms = (
        Room(LAVA_W, 0, 0, 24, 24, 1),  # (55, 49)
        Room(LAVA_W, 24, 0, 24, 24, 0),  # a dead end without a chest
        Room(LAVA_E, 48, 0, 24, 24, 1),  # (65, 100)
        Room(LAVA_E, 72, 0, 24, 24, None),  # not read yet
    )

    guidance = handler.guide(LevelSnapshot(Location(125, 0, 500, 500), rooms))

    assert [near(poi.point) for poi in guidance.pois] == [(55, 49), (48 * 5 + 65, 100)]
    assert guidance.problems == ()

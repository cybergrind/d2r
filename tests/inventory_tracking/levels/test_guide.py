"""Level guide: rule-driven arrow on entry, 5 s lease, never blocks the lock, never fails silently."""

import logging
import threading

import pytest

from inventory_tracking.levels.geometry import arrow, compass, pointer
from inventory_tracking.levels.guide import LevelGuide, pointer_lines
from inventory_tracking.levels.model import Location, Room
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import replay


@pytest.mark.parametrize(
    ('dx', 'dy', 'expected'),
    [(0, -100, '↗'), (0, 100, '↙'), (100, 0, '↘'), (-100, 0, '↖'), (100, -100, '→'), (-100, -100, '↑')],
)
def test_arrow_uses_the_isometric_screen_direction(dx, dy, expected):
    assert arrow(dx, dy) == expected


def test_compass_names_the_map_axis():
    assert [compass(0, -5), compass(0, 5), compass(5, 0), compass(-5, 0)] == ['north', 'south', 'east', 'west']


def test_pointer_line_names_target_and_arm():
    snapshot = replay('arcane_summoner_s')
    location = snapshot.location

    guidance = handler_for(74).guide(snapshot)
    lines = pointer_lines([pointer(poi, location) for poi in guidance.pois])

    assert [line.text for line in lines] == ['↗  Summoner: north']
    assert lines[0].arrow == '↗'


class Source:
    pid, images, capture = 7, {}, {}

    def ensure_connected(self):
        pass


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def make_guide(areas, *, fixture='arcane_summoner_w', lock=None, fail=None, evidence=None):
    """`areas` yields the area seen by each poll; room reads replay a real dump."""
    shown, clock, sequence = [], Clock(), iter(areas)
    snapshot = replay(fixture)
    x, y, rooms = snapshot.location.x, snapshot.location.y, list(snapshot.rooms)
    current = {}

    def observe(pid, images, capture, *, rooms_wanted=False):
        if fail:
            raise fail
        if not rooms_wanted:
            current['area'] = next(sequence)
        area = current['area']
        location = None if area is None else Location(area, 0x1000, x, y)
        return location, rooms if rooms_wanted else []

    guide = LevelGuide(
        Source(),
        capture_lock=lock or threading.Lock(),
        focused=lambda images: True,
        display=shown.append,
        seconds=5,
        poll_interval=0.5,
        clock=clock,
        observe=lambda pid, images, capture, rooms=False: observe(pid, images, capture, rooms_wanted=rooms),
        evidence=evidence,
    )
    return guide, shown, clock


def test_second_real_game_points_east():
    guide, shown, _ = make_guide([40, 74])

    guide.poll(1.0)
    guide.poll(2.0)
    guide.tick()

    *lines, card = shown[-1]
    assert [line.text for line in lines] == ['↘  Summoner: east']
    assert type(card).__name__ == 'MapCard'


def test_arrow_shows_on_entry_for_five_seconds_then_clears():
    guide, shown, clock = make_guide([40, 74, 74])

    guide.poll(1.0)
    assert guide.visible is None
    guide.poll(2.0)
    guide.tick()
    assert shown[-1]

    clock.now += 4.9
    guide.poll(3.0)
    guide.tick()
    assert shown[-1]
    clock.now += 0.2
    guide.tick()
    assert shown[-1] == []
    assert guide.visible is None


def test_reentry_shows_again_but_staying_does_not():
    guide, _, _ = make_guide([74, 74, 1, 74])

    guide.poll(1.0)
    assert guide.visible is not None
    guide.dismiss()
    guide.poll(2.0)
    assert guide.visible is None
    guide.poll(3.0)
    guide.poll(4.0)
    assert guide.visible is not None


def test_busy_capture_lock_skips_the_poll():
    lock = threading.Lock()
    guide, _, _ = make_guide([74], lock=lock)

    with lock:
        guide.poll(1.0)
    assert guide.visible is None
    guide.poll(1.1)
    assert guide.visible is not None


def test_read_failure_is_logged_once_as_a_warning(caplog):
    guide, _, _ = make_guide([], fail=ValueError('Unmapped or unreadable range at 0x18'))

    with caplog.at_level(logging.DEBUG):
        guide.poll(1.0)
        guide.poll(2.0)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert 'Unmapped' in warnings[0].getMessage()


def test_guided_area_without_its_target_is_reported(caplog):
    guide, _, _ = make_guide([74, 74], fixture='arcane_summoner_w')
    guide.observe = lambda pid, images, capture, rooms=False: (Location(74, 0x1000, 0, 0), [])

    with caplog.at_level(logging.INFO):
        guide.poll(1.0)

    assert guide.visible is None
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == ['Level guide: Arcane Sanctuary (74): Summoner: no room matches']


def test_each_entry_saves_one_evidence_record_after_releasing_the_lock():
    lock, saved = threading.Lock(), []

    def save(record):
        assert not lock.locked(), 'evidence must be written outside the capture lock'
        saved.append(record)

    guide, _, _ = make_guide([40, 74, 74, 1, 74], lock=lock, evidence=save)
    for tick in range(5):
        guide.poll(float(tick))

    assert [(r['area_id'], r['pois'][0]['preset']) for r in saved] == [(74, 525), (74, 525)]


def test_a_failed_lookup_is_saved_once_while_retrying():
    saved = []
    guide, _, _ = make_guide([74, 74, 74], evidence=saved.append)
    guide.observe = lambda pid, images, capture, rooms=False: (Location(74, 0x1000, 0, 0), [])

    for tick in range(3):
        guide.poll(float(tick))

    assert [r['problems'] for r in saved] == [['Summoner: no room matches']]


def test_evidence_failure_is_a_warning_not_a_crash(caplog):
    def broken(record):
        raise OSError('disk full')

    guide, _, _ = make_guide([74], evidence=broken)

    with caplog.at_level(logging.WARNING):
        guide.poll(1.0)

    assert guide.visible is not None
    assert any('disk full' in r.getMessage() for r in caplog.records)


def test_card_carries_the_level_map():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, _ = make_guide([40, 74])
    guide.poll(1.0)
    guide.poll(2.0)
    guide.tick()

    [card] = [line for line in shown[-1] if isinstance(line, MapCard)]
    assert len(card.rooms) == 61
    assert [p.label for p in card.pois] == ['Summoner']


def test_player_dot_and_arrow_follow_the_player_while_shown():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, _ = make_guide([74, 74, 74])
    guide.poll(1.0)
    guide.tick()
    first = next(line for line in shown[-1] if isinstance(line, MapCard))

    # Walk to 10 tiles north of the Summoner room centre (game 2: east tip, centre 5174,1090).
    guide.observe = lambda pid, images, capture, rooms=False: (Location(74, 0x1000, 5174 * 5, 1080 * 5), [])
    guide.poll(2.0)
    guide.tick()

    moved = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert moved.player == (5174.0, 1080.0)
    assert moved.player != first.player
    assert shown[-1][0].text.endswith('Summoner: south')  # the room centre is now just south of the player


def test_no_position_updates_after_expiry():
    guide, shown, clock = make_guide([74, 74])
    guide.poll(1.0)
    clock.now += 6
    guide.tick()
    reads = []
    guide.observe = lambda pid, images, capture, rooms=False: reads.append(rooms) or (Location(74, 0x1000, 0, 0), [])

    guide.poll(2.0)

    assert guide.visible is None
    assert shown[-1] == []


def test_show_redisplays_the_card_with_a_fresh_position():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, clock = make_guide([74, 74])
    guide.poll(1.0)
    clock.now += 6
    guide.tick()
    assert guide.visible is None
    snapshot = replay('arcane_summoner_w')
    here = Location(74, 0x1000, 5174 * 5, 1080 * 5)
    guide.observe = lambda pid, images, capture, rooms=False: (here, list(snapshot.rooms) if rooms else [])

    assert guide.show()
    guide.tick()

    *lines, card = shown[-1]
    assert [line.text for line in lines] == ['↙  Summoner: south']
    assert isinstance(card, MapCard)
    assert card.player == (5174.0, 1080.0)


def test_show_in_an_unguided_level_draws_just_the_map():
    from inventory_tracking.osd.level_map import MapCard

    snapshot = replay('arcane_summoner_s')
    guide, shown, _ = make_guide([])
    guide.observe = lambda pid, images, capture, rooms=False: (
        Location(1, 0x1000, snapshot.location.x, snapshot.location.y),
        list(snapshot.rooms) if rooms else [],
    )

    assert guide.show()
    guide.tick()

    [card] = shown[-1]
    assert isinstance(card, MapCard)
    assert card.pois == ()


def test_show_gives_up_when_the_capture_lock_stays_busy():
    lock = threading.Lock()
    guide, _, _ = make_guide([74], lock=lock)
    guide.lock_timeout = 0.01

    with lock:
        assert not guide.show()
    assert guide.visible is None


def pinned_guide(areas):
    guide, shown, clock = make_guide(areas)
    snapshot = replay('arcane_summoner_w')
    guide.observe = lambda pid, images, capture, rooms=False: (
        snapshot.location,
        list(snapshot.rooms) if rooms else [],
    )
    return guide, shown, clock


def test_double_press_pins_the_card_until_the_next_double_press():
    guide, shown, clock = pinned_guide([])

    assert guide.press(10.0)
    assert guide.press(10.15)  # second press within 0.2 s: pin
    clock.now += 60
    guide.tick()
    assert shown[-1]  # still shown a minute later
    assert guide.pinned

    guide.press(20.0)
    guide.press(20.15)  # double press again: unpin and hide
    assert not guide.pinned
    assert guide.visible is None
    assert shown[-1] == []


def test_presses_far_apart_are_two_single_shows():
    guide, shown, clock = pinned_guide([])

    guide.press(10.0)
    guide.press(10.9)
    clock.now += 6
    guide.tick()

    assert not guide.pinned
    assert shown[-1] == []


def test_single_press_while_pinned_refreshes_and_stays_pinned():
    guide, _, _ = pinned_guide([])
    guide.press(10.0)
    guide.press(10.15)

    assert guide.press(15.0)
    assert guide.pinned


def test_pinned_card_follows_into_an_unguided_level_as_a_map():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, _ = pinned_guide([])
    guide.press(10.0)
    guide.press(10.15)
    town = Location(1, 0x2000, 100, 100)
    guide.observe = lambda pid, images, capture, rooms=False: (town, [Room(1, 0, 0, 40, 40)] if rooms else [])

    guide.poll(100.0)
    guide.tick()

    [card] = shown[-1]
    assert isinstance(card, MapCard)
    assert card.rooms == ((0, 0, 40, 40),)


def test_pinned_card_hides_while_unfocused_and_returns_on_focus():
    guide, shown, _ = pinned_guide([])
    guide.press(10.0)
    guide.press(10.15)
    focus = {'on': False}
    guide.focused = lambda images: focus['on']

    guide.tick()
    assert shown[-1] == []
    focus['on'] = True
    guide.tick()
    assert shown[-1]


def test_a_level_with_nothing_to_mark_is_read_once_and_stays_quiet():
    # Great Marsh without a clearing (its only, optional, POI): rooms read, no POI, nothing missing.
    guide, shown, _ = make_guide([77, 77, 77], fixture='arcane_summoner_w')
    reads = []
    observe = guide.observe
    guide.observe = lambda pid, images, capture, rooms=False: (
        reads.append(rooms) or observe(pid, images, capture, rooms)
    )

    for tick in range(3):
        guide.poll(float(tick))

    assert reads.count(True) == 1
    assert guide.visible is None
    assert shown == []


def test_walkable_tiles_survive_leaving_and_returning_in_the_same_game():
    # User, 2026-09-30: Cold Plains walls (generated terrain, never in the wall library) were
    # lost after a trip to town. The same level (same rooms) keeps what was read this game.
    from inventory_tracking.levels.model import Walkable
    from inventory_tracking.osd.level_map import MapCard

    reads = iter([[Walkable(0, 0, 1, 1, '1')], [Walkable(8, 0, 1, 1, '0')], [], []])
    guide, shown, _ = make_guide([74, 74, 1, 74])
    guide.observe_walls = lambda pid, images, capture: next(reads)

    guide.poll(1.0)  # entry: first room
    guide.poll(2.0)  # still shown: a second room loads, the first is kept
    guide.tick()
    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert card.walkable == ((0, 0, 1, 1, '1'), (8, 0, 1, 1, '0'))

    guide.poll(3.0)  # to town
    guide.poll(4.0)  # back: both rooms are still known
    guide.tick()
    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert card.walkable == ((0, 0, 1, 1, '1'), (8, 0, 1, 1, '0'))


def test_a_new_game_with_other_rooms_does_not_inherit_walls():
    from inventory_tracking.levels.model import Walkable
    from inventory_tracking.osd.level_map import MapCard

    reads = iter([[Walkable(0, 0, 1, 1, '1')], []])
    guide, shown, _ = make_guide([74, 1, 74])
    guide.observe_walls = lambda pid, images, capture: next(reads)
    guide.poll(1.0)
    guide.poll(2.0)

    observe = guide.observe  # the next game: the same area, a different room layout

    def other_game(pid, images, capture, rooms=False):
        location, found = observe(pid, images, capture, rooms)
        return location, found[1:]

    guide.observe = other_game
    guide.poll(3.0)
    guide.tick()
    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert card.walkable == ()


def test_a_failing_walls_read_keeps_the_card():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, _ = make_guide([74])

    def broken(pid, images, capture):
        raise ValueError('grid unreadable')

    guide.observe_walls = broken
    guide.poll(1.0)
    guide.tick()

    assert any(isinstance(line, MapCard) for line in shown[-1])


def test_rooms_of_a_learned_layout_have_walls_on_entry_and_live_reads_teach_the_library(tmp_path):
    from inventory_tracking.levels.model import Walkable, pack_tiles
    from inventory_tracking.levels.walls import WallLibrary
    from inventory_tracking.osd.level_map import MapCard

    rooms = [r for r in replay('lower_kurast_camp').rooms if r.variant is not None and r.preset]
    known, loaded = rooms[0], rooms[1]
    library = WallLibrary(tmp_path / 'walls.json')
    cells = pack_tiles('1' * known.width * known.height, known.width)
    library.learn([known], [Walkable(known.x, known.y, known.width, known.height, cells)])

    guide, shown, _ = make_guide([79], fixture='lower_kurast_camp')
    guide.library = library
    live = Walkable(
        loaded.x, loaded.y, loaded.width, loaded.height, pack_tiles('0' * loaded.width * loaded.height, loaded.width)
    )
    guide.observe_walls = lambda pid, images, capture: [live]
    guide.poll(1.0)
    guide.tick()

    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert {(x, y) for x, y, *_ in card.walkable} >= {(known.x, known.y), (loaded.x, loaded.y)}
    assert WallLibrary(tmp_path / 'walls.json').known([loaded]) == [live]


def test_the_map_carries_the_visited_rooms_of_the_current_area():
    from inventory_tracking.osd.level_map import MapCard

    guide, shown, _ = make_guide([74])
    asked = []

    def visited(area):
        asked.append(area)
        return set()

    guide.visited_rooms = visited
    guide.poll(1.0)
    guide.tick()

    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert asked[-1] == 74
    assert card.visited == ()  # none known: unshaded


def test_the_map_carries_live_dots_of_the_current_area():
    from inventory_tracking.osd.level_map import MapCard, MapPoi

    guide, shown, _ = make_guide([74])
    dot = MapPoi('Herald T1', 'herald', 3.0, 4.0)
    guide.map_dots = lambda area: [dot] if area == 74 else []
    guide.poll(1.0)
    guide.tick()

    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert card.pois[-1] == dot


def test_a_waypoint_seen_near_the_player_moves_its_mark_from_the_room_centre_onto_the_object():
    from inventory_tracking.levels.model import Poi, Room
    from inventory_tracking.levels.spots import on_waypoint

    room = Room(296, 4524, 1336, 12, 12)  # 'Act 1 - Catacombs Waypoint E', evidence 35/20261005T064253
    waypoint, stairs = Poi('Waypoint', room, 'waypoint'), Poi('Next level', room, 'stairs')

    assert on_waypoint(waypoint, [(10.0, 10.0), (4528.0, 1341.2)]).spot == (4528.0, 1341.2)
    assert on_waypoint(waypoint, [(10.0, 10.0)]) is waypoint  # another room's waypoint: the centre stands
    assert on_waypoint(stairs, [(4528.0, 1341.2)]) is stairs


def test_the_guide_remembers_waypoints_for_the_level_and_survives_a_failed_read():
    guide, shown, _ = make_guide([74, 74, 74])
    reads = iter([[(1.0, 2.0)], [(3.0, 4.0)]])
    guide.observe_waypoints = lambda pid, images, capture: next(reads)

    guide.poll(1.0)
    guide.poll(2.0)
    assert guide.waypoints == {(1.0, 2.0), (3.0, 4.0)}

    guide.poll(3.0)  # the iterator is exhausted: a failed read keeps the card and what was seen
    guide.tick()
    assert guide.waypoints == {(1.0, 2.0), (3.0, 4.0)}
    assert shown[-1]


def test_a_guide_started_pinned_shows_the_map_in_every_level_until_a_double_press():
    from inventory_tracking.config import APPRAISAL

    guide, shown, clock = make_guide([74, 74, 1, 1])
    guide.pinned = APPRAISAL.level_guide_pinned  # what serve passes
    assert guide.pinned

    guide.poll(1.0)
    clock.now += 60
    guide.tick()
    assert shown[-1]  # no expiry

    guide.poll(2.0)
    guide.poll(3.0)  # an unguided level (town): the map alone
    guide.tick()
    assert shown[-1]

    guide.press(100.0)
    guide.press(100.15)
    assert not guide.pinned
    assert shown[-1] == []


def knowing(guide, **neighbours):
    """Later room reads of `guide` see the levels behind some Cold Plains rooms: index=areas."""
    from dataclasses import replace

    observe = guide.observe

    def read(pid, images, capture, rooms=False):
        location, found = observe(pid, images, capture, rooms)
        found = list(found)
        for index, areas in neighbours.items() if rooms else ():
            found[int(index[1:])] = replace(found[int(index[1:])], leads_to=areas)
        return location, found

    guide.observe = read
    return observe


def labels(guide):
    return [line.text.split('  ')[1].split(':')[0] for line in guide.visible[:-1]]


UNNAMED_GAP = 20  # cold_plains_entry: an open border gap ('Act 1 - Wild Border 4', DS1 file 3) not read yet


def test_an_exit_gets_its_name_while_the_card_is_shown_once_its_far_side_is_read():
    # User, 2026-10-05: outdoor exits stayed a plain 'Exit' because rooms were read once per entry.
    guide, _, clock = make_guide([3, 3, 3], fixture='cold_plains_entry')
    guide.pinned = True
    guide.poll(1.0)
    assert labels(guide).count('Exit') == 2

    knowing(guide, **{f'r{UNNAMED_GAP}': (4,)})
    guide.poll(2.0)  # too soon for another room read
    assert labels(guide).count('Exit') == 2
    clock.now += 3.0
    guide.poll(3.0)

    assert labels(guide).count('Stony Field') == 1
    assert 'Exit' not in labels(guide)  # the last gap is the Burial Grounds by elimination


def test_an_exit_named_once_stays_named_for_the_game_and_is_forgotten_in_the_menu():
    guide, _, _ = make_guide([3, 1, 3, None, 3], fixture='cold_plains_entry')
    guide.pinned = True
    plain = knowing(guide, **{f'r{UNNAMED_GAP}': (4,)})
    guide.poll(1.0)
    assert 'Stony Field' in labels(guide)

    guide.observe = plain  # after a town trip the far side is not readable again
    guide.poll(2.0)
    guide.poll(3.0)
    assert 'Stony Field' in labels(guide)

    guide.poll(4.0)  # the menu, then a new game
    guide.poll(5.0)
    assert 'Stony Field' not in labels(guide)


def test_walls_survive_room_details_that_load_later():
    from inventory_tracking.levels.model import Walkable
    from inventory_tracking.osd.level_map import MapCard

    reads = iter([[Walkable(0, 0, 1, 1, '1')], [], []])
    guide, shown, _ = make_guide([3, 1, 3], fixture='cold_plains_entry')
    guide.pinned = True
    guide.observe_walls = lambda pid, images, capture: next(reads)
    guide.poll(1.0)
    guide.poll(2.0)

    knowing(guide, r0=(2,))  # the same level, one more room detail readable
    guide.poll(3.0)
    guide.tick()

    card = next(line for line in shown[-1] if isinstance(line, MapCard))
    assert card.walkable == ((0, 0, 1, 1, '1'),)


def test_single_press_switches_a_shown_map_between_the_local_view_and_the_whole_level():
    # user, 2026-10-06
    guide, _, _ = pinned_guide([])
    guide.press(10.0)  # nothing shown yet: this press only shows the card
    assert guide.visible[-1].whole is False

    guide.press(11.0)
    assert guide.visible[-1].whole is True
    guide.press(12.0)
    assert guide.visible[-1].whole is False


def test_a_double_press_does_not_switch_the_view():
    guide, _, _ = pinned_guide([])
    guide.press(10.0)
    guide.press(10.15)  # pinned
    assert guide.pinned
    assert guide.visible[-1].whole is False

    guide.press(20.0)
    guide.press(20.3)  # 0.3 s apart: two single presses, back to the local view
    assert guide.pinned
    assert guide.visible[-1].whole is False
    guide.press(30.0)
    assert guide.visible[-1].whole is True
    guide.press(40.0)
    guide.press(40.1)  # double: unpin; the first press's switch is taken back
    assert not guide.pinned
    assert guide.whole is True


def test_the_rooms_of_an_entered_level_are_handed_on():
    # The Terror card's elite line reads the level's fixed groups from them (terror/tracker.py).
    guide, _, _ = make_guide([74])
    got = []
    guide.on_rooms = lambda area, rooms: got.append((area, len(rooms)))

    guide.poll(1.0)

    assert got[-1][0] == 74
    assert got[-1][1] > 0

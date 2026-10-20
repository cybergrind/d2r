"""The town's waypoint, clicked from where a game or a portal puts the character (routes/lower-kurast-loop-plan.md
phase 1): the game walks there and opens the panel."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.game.records import Thing
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.waypoint import open_panel
from tests.inventory_tracking.macros.fakes import Game, player, world


KURAST_DOCKS, LOWER_KURAST = 75, 79
WAYPOINT_ACT3 = 237  # objects.txt WaypointAct3


def docks(**at) -> Game:
    """Kurast Docks as the portal from Lower Kurast leaves the character: (5158, 5068), 20 units south of the
    waypoint (the player's nine trips of 2026-10-15)."""
    play = Game(world(KURAST_DOCKS, player=player(KURAST_DOCKS, x=5158.0, y=5068.0, **at)))
    play.thing = Thing(5, WAYPOINT_ACT3, 2, 5159.0, 5049.0)
    play.thing_above = 0.0  # a waypoint's picture lies on its ground point
    return play


def test_the_waypoint_in_view_is_clicked_and_done_with_its_panel_open():
    play = docks()

    open_panel(play.run())

    assert play.world.open_panels == ('waypoint',)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.said[-2:] == ['Opening the waypoint, 19 away', 'the waypoint: opened']


def test_a_waypoint_used_before_is_clicked_all_the_same():
    play = docks()
    assert play.thing is not None
    assert play.thing.mode  # activated: its mode is not 0, unlike a chest's that says "opened already"

    open_panel(play.run())

    assert play.world.open_panels == ('waypoint',)


def test_out_of_town_it_is_refused():
    play = Game(world(LOWER_KURAST))

    with pytest.raises(Abort, match='not in town'):
        open_panel(play.run())
    assert play.keys.events == []


def test_with_no_waypoint_shown_it_says_so():
    play = docks()
    play.thing = None

    with pytest.raises(Abort, match='no waypoint in sight'):
        open_panel(play.run())
    assert play.keys.events == []


PANDEMONIUM_FORTRESS = 103
WAYPOINT_ACT4 = 398  # objects.txt WaypointAct4Town


def test_the_layout_puts_the_tabs_and_rows_where_the_hand_reckons_them():
    # The fakes' 2560 x 1418 window (CybergrindAA's, the takes' `rect`): a layout unit is 1418 / 2160 pixels.
    from inventory_tracking.macros.waypoint import panel_point, row_point, tab_point

    rect = (1920, 0, 2560, 1418)
    assert panel_point(rect, *tab_point(2)) == pytest.approx((0.2095, 0.2049), abs=1e-3)  # act III
    assert panel_point(rect, *tab_point(3)) == pytest.approx((0.2539, 0.2049), abs=1e-3)  # act IV
    assert panel_point(rect, *row_point(0)) == pytest.approx((0.2021, 0.2387), abs=1e-3)
    assert panel_point(rect, *row_point(4)) == pytest.approx((0.2021, 0.4665), abs=1e-3)


def test_the_levels_tab_and_row_come_from_levels_txt():
    from inventory_tracking.macros.waypoint import WaypointRow, waypoint_of

    assert waypoint_of(LOWER_KURAST) == WaypointRow(2, 4)
    assert waypoint_of(PANDEMONIUM_FORTRESS) == WaypointRow(3, 0)
    assert waypoint_of(KURAST_DOCKS) == WaypointRow(2, 0)
    assert waypoint_of(80) == WaypointRow(2, 5)  # Kurast Bazaar
    assert waypoint_of(77) == WaypointRow(2, 2)  # Great Marsh
    assert waypoint_of(2) is None  # the Blood Moor has none


def test_from_kurast_docks_the_waypoint_takes_the_character_to_pandemonium_fortress():
    from inventory_tracking.macros.waypoint import travel

    play = docks()

    travel(play.run(), PANDEMONIUM_FORTRESS)

    assert play.character.area == PANDEMONIUM_FORTRESS
    # the waypoint, act IV's tab, its first row; then the arrival's check: a weapon swap and back
    assert [event[0] for event in play.keys.events] == ['click'] * 3 + ['key'] * 2
    assert play.said[-1] == 'The Pandemonium Fortress: there'


def test_from_pandemonium_fortress_the_waypoint_takes_the_character_to_lower_kurast():
    from inventory_tracking.macros.waypoint import travel

    start = player(PANDEMONIUM_FORTRESS, x=5048.0, y=5044.0)  # where every game of 2026-10-15 began
    play = Game(world(PANDEMONIUM_FORTRESS, player=start))
    play.thing = Thing(6, WAYPOINT_ACT4, 2, 5044.0, 5019.0)
    play.thing_above = 0.0

    travel(play.run(), LOWER_KURAST)

    assert play.character.area == LOWER_KURAST


def test_a_waypoint_not_got_yet_stops_with_the_panel_closed():
    from inventory_tracking.macros.waypoint import travel

    play = docks()
    play.greyed.add((3, 0))

    with pytest.raises(Abort, match='did not take the character to The Pandemonium Fortress'):
        travel(play.run(), PANDEMONIUM_FORTRESS)
    assert play.character.area == KURAST_DOCKS
    assert play.world.open_panels == ()


def test_the_table_is_built_from_levels_txt_in_its_waypoint_order():
    from inventory_tracking.macros.build_waypoints import build

    levels = [
        {'Id': '79', 'Act': '2', 'Waypoint': '22'},
        {'Id': '75', 'Act': '2', 'Waypoint': '18'},
        {'Id': '103', 'Act': '3', 'Waypoint': '27'},
        {'Id': '106', 'Act': '3', 'Waypoint': '28'},
        {'Id': '2', 'Act': '0', 'Waypoint': '255'},  # no waypoint
        {'Id': 'Expansion', 'Act': '', 'Waypoint': ''},  # a heading row
    ]

    assert build(levels, 'test')['waypoints'] == {
        '75': {'act': 2, 'row': 0},
        '79': {'act': 2, 'row': 4},
        '103': {'act': 3, 'row': 0},
        '106': {'act': 3, 'row': 1},
    }


def near() -> Game:
    """The character 3 units from the waypoint, within CLOSE: where the step back applies."""
    play = docks()
    play.world = replace(play.world, player=player(KURAST_DOCKS, x=5156.0, y=5050.0))
    return play


def test_a_panel_the_walk_opened_is_done_with_no_aim_and_no_step_back(caplog):
    """14:42:09 on 2026-10-18: the walk's last click opened the panel; the aims read None under the pointer and
    the step back clicked onto it, then the game was left. Caught by use_thing's PANEL_GRACE."""
    play = near()
    play.panel_covers = True
    play.later(0.12, lambda: setattr(play, 'world', replace(play.world, open_panels=('waypoint',))))  # the walk's click

    with caplog.at_level('INFO'):
        open_panel(play.run())

    assert play.keys.events == []
    assert play.world.open_panels == ('waypoint',)
    assert any('the waypoint took before any aim' in r.getMessage() for r in caplog.records)
    assert play.said[-1] == 'the waypoint: opened'


def test_a_panel_opening_between_the_aims_stops_the_aiming_with_no_step_back():
    play = near()
    reads = []

    def hovered():
        reads.append(True)
        if len(reads) == 2:
            play.world = replace(play.world, open_panels=('waypoint',))
        return None  # the open panel covers the waypoint: nothing under the pointer

    run = play.run()
    run.hovered = hovered

    open_panel(run)

    assert len(reads) >= 2
    assert [e for e in play.keys.events if e[0] == 'click'] == []
    assert play.world.open_panels == ('waypoint',)


def test_with_the_panel_closed_the_aims_still_find_the_waypoint_and_click_it():
    play = docks()

    open_panel(play.run())

    assert [event[0] for event in play.keys.events] == ['click']
    assert play.world.open_panels == ('waypoint',)


def test_a_waypoint_never_under_the_pointer_still_steps_back_with_the_panel_closed():
    play = near()
    run = play.run()
    run.hovered = lambda: None

    with pytest.raises(Abort, match='not under the pointer'):
        open_panel(run)

    assert [e for e in play.keys.events if e[0] == 'click']  # the step back's click


def test_a_corrected_walk_reapproaches_an_out_of_view_waypoint():
    # Take 20261018T175014Z-1: after three walk clicks the client reached within 8 units, then snapped back to 25.
    class Corrected(Game):
        corrected = False

        def react(self, event):
            before = len(self.walks)
            super().react(event)
            if not self.corrected and before < 2 <= len(self.walks):
                self.corrected = True
                self.world = replace(self.world, player=replace(self.character, mode=3))
                self.later(
                    0.12,
                    lambda: setattr(
                        self,
                        'world',
                        replace(self.world, player=replace(self.character, x=5866.9, y=5727.1, mode=5)),
                    ),
                )

    play = Corrected(world(PANDEMONIUM_FORTRESS, player=player(PANDEMONIUM_FORTRESS, x=5863.5, y=5733.5)))
    play.thing = Thing(9, WAYPOINT_ACT4, 2, 5884.0, 5709.0)
    play.thing_above = 0.0

    open_panel(play.run(), lambda label: ())

    assert play.corrected
    assert play.world.open_panels == ('waypoint',)


# Kurast Docks round the start (take 20261019T174959Z-75, 2026-10-19): open ground south of y 5161, a wall block west of
# x 5126 north of it; the waypoint (5159, 5049) is round its corner, out of sight from the start (5118.5, 5168.5)
DOCKS_LEFT, DOCKS_TOP, DOCKS_COLUMNS, DOCKS_ROWS = 5100, 5040, 80, 140
WAYPOINT = Thing(5, WAYPOINT_ACT3, 2, 5159.0, 5049.0)


def docks_ground():
    from inventory_tracking.levels.model import Ground, Walkable, pack_cells

    rows = (
        '0' if x <= 5125 and y <= 5160 else '1'
        for y in range(DOCKS_TOP, DOCKS_TOP + DOCKS_ROWS)
        for x in range(DOCKS_LEFT, DOCKS_LEFT + DOCKS_COLUMNS)
    )
    cells = pack_cells(''.join(rows))
    return Ground((Walkable(DOCKS_LEFT // 5, DOCKS_TOP // 5, DOCKS_COLUMNS // 5, DOCKS_ROWS // 5, cells, cells),))


def test_a_game_begun_in_kurast_docks_walks_round_the_corner_to_the_waypoint_with_no_wait():
    # 20:49-20:51 on 2026-10-19 (games 9-11 of TZ leveling in Travincal): the walk took 10 s, 4 of them two clicks
    # lifted onto the wall by the start that walked nowhere and stood WALK_SECONDS each. The player: "we must go
    # without waiting and reach dest as soon as possible"
    ground = docks_ground()

    class Docks(Game):
        into_wall: list[tuple[float, float]]
        clicked: list[float]

        def act(self, event):
            if event[0] == 'click' and 'waypoint' not in self.world.open_panels:
                self.clicked.append(self.clock.now)
                gx, gy = self.ground_under_pointer()
                if not ground.walkable(gx, gy) and not self.thing_in_reach(gx, gy):
                    self.into_wall.append((gx, gy))  # the game walks nowhere
                    return
            super().act(event)
            here = self.character
            if self.thing is None and math.dist((here.x, here.y), (5159.0, 5049.0)) < 65:
                self.thing = WAYPOINT  # in the read from 65 units (the take: at y 5113)

    play = Docks(world(KURAST_DOCKS, player=player(KURAST_DOCKS, x=5118.5, y=5168.5)))
    play.into_wall, play.clicked = [], []
    play.thing = None
    play.thing_above = 0.0
    run = play.run()
    run.ground = lambda: ground

    open_panel(run, lambda label: ((5159.0 / 5, 5049.0 / 5),) if label == 'Waypoint' else ())

    assert play.world.open_panels == ('waypoint',)
    assert play.into_wall == []
    assert all(ground.walkable(*spot) for spot in play.walks)
    gaps = [later - before for before, later in zip(play.clicked, play.clicked[1:], strict=False)]
    assert max(gaps) < 0.6  # click on click: no stand of WALK_SECONDS (1.6) between two

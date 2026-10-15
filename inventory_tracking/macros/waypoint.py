"""The town's waypoint and its panel (routes/lower-kurast-loop-plan.md phases 1 and 2).

No walk of the macro's own in town: the player's trips of 2026-10-15 put the waypoint a click away in both towns
the loop goes through. Every game of theirs started in Pandemonium Fortress at (5048, 5044), 25 units from its
waypoint (13 of 13), and every portal from Lower Kurast left them in Kurast Docks at (5158, 5068), 20 units from
its (9 of 9). They clicked it and the game walked them there. So the click is the step: the waypoint object the
game shows, clicked on its picture (teleport.use_thing, the aims checked under the pointer), done when its panel
is open.

The panel's tab and row (phase 2) are clicked where the game's own layout puts them, read from the installed game's
`data/global/ui/layouts/waypointspanelexpansionhd.json` (based on `waypointspaneloriginalhd.json`) and
`_profilehd.json` on 2026-10-16: the panel is `$LeftPanelRect` (x 236, y -651) at `$LeftPanelAnchor` (0, 0.397 of
the window); in it the five act tabs from (148, 201), 174 x 70 each with -1 padding, and the rows from (152, 264),
`buttonOffset` 123 apart. A layout unit is 1/2160 of the window's height: the pause menu's layout by the same rule
puts Save and Exit at 0.440 and Return to Game at 0.505 of the height, where the macros click them from screenshots
(0.438, 0.509; routines.py, probe.py). The level's tab and row come from levels.txt (data/waypoints.json,
build_waypoints.py). A row clicked is confirmed by the level it leads to; a waypoint the character has not got is a
greyed row that takes nothing, said as the level not reached.
"""

import functools
import json
import math
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import Target
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.teleport import ready_world, use_thing
from inventory_tracking.native.layout import TILE_UNITS


__all__ = ['WaypointRow', 'open_panel', 'panel_point', 'travel', 'waypoint_of']

REFERENCE_HEIGHT = 2160  # layout units in the window's height
PANEL_ANCHOR = (0.0, 0.397)  # $LeftPanelAnchor: window fractions
PANEL_ORIGIN = (236, -651)  # $LeftPanelRect's corner from the anchor, layout units
TAB_ORIGIN, TAB_SIZE, TAB_STEP = (148, 201), (174, 70), 173  # tabSize 174, tabPadding -1
ROW_ORIGIN, ROW_STEP = (152, 264), 123  # the first button's corner; buttonOffset
# Where in a row the click goes: past the start of its text (`text/rect` x 210), and down into the button by less
# than the gap between two rows: the button image's size is not in the layout.
ROW_AIM = (400, 45)
ARRIVES = 6.0  # seconds from the row's click to the level (a loading screen between acts)
SETTLES = 0.4  # seconds for the panel to take a tab's click


@dataclass(frozen=True)
class WaypointRow:
    act: int  # the tab, 0-based
    row: int  # the row in it, 0-based


@functools.cache
def _waypoints() -> dict[int, WaypointRow]:
    data = json.loads((Path(__file__).parent / 'data' / 'waypoints.json').read_text())
    return {int(area): WaypointRow(row['act'], row['row']) for area, row in data['waypoints'].items()}


def waypoint_of(area: int) -> WaypointRow | None:
    """The tab and row of level `area`'s waypoint; None for a level without one."""
    return _waypoints().get(area)


def panel_point(rect: tuple[int, int, int, int], x: float, y: float) -> tuple[float, float]:
    """The window fraction of the panel's point (x, y), in layout units from its corner."""
    width, height = rect[2], rect[3]
    scale = height / REFERENCE_HEIGHT
    across = PANEL_ANCHOR[0] * width + (PANEL_ORIGIN[0] + x) * scale
    down = PANEL_ANCHOR[1] * height + (PANEL_ORIGIN[1] + y) * scale
    return across / width, down / height


def tab_point(act: int) -> tuple[float, float]:
    """The middle of act `act`'s tab, in layout units from the panel's corner."""
    return TAB_ORIGIN[0] + act * TAB_STEP + TAB_SIZE[0] / 2, TAB_ORIGIN[1] + TAB_SIZE[1] / 2


def row_point(row: int) -> tuple[float, float]:
    """Where row `row` is clicked, in layout units from the panel's corner."""
    return ROW_ORIGIN[0] + ROW_AIM[0], ROW_ORIGIN[1] + row * ROW_STEP + ROW_AIM[1]


def open_panel(run: Run) -> None:
    """Click the town's waypoint and wait for its panel. `Abort` out of town and with no waypoint shown."""
    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if not player.in_town:
        raise Abort('not in town: no waypoint to walk to')
    shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
    if not shown:
        raise Abort('no waypoint in sight')
    thing = min(shown, key=lambda t: math.dist((t.x, t.y), (player.x, player.y)))
    mark = Target(
        player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), 'the waypoint', 'waypoint', use=thing.txt_id
    )
    use_thing(run, mark, player, thing, rect[2] / rect[3])


def travel(run: Run, to_area: int) -> None:
    """From the town's waypoint to level `to_area`'s: the panel opened (`open_panel`), the level's tab and row
    clicked, done in that level. Mouse mode only, as Save and Exit. `Abort` with the panel closed again when the
    level is not reached."""
    if run.pad is not None:  # the panel takes the mouse's click (macros/pad.py `input_policy`)
        raise Abort('the waypoint needs mouse mode: click once to switch, then press again')
    to = waypoint_of(to_area)
    if to is None:
        raise Abort(f'{display_name(to_area)} has no waypoint')
    with run.lightly():
        world = run.world()
    if world.player is not None and world.player.area == to_area:
        return
    if 'waypoint' not in world.open_panels:
        open_panel(run)
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    name = display_name(to_area)
    run.say(f'Waypoint to {name}')
    run.actuator.move(*panel_point(rect, *tab_point(to.act)), scatter=(20, 6))
    run.actuator.click()
    run.pace.sleep(SETTLES)
    run.actuator.move(*panel_point(rect, *row_point(to.row)), scatter=(30, 5))
    run.actuator.click()
    if run.seen(lambda w: w.player is not None and w.player.area == to_area, ARRIVES) is None:
        if 'waypoint' in run.world().open_panels:
            run.actuator.tap('Escape')
        raise Abort(f'the waypoint did not take the character to {name} (its row greyed: not got yet?)')
    run.say(f'{name}: there')

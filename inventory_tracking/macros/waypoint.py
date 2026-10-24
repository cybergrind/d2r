"""The town's waypoint and its panel (routes/lower-kurast-loop-plan.md phases 1 and 2).

In town the waypoint is a click away (the game walks the character there): `open_panel` clicks the object on its
picture (teleport.py `use_thing`) and waits for the panel. `travel` clicks the level's tab and row where the game's
layout puts them (`waypointspanelexpansionhd.json` and `_profilehd.json`, read 2026-10-16; a layout unit is 1/2160 of
the window's height), the tab and row from levels.txt (data/waypoints.json). The level reached confirms the row; a
waypoint not got is a greyed row, said as the level not reached.
"""

import functools
import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.game.records import World
from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import Target
from inventory_tracking.levels.presets import display_name
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import arrived, screen_fraction
from inventory_tracking.macros.teleport import ground_fraction, ready_world, use_thing
from inventory_tracking.native.layout import TILE_UNITS


CLOSE = 8.0  # units from the waypoint within which a click finds the character's figure over it (`open_panel`)
STEP_BACK = 7.0  # units the character steps back from a waypoint too close to be aimed at


__all__ = ['WaypointRow', 'open_panel', 'panel_point', 'travel', 'waypoint_of']

REFERENCE_HEIGHT = 2160  # layout units in the window's height
PANEL_ANCHOR = (0.0, 0.397)  # $LeftPanelAnchor: window fractions
PANEL_ORIGIN = (236, -651)  # $LeftPanelRect's corner from the anchor, layout units
TAB_ORIGIN, TAB_SIZE, TAB_STEP = (148, 201), (174, 70), 173  # tabSize 174, tabPadding -1
ROW_ORIGIN, ROW_STEP = (152, 264), 123  # the first button's corner; buttonOffset
# Where in a row the click goes: past its text's start (x 210), down less than a row's gap (the button's size is not in
# the layout)
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


def is_open(world: World) -> bool:
    return 'waypoint' in world.open_panels


def open_panel(run: Run, marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None) -> None:
    """Click the town's waypoint and wait for its panel. `Abort` out of town and with no waypoint shown. With none
    in sight (a game begun in Kurast Docks), walked toward the level card's Waypoint mark (`marks`: tiles) first."""
    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if not player.in_town:
        raise Abort('not in town: no waypoint to walk to')
    shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
    marked = marks('Waypoint') if marks is not None and not shown else ()
    if not shown and marked:
        from inventory_tracking.macros.shop import walk_until  # shop.py imports this module

        def place(now: World) -> tuple[float, float] | None:
            seen = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
            if seen:
                return seen[0].x, seen[0].y
            return marked[0][0] * TILE_UNITS, marked[0][1] * TILE_UNITS  # tiles to world units

        LOG.info(
            'Macro: waypoint: none in sight: walking to the mark at (%.0f, %.0f)', *(c * TILE_UNITS for c in marked[0])
        )
        world = walk_until(run, place, (0.15, 0.85, 0.15, 0.8), 'the waypoint', to_npc=False)
        player = world.player or player
        shown = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
    if not shown:
        raise Abort('no waypoint in sight')
    drawn = ground_fraction(player, shown[0].x, shown[0].y, rect[2] / rect[3]) if rect is not None else None
    inside = drawn is not None and 0.15 <= drawn[0] <= 0.85 and 0.15 <= drawn[1] <= 0.8
    if not inside:
        LOG.info('Macro: waypoint: outside safe view: drawn %s, marks %s, panels %s', drawn,
                 marks is not None, world.open_panels)  # fmt: skip
    if marks is not None and not inside:
        # In sight but maybe out of the window (after the stash): walked to until drawn well inside
        from inventory_tracking.macros.shop import WALK_SECONDS, WALKING, walk_until

        def near(now: World) -> tuple[float, float] | None:
            seen = [t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES]
            return (seen[0].x, seen[0].y) if seen else None

        for attempt in range(3):
            world = walk_until(run, near, (0.15, 0.85, 0.15, 0.8), 'the waypoint', to_npc=False)
            world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or world
            player = world.player or player
            shown = [
                t for t in (run.things() if run.things is not None else ()) if t.txt_id in WAYPOINT_CLASSES
            ] or shown
            drawn = ground_fraction(player, shown[0].x, shown[0].y, rect[2] / rect[3])
            if is_open(world) or (0.15 <= drawn[0] <= 0.85 and 0.15 <= drawn[1] <= 0.8):
                break
            LOG.info('Macro: waypoint: walk corrected outside safe view to %s: approaching again (%d/3)',
                     drawn, attempt + 1)  # fmt: skip
        else:
            raise Abort('the waypoint stayed outside the safe view after three walks')
    # Stood still before the aims: aims while walking miss
    standing = run.seen(lambda w: w.player is not None and w.player.mode not in (2, 3, 6), 1.6)
    player = (standing.player if standing is not None else None) or player
    thing = min(shown, key=lambda t: math.dist((t.x, t.y), (player.x, player.y)))
    mark = Target(
        player.area, (), (thing.x / TILE_UNITS, thing.y / TILE_UNITS), 'the waypoint', 'waypoint', use=thing.txt_id
    )
    try:
        # A panel the walk's last click opened is waited for there (teleport.py PANEL_GRACE): no aim then
        use_thing(run, mark, player, thing, rect[2] / rect[3])
    except Abort as stop:
        if is_open(run.world()):  # opened under the aims (they read None once it is): done, not a step back
            LOG.info('Macro: waypoint: the panel opened while aiming (%s); done', stop)
            run.say('the waypoint: opened')
            return
        away = math.dist((thing.x, thing.y), (player.x, player.y))
        if 'not under the pointer' not in str(stop) or away > CLOSE:
            raise
        # Too near: the character's own figure covers the aims; a step back, then the aims again
        from inventory_tracking.macros.shop import WALK_SECONDS, WALKING

        back = (player.x + (player.x - thing.x) / max(away, 0.1) * STEP_BACK,
                player.y + (player.y - thing.y) / max(away, 0.1) * STEP_BACK)  # fmt: skip
        LOG.info('Macro: waypoint: %.0f units off and under no aim: a step back to (%.0f, %.0f)', away, *back)
        # A click on the ground there: a walk toward a place in view ends before it begins
        run.actuator.move(*screen_fraction(player, back[0], back[1], rect[2] / rect[3]), scatter=(3, 3))
        run.actuator.click()
        stood = (player.x, player.y)
        run.seen(lambda w: w.player is not None and math.dist((w.player.x, w.player.y), stood) >= STEP_BACK / 2, 1.5)
        world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or run.world()
        use_thing(run, mark, world.player or player, thing, rect[2] / rect[3])


def travel(run: Run, to_area: int, marks: Callable[[str], tuple[tuple[float, float], ...]] | None = None) -> None:
    """From the town's waypoint to level `to_area`'s: panel opened, tab and row clicked, done in that level. Mouse mode
    only. `Abort` with the panel closed when the level is not reached."""
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
        open_panel(run, marks)
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        raise Abort('no game window')
    name = display_name(to_area)
    run.say(f'Waypoint to {name}')
    tab, row = panel_point(rect, *tab_point(to.act)), panel_point(rect, *row_point(to.row))
    LOG.info(
        'Macro: waypoint: tab %d at (%.3f, %.3f), row %d at (%.3f, %.3f) of a %dx%d window',
        to.act + 1, *tab, to.row + 1, *row, rect[2], rect[3],
    )  # fmt: skip
    run.actuator.move(*tab, scatter=(20, 6))
    run.actuator.click()
    run.pace.sleep(SETTLES)
    run.actuator.move(*row, scatter=(30, 5))
    run.actuator.click()
    loading = []

    def reached(w) -> bool:
        if w.view == 0:
            loading.append(True)  # the load began before the area changed: `arrived` waits for its end
        return w.player is not None and w.player.area == to_area

    if run.seen(reached, ARRIVES) is None:
        if 'waypoint' in run.world().open_panels:
            run.actuator.tap('Escape')
        raise Abort(f'the waypoint did not take the character to {name} (its row greyed: not got yet?)')
    # Not over before the game takes input there (rca/2026-10-16/loop-first-game-findings.md §2)
    arrived(run, name, loading=bool(loading))
    run.say(f'{name}: there')

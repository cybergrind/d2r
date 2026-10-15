"""The town's waypoint (routes/lower-kurast-loop-plan.md phases 1 and 2).

No walk of the macro's own in town: the player's trips of 2026-10-15 put the waypoint a click away in both towns
the loop goes through. Every game of theirs started in Pandemonium Fortress at (5048, 5044), 25 units from its
waypoint (13 of 13), and every portal from Lower Kurast left them in Kurast Docks at (5158, 5068), 20 units from
its (9 of 9). They clicked it and the game walked them there. So the click is the step: the waypoint object the
game shows, clicked on its picture (teleport.use_thing, the aims checked under the pointer), done when its panel
is open.
"""

import math

from inventory_tracking.levels.memory import WAYPOINT_CLASSES
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.teleport import ready_world, use_thing
from inventory_tracking.native.layout import TILE_UNITS


__all__ = ['open_panel']


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


"""Town Portal out of a level (routes/lower-kurast-loop-plan.md phase 3).

The tome's skill (220, Book of Townportal) is cast from its skill key: the slot table and the character's key file
say which (`key_names`, skills.skill_keys; CybergrindAA's slot 5 is `x`, phase 0), never a key assumed. The cast
is Quick Cast, as the player's own: the takes of 2026-10-15 in Lower Kurast show the right button's skill 220 for
0.3 to 0.4 s at each cast. The portal (objects.txt TownPortal, 59) opens beside the character and takes a click
only once open (mode 2, `Selectable2`); its click box is the permanent portal's, so it is clicked as one
(teleport.use_thing) and it took when the level changed. The new portal is told from one of an earlier trip by
its unit: it was not there before the cast.

No portal after the cast is said, not guessed: the tome empty (its charges are not read yet) or the cast not made.
The player clicked theirs 0.9 to 1.4 s after the cast (the same takes): it was open by then.
"""

import math
from collections.abc import Callable

from inventory_tracking.levels.model import TOWN_PORTAL, Target
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import press_skill
from inventory_tracking.macros.skills import TOWN_PORTAL as TOME
from inventory_tracking.macros.teleport import ready_world, use_thing
from inventory_tracking.macros.world import Thing
from inventory_tracking.native.layout import TILE_UNITS


__all__ = ['TOME', 'to_town']

OPEN = 2  # the portal's mode once it can be clicked (objects.txt Selectable2)
OPENS = 2.5  # seconds from the cast to the portal open: the player's clicks came 0.9 to 1.4 s after it
POLL = 0.05


def portals(run: Run) -> tuple[Thing, ...]:
    return tuple(t for t in (run.things() if run.things is not None else ()) if t.txt_id == TOWN_PORTAL)


def to_town(run: Run, key_names: Callable[..., dict[int, str]]) -> None:
    """Cast Town Portal and go through the portal it opens: done in town. `Abort` in town already, with the
    tome on no skill key (`key_names`), and with no portal open after the cast."""
    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if player.in_town:
        raise Abort('in town already')
    before = {t.unit_id for t in portals(run)}
    run.keys.update(key_names(world, (TOME,)))
    cast = press_skill(run, TOME)
    opened = None
    while opened is None:
        here = run.world().player or player
        new = [t for t in portals(run) if t.unit_id not in before and t.mode == OPEN]
        opened = min(new, key=lambda t: math.dist((t.x, t.y), (here.x, here.y))) if new else None
        if opened is None and run.clock() - cast >= OPENS:
            raise Abort(f'no Town Portal opened {OPENS:g}s after the cast: is the tome empty?')
        if opened is None:
            run.pace.sleep(POLL)
    here = run.world().player or player
    mark = Target(here.area, (), (opened.x / TILE_UNITS, opened.y / TILE_UNITS), 'town', 'target', use=TOWN_PORTAL)
    use_thing(run, mark, here, opened, rect[2] / rect[3])

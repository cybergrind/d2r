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
from inventory_tracking.macros.routines import arrived, press_skill
from inventory_tracking.macros.skills import TOWN_PORTAL as TOME
from inventory_tracking.macros.teleport import ready_world, use_thing
from inventory_tracking.macros.world import Thing
from inventory_tracking.native.layout import TILE_UNITS


__all__ = ['TOME', 'through_portal', 'to_town']

OPEN = 2  # the portal's mode once it can be clicked (objects.txt Selectable2)
OPENS = 2.5  # seconds from the cast to the portal open: the player's clicks came 0.9 to 1.4 s after it
POLL = 0.05


def portals(run: Run) -> tuple[Thing, ...]:
    return tuple(t for t in (run.things() if run.things is not None else ()) if t.txt_id == TOWN_PORTAL)


# Pickups made at the open portal before it is gone through, at most (`to_town` `first`)
PICKS_AT_PORTAL = 4


def to_town(run: Run, key_names: Callable[..., dict[int, str]], first: Callable[[], bool] | None = None) -> None:
    """Cast Town Portal and go through the portal it opens: done in town. `Abort` in town already, with the
    tome on no skill key (`key_names`), and with no portal open after the cast. `first`: a pickup made once the
    portal is open, again while it picks something up: a chest's drops come out over a second and more, and a Chipped
    Ruby that landed 0.8 s after its chest's click, while the portal opened, was left (03:04:17 on 2026-10-18)."""
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
    if first is not None:
        for _ in range(PICKS_AT_PORTAL):
            if not first():
                break
    here = run.world().player or player
    mark = Target(here.area, (), (opened.x / TILE_UNITS, opened.y / TILE_UNITS), 'town', 'target', use=TOWN_PORTAL)
    use_thing(run, mark, here, opened, rect[2] / rect[3])
    # Not over before the town takes input (rca/2026-10-16/loop-first-game-findings.md §2: the waypoint's aims were
    # tried 0.002 s after the portal's arrival and found nothing under the pointer)
    arrived(run, 'town')


PORTAL_SEEN = (0.15, 0.85, 0.15, 0.8)  # window fractions the portal is walked to be drawn within


def through_portal(run: Run, near: tuple[float, float] | None = None) -> None:
    """Back from town through the character's open Town Portal to its level (macros/loop.py `THROUGH_PORTAL`): walked
    toward `near` (where the portal left the character in town) until one is in sight, then clicked as `to_town` clicks
    it. `Abort` out of town and with no portal found."""
    from inventory_tracking.macros.shop import WALK_SECONDS, WALKING, walk_until  # shop.py imports this module's own

    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if not player.in_town:
        raise Abort('not in town: no portal to go back through')

    def place(now) -> tuple[float, float] | None:
        here = now.player or player
        shown = [t for t in portals(run) if t.mode == OPEN]
        if shown:
            found = min(shown, key=lambda t: math.dist((t.x, t.y), (here.x, here.y)))
            return found.x, found.y
        return near

    if place(world) is None:
        raise Abort('no Town Portal in sight, and none known')
    world = walk_until(run, place, PORTAL_SEEN, 'the portal')
    world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or run.world()
    here = world.player or player
    shown = [t for t in portals(run) if t.mode == OPEN]
    if not shown:
        raise Abort('no Town Portal in sight')
    found = min(shown, key=lambda t: math.dist((t.x, t.y), (here.x, here.y)))
    mark = Target(here.area, (), (found.x / TILE_UNITS, found.y / TILE_UNITS), 'the level', 'target', use=TOWN_PORTAL)
    use_thing(run, mark, here, found, rect[2] / rect[3])
    arrived(run, 'the level')

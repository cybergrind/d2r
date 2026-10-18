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

The Sling casts it instead when it is worn (the player, 2026-10-18: "sling provides town teleport skill, that frees two
slots in inventory (we can replace tome of town portals) ... when we have sling ring equipped - we don't need to run any
logic in regard of town portal (do not track, do not buy)"): uniqueitems.txt Sling, a Ring, gives `oskill`
"Townportal O Skill" (skills.txt 411: no mana, no delay, no charges). How the character casts it is one fact,
`portal_source`, which the cast here, the stock's count (shop.py `short`, `restock`) and the loop's texts all take
(macros/sling-plan.md).
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.levels.model import TOWN_PORTAL, Target
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import arrived, press_skill
from inventory_tracking.macros.skills import SLING_TOWN_PORTAL, TOWN_PORTAL as TOME
from inventory_tracking.macros.teleport import ready_world, use_thing
from inventory_tracking.macros.world import Pack, Thing, World
from inventory_tracking.native.layout import TILE_UNITS


__all__ = [
    'FROM_SLING',
    'FROM_TOME',
    'TOME',
    'PortalSource',
    'portal_source',
    'slot_note',
    'through_portal',
    'to_town',
]


@dataclass(frozen=True)
class PortalSource:
    """How the character casts Town Portal: the skill pressed, what it is called, and whether its casts are a stock to
    keep (the tome's charges, Town Portal scrolls bought into it at Jamella: macros/shop.py) or cost nothing."""

    skill: int
    name: str
    stocked: bool

    def count(self, pack: Pack) -> int | None:
        """The casts left as the stock goes: the tome's charges (0 with no tome), None with no stock to keep (an unread
        count, which never makes the loop short: shop.py `short`)."""
        return pack.portals if self.stocked else None

    def said(self, pack: Pack | None) -> str:
        """The casts left for a text: '<n> portals', or the Sling's."""
        return f'{pack.portals if pack is not None else None} portals' if self.stocked else f'portals from {self.name}'


FROM_TOME = PortalSource(TOME, 'the tome', stocked=True)
FROM_SLING = PortalSource(SLING_TOWN_PORTAL, 'the Sling', stocked=False)


def portal_source(run: Run) -> PortalSource:
    """The Sling's Town Portal when the worn items give it (`Run.worn_skills`: world.GameMemory.worn_skills, the skill
    411 a worn item's item_nonclassskill), else the tome's, as before the Sling, unread worn items too. The Sling's is
    taken whether or not it is on a skill key: the player's ruling is the ring worn, and a cast with no key stops
    saying so (`to_town`), where the tome's would buy scrolls into cells with no tome to take them."""
    worn = run.worn_skills() if run.worn_skills is not None else None
    return FROM_SLING if worn is not None and SLING_TOWN_PORTAL in worn else FROM_TOME


def slot_note(world: World, source: PortalSource) -> str:
    """Where the source's skill is in the slot table, for the log: 'in slot N' or 'on no skill key'."""
    return f'in slot {world.slots.index(source.skill)}' if source.skill in world.slots else 'on no skill key'


OPEN = 2  # the portal's mode once it can be clicked (objects.txt Selectable2)
OPENS = 2.5  # seconds from the cast to the portal open: the player's clicks came 0.9 to 1.4 s after it
POLL = 0.05


def portals(run: Run) -> tuple[Thing, ...]:
    return tuple(t for t in (run.things() if run.things is not None else ()) if t.txt_id == TOWN_PORTAL)


# Pickups made at the open portal before it is gone through, at most (`to_town` `first`)
PICKS_AT_PORTAL = 4


def to_town(run: Run, key_names: Callable[..., dict[int, str]], first: Callable[[], bool] | None = None) -> None:
    """Cast Town Portal (`portal_source`: the Sling's or the tome's) and go through the portal it opens: done in town.
    `Abort` in town already, with its skill on no skill key (`key_names`), and with no portal open after the cast.
    `first`: a pickup made once the portal is open, again while it picks something up: a chest's drops come out over a
    second and more, and a Chipped Ruby that landed 0.8 s after its chest's click, while the portal opened, was left
    (03:04:17 on 2026-10-18)."""
    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if player.in_town:
        raise Abort('in town already')
    before = {t.unit_id for t in portals(run)}
    source = portal_source(run)
    run.keys.update(key_names(world, (source.skill,)))
    cast = press_skill(run, source.skill)
    opened = None
    while opened is None:
        here = run.world().player or player
        new = [t for t in portals(run) if t.unit_id not in before and t.mode == OPEN]
        opened = min(new, key=lambda t: math.dist((t.x, t.y), (here.x, here.y))) if new else None
        if opened is None and run.clock() - cast >= OPENS:
            empty = ': is the tome empty?' if source.stocked else ''
            raise Abort(f'no Town Portal opened {OPENS:g}s after the cast from {source.name}{empty}')
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

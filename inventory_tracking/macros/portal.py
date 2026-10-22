"""Town Portal out of a level and back (routes/lower-kurast-loop-plan.md phase 3).

The skill is cast from its key as the slot table and key file say, never a key assumed. The portal (objects.txt
TownPortal) takes a click only once open (mode 2, `Selectable2`) and is clicked like a permanent portal
(teleport.use_thing); the new one is told from an earlier trip's by its unit id.

The Sling ring's oskill casts it instead when worn (skills.txt 411, no charges; the player, 2026-10-18: "when we have
sling ring equipped - we don't need to run any logic in regard of town portal (do not track, do not buy)").
`portal_source` is the one fact the cast, the shop's stock and the loop's texts take (macros/sling-plan.md).
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Pack, Thing, World
from inventory_tracking.levels.model import TOWN_PORTAL, Target
from inventory_tracking.loot.api import settle
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.routines import ACTING, arrived, press_skill
from inventory_tracking.macros.skills import SLING_TOWN_PORTAL, TOWN_PORTAL as TOME
from inventory_tracking.macros.teleport import KEY_DROP_MODES, ready_world, use_thing
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
    """How the character casts Town Portal: the skill, its name, and whether its casts are a stock to keep (the
    tome's charges) or cost nothing."""

    skill: int
    name: str
    stocked: bool

    def count(self, pack: Pack) -> int | None:
        """The tome's charges (0 with no tome); None with no stock to keep (never short: shop.py `short`)."""
        return pack.portals if self.stocked else None

    def said(self, pack: Pack | None) -> str:
        """The casts left for a text: '<n> portals', or the Sling's."""
        return f'{pack.portals if pack is not None else None} portals' if self.stocked else f'portals from {self.name}'


FROM_TOME = PortalSource(TOME, 'the tome', stocked=True)
FROM_SLING = PortalSource(SLING_TOWN_PORTAL, 'the Sling', stocked=False)


def portal_source(run: Run) -> PortalSource:
    """The Sling's Town Portal when a worn item gives skill 411, else the tome's (also with unread worn items). The
    Sling's is taken even when on no key: the ruling is the ring worn, and a keyless cast stops saying so, where the
    tome's would buy scrolls with no tome to take them."""
    worn = run.reads.worn_skills()
    return FROM_SLING if worn is not None and SLING_TOWN_PORTAL in worn else FROM_TOME


def slot_note(world: World, source: PortalSource) -> str:
    """Where the source's skill is in the slot table, for the log: 'in slot N' or 'on no skill key'."""
    return f'in slot {world.slots.index(source.skill)}' if source.skill in world.slots else 'on no skill key'


OPEN = 2  # the portal's mode once it can be clicked (objects.txt Selectable2)
OPENS = 2.5  # seconds from the cast to the portal open (the player clicks 0.9-1.4 s after it)
POLL = 0.05


def portals(run: Run) -> tuple[Thing, ...]:
    return tuple(t for t in (run.things() if run.things is not None else ()) if t.txt_id == TOWN_PORTAL)


# Pickups made at the open portal before it is gone through, at most (`to_town` `first`)
PICKS_AT_PORTAL = 4


def to_town(run: Run, key_names: Callable[..., dict[int, str]], first: Callable[[], bool] | None = None) -> None:
    """Cast Town Portal and go through the portal it opens: done in town. `Abort` in town already, with the skill on no
    key, and with no portal open after the cast (cast once more first: CAST_FREE). `first`: a pickup made once the
    portal is open, repeated while it picks something up (a chest's drops land over a second and more). Before the
    cast, the loot's field routine: a level's end or a trip for room (loot/api.py `settle`, M4)."""
    settle(run, 'Town Portal')
    with run.lightly():
        world, rect = ready_world(run)
    player = world.player
    assert player is not None
    if player.in_town:
        raise Abort('in town already')
    before = {t.unit_id for t in portals(run)}
    source = portal_source(run)
    run.keys.update(key_names(world, (source.skill,)))
    cast = _cast(run, source)
    again = CAST_FREE
    opened = None
    while opened is None:
        here = run.world().player or player
        new = [t for t in portals(run) if t.unit_id not in before and t.mode == OPEN]
        opened = min(new, key=lambda t: math.dist((t.x, t.y), (here.x, here.y))) if new else None
        if opened is None and again and run.clock() - cast >= RECAST_AFTER:
            again = False
            LOG.info(
                'Macro: no Town Portal %.1fs after the cast from %s, player mode %s: cast once more',
                run.clock() - cast, source.name, here.mode,
            )  # fmt: skip
            before |= {t.unit_id for t in portals(run)}  # a late first portal is shut by the second cast
            cast = _cast(run, source)
            continue
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
    if WALK_BACK and first is not None:
        here = _back_to(run, opened, here)
        if here is None:
            LOG.info('Macro: the walk back to the portal went through it: in town')
            arrived(run, 'town')
            return
    mark = Target(here.area, (), (opened.x / TILE_UNITS, opened.y / TILE_UNITS), 'town', 'target', use=TOWN_PORTAL)
    use_thing(run, mark, here, opened, rect[2] / rect[3])
    # Not over before the town takes input (rca/2026-10-16/loop-first-game-findings.md §2)
    arrived(run, 'town')


# 2026-10-22 (rca/2026-10-22/portal-cast-findings.md): the Sling's cast pressed during a block (mode 9) showed its skill
# on the right button for one frame and was dropped (09:30:05 in The Worldstone Keep Level 3); one pressed in neutral
# was cut by a block 0.04 s into the cast (22:26:32 on 2026-10-21, Spider Forest). Each time the character then stood
# neutral for two seconds and the game was left. True: the key waits for no block, hit or cast (FREE_SECONDS at most),
# and a cast with no portal open RECAST_AFTER later is made once more, the same way, before the stop. False: one
# press at once, as before.
CAST_FREE = True
FREE_SECONDS = 1.0
BUSY = KEY_DROP_MODES | ACTING  # a block or a hit drops a key (teleport.py KEY_DROP_MODES); a cast keeps it waiting
RECAST_AFTER = 1.6  # 412 Sling casts of 2026-10-19..22 opened 0.98-1.34 s after the key (median 1.15)


def _cast(run: Run, source: PortalSource) -> float:
    """The source's key once the character is free (CAST_FREE), else at once: the clock time of the key."""
    if CAST_FREE:
        began = run.clock()
        world = run.world()
        if world.player is not None and world.player.mode in BUSY:
            mode = world.player.mode
            run.seen(lambda w: w.player is None or w.player.mode not in BUSY, FREE_SECONDS, POLL)
            LOG.info('Macro: Town Portal key held %.2fs for the end of mode %d', run.clock() - began, mode)
    return press_skill(run, source.skill)


PORTAL_SEEN = (0.15, 0.85, 0.15, 0.8)  # window fractions the portal is walked to be drawn within
# A walk or a click that went through the portal is the arrival, not a failure (2026-10-21 00:55:22). False: as before
THROUGH_ON_THE_WAY = True


def through_portal(run: Run, near: tuple[float, float] | None = None) -> None:
    """Back from town through the character's open Town Portal: walk toward `near` (where it left the character)
    until a portal is in sight, then click it. `Abort` out of town and with no portal found."""
    from inventory_tracking.macros.shop import WALK_SECONDS, WALKING, walk_until  # shop.py imports this module

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
    if THROUGH_ON_THE_WAY and _out_of_town(run, here):
        # The walk's own click took the portal: 2026-10-21 00:55:22, the character in the City of the Damned by the
        # Double Bow while the step clicked for the town's portal ("the level is not under the pointer at any aim")
        # and the recovery left the game (the player: "that is VERY BAD")
        LOG.info('Macro: the walk to the portal went through it: in the level')
        arrived(run, 'the level')
        return
    shown = [t for t in portals(run) if t.mode == OPEN]
    if not shown:
        raise Abort('no Town Portal in sight')
    found = min(shown, key=lambda t: math.dist((t.x, t.y), (here.x, here.y)))
    mark = Target(here.area, (), (found.x / TILE_UNITS, found.y / TILE_UNITS), 'the level', 'target', use=TOWN_PORTAL)
    try:
        use_thing(run, mark, here, found, rect[2] / rect[3])
    except Abort:
        if not (THROUGH_ON_THE_WAY and _out_of_town(run, None)):
            raise
        LOG.info('Macro: the click on the portal did not read as taken, but the character is in the level')
    arrived(run, 'the level')


# The pickups at the open portal (`to_town` `first`) may take the character off it: at 02:30:33 on 2026-10-21 one went
# 47 units for a Magic Caduceus in Durance of Hate Level 3, every aim at the portal was off the screen ("town is not
# under the pointer at any aim") and the recovery left the game with a Magic Kriss on the ground. True: walked back
# until the portal is drawn within PORTAL_SEEN first (at once when it is). False: clicked from where the pickups left it
WALK_BACK = True


def _back_to(run: Run, portal: Thing, here):
    """WALK_BACK: walked toward the open portal until it is drawn within PORTAL_SEEN; the character then, None when the
    walk took it through (in town). `Abort` from the walk."""
    from inventory_tracking.macros.shop import WALK_SECONDS, WALKING, walk_until  # shop.py imports this module

    def place(now) -> tuple[float, float] | None:
        return None if now.player is None or now.player.in_town else (portal.x, portal.y)

    try:
        world = walk_until(run, place, PORTAL_SEEN, 'the portal')
    except Abort:
        if _out_of_town(run, None):
            raise
        return None
    world = run.seen(lambda w: w.player is not None and w.player.mode not in WALKING, WALK_SECONDS) or run.world()
    if world.player is None or world.player.in_town:
        return None
    return world.player


def _out_of_town(run: Run, here) -> bool:
    """Whether the character reads out of town now (`here`, else a fresh read): through a portal already."""
    player = here if here is not None else run.world().player
    if player is not None and not player.in_town:
        return True
    now = run.world().player
    return now is not None and not now.in_town

"""The valuables on the ground: the drops the pickup goes for, the game's sightings, the guard that keeps a game with
one, the trips back to them (the cube's room: running/room.py). A part of macros/runner.py `MacroRunner`, its methods
bound there."""

import dataclasses
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import VALUABLE, Loot, has_room
from inventory_tracking.levels.exits import short_name, through
from inventory_tracking.levels.model import Level
from inventory_tracking.levels.presets import display_name, open_passage
from inventory_tracking.levels.route import centre
from inventory_tracking.macros import actloop
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.loop import TZ_PICKUP, UNREAD
from inventory_tracking.macros.lootpolicy import GUARD, verdict
from inventory_tracking.macros.pickmode import kept
from inventory_tracking.macros.pickup import FETCH_HOPS, SHUNNED, approach, moved_in_hand, waived, wanted
from inventory_tracking.macros.running.base import AT_DROP_UNITS
from inventory_tracking.macros.shop import walk_until
from inventory_tracking.macros.sightings import Sighting, far
from inventory_tracking.macros.terrorize import SHARDS
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def _picked(self: MacroRunner, loot: Loot, tome: Callable[[], int | None] | None = None) -> Loot:
    """The drops the pickup goes for: those of the pickup level (macros/pickmode.py, KP_5), in every activity.
    `tome()`: the Tome of Identify's charges (`tome_charges`), for a big field item into the free block. A drop the
    pickup waived for the game (pickup.py `waive`: its label never under the pointer) is out of it, so neither the
    guard (`_valuable_left`) nor the sightings hold the game for it."""
    loot = kept(waived(loot), self.pickup_mode, tome)
    if not self.loop.on:
        return loot
    # A full stash stack's rune or material is not picked up (macros/loop.py `sold_full`, from the stash's one record:
    # none while it is unknown), but a Worldstone Shard always is (macros/actloop.py SHARD_ALWAYS_PICKED, 2026-10-22),
    # else one used at the next town stop while the game's overflow slot is free (PICK_OVER_LIMIT, 2026-10-21)
    skipped = self.loop.sold_full
    if skipped & SHARDS.keys():
        skipped = skipped - (SHARDS.keys() if actloop.SHARD_ALWAYS_PICKED else actloop.picked_shards(self.loop))
    if skipped:
        loot = dataclasses.replace(
            loot, drops=tuple(d for d in loot.drops if d.kind != VALUABLE or d.txt not in skipped)
        )  # the potions the belt wants are taken whatever the stash holds
    return loot


def tome_charges(memory: GameMemory) -> int | None:
    """The Tome of Identify's charges as carried now (game/decode.py `Pack.identifies`), None unread or no tome: one
    inventory read, made only when a big field item is weighed for the free block (loot/api.py FIELD_AT_ONCE)."""
    pack = memory.carried()
    return pack.identifies if pack is not None else None


def _sighted(self: MacroRunner, memory: GameMemory, loot: Loot) -> Loot:
    """`loot` noted in the game's sightings (macros/sightings.py), with the loop on and in one of its levels (not
    its town reads); the drops not on the character's level (sightings.py `far`: the level just left, still held by
    the client, 16:28:26 on 2026-10-21) left out of what the pickup goes for."""
    if self.loop.on and memory.where_area in self.loop.kind.levels:
        self.sightings.update(loot, memory.where, memory.where_area, time.monotonic())
    here = memory.where
    if here is not None and any(far(here, drop) for drop in loot.drops):
        loot = dataclasses.replace(loot, drops=tuple(drop for drop in loot.drops if not far(here, drop)))
    return loot


def _valuable_left(self: MacroRunner) -> str | None:
    """What the loop would pick up lying on the ground in sight (UNREAD when the ground cannot be read): a game
    with one is never left (`_loop_stopped`, loop.py `last_look`)."""
    try:
        table = one_unit_table(self.source.capture)
        if table is None:
            return UNREAD
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
        memory.ground_seen = self.ground_seen
        try:
            loot = self._sighted(
                memory, self._picked(self.put_down.see(memory.loot(**wanted())), lambda: tome_charges(memory))
            )
        finally:
            memory.close()
    except Exception as exc:
        LOG.info('Macro: the ground could not be read (%s)', exc)
        return UNREAD
    # What the guard must not leave is the policy's (macros/lootpolicy.py `verdict`)
    found = [
        drop
        for drop in loot.drops
        if verdict(drop, GUARD, room=has_room(loot.room, drop.size), shown=drop.unit_id in loot.shown, looped=True).hold
    ]
    if found:
        return found[0].label
    # One seen this game and out of the client's reach now lies there all the same (macros/sightings.py)
    return self.sightings.left()


def _fetch(self: MacroRunner, run: Run, level, key_names) -> bool:
    """A trip back to a valuable the loop saw and no press picked up (macros/sightings.py `fetch`); whether one was
    made. `Abort` when its trips back fail: the leg stops and the guard (`_valuable_left`) keeps the game. The terror
    zone's pickup leg also goes back to one on a level an open passage leads to (`crossing`, 2026-10-20 00:05:52: a
    Grand Charm left in the Outer Steppes stopped the loop in the Plains of Despair)."""
    player = run.world().player
    if player is None:
        return False
    trip = self.loop.trip
    if trip is not None and self.loop.returned == trip and self.loop.forgiven != (trip, self.loop.trips):
        # Back from a trip for room: its valuables' trips back start over (the player, 2026-10-18: "one game can
        # do several trips to the town")
        self.loop.forgiven = (trip, self.loop.trips)
        self.sightings.again()
    here = (player.x, player.y)
    across = None
    if self.loop.current == TZ_PICKUP and level is not None and level.area == player.area:
        # Not in other legs: the portal's pickup has a portal open here, a way on's its door (2026-10-20)
        def across(to: int) -> bool:
            return crossing(level, to, self.marks, here) is not None

    return self.sightings.fetch(
        here, player.area, time.monotonic(), lambda found: self._go_back(run, found, level, key_names), across
    )


def _go_back(self: MacroRunner, run: Run, found, level, key_names) -> None:
    """A trip back to `found`: within a click (`approach`), the pickup's give-up lifted, and, if not at it, a move
    to it so the clicks come from another footing (11 clicks from one place took nothing, 2026-10-18 15:53). On
    another level, across its open passage first (`cross`)."""
    SHUNNED.pop(found.unit_id, None)
    now = run.world().player if level is not None else None
    if now is not None and found.area is not None and now.area != found.area:
        level = cross(self, run, found, level, key_names)
    approach(run, found, level, key_names, FETCH_HOPS)
    player = run.world().player if level is not None else None
    if player is None or math.dist((player.x, player.y), (found.x, found.y)) <= AT_DROP_UNITS:
        return
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        return
    try:
        moved_in_hand(run, found, level, rect[2] / rect[3], key_names, Abort('a trip back, within a click'))
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: a trip back to %s: no move to it (%s); clicked from here', found.label, stop)


CROSS_CLICKS = 8  # walk clicks across an open passage (shop.py STEP 12 units each), from within a click of it
INSIDE_TILES = 2.0  # tiles back from the passage's far place: where the walk across starts
LEVEL_SECONDS = 3.0  # for the level guide to show the level crossed into


@dataclass(frozen=True)
class Place:
    """A place `approach` goes to (pickup.py `Spot`)."""

    x: float
    y: float
    label: str


def crossing(
    level: Level | None,
    to: int,
    marks: Callable[[str], tuple[tuple[float, float], ...]] | None,
    toward: tuple[float, float],
) -> tuple[float, float] | None:
    """The far place (world units) of the open passage from `level` into level `to` (levels/exits.py `through`): at
    the card's mark of `to` nearest `toward` (world units), else at the room touching `to` nearest their middle (as
    `border_exits` marks it). None: no level map, a door or stairs (no open passage), no room known to touch `to`."""
    if level is None or level.area == to or not open_passage(level.area, to):
        return None
    found = [mark for label in {short_name(to), display_name(to)} for mark in (marks(label) if marks else ())]
    if not found:
        touching = [room for room in level.rooms if to in room.leads_to]
        if not touching:
            return None
        middle = (
            sum(centre(room)[0] for room in touching) / len(touching),
            sum(centre(room)[1] for room in touching) / len(touching),
        )
        found = [min((centre(room) for room in touching), key=lambda point: math.dist(point, middle))]
    tiles = (toward[0] / TILE_UNITS, toward[1] / TILE_UNITS)
    far = through(level.rooms, min(found, key=lambda mark: math.dist(mark, tiles)), to, level.ground)
    return (far[0] * TILE_UNITS, far[1] * TILE_UNITS) if far is not None else None


def cross(self: MacroRunner, run: Run, found: Sighting, level: Level | None, key_names) -> Level | None:
    """Into `found`'s level across the open passage (`crossing`): within a click of it, then walked through (pursuit.py
    `through`); the level guide's map of the level crossed into (None: not shown in LEVEL_SECONDS). `Abort` with no
    way back (the guard keeps the game, as before) or no crossing."""
    to = found.area
    assert to is not None
    far = crossing(level, to, self.marks, (found.x, found.y))
    if far is None or level is None:
        raise Abort(f'{found.label} lies in {display_name(to)} and no open passage is known back into it')
    room = min(level.rooms, key=lambda r: math.dist(centre(r), (far[0] / TILE_UNITS, far[1] / TILE_UNITS)))
    middle = (centre(room)[0] * TILE_UNITS, centre(room)[1] * TILE_UNITS)
    gap = math.dist(far, middle)
    back = min(1.0, INSIDE_TILES * TILE_UNITS / gap) if gap else 0.0
    inside = (far[0] + (middle[0] - far[0]) * back, far[1] + (middle[1] - far[1]) * back)
    what = f'the open passage into {display_name(to)}'
    LOG.info('Macro: a trip back to %s in %s: across %s at (%.0f, %.0f) first', found.label, display_name(to), what,
             *far)  # fmt: skip
    approach(run, Place(*inside, what), level, key_names, FETCH_HOPS)

    def crossed(world) -> bool:
        return world.player is not None and world.player.area == to

    walk_until(run, lambda world: far, None, what, until=crossed, clicks=CROSS_CLICKS)

    def shown() -> Level | None:
        hunter = self.hunter
        now = hunter.level() if hunter is not None and hunter.level is not None else None
        return now if now is not None and now.area == to else None

    run.seen(lambda world: shown() is not None, LEVEL_SECONDS)
    LOG.info('Macro: a trip back to %s: in %s', found.label, display_name(to))
    return shown()

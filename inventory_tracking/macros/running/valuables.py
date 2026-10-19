"""The valuables on the ground: the drops the pickup goes for, the game's sightings, the guard that keeps a game with
one, the trips back to them and the cube's room. A part of macros/runner.py `MacroRunner`, its methods bound there."""

import dataclasses
import math
import time
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.game.records import VALUABLE, Loot, has_room
from inventory_tracking.input.keybindings import INVENTORY, action_key
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.cube import stash
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.lootpolicy import GUARD, verdict
from inventory_tracking.macros.pickmode import kept
from inventory_tracking.macros.pickup import FETCH_HOPS, SHUNNED, TAKEN, approach, moved_in_hand, wanted
from inventory_tracking.macros.running.base import AT_DROP_UNITS
from inventory_tracking.native.memory import one_unit_table


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


def _picked(self: MacroRunner, loot: Loot) -> Loot:
    """The drops the pickup goes for: with the loop on, those of its pickup mode (macros/pickmode.py)."""
    if not self.loop.on:
        return loot
    loot = kept(loot, self.pickup_mode)
    skipped = self.loop.sold_full  # a full stash stack's rune is not picked up (macros/loop.py `sold_full`)
    if skipped:
        loot = dataclasses.replace(
            loot, drops=tuple(d for d in loot.drops if d.kind != VALUABLE or d.txt not in skipped)
        )  # the potions the belt wants are taken whatever the stash holds
    return loot


def _sighted(self: MacroRunner, memory: GameMemory, loot: Loot) -> Loot:
    """`loot` noted in the game's sightings (macros/sightings.py), with the loop on and in one of its levels (not
    its town reads)."""
    if self.loop.on and memory.where_area in self.loop.kind.levels:
        self.sightings.update(loot, memory.where, memory.where_area, time.monotonic())
    return loot


def _valuable_left(self: MacroRunner) -> str | None:
    """What the loop would pick up lying on the ground in sight ('unread' when the ground cannot be read): a game
    with one is never left (`_loop_stopped`)."""
    try:
        table = one_unit_table(self.source.capture)
        if table is None:
            return 'unread'
        memory = GameMemory(self.source.pid, self.source.images['candidate_base'], table)
        memory.ground_seen = self.ground_seen
        try:
            loot = self._sighted(memory, self._picked(self.put_down.see(memory.loot(**wanted()))))
        finally:
            memory.close()
    except Exception as exc:
        LOG.info('Macro: the ground could not be read (%s)', exc)
        return 'unread'
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
    made. `Abort` when its trips back fail: the leg stops and the guard (`_valuable_left`) keeps the game."""
    player = run.world().player
    if player is None:
        return False
    trip = self.loop.trip
    if trip is not None and self.loop.returned == trip and self.loop.forgiven != (trip, self.loop.trips):
        # Back from a trip for room: its valuables' trips back start over (the player, 2026-10-18: "one game can
        # do several trips to the town")
        self.loop.forgiven = (trip, self.loop.trips)
        self.sightings.again()
    return self.sightings.fetch(
        (player.x, player.y),
        player.area,
        time.monotonic(),
        lambda found: self._go_back(run, found, level, key_names),
    )


def _go_back(self: MacroRunner, run: Run, found, level, key_names) -> None:
    """A trip back to `found`: within a click (`approach`), the pickup's give-up lifted, and, if not at it, a move
    to it so the clicks come from another footing (11 clicks from one place took nothing, 2026-10-18 15:53)."""
    SHUNNED.pop(found.unit_id, None)
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


def _room_in_cube(self: MacroRunner, run: Run) -> int:
    """Outside the KP_6 loop, the valuables the macro picked up itself (pickup.py TAKEN) into the cube; how many."""
    if self.loop.on or run.carried is None:
        return 0
    pack = run.carried()
    world = run.world()
    if pack is None or world.player is None:
        return 0
    key = action_key(self.saved_games, world.player.name, INVENTORY)
    if key is None:
        return 0
    own = frozenset((item.txt, item.x, item.y) for item in pack.items if item.unit_id not in TAKEN)
    return stash(run, key, own)

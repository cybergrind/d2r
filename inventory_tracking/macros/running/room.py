"""The no-room routine every activity shares (the player, 2026-10-19: "EVERY loop and activity should have the same
routines for situations when we don't have space: move to cube, if no space after that - go to town and do town
routine"): the loop's own items into the cube (the protected cells, macros/volatile.py; never the player's), then a
trip to town by the room package (macros/agenda.py `room_package`, macros/tzloop.py) and back through the portal, and
the valuable taken. The KP_6 loop's kinds make it through their stops (running/recovery.py, macros/stops.py); an
activity by hand (the KP_1 level run, attack mode, a pickup or teleport press) through ROOM, a run of its own
(`_room_errand`), after which the activity goes on as the player left it. A part of macros/runner.py `MacroRunner`,
its methods bound there."""

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inventory_tracking.common import LOG
from inventory_tracking.game.records import VALUABLE, Drop, Loot, World, has_room
from inventory_tracking.input.keybindings import INVENTORY, action_key
from inventory_tracking.macros import tzloop
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.cube import arrange_keys, stash
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_NEAR
from inventory_tracking.macros.hunting.base import SIGHT, hostiles, threat
from inventory_tracking.macros.lootpolicy import trip_for
from inventory_tracking.macros.pickup import pick_up
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.routines import DEAD
from inventory_tracking.macros.running.base import PICKUP
from inventory_tracking.macros.stops import low_life
from inventory_tracking.native.layout import TOWN_IDS


if TYPE_CHECKING:
    from inventory_tracking.macros.runner import MacroRunner


ROOM = 'room trip'  # the routine: the trip of an activity by hand (`_room_errand`)
# How the activity goes on after its trip (`Errand.resume`)
RESUME_RUN = 'the level run'  # a fresh KP_1 press: the level's run again, the valuable its side drop
RESUME_ATTACK = 'attack mode'  # attack mode on again: its sweep takes the valuable
RESUME_NONE = 'the press'  # a press's: the trip ends with the valuable picked up


@dataclass
class Errand:
    """A trip for room of an activity by hand. `unit` the valuable (None: the nearest with no room, for a press's
    stop); `resume` how the activity goes on (RESUME_*), only once `done`."""

    unit: int | None
    label: str
    resume: str
    done: bool = False


def tripped(drop: Drop, loot: Loot) -> bool:
    """Whether a trip is made for `drop` with no room for it (macros/lootpolicy.py `trip_for`)."""
    return trip_for(drop, shown=drop.unit_id in loot.shown)


def _room_in_cube(self: MacroRunner, run: Run) -> int:
    """Outside the KP_6 loop, the loop's items (the protected cells decide: `Loop.told`) into the cube, the keys out of
    the free block first as the loop's `make_room` does (execution.py); how many moved (an arranged key stack counts
    one). The loop on: 0, its stops make the room."""
    if self.loop.on or run.carried is None:
        return 0
    world = run.world()
    pack = run.carried()
    if pack is None or world.player is None:
        return 0
    key = action_key(self.saved_games, world.player.name, INVENTORY)
    own = self.loop.told(pack, world.player.name, self.item_stats)
    if key is None or own is None:
        return 0
    arranged = arrange_keys(run, key)
    return stash(run, key, own) + int(bool(arranged))


def unsafe(world: World, loot: Loot) -> str | None:
    """Why no trip starts now, None when one may: a hostile within SIGHT of the character (running/recovery.py
    `_attacker_near`'s ring) or life under the healer's floor (macros/stops.py `low_life`): "we must not die"."""
    player = world.player
    if player is None:
        return 'no character read'
    near = sum(1 for m in hostiles(world) if math.dist((m.x, m.y), (player.x, player.y)) <= SIGHT)
    if near:
        return f'{near} hostiles within {SIGHT:.0f}'
    if loot.max_life and low_life((loot.life, loot.max_life)):
        return f'life low ({loot.life}/{loot.max_life})'
    return None


def _room_trip_possible(self: MacroRunner) -> bool:
    """Whether an activity by hand could make a trip for room in the game the last poll read (the hunt's `can_trip`,
    no read of its own): the loop off, none under way, out of town, trips left (`Loop.may_trip`)."""
    game, area = self.journey.game, self.area_seen
    if self.loop.on or self.closed or self.errand is not None or game is None or area is None or area in TOWN_IDS:
        return False
    return self.loop.may_trip(game)


def _room_trip_due(self: MacroRunner, run: Run, drop: Drop, world: World, loot: Loot) -> bool:
    """The hunt's ask (hunting/choice.py `no_room`, at each look of its stand), from the run's thread: a valuable of
    an activity by hand still has no room after the cube; whether its trip is due (the run is then cancelled and ROOM
    follows: `_follow`). Never with the loop on (its own stops make it), past TRIPS_A_GAME trips a game
    (`Loop.may_trip`), in controller mode, in town, dead or `unsafe`; not for an identify candidate (`tripped`)."""
    player = world.player
    if player is None or player.in_town or player.mode in DEAD or not world.in_game or run.pad is not None:
        return False
    if not tripped(drop, loot) or unsafe(world, loot) is not None:
        return False
    game = world.game_name
    with self.lock:
        if self.loop.on or self.closed or self.errand is not None or not self.loop.may_trip(game):
            return False
        hunter = self.hunter
        resume = RESUME_RUN if hunter is not None and hunter.leashed else RESUME_ATTACK if self.attack_mode else ''
        errand = self.errand = Errand(drop.unit_id, drop.label, resume or RESUME_NONE)
        self.attack_mode = False
        self._end_run('a trip to town for room')
        self.cancelled.set()  # the run ends at its next look; ROOM follows it (`_follow`)
    LOG.info('Macro: room: no room for %s at (%.0f, %.0f) after the cube: a trip to town, then %s goes on',
             drop.label, drop.x, drop.y, errand.resume)  # fmt: skip
    run.say(f'No room for {drop.label}: a trip to town for room')
    return True


def _room_after_press(self: MacroRunner, stop: Abort, routine: str) -> bool:
    """A press of the player's stopped for a valuable with no room (pickup.py `pick_up`'s 'room' stop): whether its
    errand is due (`_room_errand` finds the drop, makes the cube's room, then the trip). Under the lock."""
    if self.loop.on or self.closed or self.errand is not None or stop.cause != 'room':
        return False
    self.errand = Errand(None, str(stop), RESUME_ATTACK if self.attack_mode else RESUME_NONE)
    LOG.info('Macro: room: %s (%s): the cube, then a trip to town for room', stop, routine)
    return True


def _room_errand(self: MacroRunner, run: Run, key_names) -> None:
    """ROOM: the errand's valuable (`self.errand`) taken by the shared routine: the cube, then the room package
    (tzloop.py `errand`), then taken (a press's) or left to the activity that goes on (`_follow`). Says why at every
    stop; never leaves the game, never acts dead, stops for the player's hand (actuator.py `Hand`)."""
    errand = self.errand
    if errand is None:
        return
    world = run.world()
    player = world.player
    look = run.loot
    if player is None or player.mode in DEAD or not world.in_game or look is None:
        return  # "if we died - we MUST not take ANY other actions" (the player, 2026-10-19)
    try:
        loot = look()
        drop = _errand_drop(loot, (player.x, player.y), errand)
        if drop is None:
            LOG.info('Macro: room: %s no longer lies here: no trip', errand.label)
            errand.done = True
            return
        errand.unit, errand.label = drop.unit_id, drop.label
        if not has_room(loot.room, drop.size):
            moved = self._room_in_cube(run)
            loot = look()
            if has_room(loot.room, drop.size):
                LOG.info('Macro: room: %d items into the cube: room for %s', moved, drop.label)
        if not has_room(loot.room, drop.size):
            if not tripped(drop, loot):
                LOG.info('Macro: room: no room for %s, an identify candidate: no trip for it', drop.label)
                run.warn(f'Inventory full: {drop.label} left on the ground')
                errand.done = True
                return
            _trip(self, run, key_names, drop, loot)
        if errand.resume == RESUME_NONE:
            level = self.hunter.level() if self.hunter is not None and self.hunter.level is not None else None
            pick_up(run, level, key_names, lambda: None, threat(run), unit=drop.unit_id)
        errand.done = True
        run.warn(None)
    except Abort as stop:
        if isinstance(stop, Cancelled):
            raise
        # The player's hand included: the trip never goes on over it; the valuable is said where it lies
        LOG.info('Macro: room: the trip for %s stopped: %s', errand.label, stop)
        run.warn(f'Room trip stopped ({stop}): {errand.label} lies on the ground')
        if self.loop.tripping(world.game_name):
            # Over for the loop's bookkeeping: a later stand may make the next of the game's trips (`may_trip`)
            self.loop.returned = world.game_name
        raise


def _trip(self: MacroRunner, run: Run, key_names, drop: Drop, loot: Loot) -> None:
    """The trip itself: only in the quiet with life not low and trips left (as the loop's: `Loop.may_trip`)."""
    world = run.world()
    player = world.player
    assert player is not None
    why = unsafe(world, loot)
    if why is not None:
        raise Abort(f'no trip to town for room now: {why}')
    game = world.game_name
    if not self.loop.may_trip(game):
        raise Abort(f'no trip to town for room: {self.loop.trips_in(game)} made in this game')
    if run.pad is not None:
        raise Abort('the trip to town for room needs mouse mode')
    self.loop.marks = self.marks
    if run.carried is not None and (pack := run.carried()) is not None:
        self.loop.told(pack, player.name, self.item_stats)  # the visit's own: the protected cells
    LOG.info('Macro: room: no room for %s after the cube: the room package from level %d', drop.label, player.area)
    tzloop.errand(self.loop, run, key_names, self.progress, self._loop_hands(run, key_names), game, player.area)


def _errand_drop(loot: Loot, here: tuple[float, float], errand: Errand) -> Drop | None:
    """The errand's valuable in `loot`: its unit, else (a press's) the nearest to `here` with no room within PICK_NEAR
    that a trip is made for."""
    drops = [d for d in loot.drops if d.kind == VALUABLE]
    if errand.unit is not None:
        return next((d for d in drops if d.unit_id == errand.unit), None)
    roomless = [
        d
        for d in drops
        if not has_room(loot.room, d.size) and math.dist(here, (d.x, d.y)) <= PICK_NEAR and tripped(d, loot)
    ]
    return min(roomless, key=lambda d: math.dist(here, (d.x, d.y))) if roomless else None


def _resume_errand(self: MacroRunner, errand: Errand) -> None:
    """After the trip (or with it dropped) the activity goes on as the player left it: the KP_1 level run posted again
    as its press posts it (runner.py `_dispatch`; the level's own mode, a terror zone's full clear), or attack mode on
    again; a press's ends here. Never with the loop on. Under the lock (`_follow`)."""
    hunter = self.hunter
    if self.loop.on or self.closed:
        return
    if errand.resume == RESUME_RUN and hunter is not None and self.pursuit:
        hunter.hand_over, hunter.run_over = self._hand_over, self._run_over
        hunter.post(Pursuit(PICKUP, time.monotonic(), advance=False, leash=FULL))
        if errand.unit is not None:
            hunter.waived.discard(errand.unit)  # the stand-by's valuable is the run's side drop now, not passed
        self.attack_mode, self.attack_declined = True, False
    elif errand.resume == RESUME_ATTACK:
        self.attack_mode, self.attack_declined = True, False
    else:
        return
    LOG.info('Macro: room: %s goes on after the trip for %s', errand.resume, errand.label)

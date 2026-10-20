"""The valuables the KP_6 loop has seen this game, kept until off the ground (routes/lower-kurast-loop-plan.md §14):
never leave a game while a valuable the loop would pick up lies on the ground (the player, 2026-10-17 01:21). The
pickup reads only what the client holds now, so a drop out of the client's reach was forgotten before this.

- *off the ground*: the character within GONE_UNITS of its place and the unit not read: resolved.
- *out of the read*: further off and not read: still wanted (said once, with the distance).
- `fetch`: the loop's "what is left" leg goes back to the nearest one (on another level across an open passage,
  2026-10-20); past FETCH_TRIES or FETCH_SECONDS it raises `Abort` and the runner's guard (`outstanding`) keeps the
  game.
"""

import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Drop, Loot, has_room
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.lootpolicy import SIGHTINGS, verdict


__all__ = ['ARRIVAL_SECONDS', 'FETCH_SECONDS', 'FETCH_TRIES', 'GONE_UNITS', 'Sighting', 'Sightings']

GONE_UNITS = 20.0  # world units: a valuable not read this near is off the ground (the pickup's PICK_UNITS)
FETCH_TRIES = 2  # trips back to one valuable before the loop stops for the player
# Seconds after the character enters a level in which a valuable not read near it is not yet judged off the ground:
# the client fills the level's units after the arrival. On 2026-10-21 00:55:22 the first read back through the portal
# held no ground units; the Unique Double Bow 2 units off was forgotten as "taken", the guard read none and the game
# was left with it on the ground (the player: "we returned to item on the ground, and instead of picking it - we exit
# the game / that is VERY BAD"). 0: judged at the first read, as before
ARRIVAL_SECONDS = 3.0
FETCH_SECONDS = 40.0  # a game's trips back, all of them


@dataclass
class Sighting:
    """A valuable seen on the ground: where, and how the loop has fared with it."""

    unit_id: int
    label: str
    x: float
    y: float
    area: int | None
    seen: float  # the clock it was first seen
    read: bool = True  # in the last read
    tries: int = 0  # trips back (`Sightings.fetch`)


class Sightings:
    """The game's valuables seen and not yet off the ground."""

    def __init__(self) -> None:
        self.game: tuple[str, int] | None = None
        self.items: dict[int, Sighting] = {}
        self.fetching: float | None = None  # the clock of the game's first trip back
        self.area: int | None = None  # the level of the last read, and the clock the character entered it
        self.entered: float | None = None

    def update(self, loot: Loot, here: tuple[float, float] | None, area: int | None, now: float) -> None:
        """A read of the ground (`loot`: the drops the loop's pickup takes) with the character at `here` in `area`."""
        if loot.game is None:
            return
        if loot.game != self.game:
            self.game, self.items, self.fetching = loot.game, {}, None
        read = {drop.unit_id: drop for drop in loot.drops if self.held(drop, loot)}
        for drop in read.values():
            found = self.items.get(drop.unit_id)
            if found is None:
                self.items[drop.unit_id] = Sighting(drop.unit_id, drop.label, drop.x, drop.y, area, now)
            else:
                # Kept at its first place: a read mid-pickup gives inventory-cell coordinates (2026-10-17 19:02:23)
                found.read = True
        if area != self.area:
            self.area, self.entered = area, now
        if here is None:
            return
        settling = self.entered is not None and now - self.entered < ARRIVAL_SECONDS
        for found in list(self.items.values()):
            if found.unit_id in read or found.area != area:
                continue
            away = math.dist(here, (found.x, found.y))
            if away <= GONE_UNITS and settling and self.entered is not None and found.seen < self.entered:
                continue  # seen before this arrival, the level's units maybe not read yet: judged once it settles
            if away <= GONE_UNITS:
                del self.items[found.unit_id]
                if found.tries:
                    LOG.info('Macro: remembered %s at (%.0f, %.0f): off the ground (taken, or no longer there)',
                             found.label, found.x, found.y)  # fmt: skip
            elif found.read:
                found.read = False
                LOG.info('Macro: remembered %s at (%.0f, %.0f): out of the read, the character %.0f away',
                         found.label, found.x, found.y, away)  # fmt: skip

    @staticmethod
    def held(drop: Drop, loot: Loot) -> bool:
        """Whether `drop`, read in `loot`, is remembered until it is off the ground (lootpolicy.py `SIGHTINGS`)."""
        room = has_room(loot.room, drop.size)
        return verdict(drop, SIGHTINGS, room=room, shown=drop.unit_id in loot.shown, looped=True).hold

    def state(self) -> dict:
        """What a service restart carries over (runner.py `resume_state`; a forgotten Flawless Topaz, 2026-10-18 13:18).
        Clocks are time.monotonic(), shared by every process."""
        return {
            'game': list(self.game) if self.game is not None else None,
            'items': [dataclasses.asdict(found) for found in self.items.values()],
            'fetching': self.fetching,
        }

    def restore(self, state: dict) -> None:
        """Take up `state`; a malformed one is ignored."""
        try:
            game = tuple(state['game']) if state.get('game') else None
            items = {int(found['unit_id']): Sighting(**found) for found in state.get('items', ())}
        except KeyError, TypeError, ValueError:
            return
        self.game = (str(game[0]), int(game[1])) if game is not None else None
        self.items, self.fetching = items, state.get('fetching')

    def again(self) -> None:
        """Reset the trips back and their seconds after a trip to town for room (2026-10-18 13:16:00)."""
        self.fetching = None
        for found in self.items.values():
            found.tries = 0

    def outstanding(self) -> list[Sighting]:
        """The game's valuables seen and not yet off the ground."""
        return list(self.items.values())

    def left(self) -> str | None:
        """The first valuable still on the ground, by its label and place; None with none."""
        found = self.outstanding()
        return f'{found[0].label} at ({found[0].x:.0f}, {found[0].y:.0f})' if found else None

    def fetch(
        self,
        here: tuple[float, float],
        area: int | None,
        now: float,
        go: Callable[[Sighting], None],
        across: Callable[[int], bool] | None = None,
    ) -> bool:
        """One trip back to the nearest valuable in `area` (`go` brings it within a click); with none there, to one on
        a level `across` says is reached from here (an open passage; `go` crosses first, 2026-10-20); whether one was
        made. `Abort` past FETCH_TRIES or FETCH_SECONDS."""
        wanted = [found for found in self.items.values() if found.area == area]
        if not wanted and across is not None:
            wanted = [
                found
                for found in self.items.values()
                if found.area is not None and found.area != area and across(found.area)
            ]
        if not wanted:
            return False
        found = min(wanted, key=lambda s: math.dist(here, (s.x, s.y)))
        self.fetching = now if self.fetching is None else self.fetching
        if found.tries >= FETCH_TRIES or now - self.fetching > FETCH_SECONDS:
            raise Abort(
                f'{found.label} at ({found.x:.0f}, {found.y:.0f}) was not picked up after {found.tries} trips back'
            )
        found.tries += 1
        LOG.info('Macro: remembered %s at (%.0f, %.0f)%s, %.0f away: gone back for it (trip %d)', found.label, found.x,
                 found.y, '' if found.area == area else f' in level {found.area}', math.dist(here, (found.x, found.y)),
                 found.tries)  # fmt: skip
        go(found)
        return True

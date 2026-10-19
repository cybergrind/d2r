"""The valuables the KP_6 loop has seen this game, kept until they are off the ground (routes/lower-kurast-loop-plan.md
§14). The player's hard rule (2026-10-17 01:21): never leave a game while a valuable the loop would pick up lies on
the ground.

The loop forgot what it could no longer read: a Flawless Emerald seen in a Blade Warp's flight off the route
(08:58:34 on 2026-10-17) was 104 units away when the run ended, and the client no longer had its unit; a Small Charm
in a pile (04:41:12) whose two presses failed was left when the run moved on. The pickup goes only for what it reads
now (macros/pickup.py), and so did `runner.valuable_left`.

`Sightings` keeps each valuable the loop's pickup would take (the runner's loot read, after the pickup mode's
filter), by unit, for the game it was seen in:

- *off the ground*: a read with the character within GONE_UNITS of its place and the unit not in it (taken, or no
  longer there); resolved, no more wanted;
- *out of the read*: further off and not read (the client's units do not reach so far): still wanted; said once with
  the distance, which measures the client's reach;
- `fetch`: the loop's "what is left" leg, when its press finds nothing to pick up, goes back to the nearest one still
  wanted (`approach`, as the pickup's far drops); at most FETCH_TRIES times a valuable and FETCH_SECONDS a game, then
  `Abort`: the leg stops, and the runner's guard (`outstanding`) keeps the game rather than leaving it.
"""

import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass

from inventory_tracking.common import LOG
from inventory_tracking.game.records import Drop, Loot, has_room
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.lootpolicy import SIGHTINGS, verdict


__all__ = ['FETCH_SECONDS', 'FETCH_TRIES', 'GONE_UNITS', 'Sighting', 'Sightings']

GONE_UNITS = (
    20.0  # world units: a valuable not read this near is off the ground (the pickup clicks from 20: PICK_UNITS)
)
FETCH_TRIES = 2  # trips back to one valuable before the loop stops for the player
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
    """The game's valuables seen and not yet off the ground (the module text)."""

    def __init__(self) -> None:
        self.game: tuple[str, int] | None = None
        self.items: dict[int, Sighting] = {}
        self.fetching: float | None = None  # the clock of the game's first trip back

    def update(self, loot: Loot, here: tuple[float, float] | None, area: int | None, now: float) -> None:
        """A read of the ground (`loot`: the drops the loop's pickup takes) with the character at `here` in `area`."""
        if loot.game is None:
            return
        if loot.game != self.game:
            self.game, self.items, self.fetching = loot.game, {}, None
        # The sightings' "must not leave it" is the policy's (macros/lootpolicy.py `verdict`): a candidate for an
        # identify (macros/pickmode.py) is no valuable a game is kept for; a plain one with no room is (the ruling of
        # 2026-10-18 17:50)
        read = {drop.unit_id: drop for drop in loot.drops if self.held(drop, loot)}
        for drop in read.values():
            found = self.items.get(drop.unit_id)
            if found is None:
                self.items[drop.unit_id] = Sighting(drop.unit_id, drop.label, drop.x, drop.y, area, now)
            else:
                # Kept where it was first seen: an item on the ground does not move, and a read in the moment of its
                # pickup had a Chipped Sapphire at its inventory cell (3, 3), 5372 units off: the loop went back for
                # it and stopped for the player (19:02:23 on 2026-10-17)
                found.read = True
        if here is None:
            return
        for found in list(self.items.values()):
            if found.unit_id in read or found.area != area:
                continue
            away = math.dist(here, (found.x, found.y))
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
        """What a restart of the service carries over (runner.py `resume_state`): the game and its valuables still on
        the ground. A restart forgot a Flawless Topaz 94 units off, and the game was left with it (13:18 on 2026-10-18).
        The clocks are time.monotonic(), one clock for every process."""
        return {
            'game': list(self.game) if self.game is not None else None,
            'items': [dataclasses.asdict(found) for found in self.items.values()],
            'fetching': self.fetching,
        }

    def restore(self, state: dict) -> None:
        """Take up `state` (`state`); a malformed one is none."""
        try:
            game = tuple(state['game']) if state.get('game') else None
            items = {int(found['unit_id']): Sighting(**found) for found in state.get('items', ())}
        except KeyError, TypeError, ValueError:
            return
        self.game = (str(game[0]), int(game[1])) if game is not None else None
        self.items, self.fetching = items, state.get('fetching')

    def again(self) -> None:
        """A trip to town for room is over: the valuables' trips back and the game's seconds for them begin again
        (13:16:00 on 2026-10-18: "not picked up after 2 trips back" 2 s after the return, the seconds counted from
        before the trip's 37 s)."""
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

    def fetch(self, here: tuple[float, float], area: int | None, now: float, go: Callable[[Sighting], None]) -> bool:
        """One trip back to the nearest valuable still on the ground in `area` (`go`: brings it within a click);
        whether one was made. `Abort` past FETCH_TRIES for it or FETCH_SECONDS for the game."""
        wanted = [found for found in self.items.values() if found.area == area]
        if not wanted:
            return False
        found = min(wanted, key=lambda s: math.dist(here, (s.x, s.y)))
        self.fetching = now if self.fetching is None else self.fetching
        if found.tries >= FETCH_TRIES or now - self.fetching > FETCH_SECONDS:
            raise Abort(
                f'{found.label} at ({found.x:.0f}, {found.y:.0f}) was not picked up after {found.tries} trips back'
            )
        found.tries += 1
        LOG.info('Macro: remembered %s at (%.0f, %.0f), %.0f away: gone back for it (trip %d)',
                 found.label, found.x, found.y, math.dist(here, (found.x, found.y)), found.tries)  # fmt: skip
        go(found)
        return True

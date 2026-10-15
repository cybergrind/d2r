"""How often the service loop's slow work runs: one table, by what the character and the macro are doing.

rca/2026-10-13/latency-findings.md (fix 1): in the slow stretches of the 21:42 game (2026-10-13) the main loop's
watchers read the unit tables the macro reads (the level map 23.6 s, the terror probe 9.7, the runes 9.2, the stash
6.1 of 3 1/4 minutes of Chaos Sanctuary), each field one pread that gives up the GIL and takes it back, their
Python holding it in between, and the macro's look-and-decide after a warp grew from ~140 to 500-770 ms. So while
the macro works in a level (a run acts, or attack mode is on) what it does not need runs seldom or not at all, and
the stash watch runs only in town. In town every watcher keeps the interval it is configured with, the macro working
or not (attack mode stays on through a town visit, napping, while the player uses the stash and the vendors).

`Schedule.paced` sets a watcher's `poll_interval` from the table (every watcher gates its own reads by it) or says
it is not polled now; the level map's area read is not in the table (it stays at its 0.5 s: the teleport step waits
on a new level's card, macros/teleport.py `card_for`), nor its waypoints (the step's mark moves onto one when seen),
only its walls and card (levels/guide.py `refresh_interval`).
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.native.layout import TOWN_IDS


class Mode(StrEnum):
    TOWN = 'town'  # a town (the macro working or not), the menu, or not known: every watcher at its configured pace
    LEVEL = 'level'  # a level, the macro idle: the player plays
    WORKING = 'working'  # out of town, a macro run acts or attack mode is on


def mode_of(working: bool, area: int | None) -> Mode:
    if area in TOWN_IDS:
        return Mode.TOWN
    if working:
        return Mode.WORKING
    return Mode.TOWN if area is None else Mode.LEVEL


@dataclass(frozen=True)
class Cadence:
    """Seconds between a watcher's reads in each mode; None: it is not polled in that mode."""

    town: float | None
    level: float | None
    working: float | None

    def seconds(self, mode: Mode) -> float | None:
        return {Mode.TOWN: self.town, Mode.LEVEL: self.level, Mode.WORKING: self.working}[mode]


LEVEL_MAP_WORKING = 2.0  # the level map's walls and card while the macro works (sooner on a room's width moved)
RUNES_LEVEL, RUNES_WORKING = 1.0, 2.0
TERROR_LEVEL, TERROR_WORKING = 0.5, 1.0


def cadences(*, shop: float, identify: float, stash: float, runes: float, terror: float) -> dict[str, Cadence]:
    """The table. The town column is each watcher's configured interval (config.py, `serve`'s options); the
    level and working columns are no faster than it. Each row: who reads the result, how fresh it must be."""
    return {
        # Vendor stock (shop/service.py): a vendor is in town only; outside it the worker already probes 5x slower
        # to see the player come back. Nothing of the macro's.
        'shop': Cadence(shop, shop, None),
        # Items as they become identified (identify/service.py): Cain in town, a scroll by the player's own hand.
        'identify': Cadence(identify, identify, None),
        # The stash panel's close edge (collection/watch.py): the stash is in town only. An edge missed in a
        # level is not lost: the flag is read again on return, closed, and the collection follows.
        'stash': Cadence(stash, None, None),
        # The level map's walls and card (levels/guide.py `refresh_interval`, 0: every 0.5 s poll). The
        # macro paths over the walls (the guide's `level`, macros/hunt.py): the game loads rooms one or more past
        # the character's, and the guide reads sooner once it has moved a room's width (`REFRESH_MOVE`), so 2 s
        # is fresh enough; the HUD follows the character and every monster dot live between cards and walks the
        # monster table itself for new ones, in its own process (hud/live.py, hud/dots.py; run-1916-hud-findings.md).
        'level map': Cadence(0.0, 0.0, LEVEL_MAP_WORKING),
        # Ground arrows to runes and marked drops (loot/watch.py): for the player's eyes. The pickup step reads
        # the ground itself.
        'runes': Cadence(runes, max(runes, RUNES_LEVEL), max(runes, RUNES_WORKING)),
        # Monsters and kills (terror/probe.py): the route's kills (routes/progress.py), the remembered elites and
        # the explored rooms the hunter asks for (terror/tracker.py), the danger rows and the Terror card. A kill
        # or a pack seen a second late; `around` events come once a second anyway.
        'terror probe': Cadence(terror, max(terror, TERROR_LEVEL), max(terror, TERROR_WORKING)),
    }


class Schedule:
    """The mode of this pass of the service loop and each watcher's interval in it (`cadences`)."""

    def __init__(
        self, table: dict[str, Cadence], *, working: Callable[[], bool], area: Callable[[], int | None]
    ) -> None:
        self.table, self.working, self.area = table, working, area
        self.mode = Mode.TOWN

    def update(self) -> Mode:
        """The mode for this pass: asked once a pass, before the watchers."""
        self.mode = mode_of(bool(self.working()), self.area())
        return self.mode

    def seconds(self, step: str) -> float | None:
        return self.table[step].seconds(self.mode)

    def paced(self, step: str, watcher) -> bool:
        """Set `watcher.poll_interval` to the step's interval in this mode; False when it is not polled now."""
        seconds = self.seconds(step)
        if seconds is None:
            return False
        watcher.poll_interval = seconds
        return True

    def describe(self) -> str:
        def said(value: float | None) -> str:
            return 'off' if value is None else ('each poll' if value == 0 else f'{value:g} s')

        return '; '.join(
            f'{step} {said(row.town)} / {said(row.level)} / {said(row.working)}' for step, row in self.table.items()
        )

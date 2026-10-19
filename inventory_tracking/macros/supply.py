"""The potions of a level as a level run sees them (rca/2026-10-13/potions-findings.md, steps 2-4).

`Potions` remembers every healing/rejuvenation potion seen on the level until seen gone (the client holds only nearby
rooms), says once why one was left (`refuse`), and warns when the belt's last healing potion goes (`empty`; the
player, 2026-10-13: "something is wrong if we're empty"), naming who drank it. `worth`/`detour` price a potion on the
ground against the route; `low`/`restock` pick one for a belt running short.
"""

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from inventory_tracking.config import BELT, HEAL_PRIORITY, MERC_HEALING
from inventory_tracking.game.records import HEALING, REJUVENATION, Drop, Loot
from inventory_tracking.levels.doors import Door
from inventory_tracking.levels.geometry import Point
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.travel import walked_length
from inventory_tracking.models import PotionType
from inventory_tracking.tracking.belt import column_shortages


SEEN_GONE = 20.0  # units: a remembered potion not in a look made this near its place is gone (taken, by anyone)
DRUNK_BY = 1.0  # seconds: a potion gone from the belt this soon after the macro's key for its kind was the macro's
GONE_KEPT = 8  # potions gone from the belt remembered for the warning
KINDS = {HEALING: PotionType.HEALING, REJUVENATION: PotionType.REJUVENATION}
# Walked units within which a potion lying is a restock's goal (the player, 2026-10-14: "potions on the ground within
# ~40 walked units come before the standing goal")
RESTOCK_UNITS = 40.0
# The player, 2026-10-13: "keep at least 2 rev potions for user" (config.py MERC_HEALING)
REJUVENATION_RESERVE = MERC_HEALING.rejuvenation_reserve


@dataclass(frozen=True)
class Seen:
    """A potion seen on the ground of the level (kind: HEALING or REJUVENATION)."""

    unit: int
    kind: str
    x: float
    y: float
    label: str


def worth(count: int, reserve: int, seconds: float) -> float:
    """Seconds of detour a healing potion on the ground is worth: `seconds` (harm.py's price of one) for each the belt
    is below the `reserve` (automation/priority.py), none at it or above."""
    return seconds * max(0, reserve - count)


def unread(loot: Loot) -> bool:
    """Whether the belt is not known: no life read, or no game it is of."""
    return not loot.max_life or loot.game is None


def low(loot: Loot) -> tuple[str, ...]:
    """The kinds a belt low on potions restocks, the rarer first (the player, 2026-10-14): rejuvenations under
    REJUVENATION_RESERVE, healing potions under half of what their columns hold (rca/2026-10-14/run-1932-findings.md
    issue 2). None for an unread belt."""
    if unread(loot):
        return ()
    belt = on_belt(loot)
    rejuvenation_short, healing_short = column_shortages(loot.belt, loot.columns, BELT.layout)
    healing, rejuvenations = belt[PotionType.HEALING], belt[PotionType.REJUVENATION]
    kinds = []
    if rejuvenation_short and rejuvenations < REJUVENATION_RESERVE:
        kinds.append(REJUVENATION)
    if healing_short and 2 * healing < healing + healing_short:
        kinds.append(HEALING)
    return tuple(kinds)


def restock(loot: Loot, here: Point, ground: Ground | None, doors: Sequence[Door]) -> Drop | None:
    """The potion a `low` belt takes before the goal: the rarer kind first, the nearest within RESTOCK_UNITS walked.
    The quiet it is taken in is the caller's."""
    for kind in low(loot):
        near = sorted(
            (d for d in loot.drops if d.kind == kind and math.dist(here, (d.x, d.y)) <= RESTOCK_UNITS),
            key=lambda d: math.dist(here, (d.x, d.y)),
        )
        for drop in near:
            if walked_length(ground, doors, here, (drop.x, drop.y)) <= RESTOCK_UNITS:
                return drop
    return None


def spendable(loot: Loot, healing_points: float, floor: float) -> float | None:
    """Life points the belt can give beyond what it keeps (combat/harm.py `budget`): healing potions over the reserve
    (floor to full once, at least HEAL_PRIORITY.least_reserve, one more per missing rejuvenation). None unread."""
    if unread(loot):
        return None
    belt = on_belt(loot)
    rejuvenations = belt[PotionType.REJUVENATION]
    need = math.ceil((100 - floor) / 100 * loot.max_life / healing_points)
    kept = max(HEAL_PRIORITY.least_reserve, need) + max(0, REJUVENATION_RESERVE - rejuvenations)
    return max(0, belt[PotionType.HEALING] - kept) * healing_points


def detour(there: float, work: float) -> float:
    """Seconds a side goal `there` seconds away adds to the route: there, `work`, and back. An upper bound by the
    triangle inequality: the navigator's eta is from where the character stands only."""
    return 2 * there + work


class Potions:
    """What a level run knows of the potions of the level it is on, and of the belt's healing potions."""

    def __init__(self) -> None:
        self.area: int | None = None
        self.since = 0.0  # clock time the level was first looked at
        self.seen: dict[int, Seen] = {}  # on the ground, as far as known
        self.fates: dict[int, str] = {}  # unit -> what became of it: 'gone' (off the ground), or why it was left
        self.kinds: dict[int, str] = {}  # every potion seen on the level -> its kind
        self.said: set[tuple[int, str]] = set()
        self.healing: int | None = None  # healing potions on the belt at the last look
        self.gone: deque[tuple[float, str]] = deque(maxlen=GONE_KEPT)  # (when, by whom) of the belt's healing potions
        self.empty_said = False

    def see(self, loot: Loot, area: int, here: tuple[float, float], now: float, pressed: float) -> str | None:
        """One look at the ground and the belt; `pressed`: when the macro last pressed a healing key. The `empty`
        warning's text when the belt's last healing potion went now, else None."""
        if area != self.area:
            self.area, self.since = area, now
            self.seen, self.fates, self.kinds, self.said = {}, {}, {}, set()
            self.empty_said = False
        on_ground = {drop.unit_id for drop in loot.drops}
        for drop in loot.drops:
            if drop.kind in KINDS:
                self.seen[drop.unit_id] = Seen(drop.unit_id, drop.kind, drop.x, drop.y, drop.label)
                self.kinds[drop.unit_id] = drop.kind
        for unit, potion in list(self.seen.items()):
            if unit not in on_ground and math.dist(here, (potion.x, potion.y)) <= SEEN_GONE:
                del self.seen[unit]
                self.fates[unit] = 'gone'
        healing = on_belt(loot)[PotionType.HEALING]
        if not loot.max_life:
            return None  # an unread belt is no fall
        if self.healing is not None and healing < self.healing:
            by = 'the macro' if 0.0 <= now - pressed <= DRUNK_BY else 'not the macro (the healer or a hand)'
            self.gone.extend((now, by) for _ in range(self.healing - healing))
        fell = self.healing is not None and self.healing > 0 and healing == 0
        self.healing = healing
        if healing:
            self.empty_said = False
        if not fell or self.empty_said:
            return None
        self.empty_said = True
        return self.empty(loot, here, now)

    def refuse(self, unit: int, why: str) -> bool:
        """`unit` left for `why`: kept as its fate; whether that was not said before (to be said now)."""
        self.fates[unit] = why
        if (unit, why) in self.said:
            return False
        if len(self.said) > 500:
            self.said.clear()
        self.said.add((unit, why))
        return True

    def lying(self, kind: str, here: tuple[float, float]) -> list[Seen]:
        """The potions of `kind` known on the ground of the level, the nearest first."""
        found = [potion for potion in self.seen.values() if potion.kind == kind]
        return sorted(found, key=lambda potion: math.dist(here, (potion.x, potion.y)))

    def empty(self, loot: Loot, here: tuple[float, float], now: float) -> str:
        """The warning's text: the belt, who took the last healing potions, and the level's healing potions."""
        rejuvenations = on_belt(loot)[PotionType.REJUVENATION]
        takers = ', '.join(f'{by} {now - at:.1f} s ago' for at, by in reversed(self.gone)) or 'none seen go'
        healing = [unit for unit, kind in self.kinds.items() if kind == HEALING]
        fates: dict[str, int] = {}
        for unit in healing:
            fate = 'still on the ground' if unit in self.seen else self.fates.get(unit, 'gone')
            fates[fate] = fates.get(fate, 0) + 1
        told = '; '.join(f'{count} {fate}' for fate, count in sorted(fates.items(), key=lambda row: -row[1]))
        lying = self.lying(HEALING, here)
        nearest = f', the nearest {math.dist(here, (lying[0].x, lying[0].y)):.0f} away' if lying else ''
        return (
            f'no healing potion on the belt {now - self.since:.0f} s into the level (rejuvenations {rejuvenations}, '
            f'life {loot.life}/{loot.max_life}); the last gone, newest first: {takers}; healing potions seen on '
            f'the level: {len(healing)}{": " + told if told else ""}{nearest}'
        )

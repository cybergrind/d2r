"""The potions of a level as a level run sees them (rca/2026-10-13/potions-findings.md, steps 2-4).

The pickup key's own rule (macros/pickup.py `choose`) wants a potion of a kind the belt is short of within
POTION_UNITS, and a level run took such a potion only while no hostile stood within GATHER_CLEAR of it or the
character, forgetting it silently otherwise (moment M4 of the game of 21:42: three super healing potions left
6-10 units away while the run warped on toward a seal). What a level run keeps here, beside that rule:

- **what lies on the level** (`Potions.see`): every super healing and full rejuvenation potion seen on the
  ground of the level, by place and kind, until it is seen gone (the character within SEEN_GONE of its place
  and the potion not in the look) or the level is left. The client holds only the units of the rooms near the
  character, so a potion passed is still known after it has left the look;
- **why one was left** (`Potions.refuse`): said once a potion and reason in the log, and counted for the
  warning below (never again silent);
- **its value** (`worth`): a healing potion on the ground is worth what it saves, harm.py's price of one
  (`SafetySettings.healing_seconds`, Q6) for each potion the belt is below the healing reserve the character
  keeps (automation/priority.py `reserve`: those that bring him from the life floor back to full once). With the
  belt at the reserve or above it is worth no detour (U8: no hunger for potions with a full belt; the pickup key's
  own rule still takes one on the way); below it, a detour of up to that many seconds (`detour`) beats the
  route's next stage;
- **empty is a defect** (the player, 2026-10-13: "usually we shouldn't get into situation when we have no
  potions. something is wrong if we're empty"): the moment the belt's last healing potion goes on a level, one
  WARNING with what the run can see of why (`Potions.empty`): who took the last ones (the macro's drinker, or
  not: the healer of `make osd` or a hand), and every healing potion seen on the level with what became of it.
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
# ~40 walked units come before the standing goal"; goals.py PICK_NEAR, a valuable's own measure)
RESTOCK_UNITS = 40.0
# The rejuvenations kept for the character (the player, 2026-10-13: "keep at least 2 rev potions for user"; the
# healer gives the mercenary none of them: config.py MERC_HEALING)
REJUVENATION_RESERVE = MERC_HEALING.rejuvenation_reserve


@dataclass(frozen=True)
class Seen:
    """A potion seen on the ground of the level: its unit, kind (game/records.py HEALING or REJUVENATION), place and
    label."""

    unit: int
    kind: str
    x: float
    y: float
    label: str


def worth(count: int, reserve: int, seconds: float) -> float:
    """Seconds of detour a healing potion on the ground is worth with `count` on the belt (the module text):
    `seconds` for each one the belt is below the `reserve`, none at it or above."""
    return seconds * max(0, reserve - count)


def unread(loot: Loot) -> bool:
    """Whether the belt is not known: no life read, or no game it is of (game/records.py `Loot.game`)."""
    return not loot.max_life or loot.game is None


def low(loot: Loot) -> tuple[str, ...]:
    """The kinds (game/records.py HEALING, REJUVENATION) a belt low on potions restocks, the rarer first (the player,
    2026-10-14): rejuvenations under the REJUVENATION_RESERVE kept for the character, healing potions under half of
    what their columns hold (pickup.py `shortages`: the columns by what they hold, an empty one by the configured
    layout). At 22:55:31 on 2026-10-14 the belt held 2 healing potions of 8 and the run warped on past three potions
    13 units and less away (run-1932-findings.md issue 2). None for an unread belt (`unread`)."""
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
    """The potion a belt low on potions (`low`) takes before the goal: of the rarer kind wanted first, the nearest
    within RESTOCK_UNITS walked (travel.py `walked_length`). The quiet it is taken in is the caller's."""
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
    """Life points the belt can give back beyond what it keeps (combat/harm.py `budget`, `stock`): its healing
    potions over the ones the character keeps for under the life floor (automation/priority.py `reserve`: from the
    floor to full life once, at least HEAL_PRIORITY.least_reserve), one more kept for each rejuvenation under
    REJUVENATION_RESERVE, each potion worth `healing_points`. None for an unread belt (`unread`: nothing counted)."""
    if unread(loot):
        return None
    belt = on_belt(loot)
    rejuvenations = belt[PotionType.REJUVENATION]
    need = math.ceil((100 - floor) / 100 * loot.max_life / healing_points)
    kept = max(HEAL_PRIORITY.least_reserve, need) + max(0, REJUVENATION_RESERVE - rejuvenations)
    return max(0, belt[PotionType.HEALING] - kept) * healing_points


def detour(there: float, work: float) -> float:
    """Seconds a side goal `there` seconds away by the movement in hand adds to the route: the way there, the
    act's own `work`, and the way back as long as the way there. An upper bound of the spec's
    eta(here -> g) + work + eta(g -> primary) - eta(here -> primary) by the triangle inequality: the
    navigator's eta is asked from where the character stands only (travel.py `Travel.eta`)."""
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
        """One look at the ground and the belt on level `area` with the character at `here`; `pressed`: when
        the macro's drinker last pressed a healing potion's key. The warning's text when this look found the
        belt's last healing potion gone (`empty`), else None."""
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

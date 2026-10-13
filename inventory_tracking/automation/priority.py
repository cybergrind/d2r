"""Whom the healer feeds first, the healing potions it keeps for the character, and the belt running low.

The player's ruling (2026-10-13): "healer should feed merc, then me. but if situation is critical - then
feed player"; "usually we shouldn't get into situation when we have no potions. something is wrong if we're
empty". The constants are `config.HealPriorityConfig`'s, each with its reason; the study and the replay of the
game that asked for it are rca/2026-10-13/potions-findings.md, "Healer priority, built".

- **Critical** (`judge`): the character's life share, played `horizon` seconds ahead at its fall over the last
  `window` seconds (counted from the most it was in the window, as the burst rule counts it), is under the
  macro's floor. Then the character is stepped first and the mercenary is given no healing potion.
- **Reserve** (`reserve`): healing potions kept for the character whatever his life: those that bring him from
  the floor back to full life once, one more with no rejuvenation on the belt. While the belt holds no more, the
  mercenary is given none (a rejuvenation by its own rules, `HealingConfig.rejuvenation_reserve`, or nothing).
- Otherwise the mercenary is stepped first: when both want a potion at one sample it is his, and the
  character's at the next sample that shows the belt after it (`Outcome.STALE_BELT` in between).
- **Stock** (`StockWatch`): the belt's healing potions at the reserve or under it ("low") or none ("empty").
  The healer logs one `Potion stock:` line at each change, a warning when the stock falls, with who took the
  last ones (the healer's own deliveries by actor; the rest are "not the healer": the macro's drinker, a hand
  or a potion moved off the belt). The OSD belt card shows it while a fall of this game lasts.
"""

import math
from collections import deque
from collections.abc import Hashable
from dataclasses import dataclass
from enum import StrEnum

from inventory_tracking.config import HealPriorityConfig
from inventory_tracking.models import Actor, Hold, PotionSent, PotionType, State
from inventory_tracking.tracking.belt import potion_count


POINTS = 256  # raw life units to a life point (PlayerHealth, the OSD's `>> 8`)
KEPT = 8  # the healing potions gone that a stock line names
SENT_KEPT = 64  # the healer's healing deliveries remembered by item until the belt shows them gone


def reserve(most: float | None, rejuvenations: int, config: HealPriorityConfig) -> int:
    """Healing potions kept for the character: those from the floor back to full life (`most` points, None
    unread), one more with no rejuvenation on the belt, and never fewer than `least_reserve`."""
    need = math.ceil((100 - config.floor) / 100 * most / config.healing_points) if most else 0
    return max(config.least_reserve, need + (0 if rejuvenations else config.bare_extra))


def stock(state: State) -> tuple[int, int]:
    """(healing, rejuvenation) potions on the belt, every row; none where the belt is unread."""
    contents = state.belt.contents if state.belt is not None else ()
    return potion_count(contents, PotionType.HEALING), potion_count(contents, PotionType.REJUVENATION)


@dataclass(frozen=True)
class Verdict:
    """The character's situation at one sample, as the healer reads it. Shares are of the most life."""

    share: float  # the life now
    fall: float  # lost over the window, from the most it was in it
    ahead: float  # the life `horizon` seconds ahead if the fall goes on
    critical: bool
    healing: int  # healing potions on the belt
    rejuvenations: int
    reserve: int  # healing potions kept for the character
    keeps: bool = True  # the reserve is held back from the mercenary (`HealPriorityConfig.keep_healing`)

    @property
    def hold(self) -> Hold | None:
        """Why the mercenary is given no healing potion now; None: he may have one."""
        if self.critical:
            return Hold.CRITICAL
        if self.keeps and self.healing <= self.reserve:
            return Hold.RESERVE
        return None

    def __str__(self) -> str:
        return (
            f'life {self.share:.0%}, {self.ahead:.0%} ahead (fell {self.fall:.0%}); belt healing {self.healing} '
            f'(the character keeps {self.reserve}), rejuvenations {self.rejuvenations}'
        )


def judge(
    share: float, fall: float, most: float | None, healing: int, rejuvenations: int, config: HealPriorityConfig
) -> Verdict:
    """The verdict on the character's life `share` after a `fall` over the last window (pure)."""
    ahead = share - fall / config.window * config.horizon
    kept = reserve(most, rejuvenations, config)
    return Verdict(share, fall, ahead, ahead * 100 < config.floor, healing, rejuvenations, kept, config.keep_healing)


class PlayerWatch:
    """The character's life over the last window of one game, and the verdict at each sample."""

    def __init__(self, config: HealPriorityConfig) -> None:
        self.config = config
        self.game: Hashable = None
        self.recent: deque[tuple[float, float]] = deque()

    def look(self, state: State) -> Verdict | None:
        """The verdict; None where the character's life or the game is unread (the character first then)."""
        health = state.health_for(Actor.PLAYER)
        if state.session is None or health is None or not 0 < health[0] <= health[1]:
            return None
        if state.session.core != self.game:
            self.game = state.session.core
            self.recent.clear()
        current, maximum = health
        share = current / maximum
        while self.recent and state.sampled_at - self.recent[0][0] > self.config.window:
            self.recent.popleft()
        most = max((seen for _, seen in self.recent), default=share)
        self.recent.append((state.sampled_at, share))
        healing, rejuvenations = stock(state)
        return judge(share, max(0.0, most - share), maximum / POINTS, healing, rejuvenations, self.config)


class Level(StrEnum):
    STOCKED = 'stocked'  # more healing potions than the reserve
    LOW = 'low'  # the reserve or fewer
    EMPTY = 'empty'  # none


def level(healing: int, kept: int) -> Level:
    return Level.EMPTY if healing <= 0 else Level.LOW if healing <= kept else Level.STOCKED


ORDER = (Level.EMPTY, Level.LOW, Level.STOCKED)


@dataclass(frozen=True)
class Gone:
    """A healing potion that left the belt: when (the sample's clock) and who took it."""

    at: float
    by: Actor | None  # the actor the healer gave it to; None: not the healer


@dataclass(frozen=True)
class Change:
    """The belt's healing stock went from one level to another (`before` None: the game's first look)."""

    before: Level | None
    after: Level
    healing: int
    rejuvenations: int
    reserve: int
    gone: tuple[Gone, ...]  # the last healing potions gone this game, oldest first
    at: float

    @property
    def fell(self) -> bool:
        """Down to low or empty, or a game that begins there."""
        if self.after == Level.STOCKED:
            return False
        return self.before is None or ORDER.index(self.after) < ORDER.index(self.before)

    @property
    def line(self) -> str:
        """The log line, its prefix stable for the RCA's search: `Potion stock:`."""
        start = 'the game begins with ' if self.before is None else ''
        if self.after == Level.EMPTY:
            what = f'{start}no healing potion on the belt (rejuvenations {self.rejuvenations})'
        else:
            what = (
                f'{start}healing potions {self.after}: {self.healing} on the belt, the character keeps '
                f'{self.reserve} (rejuvenations {self.rejuvenations})'
            )
        if not self.gone:
            return f'Potion stock: {what}'
        takers = ', '.join(
            f'{"not the healer" if gone.by is None else f"{gone.by} by the healer"} {self.at - gone.at:.1f} s ago'
            for gone in reversed(self.gone)
        )
        return f'Potion stock: {what}; the last gone, newest first: {takers}'


class StockWatch:
    """The belt's healing potions over one game: their level, whether it fell during the game (`alarm`, the OSD
    card), and who took the last ones. Fed the samples (`look`) and the healer's deliveries (`sent`)."""

    def __init__(self, config: HealPriorityConfig) -> None:
        self.config = config
        self.game: Hashable = None
        self.level: Level | None = None
        self.alarm = False
        self.healing = 0
        self.ids: frozenset[int] = frozenset()
        self.delivered: dict[int, Actor] = {}
        self.gone: deque[Gone] = deque(maxlen=KEPT)

    def sent(self, event: PotionSent) -> None:
        """A potion the healer pressed: a healing one is named by its taker when the belt shows it gone."""
        if event.request.potion == PotionType.HEALING:
            self.delivered[event.request.item.item_id] = event.request.actor
            if len(self.delivered) > SENT_KEPT:
                self.delivered.pop(next(iter(self.delivered)))

    def look(self, state: State) -> Change | None:
        """The change of level this sample makes; None while it stays, or where the belt or game is unread."""
        if state.session is None or state.belt is None:
            return None
        if state.session.core != self.game:
            self.game = state.session.core
            self.level = None
            self.alarm = False
            self.gone.clear()
            self.delivered.clear()
        healing, rejuvenations = stock(state)
        ids = frozenset(state.belt.item_ids)
        if self.level is not None:
            takers = [self.delivered.pop(item) for item in self.ids - ids if item in self.delivered]
            for index in range(self.healing - healing):
                self.gone.append(Gone(state.sampled_at, takers[index] if index < len(takers) else None))
        self.healing, self.ids = healing, ids
        health = state.health_for(Actor.PLAYER)
        kept = reserve(health[1] / POINTS if health else None, rejuvenations, self.config)
        now = level(healing, kept)
        if now == self.level:
            return None
        change = Change(self.level, now, healing, rejuvenations, kept, tuple(self.gone), state.sampled_at)
        self.alarm = now != Level.STOCKED and (self.alarm or (self.level is not None and change.fell))
        self.level = now
        return change

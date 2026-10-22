"""Survival, the pure part: what the character's life has been doing and whether to drink now (macros/architecture.md
§4.4; macros/drinking.py presses the keys). Readings in, a `Pressure` and a potion kind out; no game, no clock.

The user's rulings (2026-10-12): drink when the life is not full, "maybe 90% mark", without wasting the potions;
rejuvenations for the more severe situations. `make osd` (automation/heal.py) stays the independent last resort
below these marks.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from inventory_tracking.config import Config, Percent, Positive
from inventory_tracking.models import PotionType


@dataclass(frozen=True)
class Reading:
    """The character's life at one look."""

    at: float  # seconds, any clock
    life: float  # points
    most: float  # points at full life (it changes with the weapon set)


@dataclass(frozen=True)
class Supply:
    """The potions at hand, by kind: on the belt, and on the ground near enough to be picked up after."""

    healing: int = 0
    rejuvenation: int = 0
    healing_near: int = 0
    rejuvenation_near: int = 0


@dataclass(frozen=True)
class Pressure:
    """What the life did over the window that ends at the last reading. Shares are of the most life."""

    share: float  # the life now
    lost: float  # every drop in the window summed; what a potion gave back is not taken off
    rate: float  # `lost` a second, over the seconds the window's readings cover
    burst: float  # the most lost within any `burst` seconds of the window

    @property
    def sustained(self) -> bool:
        return self.lost > 0.0


CALM = Pressure(1.0, 0.0, 0.0, 0.0)


def pressure(readings: Sequence[Reading], *, window: float = 4.0, burst: float = 1.0) -> Pressure:
    """The pressure at the last of `readings` (in time order). A reading with no most life (an unread
    frame) is left out; with none left the character is taken to be whole and unhurt."""
    known = [reading for reading in readings if reading.most > 0 and reading.life > 0]
    if not known:
        return CALM
    now = known[-1].at
    recent = [reading for reading in known if now - reading.at <= window]
    # Between two readings with another most life the weapon set was swapped: the share moves, no blow fell.
    drops = [
        (after.at, max(0.0, before.life / before.most - after.life / after.most) if before.most == after.most else 0.0)
        for before, after in pairwise(recent)
    ]
    lost = sum(drop for _, drop in drops)
    worst = max(
        (sum(drop for at, drop in drops if start < at <= start + burst) for start in _starts(recent)), default=0.0
    )
    seconds = now - recent[0].at
    return Pressure(recent[-1].life / recent[-1].most, lost, lost / seconds if seconds > 0 else 0.0, worst)


def _starts(readings: Sequence[Reading]) -> list[float]:
    return [reading.at for reading in readings]


# The death at 23:35:33.97 on 2026-10-21 (Disused Fane, take 20261021T203514Z-95, rca/2026-10-21/death-findings.md):
# no rejuvenation was drunk, 8 on the belt. One blow took 2014 -> 1578 of 2943 (22% within a second, Amplify Damage on
# the character), but the window's mean rate (9% a second) played `horizon` ahead kept the life over `danger`, and so
# did every look after; the last two frames took 1128. The player, 2026-10-21: "we must have top priority to no die
# ourselves and prevent loosing experience"; "a rejuvenation only in very scary moments" (of the mana: a life falling
# this fast is one). True: under EMERGENCY_BELOW, the window's worst second (`Pressure.burst`) played BURST_AHEAD
# seconds ahead under `danger` is a severe moment too. False: the mean rate alone, as before.
EMERGENCY_REJUVENATION = True
EMERGENCY_BELOW = 60.0  # percent of the most life
BURST_AHEAD = 1.5  # seconds of the worst second's loss
# 2026-10-22: the client's life read refreshes every 0.4 s (70% of 35,798 changes over the takes of 2026-10-20..22 came
# 0.36-0.46 s apart; rca/2026-10-21/fane-death-sim-findings.md §7), so the drinker sees the life up to that late. True:
# the emergency rule plays the worst second LIFE_READ_LAG s further ahead. False: BURST_AHEAD alone.
READ_LAG = True
LIFE_READ_LAG = 0.4


class DrinkSettings(Config):
    """The drinking marks. Shares are percents of the most life; a build changes them by `with_overrides`."""

    enabled: bool = True
    healing_below: Percent = 90.0  # user: "maybe 90% mark is good"
    # Under `healing_below` only while life is being lost; under `idle_below` whatever happens.
    idle_below: Percent = 75.0
    healing_gap: Positive = 6.0  # seconds a healing potion is given to work before the next one
    hurry_below: Percent = 65.0  # under it the gap is `hurry_gap`
    hurry_gap: Positive = 2.5
    # With no more healing potions than this on the belt and none near on the ground, they are kept for
    # under `hurry_below` (user: "I don't want to waste all potions very fast").
    keep_healing: int = 2
    # A rejuvenation ("for more severe situations"): the loss of the window played `horizon` seconds
    # ahead takes the life under `danger`, and the life is under `rejuvenation_below` already.
    rejuvenation_below: Percent = 55.0
    horizon: Positive = 1.5
    danger: Percent = 30.0
    rejuvenation_gap: Positive = 1.0


def drink(
    felt: Pressure, supply: Supply, since: Mapping[PotionType, float], settings: DrinkSettings
) -> PotionType | None:
    """The potion to drink now, or None. `since`: seconds since a potion of each kind was last drunk, by
    whoever drank it (a kind never drunk is missing)."""
    if not settings.enabled:
        return None
    share = felt.share * 100
    ago = {kind: since.get(kind, float('inf')) for kind in PotionType}
    ahead = (felt.share - felt.rate * settings.horizon) * 100
    severe = felt.sustained and share < settings.rejuvenation_below and ahead < settings.danger
    # The worst second again, BURST_AHEAD over (EMERGENCY_REJUVENATION)
    burst_ahead = (felt.share - felt.burst * (BURST_AHEAD + (LIFE_READ_LAG if READ_LAG else 0.0))) * 100
    severe = severe or (
        EMERGENCY_REJUVENATION and felt.sustained and share < EMERGENCY_BELOW and burst_ahead < settings.danger
    )
    if severe and supply.rejuvenation and ago[PotionType.REJUVENATION] >= settings.rejuvenation_gap:
        return PotionType.REJUVENATION
    if not supply.healing or share >= settings.healing_below:
        return None
    hurried = share < settings.hurry_below or severe
    if ago[PotionType.HEALING] < (settings.hurry_gap if hurried else settings.healing_gap):
        return None
    if not hurried:
        if not felt.sustained and share >= settings.idle_below:
            return None
        if supply.healing <= settings.keep_healing and not supply.healing_near:
            return None
    return PotionType.HEALING

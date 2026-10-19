"""A companion kept alive by where the character jumps (the player, 2026-10-14: "Blade Warp teleports minions with me,
so it can be used to reposition the merc to avoid his death, for example in the Diablo fight";
rca/2026-10-14/navigation-classes.md §4).

A jump that brings the companions along (macros/build.py `JumpSource.brings`) lands them round the character. Where
the mercenary stands in a place it dies at within the safety's horizon (Diablo's fire wall, his lightning, a pack on
it), such a jump to a place it lives at saves what its death costs: the way to town, the hire and its gear again,
priced in seconds (`Kept.worth`, REHIRE_SECONDS), the arbiter's one unit (macros/pursuit.py `arbitrate`: T + kappa H).
`escorts` names those places and what each saves; the caller makes them legs by the movement set (a jump that brings,
over a clear line) and offers them as acts among the others (macros/hunting/judging.py `escorted`), which price the
character's own harm as every act's is. Pure: no input, no game read.

How a companion dies is the character's harm model at its place (combat/harm.py `harm`): the hostiles go for the
nearest body, and one standing there is that body. Its resistances are not read: the character's battle set stands
in for them, an approximation the takes have not been fitted to (the healer's mercenary life is read, its blows not).
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from inventory_tracking.combat.harm import Look, SafetySettings, harm
from inventory_tracking.game.records import Monster
from inventory_tracking.levels.geometry import Point
from inventory_tracking.native.layout import HIRELING_CLASS_ID, LIFE_FRACTION_MAX


# Seconds a dead mercenary costs the run: a town portal, the hire at the act's NPC and its gear put back, the way back
# (a named stand-in, not measured: the healer's ledger has no death of one yet)
REHIRE_SECONDS = 60.0
# The share of the rollouts in which a companion dies within the horizon from which it is in lethal danger where it
# stands (the safety's own veto is 5% for the character, `SafetySettings.veto_share`: a companion is cheaper)
LETHAL = 0.25
ESCORTS_MOST = 3  # places offered per look, the most saved first
RAYS = 12  # directions round the character a place is looked for in
RINGS = (0.6, 1.0)  # fractions of the jump's reach the places are looked for at
# A monster's life stat is a share of its most life out of this, the mercenary's too (native/mercenary.py, the healer's
# reading); its most life is in points. Read as points, a whole mercenary had 128 of its 2367 and was escorted out of
# Lower Kurast's trash 35 times in 65 stays (2026-10-17)
LIFE_SHARE = LIFE_FRACTION_MAX >> 8


@dataclass(frozen=True)
class Kept:
    """A companion kept alive: its unit, where it stands, its life and most life, and what its death costs (s)."""

    unit: int
    at: Point
    life: float
    most: float
    worth: float


@dataclass(frozen=True)
class Escort:
    """A place to jump to that takes `kept` out of danger: the share of the rollouts it dies in where it stands
    (`here`) and round `spot` (`there`), and the seconds that saves (`credit`)."""

    spot: Point
    kept: Kept
    here: float
    there: float
    credit: float

    def line(self) -> str:
        """The reason the act is said and logged with (`Macro: pursuit: escorting ...`)."""
        kept = self.kept
        return (
            f'escorting the mercenary ({kept.life:.0f}/{kept.most:.0f}) at ({kept.at[0]:.0f}, {kept.at[1]:.0f}): it '
            f'dies in {self.here:.0%} of the rollouts there, {self.there:.0%} round ({self.spot[0]:.0f}, '
            f'{self.spot[1]:.0f}); {self.credit:.0f} s saved'
        )


ESCORTING = 'escorting the mercenary'  # the act's reason begins so (`Escort.line`)


def kept_alive(monsters: Iterable[Monster], owner: int) -> tuple[Kept, ...]:
    """The character's mercenary, alive and with its life read (in points: its share of its most life); none
    otherwise. The summons are left out: one dead is summoned again in a cast, not worth a jump's price (a summon's
    upkeep is the build's buffs')."""
    return tuple(
        Kept(
            m.unit_id, (m.x, m.y), m.max_life * min(m.life, LIFE_SHARE) / LIFE_SHARE, float(m.max_life), REHIRE_SECONDS
        )
        for m in monsters
        if m.txt_id == HIRELING_CLASS_ID and m.owner == owner and m.max_life > 0 and m.life > 0
    )


def dies(look: Look, at: Point, life: float, settings: SafetySettings) -> float:
    """The share of the safety's rollouts in which a companion with `life` standing at `at` loses all of it within the
    horizon (the module text: the character's harm model at its place)."""
    priced = harm(look, at, settings.horizon, 'battle', settings)
    if not priced.losses:
        return 1.0 if priced.mean >= life else 0.0
    return sum(loss >= life for loss in priced.losses) / len(priced.losses)


def around(here: Point, reach: float, least: float) -> list[Point]:
    """The places a jump from `here` is asked toward: RAYS directions at RINGS of its reach, none under `least`."""
    found = []
    for ring in RINGS:
        away = max(least, reach * ring)
        for index in range(RAYS):
            angle = index * math.tau / RAYS
            found.append((here[0] + away * math.cos(angle), here[1] + away * math.sin(angle)))
    return found


def in_danger(look: Look, found: Sequence[Kept], settings: SafetySettings) -> list[tuple[Kept, float]]:
    """The kept_alive in lethal danger where they stand (LETHAL), with the share of the rollouts they die in there."""
    return [(kept, share) for kept in found if (share := dies(look, kept.at, kept.life, settings)) >= LETHAL]


def escorts(
    look: Look, endangered: Sequence[tuple[Kept, float]], spots: Iterable[Point], settings: SafetySettings
) -> list[Escort]:
    """Of `spots` (the landings a jump that brings can make), those round which an endangered kept dies in fewer of the
    rollouts than where it stands, with the seconds that saves (its worth by the share spared); the most saved first,
    ESCORTS_MOST at most. The kept lands round the character: its place there is the landing's."""
    found = []
    places = list(spots)
    for kept, here in endangered:
        for spot in places:
            there = dies(look, spot, kept.life, settings)
            if there < here:
                found.append(Escort(spot, kept, here, there, (here - there) * kept.worth))
    found.sort(key=lambda escort: -escort.credit)
    return found[:ESCORTS_MOST]

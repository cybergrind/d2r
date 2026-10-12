"""Echoing Strike as the framework asks an attack (macros/build.py `Attack`): the skill the fight
holds, how far the blades hurt, what the strike reads off the character's own units, where to cast,
and what a cast takes off whom when a place to stand is priced.

`EchoingStrike` is the line sweep (combat/policy.py `LinePolicy`, with `virtual_cast` and the blade
constants still there: framework-plan.md Task 3.8 moves them here) with the rest of the contract on it:

- `aim`: the sweep's best line, and with `through` the best line laid through one of those units;
  both yield to a moving player and want MIN_SCORE;
- `sees`: the monsters the Defiler's Health Link holds, and the share of the damage dealt again;
- `dealt`: the line model a place is priced by, which is not `virtual_cast`: every monster ahead of
  the character within the blades' contact radius of the line to the focal point takes
  BLADES_A_CAST blades.
"""

import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, fields, replace

from inventory_tracking.combat.mechanics.damage import DEFILER, link_table
from inventory_tracking.combat.mechanics.hits import CONTACT_RADIUS
from inventory_tracking.combat.policy import MIN_SCORE, Choice, Foe, LinePolicy, Observation, Point, linked_set
from inventory_tracking.macros.skills import ECHOING_STRIKE
from inventory_tracking.macros.world import Monster


# What one cast takes off a monster on its line, in blades: the first whole and the rest by the
# duplicate rule, out and back (combat/policy.py `virtual_cast`: 2,800 points of a 1,000-point blade).
BLADES_A_CAST = 2.8


@dataclass
class EchoingStrike(LinePolicy):
    """The strike of the Echoing Strike Warlock. `reach` is the blades' range (`LinePolicy.reach`)."""

    skill: int = ECHOING_STRIKE  # the skill whose input the fight holds

    @classmethod
    def of(cls, policy: LinePolicy) -> EchoingStrike:
        """The attack of a line sweep made on its own (a test's or a harness's, with its damage table
        and its reach): the same sweep, as an attack."""
        return cls(**{part.name: getattr(policy, part.name) for part in fields(LinePolicy)})

    def sees(self, seen: Observation, companions: Sequence[Monster]) -> Observation:
        """A copy of the observation with the monsters the Defiler's Health Link holds, and the share
        of the damage dealt again to each other linked one."""
        link_range, links, share = link_table()
        defilers = [(c.x, c.y) for c in companions if c.txt_id == DEFILER]
        linked = linked_set(defilers, {unit: foe.at for unit, foe in seen.foes.items()}, link_range, links)
        return replace(seen, linked=linked, share=share)

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """The best line worth MIN_SCORE, or None; nothing while the player is moving (`yields`).
        With `through`, the best of the lines laid through those units, whatever another is worth."""
        if not through:
            return self(seen)
        if self.yields and seen.moving:
            return None
        best = self.choose(seen, through=through)
        return best if best is not None and best.worth >= MIN_SCORE else None

    def dealt(self, origin: Point, focal: Point, foes: Mapping[int, Foe]) -> Mapping[int, float]:
        """The points a cast from `origin` at `focal` takes off each of `foes` on its line:
        BLADES_A_CAST blades off every one ahead of the character and within the contact radius of
        the straight line through the focal point, however far along it (the caller gives the ones
        in reach). Nothing from a focal point under the character."""
        tx, ty = focal[0] - origin[0], focal[1] - origin[1]
        away = math.hypot(tx, ty)
        if not away:
            return {}
        ux, uy = tx / away, ty / away
        hit = {}
        for unit, foe in foes.items():
            dx, dy = foe.at[0] - origin[0], foe.at[1] - origin[1]
            if dx * ux + dy * uy > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS:
                hit[unit] = self.damage_of(foe.txt) * BLADES_A_CAST
        return hit


ECHOING_STRIKE_ATTACK = EchoingStrike()  # the build's: the sweep as the game runs it, with the build's damage table

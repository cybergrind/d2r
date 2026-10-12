"""A build that exists only for tests: a walker with one plain bolt, nothing like the real one."""

import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from inventory_tracking.combat.policy import AIM_BEYOND, Choice, Foe, Observation, Point
from inventory_tracking.combat.stance import Jump
from inventory_tracking.macros.build import Build, Intent, JumpSource, Leg, MoveFacts, NoWay
from inventory_tracking.macros.skills import ATTACK
from inventory_tracking.macros.travel import Step
from inventory_tracking.macros.world import Monster, World


STRIDE = 16.0  # units a step goes at most
CLOSE = 2.0  # units: nearer than this to the goal is there
PACE = 20.0  # units a second
BOLT = 100.0  # points a bolt takes off a foe
SPLASH = 2.0  # units from the focal point a bolt hurts


@dataclass(frozen=True)
class DummyWalk:
    """Walks straight toward the goal, a stride at a time."""

    name: str = 'dummy walk'
    sources: tuple[JumpSource, ...] = ()  # a walker: no jump

    def applies(self, facts: MoveFacts) -> bool:
        """Always."""
        return True

    def aim(self, facts: MoveFacts, goal: Point, intent: Intent) -> tuple[float, Point | None]:
        """(the distance left once `intent.short` is kept, the spot a step would end at; None: there already)."""
        away = math.dist(facts.here, goal)
        left = away - intent.short
        if left < CLOSE:
            return left, None
        walk = min(STRIDE, left)
        return left, (
            facts.here[0] + (goal[0] - facts.here[0]) / away * walk,
            facts.here[1] + (goal[1] - facts.here[1]) / away * walk,
        )

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """A walk toward the goal, or the reason there is none."""
        _, spot = self.aim(facts, goal, intent)
        if spot is None:
            return NoWay('already there', arrived=True)
        if intent.shuns(spot):
            return NoWay('the spot is shunned')
        return Step(spot)

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to walk there; inf where `leg` has no way."""
        left, spot = self.aim(facts, goal, intent)
        if spot is None or intent.shuns(spot):
            return math.inf
        return left / PACE

    def jumps(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """None: a walker."""
        return ()

    def wait(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Never."""
        return 0.0


@dataclass(frozen=True)
class DummyBolt:
    """One plain bolt at the nearest foe."""

    skill: int = ATTACK
    reach: float = 20.0

    def sees(self, seen: Observation, companions: Sequence[Monster]) -> Observation:
        """Nothing to add."""
        return seen

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """The nearest foe in reach (of `through` if named), focal point just past it."""
        near = [
            (math.dist(foe.at, seen.origin), unit)
            for unit, foe in seen.foes.items()
            if (not through or unit in through) and 0 < math.dist(foe.at, seen.origin) <= self.reach
        ]
        if not near:
            return None
        away, unit = min(near)
        at = seen.foes[unit].at
        focal = (
            at[0] + (at[0] - seen.origin[0]) / away * AIM_BEYOND,
            at[1] + (at[1] - seen.origin[1]) / away * AIM_BEYOND,
        )
        return Choice(focal, unit, BOLT)

    def dealt(self, origin: Point, focal: Point, foes: Mapping[int, Foe]) -> Mapping[int, float]:
        """The bolt hurts the one foe nearest the focal point, within SPLASH of it."""
        near = [(math.dist(foe.at, focal), unit) for unit, foe in foes.items() if math.dist(foe.at, focal) <= SPLASH]
        return {min(near)[1]: BOLT} if near else {}


def is_dummy(world: World) -> bool:
    """Whose it is: the character named Dummy."""
    return world.player is not None and world.player.name == 'Dummy'


DUMMY = Build(name='dummy', applies=is_dummy, attack=DummyBolt(), movement=(DummyWalk(),))

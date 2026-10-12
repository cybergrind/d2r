"""The movement sets any character has: Teleport from a worn staff, Teleport as a skill of its own, a walk.

A movement set (macros/build.py `MovementSet`) is a combination of ways to move. Here it is composed
of jump sources (`JumpSource`: a skill, what a jump by it takes, its casting delay and its own test of
the facts) and the walk every character has. The jumps a set can make now are its sources that are
ready, in the sources' order; the move itself is the pure choice of macros/travel.py (`stride_of`,
`around_of`) asked with those jumps. `leg` is that one decision and `eta` is priced from it, so the
two cannot disagree.

A build takes the shared sets as they are (`SHARED`), or with jumps of its own put before theirs
(`Ways.led_by`): the order of a set's sources is the order its jumps are preferred in. This module
names no skill but Teleport, which a staff or an item gives to any class.
"""

import math
from dataclasses import dataclass, replace
from typing import Self

from inventory_tracking.combat.stance import RUN_SPEED, WALK_LATENCY, Jump
from inventory_tracking.macros.build import Intent, JumpSource, Leg, MoveFacts, NoWay, Point
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.teleport import MOVED
from inventory_tracking.macros.travel import JUMP_LEAST, JUMP_REACH, around_of, known, stride_of


# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
TELEPORT_SECONDS = 0.31  # Teleport with the staff in hand
TELEPORT_JUMP = Jump(TELEPORT, TELEPORT_SECONDS, math.inf, JUMP_REACH, JUMP_LEAST, line=False)


def staff_in_hand(facts: MoveFacts, intent: Intent) -> bool:
    """The worn staff is in the weapon set in hand (no swap is made for a set's jump) and holds
    `intent.reserve` charges or more."""
    staff = facts.staff
    return staff is not None and staff.in_hand and staff.charges >= intent.reserve


def no_staff(facts: MoveFacts, intent: Intent) -> bool:
    """No staff is worn: Teleport, on a key, is the character's own and costs no charge."""
    return facts.staff is None


STAFF_TELEPORT = JumpSource(TELEPORT_JUMP, usable=staff_in_hand)
OWN_TELEPORT = JumpSource(TELEPORT_JUMP, usable=no_staff)


@dataclass(frozen=True)
class Ways:
    """A movement set made of jump sources and the walk: the base of the shared sets. A set of this
    kind differs from another by when it applies and by its sources; how a move is chosen from them is
    the same for all."""

    name: str
    sources: tuple[JumpSource, ...] = ()

    def applies(self, facts: MoveFacts) -> bool:
        """Whether this is the character's situation now: each set's own."""
        raise NotImplementedError

    def led_by(self, *sources: JumpSource) -> Self:
        """This set with `sources` before its own: jumps a build adds that are preferred to the set's."""
        return replace(self, sources=(*sources, *self.sources))

    def jumps(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The jumps that can be made now within `intent`, in the sources' order: no weapon swap is
        made for any of them."""
        return tuple(source.jump for source in self.sources if source.ready(facts, intent))

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """A stride straight toward `goal` by the first jump that can be made, else walked; with
        `intent.detour`, a move along the walked way round a wall instead. The one decision of the
        set: `eta` prices what it answers."""
        jumps = self.jumps(facts, intent)
        if intent.detour:
            return around_of(facts, goal, jumps=jumps)
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to the end of the move, `intent.short` of the goal: what the next leg takes, and
        the rest of the straight line at that leg's pace. inf where `leg` has no way."""
        found = self.leg(facts, goal, intent)
        if isinstance(found, NoWay):
            return math.inf
        made = math.dist(facts.here, found.spot)
        by = next((source.jump for source in self.sources if source.jump.skill == found.skill), None)
        took = WALK_LATENCY + made / RUN_SPEED if by is None else by.takes(made)
        left = math.dist(facts.here, goal) - intent.short
        return took * max(left / made, 1.0) if made > 0 else took

    def wait(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds of a casting delay still to run on a jump of the set that is on a key, when the
        jump is worth the wait: the goal further than a move counts for, and for a jump that needs a
        clear line, the line toward the goal clear as far as the jump carries. With
        `intent.waits_blind` the delay alone decides. 0.0 with no such jump, and with `intent.may_wait` off."""
        if not intent.may_wait:
            return 0.0
        here = facts.here
        away = math.dist(here, goal)
        for source in self.sources:
            left = source.cooling(facts)
            if left <= 0 or source.jump.skill not in facts.slots:
                continue
            if intent.waits_blind:
                return left
            if away > MOVED:
                reach = min(1.0, source.jump.reach / away)
                end = (here[0] + (goal[0] - here[0]) * reach, here[1] + (goal[1] - here[1]) * reach)
                if not source.jump.line or clear_shot(known(facts.ground), here, end, facts.doors):
                    return left
        return 0.0


@dataclass(frozen=True)
class StaffTeleport(Ways):
    """A staff with Teleport charges is worn: Teleport by its charges while it is in hand."""

    name: str = 'staff teleport'
    sources: tuple[JumpSource, ...] = (STAFF_TELEPORT,)

    def applies(self, facts: MoveFacts) -> bool:
        """A staff is worn, in hand or not, with charges or without."""
        return facts.staff is not None


@dataclass(frozen=True)
class OwnTeleport(Ways):
    """Teleport is a skill of the character's own (an item that gives it, as Enigma does): no
    charges, no swap."""

    name: str = 'own teleport'
    sources: tuple[JumpSource, ...] = (OWN_TELEPORT,)

    def applies(self, facts: MoveFacts) -> bool:
        """Teleport is on a key and no staff is worn (or none could be read)."""
        return facts.staff is None and TELEPORT in facts.slots


@dataclass(frozen=True)
class Walk(Ways):
    """No Teleport at all: the walk, and whatever jumps a build puts before it."""

    name: str = 'walk'

    def applies(self, facts: MoveFacts) -> bool:
        """Always: the set of last resort."""
        return True


SHARED: tuple[Ways, ...] = (StaffTeleport(), OwnTeleport(), Walk())  # in the order they are asked whether they apply

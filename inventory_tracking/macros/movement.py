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
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.build import PAD_SLACK, Intent, JumpSource, Leg, MoveFacts, NoWay, Point, Step
from inventory_tracking.macros.pad import TELEPORT_REACH
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.teleport import FAR_DISTRUST, MOVED, Way, landing, scaled, way_for
from inventory_tracking.macros.travel import (
    JUMP_LEAST,
    JUMP_REACH,
    NO_NEARER,
    THERE,
    around_of,
    known,
    stride_of,
    way_left,
    way_leg,
)
from inventory_tracking.macros.view import Viewport
from inventory_tracking.native.layout import TILE_UNITS


# What a jump takes from its key to standing there, for the choice of a place (combat/stance.py `Jump`).
TELEPORT_SECONDS = 0.31  # Teleport with the staff in hand
TELEPORT_JUMP = Jump(TELEPORT, TELEPORT_SECONDS, math.inf, JUMP_REACH, JUMP_LEAST, line=False)
# In controller mode a Teleport lands at its controller distance in the stick's direction (macros/pad.py).
TELEPORT_RING = (TELEPORT_REACH - PAD_SLACK, TELEPORT_REACH + PAD_SLACK)


def staff_in_hand(facts: MoveFacts, intent: Intent) -> bool:
    """The worn staff is in the weapon set in hand (no swap is made for a set's jump) and holds
    `intent.reserve` charges or more."""
    staff = facts.staff
    return staff is not None and staff.in_hand and staff.charges >= intent.reserve


def no_staff(facts: MoveFacts, intent: Intent) -> bool:
    """No staff is worn: Teleport, on a key, is the character's own and costs no charge."""
    return facts.staff is None


STAFF_TELEPORT = JumpSource(TELEPORT_JUMP, usable=staff_in_hand, pad_reach=TELEPORT_REACH)
OWN_TELEPORT = JumpSource(TELEPORT_JUMP, usable=no_staff, pad_reach=TELEPORT_REACH)

NO_LANDING = 'no footing in view brings the character nearer by hops'
NO_HOP_WAY = 'no way of hops leads over the rooms to the goal'
FAR_WAY = 'far way'  # the name a hop's far potential is distrusted under (`NoWay.distrust`), with the goal's tile


@dataclass(frozen=True)
class Stand:
    """Where a hop starts from, for the landing's choice (teleport.py `landing` reads a place and no more)."""

    x: float
    y: float


def hops(facts: MoveFacts, goal: Point, intent: Intent) -> bool:
    """Whether a Teleport hop toward a far goal can be made within `intent`: Teleport on a key and not
    one that moved nothing less than `intent.distrust` seconds ago; of a worn staff a charge left above
    the reserve (the last one is not a reserve: one charge at least), and the staff in hand unless the
    weapon set may be changed for the move; and the level's rooms known, which the hops are planned over."""
    if TELEPORT not in facts.slots or facts.since_failed(TELEPORT) <= intent.distrust or not facts.rooms:
        return False
    staff = facts.staff
    return staff is None or (staff.charges >= max(intent.reserve, 1) and (staff.in_hand or intent.may_swap))


def hop_way(facts: MoveFacts, goal: Point) -> tuple[Target, Way, object]:
    """The potential of hops to `goal` over the level's rooms (teleport.py `Way`: a Teleport crosses
    walls), and the name it is distrusted under: the far one, which a hop is planned by, unless it gave
    no landing less than FAR_DISTRUST seconds ago (`MoveFacts.distrusted`); then the near one, every hop
    of which can be made."""
    tile = (goal[0] / TILE_UNITS, goal[1] / TILE_UNITS)
    grids = facts.ground.grids if facts.ground is not None else ()
    target = Target(facts.area, facts.rooms, tile, 'the goal', 'hunt', False, grids)
    key = (FAR_WAY, facts.area, math.floor(tile[0]), math.floor(tile[1]))
    far = facts.now - facts.distrusted.get(key, -math.inf) >= FAR_DISTRUST
    return target, way_for(target, Viewport(facts.aspect), far), key if far else None


def hops_left(facts: MoveFacts, goal: Point) -> float:
    """Units of the way left to `goal` by hops; inf: none leads there."""
    _, way, _ = hop_way(facts, goal)
    return way.from_here((facts.here[0] / TILE_UNITS, facts.here[1] / TILE_UNITS)) * TILE_UNITS


def hop_leg(facts: MoveFacts, goal: Point, intent: Intent, spare: tuple[Jump, ...] = ()) -> Leg:
    """The next hop toward a far goal: the footing in view that leaves the shortest way of hops
    (teleport.py `landing`), by Teleport; or, with fewer charges than `intent.sparing`, by the first
    of `spare` (the jumps that cost none) when it reaches toward that landing and still shortens the way
    of hops. A far potential with no landing from here is named to be distrusted, and the near one asked next."""
    here = facts.here
    if math.dist(here, goal) - intent.short < MOVED:
        return NoWay(THERE, arrived=True)
    target, way, far = hop_way(facts, goal)
    start = (here[0] / TILE_UNITS, here[1] / TILE_UNITS)
    now = way.from_here(start)
    ring = TELEPORT_RING if facts.pad else None  # controller mode: a hop lands at its one distance
    found = landing(target, Stand(*here), way, facts.aspect, ring) if now < math.inf else None  # type: ignore[arg-type]
    if found is None:
        if far is not None:
            return NoWay(f'{NO_LANDING} (the far way)', distrust=far)
        return NoWay(NO_HOP_WAY if now == math.inf else NO_LANDING)
    spot = scaled(found[0])
    if math.dist(spot, here) < MOVED:
        return NoWay(THERE, arrived=True)  # the best landing is where the character stands
    staff = facts.staff
    if spare and staff is not None and staff.charges < intent.sparing:
        saved = stride_of(facts, spot, jumps=spare)
        if isinstance(saved, Step) and saved.skill is not None:
            after = way.to_go((saved.spot[0] / TILE_UNITS, saved.spot[1] / TILE_UNITS))
            if after < now:
                return saved
    return Step(spot, TELEPORT)


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
        if facts.pad:  # controller mode: each jump of its one length, none without one (`JumpSource.pad_jump`)
            made = (source.pad_jump() for source in self.sources if source.ready(facts, intent))
            return tuple(jump for jump in made if jump is not None)
        return tuple(source.jump for source in self.sources if source.ready(facts, intent))

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """A stride straight toward `goal` by the first jump that can be made, else walked; with
        `intent.detour`, a move along the walked way round a wall instead. The one decision of the
        set: `eta` prices what it answers."""
        jumps = self.jumps(facts, intent)
        if intent.routed:
            return self.routed(facts, goal, intent)
        if intent.detour:
            return around_of(facts, goal, jumps=jumps)
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)

    def spare(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The jumps of the set that cost no charge and can be made now (every one but Teleport)."""
        return tuple(jump for jump in self.jumps(facts, intent) if jump.skill != TELEPORT)

    def routed(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The next move toward a goal at any distance, by the set's own way there (`Intent.routed`).
        A set that can make a Teleport hop now (`hops`) goes by the way of hops over the level's rooms,
        which crosses walls (`hop_leg`); one that cannot (no Teleport, no charge to spend, the staff out
        of hand and no swap allowed) goes by the walked way (travel.py `way_leg`), on which a jump is
        made where its line is clear and a walk elsewhere. One measure for each, `left`, and a move
        that does not shorten it is no move."""
        spare = self.spare(facts, intent)
        if hops(facts, goal, intent):
            found = hop_leg(facts, goal, intent, spare)
        else:
            found = way_leg(facts, goal, intent, jumps=spare)
        if isinstance(found, Step) and not self.left(replace(facts, here=found.spot), goal, intent) < self.left(
            facts, goal, intent
        ):
            return NoWay(NO_NEARER)
        return found

    def left(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units of the way left to a far goal by the means the set would go by now: of hops where it
        can hop, on foot where it cannot; inf: no way is known."""
        if hops(facts, goal, intent):
            return hops_left(facts, goal)
        return way_left(facts, goal)

    def pace(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units a second the set makes on its way to a far goal: a hop's reach in a hop's time where it
        hops; on foot the first jump it has that costs no charge, a reach in its casting delay or its
        flight, whichever is longer; else the run."""
        if hops(facts, goal, intent):
            return TELEPORT_JUMP.reach / TELEPORT_JUMP.takes(TELEPORT_JUMP.reach)
        free = next((source for source in self.sources if source.jump.skill != TELEPORT), None)
        if free is None or free.jump.skill not in facts.slots:
            return RUN_SPEED
        return free.jump.reach / max(free.delay, free.jump.takes(free.jump.reach))

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to the end of the move, `intent.short` of the goal: what the next leg takes, and
        the rest of the straight line at that leg's pace. inf where `leg` has no way. For a far goal
        (`intent.routed`): the way left by the set's own means at its pace, 0.0 on arrival."""
        found = self.leg(facts, goal, intent)
        if intent.routed:
            if isinstance(found, NoWay):
                return 0.0 if found.arrived else math.inf
            return max(self.left(facts, goal, intent) - intent.short, 0.0) / self.pace(facts, goal, intent)
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
        if intent.routed:
            return self.routed_wait(facts, goal, intent)
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

    def routed_wait(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds of a casting delay still to run on a jump the set would make toward a far goal were
        the delay over: the next move asked with that jump taken as ready is a jump by it. 0.0 otherwise."""
        for source in self.sources:
            left = source.cooling(facts)
            if left <= 0 or source.jump.skill not in facts.slots:
                continue
            rested = replace(facts, last_used={k: v for k, v in facts.last_used.items() if k != source.jump.skill})
            found = self.routed(rested, goal, intent)
            if isinstance(found, Step) and found.skill == source.jump.skill:
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

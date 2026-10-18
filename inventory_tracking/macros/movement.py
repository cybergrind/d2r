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

**The navigation classes** (the player, 2026-10-14: "we should have different navigational classes for
different cases"; rca/2026-10-14/navigation-classes.md). A far goal's way (`Intent.routed`) is planned by the
class of means the character has now (`Ways.means`), and every leg, its measure (`left`) and its pace come
from that one class, so a way is never planned by one means and walked by another:

- HOPS, Teleport on a key with a charge to spend: legs may cross walls (the way of hops over the rooms);
- WARPS, no Teleport to spend but a jump that costs nothing and needs a clear line (the Warlock's Blade
  Warp): the walked way, a jump leg only over a clear line and only where it gets on faster than walking that
  stretch (travel.py `beats_walk`: its reach, its casting delay, its cast against the walk's pace);
- WALKS, neither: the walked way on foot.
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
    walk_seconds,
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

# The navigation classes (the module text): what a far goal's way is planned by.
HOPS = 'teleport'  # legs may cross walls
WARPS = 'blade warp and walk'  # the walked way; a free jump over a clear line where it beats the walk
WALKS = 'walk'  # the walked way on foot

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
    weapon set may be changed for the move; and the goal no nearer than `intent.hop_from`. With no room map yet,
    own Teleport can still make a local stride using the collision already known; charged staff routing waits for
    the rooms as before."""
    if TELEPORT not in facts.slots or facts.since_failed(TELEPORT) <= intent.distrust:
        return False
    if not facts.rooms and facts.staff is not None:
        return False
    if intent.hop_from and math.dist(facts.here, goal) < intent.hop_from:
        return False  # near: by the free jump (`Intent.hop_from`)
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
    if not facts.rooms:
        return math.dist(facts.here, goal)  # local strides until the level's room graph arrives
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
    if not facts.rooms:
        # A level change can expose the goal and collision before its room graph. Keep own Teleport as the
        # navigation means, using the same bounded, visible, footed stride as combat; do not replace it with
        # the slower free-jump route merely because long-distance planning is not ready yet.
        jump = replace(TELEPORT_JUMP, least=TELEPORT_RING[0], reach=TELEPORT_RING[1]) if facts.pad else TELEPORT_JUMP
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=(jump,))
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
    off = math.dist(spot, goal)
    if off < intent.short:
        # A landing within `short` of the goal is taken back to `short` of it, on the character's side (LOOPED: a
        # Teleport aimed onto a chest's own spot is not cast)
        away = math.dist(here, goal)
        spot = goal if away <= intent.short else (
            goal[0] + (here[0] - goal[0]) * intent.short / away, goal[1] + (here[1] - goal[1]) * intent.short / away
        )  # fmt: skip
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

    def then(self, *sources: JumpSource) -> Self:
        """This set with `sources` after its own: jumps a build adds that its own are preferred to."""
        return replace(self, sources=(*self.sources, *sources))

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

    def free(self, facts: MoveFacts, intent: Intent) -> JumpSource | None:
        """The set's first jump that costs no charge (every one but Teleport) and that the character has: on a key,
        not one that moved nobody less than `intent.distrust` ago, and in controller mode one of a fixed reach. Its
        casting delay may still run: the class is what the character has, a leg is what it can make now."""
        for source in self.sources:
            skill = source.jump.skill
            if skill == TELEPORT or skill not in facts.slots or facts.since_failed(skill) <= intent.distrust:
                continue
            if facts.pad and source.pad_reach is None:
                continue
            return source
        return None

    def means(self, facts: MoveFacts, goal: Point, intent: Intent) -> str:
        """The navigation class a far goal's way is planned by now (the module text): HOPS where a Teleport hop
        can be made (`hops`), else WARPS with a jump that costs nothing (`free`), else WALKS."""
        if hops(facts, goal, intent):
            return HOPS
        return WARPS if self.free(facts, intent) is not None else WALKS

    def routed(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The next move toward a goal at any distance, by the set's own way there (`Intent.routed`), planned by
        its navigation class now (`means`). HOPS goes by the way of hops over the level's rooms, which crosses
        walls (`hop_leg`); WARPS and WALKS by the walked way (travel.py `way_leg`), on which a jump that costs
        nothing is made only over a clear line and where it beats walking (WARPS), a walk elsewhere. One measure
        for each, `left`, and a move that does not shorten it is no move."""
        kind = self.means(facts, goal, intent)
        spare = self.spare(facts, intent)
        if kind == HOPS:
            found = hop_leg(facts, goal, intent, spare)
        else:
            found = way_leg(facts, goal, intent, jumps=spare if kind == WARPS else (), delays=self.delays())
        if isinstance(found, Step) and not self.left(replace(facts, here=found.spot), goal, intent) < self.left(
            facts, goal, intent
        ):
            return NoWay(NO_NEARER)
        return found

    def delays(self) -> dict[int, float]:
        """skill -> its casting delay: what a jump leg holds the next one back by (travel.py `beats_walk`)."""
        return {source.jump.skill: source.delay for source in self.sources if source.delay}

    def left(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units of the way left to a far goal by the class the set plans by now: of hops for HOPS, on foot for
        WARPS and WALKS (a jump that costs nothing goes along the walked way); inf: no way is known."""
        if self.means(facts, goal, intent) == HOPS:
            return hops_left(facts, goal)
        return way_left(facts, goal)

    def pace(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units a second the set makes on its way to a far goal by its class: HOPS a hop's reach in a hop's
        time; WARPS the free jump's reach in its casting delay or its flight, whichever is longer; WALKS the run."""
        kind = self.means(facts, goal, intent)
        if kind == HOPS:
            return TELEPORT_JUMP.reach / TELEPORT_JUMP.takes(TELEPORT_JUMP.reach)
        free = self.free(facts, intent) if kind == WARPS else None
        if free is None:
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
            if source.ready(facts, intent):
                return 0.0  # a jump preferred to the ones after it can be made now: none of theirs is waited for
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
        the delay over: the next move asked with that jump taken as ready is a jump by it, and that jump made
        after the wait gets on faster than the move there is now (a walk: `waited`). 0.0 otherwise."""
        for source in self.sources:
            if source.ready(facts, intent):
                return 0.0
            left = source.cooling(facts)
            if left <= 0 or source.jump.skill not in facts.slots:
                continue
            rested = replace(facts, last_used={k: v for k, v in facts.last_used.items() if k != source.jump.skill})
            found = self.routed(rested, goal, intent)
            if (
                isinstance(found, Step)
                and found.skill == source.jump.skill
                and self.waited(facts, goal, intent, source, found, left)
            ):
                return left
        return 0.0

    def waited(
        self, facts: MoveFacts, goal: Point, intent: Intent, source: JumpSource, jump: Step, left: float
    ) -> bool:
        """Whether `jump`, made once its casting delay's `left` seconds are over, gets on along the way faster than
        the move the set makes now instead (the navigation class WARPS: the delay is the jump's price): the units
        of the way each saves over its seconds. With no move now (or one that is no walk) the jump is waited for."""
        now = self.routed(facts, goal, intent)
        if not isinstance(now, Step) or now.skill is not None:
            return True
        start = self.left(facts, goal, intent)
        gained = start - self.left(replace(facts, here=jump.spot), goal, intent)
        walk_gained = start - self.left(replace(facts, here=now.spot), goal, intent)
        jumping = left + max(source.jump.takes(math.dist(facts.here, jump.spot)), source.delay)
        return walk_gained <= 0.0 or gained / jumping >= walk_gained / walk_seconds(math.dist(facts.here, now.spot))


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

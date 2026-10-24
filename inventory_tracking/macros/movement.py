"""The shared movement sets (macros/build.py `MovementSet`): staff Teleport, own Teleport, the walk.

A set is jump sources in preference order plus the walk; the move is travel.py's pure choice with the
ready jumps. `leg` is the one decision and `eta` is priced from it. Builds put their own jumps first
(`Ways.led_by`). No skill but Teleport is named here.

A far goal's way is planned, walked and measured by one navigation class (`Ways.means`): HOPS (Teleport
to spend: legs cross walls), WARPS (a free clear-line jump only where it beats the walk), WALKS. The
player, 2026-10-14: "we should have different navigational classes for different cases"
(rca/2026-10-14/navigation-classes.md).
"""

import math
from dataclasses import dataclass, replace
from typing import Self

from inventory_tracking.combat.stance import RUN_SPEED, WALK_LATENCY, Jump
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.model import Target
from inventory_tracking.macros import hopway, teleport
from inventory_tracking.macros.build import PAD_SLACK, Intent, JumpSource, Leg, MoveFacts, NoWay, Point, Step
from inventory_tracking.macros.pad import TELEPORT_REACH
from inventory_tracking.macros.sight import clear_shot
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.teleport import FAR_DISTRUST, MOVED, Way, scaled
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
from inventory_tracking.native.layout import TILE_UNITS


# Key to standing there, for the choice of a place (combat/stance.py `Jump`).
TELEPORT_SECONDS = 0.31  # Teleport with the staff in hand
TELEPORT_JUMP = Jump(TELEPORT, TELEPORT_SECONDS, math.inf, JUMP_REACH, JUMP_LEAST, line=False)
# Controller mode: a Teleport lands at a fixed distance along the stick (macros/pad.py).
TELEPORT_RING = (TELEPORT_REACH - PAD_SLACK, TELEPORT_REACH + PAD_SLACK)


def staff_in_hand(facts: MoveFacts, intent: Intent) -> bool:
    """The worn staff is in hand (no swap for a set's jump) with `intent.reserve` charges or more."""
    staff = facts.staff
    return staff is not None and staff.in_hand and staff.charges >= intent.reserve


def no_staff(facts: MoveFacts, intent: Intent) -> bool:
    """No staff worn: Teleport is the character's own, no charge."""
    return facts.staff is None


STAFF_TELEPORT = JumpSource(TELEPORT_JUMP, usable=staff_in_hand, pad_reach=TELEPORT_REACH)
OWN_TELEPORT = JumpSource(TELEPORT_JUMP, usable=no_staff, pad_reach=TELEPORT_REACH)

# The navigation classes (module docstring).
HOPS = 'teleport'  # legs may cross walls
WARPS = 'blade warp and walk'
WALKS = 'walk'

NO_LANDING = 'no footing in view brings the character nearer by hops'
NO_HOP_WAY = 'no way of hops leads over the rooms to the goal'
# 2026-10-23 (rca/2026-10-23/realtime-2-findings.md): the hop's potential grown lazily, only as far as the character's
# own way (macros/hopway.py `LazyWay`: the same Dijkstra paused, the same landing; 55 -> 7 ms per new goal on a
# 32-80 room level). A goal that follows a monster is a new Target nearly every look, and the whole potential was
# rebuilt each time ("the act asked for", "the goal's way": 90 of 97 over-budget looks). False: teleport.py `Way`.
LAZY_HOPS = True  # on 2026-10-23 ~22:00: realtime-2 gate no worse (2440 plays + slow host k 1 and 1.5)
FAR_WAY = 'far way'  # `NoWay.distrust` key of a hop's far potential, with the goal's tile


@dataclass(frozen=True)
class Stand:
    """Where a hop starts (teleport.py `landing` reads only a place)."""

    x: float
    y: float


def hops(facts: MoveFacts, goal: Point, intent: Intent) -> bool:
    """Whether a Teleport hop toward a far goal fits `intent`: on a key, not failed within `intent.distrust`,
    a staff's charges above the reserve (at least one) and in hand unless `may_swap`, the goal past
    `intent.hop_from`. Without rooms only own Teleport strides; staff routing waits for them."""
    if TELEPORT not in facts.slots or facts.since_failed(TELEPORT) <= intent.distrust:
        return False
    if not facts.rooms and facts.staff is not None:
        return False
    if intent.hop_from and math.dist(facts.here, goal) < intent.hop_from:
        return False  # near: by the free jump (`Intent.hop_from`)
    staff = facts.staff
    return staff is None or (staff.charges >= max(intent.reserve, 1) and (staff.in_hand or intent.may_swap))


def hop_way(facts: MoveFacts, goal: Point) -> tuple[Target, Way | hopway.LazyWay, object]:
    """The hop potential to `goal` over the rooms (teleport.py `Way`) and its distrust key: the far one
    unless it gave no landing within FAR_DISTRUST (`MoveFacts.distrusted`), then the near one (key None)."""
    tile = (goal[0] / TILE_UNITS, goal[1] / TILE_UNITS)
    grids = facts.ground.grids if facts.ground is not None else ()
    target = Target(facts.area, facts.rooms, tile, 'the goal', 'hunt', False, grids)
    key = (FAR_WAY, facts.area, math.floor(tile[0]), math.floor(tile[1]))
    far = facts.now - facts.distrusted.get(key, -math.inf) >= FAR_DISTRUST
    found = (hopway.way_for if LAZY_HOPS else teleport.way_for)(target, Viewport(facts.aspect), far)
    return target, found, key if far else None


def hops_left(facts: MoveFacts, goal: Point) -> float:
    """Units of the way left to `goal` by hops; inf: none leads there."""
    if not facts.rooms:
        return math.dist(facts.here, goal)  # local strides until the room graph arrives
    _, way, _ = hop_way(facts, goal)
    return way.from_here((facts.here[0] / TILE_UNITS, facts.here[1] / TILE_UNITS)) * TILE_UNITS


def hop_leg(facts: MoveFacts, goal: Point, intent: Intent, spare: tuple[Jump, ...] = ()) -> Leg:
    """The next hop: the footing in view leaving the shortest hop way (teleport.py `landing`), by Teleport, or
    below `intent.sparing` charges by a free `spare` jump that still shortens it. A far potential with no
    landing comes back to be distrusted."""
    here = facts.here
    if math.dist(here, goal) - intent.short < MOVED:
        return NoWay(THERE, arrived=True)
    if not facts.rooms:
        # Goal and collision can arrive before the room graph: own Teleport strides as in combat, not the slower
        # free-jump route.
        jump = replace(TELEPORT_JUMP, least=TELEPORT_RING[0], reach=TELEPORT_RING[1]) if facts.pad else TELEPORT_JUMP
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=(jump,))
    target, way, far = hop_way(facts, goal)
    start = (here[0] / TILE_UNITS, here[1] / TILE_UNITS)
    now = way.from_here(start)
    ring = TELEPORT_RING if facts.pad else None
    land = hopway.landing if isinstance(way, hopway.LazyWay) else teleport.landing
    found = land(target, Stand(*here), way, facts.aspect, ring) if now < math.inf else None  # type: ignore[arg-type]
    if found is None:
        if far is not None:
            return NoWay(f'{NO_LANDING} (the far way)', distrust=far)
        return NoWay(NO_HOP_WAY if now == math.inf else NO_LANDING)
    spot = scaled(found[0])
    off = math.dist(spot, goal)
    if off < intent.short:
        # Back off to `short` of the goal: a Teleport aimed onto a chest's own spot is not cast (LOOPED).
        away = math.dist(here, goal)
        spot = goal if away <= intent.short else (
            goal[0] + (here[0] - goal[0]) * intent.short / away, goal[1] + (here[1] - goal[1]) * intent.short / away
        )  # fmt: skip
    if math.dist(spot, here) < MOVED:
        return NoWay(THERE, arrived=True)  # the best landing is here
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
    """A movement set of jump sources and the walk; sets differ only by `applies` and their sources."""

    name: str
    sources: tuple[JumpSource, ...] = ()

    def applies(self, facts: MoveFacts) -> bool:
        """Whether this set is the character's situation now."""
        raise NotImplementedError

    def led_by(self, *sources: JumpSource) -> Self:
        """This set with `sources` preferred to its own."""
        return replace(self, sources=(*sources, *self.sources))

    def then(self, *sources: JumpSource) -> Self:
        """This set with `sources` after its own."""
        return replace(self, sources=(*self.sources, *sources))

    def jumps(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The jumps makeable now within `intent`, in preference order (no weapon swap)."""
        if facts.pad:  # controller mode: fixed-length jumps only (`JumpSource.pad_jump`)
            made = (source.pad_jump() for source in self.sources if source.ready(facts, intent))
            return tuple(jump for jump in made if jump is not None)
        return tuple(source.jump for source in self.sources if source.ready(facts, intent))

    def leg(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The set's one decision (`eta` prices it): a stride by the first ready jump, else walked; a detour
        round a wall with `intent.detour`; the routed way with `intent.routed`."""
        jumps = self.jumps(facts, intent)
        if intent.routed:
            return self.routed(facts, goal, intent)
        if intent.detour:
            return around_of(facts, goal, jumps=jumps)
        return stride_of(facts, goal, intent.short, intent.shot, intent.shuns, jumps=jumps)

    def spare(self, facts: MoveFacts, intent: Intent) -> tuple[Jump, ...]:
        """The ready jumps that cost no charge (all but Teleport)."""
        return tuple(jump for jump in self.jumps(facts, intent) if jump.skill != TELEPORT)

    def free(self, facts: MoveFacts, intent: Intent) -> JumpSource | None:
        """The first free (non-Teleport) jump the character has: on a key, not failed within `intent.distrust`, of
        fixed reach in controller mode. Its delay may still run: the class is what it has, not what it can do now."""
        for source in self.sources:
            skill = source.jump.skill
            if skill == TELEPORT or skill not in facts.slots or facts.since_failed(skill) <= intent.distrust:
                continue
            if facts.pad and source.pad_reach is None:
                continue
            return source
        return None

    def means(self, facts: MoveFacts, goal: Point, intent: Intent) -> str:
        """The navigation class now: HOPS if `hops`, else WARPS with a `free` jump, else WALKS."""
        if hops(facts, goal, intent):
            return HOPS
        return WARPS if self.free(facts, intent) is not None else WALKS

    def routed(self, facts: MoveFacts, goal: Point, intent: Intent) -> Leg:
        """The next move on the routed way by the class now: HOPS by `hop_leg`, WARPS/WALKS by travel.py
        `way_leg`. A move that does not shorten `left` is no move."""
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
        """skill -> casting delay (travel.py `beats_walk`)."""
        return {source.jump.skill: source.delay for source in self.sources if source.delay}

    def left(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units of the way left by the class now: hops for HOPS, the walked way otherwise; inf: no way."""
        if self.means(facts, goal, intent) == HOPS:
            return hops_left(facts, goal)
        return way_left(facts, goal)

    def pace(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Units a second by the class now: a hop; the free jump's reach over max(delay, flight); the run."""
        kind = self.means(facts, goal, intent)
        if kind == HOPS:
            return TELEPORT_JUMP.reach / TELEPORT_JUMP.takes(TELEPORT_JUMP.reach)
        free = self.free(facts, intent) if kind == WARPS else None
        if free is None:
            return RUN_SPEED
        return free.jump.reach / max(free.delay, free.jump.takes(free.jump.reach))

    def eta(self, facts: MoveFacts, goal: Point, intent: Intent) -> float:
        """Seconds to `intent.short` of the goal: the next leg, then the rest at its pace; inf with no way.
        Routed: the way left at the class's pace, 0.0 on arrival."""
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
        """Seconds of casting delay worth waiting for on a keyed jump: the goal past MOVED and, for a line jump,
        the line clear as far as it carries (`intent.waits_blind`: the delay alone). 0.0 otherwise."""
        if not intent.may_wait:
            return 0.0
        if intent.routed:
            return self.routed_wait(facts, goal, intent)
        here = facts.here
        away = math.dist(here, goal)
        for source in self.sources:
            if source.ready(facts, intent):
                return 0.0  # a preferred jump is ready: none after it is waited for
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
        """Routed: the delay of a jump the set would make were it ready, when worth the wait (`waited`); else 0.0."""
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
        """Whether `jump` after `left` seconds of delay gains more way per second than the walk now (WARPS: the
        delay is its price). No move now, or one that is no walk: wait."""
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
        """A staff is worn (in hand or not, charged or not)."""
        return facts.staff is not None


@dataclass(frozen=True)
class OwnTeleport(Ways):
    """Teleport of the character's own (Enigma): no charges, no swap."""

    name: str = 'own teleport'
    sources: tuple[JumpSource, ...] = (OWN_TELEPORT,)

    def applies(self, facts: MoveFacts) -> bool:
        """Teleport on a key, no staff worn (or none read)."""
        return facts.staff is None and TELEPORT in facts.slots


@dataclass(frozen=True)
class Walk(Ways):
    """No Teleport at all: the walk, and whatever jumps a build puts before it."""

    name: str = 'walk'

    def applies(self, facts: MoveFacts) -> bool:
        """Always: the set of last resort."""
        return True


SHARED: tuple[Ways, ...] = (StaffTeleport(), OwnTeleport(), Walk())  # asked in this order

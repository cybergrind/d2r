"""Echoing Strike as the framework asks an attack (macros/build.py `Attack`): the skill held, the blades' reach, what
the strike reads off the character's units, where to cast and what a cast takes off whom when a place is priced.
One decision for the simulator (sim/engine.py) and for the game (combat/plan.md stage 5).

`LinePolicy`, the line sweep (a combat/policy.py `Policy`): through each live hostile within REACH a virtual cast
is laid with the focal point on, short of and past it (OFFSETS), scored by the emulated blades' points capped by
each monster's life (duplicate rule, Health Link share); the best line worth MIN_SCORE is cast, nothing while the
player moves (`yields`). With `hold` (HOLD_LEADER) a leader in reach comes first, a Herald before any: the line
through it with the focal point on it, kept on the same one until it dies (`kept`). `EchoingStrike` adds the rest
of the contract: `aim` (and `through` units), `sees` (Health Link), `dealt` (the line model a place is priced by:
BLADES_A_CAST blades on each monster near the line, up to a wall). Two classes, as harnesses score sweeps of their
own; `EchoingStrike.of` makes the attack of one.
"""

import math
import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from itertools import pairwise

from inventory_tracking.builds.warlock.echoing_strike.damage import DEFILER, damage_table, link_table
from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import (
    BLADES,
    LIFE,
    OUT_FRAMES,
    RANGE,
    SPEED,
    cast,
    flown,
)
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat.mechanics.movement import Route
from inventory_tracking.combat.policy import ELITE_WEIGHT, MIN_FOCAL, MIN_SCORE, Choice, Foe, Observation, Point
from inventory_tracking.common import LOG
from inventory_tracking.game.records import Monster
from inventory_tracking.takes.timeline import GAME_RATE


DUPLICATE = 1 / (2 * BLADES)  # skills.txt calc6 (100 / count) / 2: a cast's blades after the first on a monster and leg
REACH = RANGE  # units: a monster further than the blades fly is not a line
OFFSETS = (0.0, -3.0, 4.0)  # focal point along the line relative to the monster: on, short, past (ties: on)
# What one cast takes off a monster on its line, in blades: the first whole and the rest by the
# duplicate rule, out and back (`virtual_cast`: 2,800 points of a 1,000-point blade).
BLADES_A_CAST = 2.8
# The share of casts whose blades hit the monster aimed at, by its distance: (the bin's furthest units, the share)
# (rca/2026-10-14/run-1932-findings.md §4.1, 694 casts). At the end of the blades' flight a monster's step is a miss.
HIT_BY_DISTANCE = ((6.0, 0.743), (10.0, 0.747), (14.0, 0.606), (18.0, 0.493), (REACH, 0.356))


# The player, 2026-10-20 ~15:04: "and overall aim against moving enemies was pretty bad. probably we need to do some
# smart targeting against moving enemies". True: the game's lines are laid and scored where each monster's velocity
# has it as the blades fly (`Motion`, `sees`; `LinePolicy.lead` LIVE_LEAD frames), every monster on a line, not the
# aimed one only. Measured on the 14,248 casts of 2026-10-20 and replayed in the simulator
# (rca/2026-10-20/leader-not-marked-findings.md, "Moving monsters"): a monster moving across the line is missed more
# (64% hit still, 58% walking, 54% running), but the velocity's lead lost hits on the recorded paths (every group)
# and 4% of the contacts and kills a cast in the simulator's 30 takes, so it is off; the monsters' own routes (path
# records, not read on the live look) did better (§5.4). False: the lines through where the monsters stand.
LEAD_MOVING = False
LIVE_LEAD = 5  # frames from a look's decision to the blades' first frame (median of 14,248 casts; quartiles 4, 12)
MOTION_SECONDS = (0.15, 0.5)  # a velocity is measured over the oldest sample this old at least, this old at most
STILL_SPEED = 1.0  # units a second: slower is standing
MOST_SPEED = 16.0  # units a second: the velocity is capped here (monstats Run of the fastest of the takes' monsters)
LEAD_MOST = 6.0  # units: most a monster is taken to go along its velocity (one that turns drags no line far off)
# The player, 2026-10-20 ~18:45, asked whether to mark pack leaders first and weight the leader in the aim: "ok,
# recast. pack leader/herald first" (rca/2026-10-20/mark-recast-leaders-findings.md). True: where the best line is not
# laid through a leader (a unique, champion or super unique: a Herald is a unique), the best line laid through one is
# cast instead while it is worth LEADER_SHARE of the best (`LinePolicy.focus`). False: the best line, a leader's points
# counting ELITE_WEIGHT.
FOCUS_LEADERS = False
LEADER_SHARE = 0.85
# The player, 2026-10-21 ~18:58, of a tier 5 Herald pack of Vile Witches: "current T5 fight is bad aiming - we're not
# focusing and delivering good damage. we were able to kill herald several times, but was targeted at wrong location
# => spread projectiles => low dps => lost a lot of time and health". Of the 79 casts with the Herald in reach, 34 went
# on lines the sweep laid through its pack, 8 of them with the focal point 4 units off the character (the "short"
# offset and MIN_FOCAL: the blades cross there and fan out over the pack), and the line went to the Herald 17 times
# and off it 17 times (rca/2026-10-21/herald-aiming-findings.md). True: a leader in reach is struck until it dies,
# a Herald first (`Foe.herald`), then a unique, champion or super unique: the line through it with the focal point on
# it, where the five blades meet (LEADER_OFFSETS), whatever its pack's lines are worth; the one struck is kept while
# it is seen (`Held`: a nearer leader takes it over only when it is gone, a Herald when it is not one), and a look
# that cannot lay a line to it strikes the best line without letting it go (`LinePolicy.hold`). The rules before the
# sweep stay first (a boss, a bound summoner, what bars the goal, the dolls: the `through` units of `aim`). False: the
# best line (with FOCUS_LEADERS' share rule when that is on).
HOLD_LEADER = True
# T5_BEST_LINE (2026-10-23, the player ~20:35: "Best line in T5 packs (Recommended)"; rca/2026-10-23/
# death-canyon-findings.md §10): in the canyon's tier 5 Hell Slinger pack the hold kept the blades on the Herald (164k
# life, a minion 33k) while the minions' javelins came on; the best line killed 13.7 a play there against 8.4. True: a
# tier 5 Herald is no leader the strike holds (HERALD_TIER): the best line, its minions included; every other leader,
# the bosses too, is held as before. False: as before.
T5_BEST_LINE = True  # on 2026-10-24 ~09:50: "Best line in T5 packs (Recommended)"; gate passed
HERALD_TIER = 5
# A leader whose resistance to the blades' damage is IMMUNE (physical: Echoing Strike is weapon damage, skills.txt 388;
# the 18:35 Gloam Herald of the same day, stat 36 at 110 with Stone Skin, rca/2026-10-21/herald-gloam-findings.md) is
# not held: the blades take nothing off it, its mark and the demons are its answer (mark.py MARK_IMMUNE). This fight's
# Vile Witch Herald stood at 75 (its minions 25): hurt, a quarter of a blade's points a contact.
# Empty since 2026-10-21 ~20:15, the player: "we still need to focus physical immune mobs, and magical immune"; "we
# need to do the best aiming when we're trying to focus mob": every leader is held, immune or not (was
# (PHYSICAL_RESIST,))
HELD_IMMUNE: tuple[int, ...] = ()
# The focal point along the line from the leader: on it and one unit past (AIM_BEYOND); the blades meet within 0.2
# units of it at either (LATERAL's 1.9 units, times 1 over the 13 units to the focal, at the engage ring). The
# sweep's short offset (-3) is not used for a leader: on a leader within 7 units MIN_FOCAL holds it at 4 and the blades
# are 1.8 units apart either side of it, in contact only with its edge.
LEADER_OFFSETS = (0.0, 1.0)


def unheld(foe: Foe) -> bool:
    """T5_BEST_LINE: a tier 5 Herald, struck by the best line, not held."""
    return T5_BEST_LINE and foe.herald and foe.tier >= HERALD_TIER


@dataclass
class Held:
    """The leader the strike is kept on until it dies (HOLD_LEADER); None: none. Shared by the copies `replace`
    makes of a sweep, so the game's one attack keeps it from look to look."""

    unit: int | None = None


# The bins' middles with their shares: what `hit_share` runs straight between.
HIT_MIDDLES = tuple(
    ((low + high) / 2, share)
    for (low, _), (high, share) in zip(((0.0, 0.0), *HIT_BY_DISTANCE), HIT_BY_DISTANCE, strict=False)
)


def hit_share(away: float) -> float:
    """`HIT_BY_DISTANCE` at `away` units: straight between the bins' middles, the end bins' own beyond them."""
    if away <= HIT_MIDDLES[0][0]:
        return HIT_MIDDLES[0][1]
    for (near, first), (far, second) in pairwise(HIT_MIDDLES):
        if away <= far:
            return first + (second - first) * (away - near) / (far - near)
    return HIT_MIDDLES[-1][1]


def engage_ring() -> float:
    """Units from a monster a stand is best at: where `hit_share` falls half way from its best to its worst (13.9,
    as the player engages)."""
    best = max(share for _, share in HIT_MIDDLES)
    half = (best + HIT_MIDDLES[-1][1]) / 2
    for (near, first), (far, second) in pairwise(HIT_MIDDLES):
        if first >= half > second:
            return near + (far - near) * (first - half) / (first - second)
    return REACH


ENGAGE = engage_ring()  # units: the firing ring an approach plans and the place a jump is best ended at


def virtual_cast(
    origin: Point,
    focal: Point,
    foes: dict[int, Foe],
    linked: frozenset[int] | set[int],
    share: float,
    damage_of: Callable[[int], float],
    radius: float = CONTACT_RADIUS,
    blocked: Callable[[Point], bool] | None = None,
    elite_weight: float = 1.0,
    lead: int | None = None,
) -> float:
    """Points one cast would take off the monsters where they stand (with `lead`, the frames from now
    to the blades' first frame: where each one's route has it as the blades fly), out and back: the duplicate
    rule, each contact capped by what the monster has left, and the link's spread to the other
    linked monsters, each capped by its own points; `blocked` are the walls the blades stop at. Points
    taken off an elite count `elite_weight` times (the worth of a line, not damage)."""
    left = {unit: foe.left for unit, foe in foes.items()}
    total = 0.0
    first: set[tuple[int, str]] = set()
    walkers = (
        {unit: [foe.ahead(lead + k) for k in range(LIFE)] for unit, foe in foes.items() if foe.route is not None}
        if lead is not None
        else {}
    )
    for path in cast(origin, focal, lambda k: origin, blocked):
        touched: set[tuple[int, str]] = set()
        for k, position in enumerate(path):
            leg = 'out' if k <= OUT_FRAMES else 'back'
            for unit, foe in foes.items():
                where = walkers[unit][k] if unit in walkers else foe.at
                if (unit, leg) in touched or left[unit] <= 0 or math.dist(position, where) > radius:
                    continue
                touched.add((unit, leg))
                dealt = damage_of(foe.txt) * (DUPLICATE if (unit, leg) in first else 1.0)
                first.add((unit, leg))
                taken = min(dealt, left[unit])
                left[unit] -= taken
                total += taken * (elite_weight if foe.elite else 1.0) * foe.weight
                if unit in linked:
                    for other in linked:
                        if other != unit and left.get(other, 0) > 0:
                            spread = min(dealt * share, left[other])
                            left[other] -= spread
                            total += spread * (elite_weight if foes[other].elite else 1.0) * foes[other].weight
    return total


def linked_set(defilers: Iterable[Point], foes: dict[int, Point], link_range: float, links: int) -> frozenset[int]:
    """The `links` live hostiles nearest a Defiler within its aura range: the ones Health Link holds."""
    posts = list(defilers)
    if not posts or not links:
        return frozenset()
    near = sorted((min(math.dist(post, at) for post in posts), unit) for unit, at in foes.items())
    return frozenset(unit for gap, unit in near[:links] if gap <= link_range)


@dataclass
class LinePolicy:
    yields: bool = True  # nothing while the player is moving
    reach: float = REACH
    offsets: tuple[float, ...] = OFFSETS
    damage_of: Callable[[int], float] = field(default_factory=damage_table)
    elite_weight: float = ELITE_WEIGHT
    # Frames from the decision to the blades' first frame: lines are laid and scored where the monsters'
    # routes have them as the blades fly. None: where they stand (the game's fight until it reads routes).
    lead: int | None = None
    # A line laid through a leader (`Foe.elite`) worth this share of the best line is cast instead of it
    # (FOCUS_LEADERS); 0: the best line
    focus: float = 0.0
    # A leader in reach is struck until it dies, the line through it with the focal point on it (HOLD_LEADER)
    hold: bool = False
    held: Held = field(default_factory=Held)  # the leader struck last (`hold`)

    def __call__(self, seen: Observation) -> Choice | None:
        if self.yields and seen.moving:
            return None
        best = self.kept(seen)
        if best is None:
            best = self.focused(seen, self.choose(seen))
        return best if best is not None and best.worth >= MIN_SCORE else None

    def kept(self, seen: Observation) -> Choice | None:
        """With `hold`, the line through a leader in reach (`leader_line`), none immune to the blades (HELD_IMMUNE):
        the one held while it is seen, a Herald before any other; else the nearest. The one found is held from here
        when none is (or a Herald is found and the held one is not); a held one gone from the foes is let go. None:
        no leader has a line to it now, or no `hold`."""
        if not self.hold:
            return None
        held = self.held
        if held.unit is not None and held.unit not in seen.foes:
            LOG.info('Macro: strike: the leader %d held is gone: let go', held.unit)
            held.unit = None
        if held.unit is not None and unheld(seen.foes[held.unit]):
            held.unit = None  # a tier 5 Herald: the best line (T5_BEST_LINE)
        leaders = sorted(
            (
                unit
                for unit, foe in seen.foes.items()
                if foe.elite and not foe.immune_to & set(HELD_IMMUNE) and not unheld(foe)
            ),
            key=lambda unit: (
                not seen.foes[unit].herald,
                unit != held.unit,
                math.dist(seen.origin, seen.foes[unit].at),
            ),
        )
        for unit in leaders:
            found = self.leader_line(seen, unit)
            if found is None:
                continue
            taken = held.unit is None or (seen.foes[unit].herald and not seen.foes[held.unit].herald)
            if taken and unit != held.unit:
                held.unit = unit
                LOG.info(
                    'Macro: strike: %s %d held until it dies, %.1f away',
                    'the Herald' if seen.foes[unit].herald else 'the leader', unit,
                    math.dist(seen.origin, seen.foes[unit].at),
                )  # fmt: skip
            return found
        return None

    def leader_line(self, seen: Observation, unit: int) -> Choice | None:
        """The line through `unit` with the focal point on it (LEADER_OFFSETS), where the five blades meet: the one
        that takes the most off it, then the most worth over all; None out of reach, off the screen, or with no blade
        reaching it (a wall)."""
        foe = seen.foes[unit]
        at = foe.at
        if self.lead is not None:  # through where it is when a blade gets as far as it stands now (`choose`)
            at = foe.ahead(self.lead + min(round(math.dist(at, seen.origin) / SPEED), OUT_FRAMES))
        away = math.dist(at, seen.origin)
        if away > self.reach or away == 0:
            return None
        ux, uy = (at[0] - seen.origin[0]) / away, (at[1] - seen.origin[1]) / away
        best: tuple[tuple[float, float], Choice] | None = None
        for offset in LEADER_OFFSETS:
            distance = max(MIN_FOCAL, min(away + offset, self.reach - 1))
            focal = (seen.origin[0] + ux * distance, seen.origin[1] + uy * distance)
            if seen.aimable is not None:
                reached = seen.aimable(focal)
                if reached is None:
                    continue
                focal = reached
            on = virtual_cast(
                seen.origin, focal, {unit: foe}, frozenset(), 0.0, self.damage_of, blocked=seen.blocked,
                lead=self.lead,
            )  # fmt: skip
            if on <= 0:
                continue
            worth = virtual_cast(
                seen.origin, focal, seen.foes, seen.linked, seen.share, self.damage_of, blocked=seen.blocked,
                elite_weight=self.elite_weight, lead=self.lead,
            )  # fmt: skip
            if best is None or (on, worth) > best[0]:
                best = ((on, worth), Choice(focal, unit, worth))
        return best[1] if best is not None else None

    def focused(self, seen: Observation, best: Choice | None) -> Choice | None:
        """`best`, or with `focus` the best line laid through a leader where `best` is laid through none and that
        one is worth `focus` of it."""
        if not self.focus or best is None or seen.foes[best.unit].elite:
            return best
        leaders = [unit for unit, foe in seen.foes.items() if foe.elite]
        if not leaders:
            return best
        found = self.choose(seen, through=leaders)
        return found if found is not None and found.worth >= self.focus * best.worth else best

    def choose(self, seen: Observation, through: Collection[int] | None = None) -> Choice | None:
        """The best line through the live hostiles; with `through`, of the lines laid through those."""
        best: Choice | None = None
        for unit, foe in seen.foes.items():
            if through is not None and unit not in through:
                continue
            at = foe.at
            if self.lead is not None:  # through where it is when a blade gets as far as it stands now
                at = foe.ahead(self.lead + min(round(math.dist(at, seen.origin) / SPEED), OUT_FRAMES))
            away = math.dist(at, seen.origin)
            if away > self.reach or away == 0:
                continue
            ux, uy = (at[0] - seen.origin[0]) / away, (at[1] - seen.origin[1]) / away
            for offset in self.offsets:
                distance = max(MIN_FOCAL, min(away + offset, self.reach - 1))
                focal = (seen.origin[0] + ux * distance, seen.origin[1] + uy * distance)
                if seen.aimable is not None:
                    # The line is scored with the focal point the cast will have, not one off the screen
                    # that the aim would shorten after the choice (review.md, finding 8).
                    reached = seen.aimable(focal)
                    if reached is None:
                        continue
                    focal = reached
                worth = virtual_cast(
                    seen.origin, focal, seen.foes, seen.linked, seen.share, self.damage_of, blocked=seen.blocked,
                    elite_weight=self.elite_weight, lead=self.lead,
                )  # fmt: skip
                if worth > (best.worth if best is not None else 0.0):
                    best = Choice(focal, unit, worth)
        return best


@dataclass
class Motion:
    """The hostiles' places as the looks saw them, by unit: (clock, place), the newest last, MOTION_SECONDS long."""

    clock: Callable[[], float] = time.monotonic
    seen: dict[int, list[tuple[float, Point]]] = field(default_factory=dict)

    def note(self, foes: Mapping[int, Foe]) -> None:
        """Remember where each of `foes` stands now; forget the units unseen for longer than MOTION_SECONDS."""
        now = self.clock()
        for unit, foe in foes.items():
            samples = self.seen.setdefault(unit, [])
            if not samples or samples[-1][0] < now:
                samples.append((now, foe.at))
            del samples[: len(samples) - sum(1 for at, _ in samples if now - at <= MOTION_SECONDS[1])]
        for unit in [u for u, samples in self.seen.items() if now - samples[-1][0] > MOTION_SECONDS[1]]:
            del self.seen[unit]

    def velocity(self, unit: int) -> tuple[float, float] | None:
        """Units a second of `unit` between its newest place and the oldest within MOTION_SECONDS (at least the
        first's age), capped at MOST_SPEED; None with no such pair."""
        samples = self.seen.get(unit, [])
        if len(samples) < 2:
            return None
        now, here = samples[-1]
        old = [(at, place) for at, place in samples[:-1] if MOTION_SECONDS[0] <= now - at <= MOTION_SECONDS[1]]
        if not old:
            return None
        at, there = old[0]
        vx, vy = (here[0] - there[0]) / (now - at), (here[1] - there[1]) / (now - at)
        speed = math.hypot(vx, vy)
        if speed > MOST_SPEED:
            vx, vy = vx * MOST_SPEED / speed, vy * MOST_SPEED / speed
        return vx, vy

    def route(self, unit: int, at: Point) -> Route | None:
        """A straight route along its velocity from `at`, LEAD_MOST units long; None standing (STILL_SPEED)."""
        found = self.velocity(unit)
        if found is None:
            return None
        speed = math.hypot(*found)
        if speed < STILL_SPEED:
            return None
        end = (at[0] + found[0] / speed * LEAD_MOST, at[1] + found[1] / speed * LEAD_MOST)
        return Route((end,), speed / GAME_RATE)


@dataclass
class EchoingStrike(LinePolicy):
    """The strike of the Echoing Strike Warlock. `reach` is the blades' range (`LinePolicy.reach`). With
    LEAD_MOVING its lines are laid where the monsters' velocities (`motion`) have them LIVE_LEAD frames on."""

    skill: int = ECHOING_STRIKE  # the skill whose input the fight holds
    engage: float = ENGAGE
    motion: Motion = field(default_factory=Motion)

    def choose(self, seen: Observation, through: Collection[int] | None = None) -> Choice | None:
        """`LinePolicy.choose`, with LIVE_LEAD frames of lead under LEAD_MOVING where no lead is set."""
        if LEAD_MOVING and self.lead is None:
            return replace(self, lead=LIVE_LEAD).choose(seen, through)
        return super().choose(seen, through)

    def focused(self, seen: Observation, best: Choice | None) -> Choice | None:
        """`LinePolicy.focused`, at LEADER_SHARE under FOCUS_LEADERS where no focus is set."""
        if FOCUS_LEADERS and not self.focus:
            return replace(self, focus=LEADER_SHARE).focused(seen, best)
        return super().focused(seen, best)

    def holding(self) -> int | None:
        """The leader the strike is held on (HOLD_LEADER), None with none: what the run's side goals wait for
        (macros/hunting/choice.py HELD_STAYS)."""
        return self.held.unit

    def forget(self) -> None:
        """Drop what the earlier looks left: the leader held, the monsters' places (a new hunt, macros/hunt.py
        `Hunter`: the game's one attack serves every hunt made, and a replay played twice plays the same)."""
        self.held.unit = None
        self.motion.seen.clear()

    def kept(self, seen: Observation) -> Choice | None:
        """`LinePolicy.kept`, held under HOLD_LEADER where no hold is set (the copy shares `held`)."""
        if HOLD_LEADER and not self.hold:
            return replace(self, hold=True).kept(seen)
        return super().kept(seen)

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
        foes = seen.foes
        if LEAD_MOVING:
            self.motion.note(foes)
            foes = {
                unit: foe if foe.route is not None else replace(foe, route=self.motion.route(unit, foe.at))
                for unit, foe in foes.items()
            }
        return replace(seen, foes=foes, linked=linked, share=share)

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """The best line worth MIN_SCORE, or None; nothing while the player is moving (`yields`).
        With `through`, the best of the lines laid through those units, whatever another is worth."""
        if not through:
            return self(seen)
        if self.yields and seen.moving:
            return None
        best = self.choose(seen, through=through)
        return best if best is not None and best.worth >= MIN_SCORE else None

    def dealt(
        self, origin: Point, focal: Point, foes: Mapping[int, Foe], blocked: Callable[[Point], bool] | None = None
    ) -> Mapping[int, float]:
        """The points a cast from `origin` at `focal` takes off each of `foes` on its line: BLADES_A_CAST blades off
        every one ahead within the contact radius of the line (the caller gives those in reach); nothing from a focal
        point under the character. At the first wall `blocked` says (mechanics.py `flown`) one past it takes nothing,
        one before it half (the way out only; run-2040-findings.md §3.3)."""
        tx, ty = focal[0] - origin[0], focal[1] - origin[1]
        away = math.hypot(tx, ty)
        if not away:
            return {}
        ux, uy = tx / away, ty / away
        stop = flown(origin, focal, blocked)
        blades = BLADES_A_CAST if stop is None else BLADES_A_CAST / 2  # out and back, or out only
        hit = {}
        for unit, foe in foes.items():
            dx, dy = foe.at[0] - origin[0], foe.at[1] - origin[1]
            ahead = dx * ux + dy * uy
            if ahead > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS:
                if stop is not None and ahead > stop + CONTACT_RADIUS:
                    continue  # behind the wall the blades died in
                hit[unit] = self.damage_of(foe.txt) * blades
        return hit

    def lands(self, away: float) -> float:
        """The share of casts that hit a monster `away` units off, against the casts close in (`hit_share` over its
        best): 1.0 within 10 units, about 0.48 at the end of the reach."""
        return hit_share(away) / max(share for _, share in HIT_MIDDLES)


ECHOING_STRIKE_ATTACK = EchoingStrike()  # the build's: the sweep as the game runs it, with the build's damage table

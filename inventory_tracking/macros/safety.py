"""Observation and candidate assembly for the pure pursuit arbiter.

The only memory is observed weapon profiles, how long the same pressed goal
has been blocked and the way the character came (the walked way back an
escape may take). Nothing here delivers input or chooses a goal.

Second pass (rca/2026-10-13/safety-pricing.md, "Second pass"): the price of
a place counts the character's own strikes from it (combat/stance.py `falls`
through the build's `Attack`: what dies when, so a dead hostile deals nothing
after) and the build's guard (`Shield`); escapes are drawn from the threat's
geometry; the look's work is bounded by caps and, in the game, a deadline.
"""

import math
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import NamedTuple

from inventory_tracking.combat import threats
from inventory_tracking.combat.harm import (
    GROUND_UNIT,
    Hands,
    Harm,
    Hostile,
    Look,
    Protection,
    SafetySettings,
    blockers,
    budget,
    harm,
    harm_path,
    life_factor,
    life_price,
    sent_onto,
    stock_share,
    veto,
)
from inventory_tracking.combat.policy import Observation, Point
from inventory_tracking.combat.stance import (
    HORIZON,
    KEEP_AWAY,
    RUN_SPEED,
    WALK_LATENCY,
    Field,
    Jump,
    camp,
    falls,
    taken,
)
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.common import LOG
from inventory_tracking.macros.build import Attack, Draw, DrawPrice, Leg, NoWay, PricedStep, Shield, Step
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.game.layout import NO_OWNER
from inventory_tracking.macros.game.records import Loot, World
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.pursuit import Act, Candidate, Facts, Hold, Move, Operate, decide
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.supply import spendable as stock_life
from inventory_tracking.macros.travel import planning
from inventory_tracking.models import PotionType


# How far the escapes are looked for: away from the threat's weighted centre, near and far, and turned
# either side of it; the way the character came, one point of it no nearer the threat; behind a companion.
ESCAPE_REACH = (12.0, 22.0)
ESCAPE_TURN = math.radians(40)
TRAIL_STEP = 4.0  # units between two points of the way the character came
TRAIL_POINTS = 24
ESCAPE_SAME = 4.0  # units: two escapes nearer than this are one
BEHIND = 4.0  # units beyond a companion, away from the threat
ESCAPES_MOST = 6  # escape places asked of the navigator in one look, the threat's first (the cost of a look)
RAYS = 8  # the plain rays round the character, asked after those while time is left
FOOTING_RINGS = (1.5, 3.0)  # units round an escape's place where footing is looked for when it has none
FOOTING_TURNS = 8
FALL_HORIZON = 10.0  # seconds the character's own strikes are counted over for a stand's clear time
RESISTS = ((36, 'physical'), (39, 'fire'), (41, 'lightning'), (43, 'cold'), (45, 'poison'), (37, 'magic'))
# Stats store unpenalized percentages. Difficulty is not yet an observation: the
# macro's supported economy is Hell. Keep this explicit, never assume capped gear.
HELL_PENALTY = 100.0
SWAP_SECONDS = 0.75
WAITING = 'safety: waiting here: every way out costs more than standing'
BURNING = 'safety: waiting for what burns on the way to go out'  # `burnt_out`: the act asked for, made after
FIRING = 'firing spot'  # the reason of a move to a stand the strike is made from (pursuit.py's commitment)
# The reason of an escape priced against holding (not a retreat): a stand the strike goes on from, taken for the
# life it saves, so not held to the firing stand's commitment (pursuit.py), which is against changing stands for
# a strike pace barely better. `Macro: pursuit: stepping across ...` in the log.
STEPPING = 'stepping'
AWAY = 'away from the threat'  # why a place of the threat's geometry is offered
# The build's draw (macros/build.py `Draw`: a cast that sends its companions onto a hostile), weighed at a look of a
# fight (`Safety.weigh`): onto the DRAW_TARGETS hostiles with the largest shares of holding's harm, the one it gains
# most on and the DRAW_LEADERS nearest leaders (a unique, a champion, a super unique, a boss: what a pack follows and
# what outlives it; the player, 2026-10-14: the mark goes "on the leader / most dangerous monster"); not onto one the
# companions stand within DRAW_HELD units of its landing distance of already (they hold it: a cast would change
# nothing). A price is the fight's for DRAW_FRESH seconds (a few looks of the fight's DECIDE_SECONDS 0.12), older
# the row that casts it goes by its own rule.
DRAW_TARGETS = 2
DRAW_LEADERS = 2
DRAW_HELD = 3.0
DRAW_FRESH = 0.5
# A retreat that keeps the fight (rca/2026-10-14/baal-sim.md fix 1, `keeper`, `keeping`): offered when one hostile's
# kill ends KEEP_SHARE or more of the harm where the character stands (its own and that of what is bound to it, a
# summon gone with its summoner: combat/threats `bound`), on the ring KEEP_MARGIN units inside the strike's reach of
# it, at these turns from the character's bearing (the nearest first).
KEEP_SHARE = 0.5
KEEP_MARGIN = 1.5
KEEP_TURNS = tuple(math.radians(turn) for turn in (0, 35, -35, 70, -70, 110, -110, 180))
KEEP_MOST = 4  # such places asked of the navigator in one look
# A missile the look reads for a read model (combat/threats): (owner unit, missile class, x, y).
Flights = Callable[[frozenset[int]], Sequence[tuple[int, int, float, float]]]
# A better place to fight from that the fight's own look found (macros/hunt.py: the sweep's `next_step` ->
# combat/stance.py `camp`, every FOLLOW_CHECK 0.7 s of a level run's fight) is priced as a firing stand against
# holding for STAND_FRESH seconds after (`offer`): the looks of the fight and the look that makes the move in between
# price the same place. rca/2026-10-14/run-1932-findings.md §4: a safe fight's only candidate was holding, so the
# character struck from the edge of its reach (17 to 22 units, a third of the casts hitting nothing).
STAND_FRESH = 0.7
# The look's time (`SafetySettings.look_seconds`, 0.08 s) the goal's way may take (travel.py `planning`): a walked
# field not grown as far as the character by then is the straight line for this look and grows on at the next. The
# rest is holding's and the escapes'. Before 2026-10-15 the way had no bound: the Plains of Despair's cold field
# made two looks of 5.1 and 4.7 s at 23:48 on 2026-10-14 with the strike and the drinker waiting on them
# (rca/2026-10-14/run-2040-findings.md §1.2).
WAY_SHARE = 0.5
# The way's time with no hostile within QUIET_WAY_UNITS: a cold field to the next chest grew 40 ms a look and was the
# straight line or no way for three or four looks (268 waits in 78 games, 1.1 s a game, 2026-10-17); with nothing near
# to strike or flee from, one look grows it, well within STALE_LOOK (hunt.py, 0.3 s)
QUIET_WAY_SECONDS = 0.15
QUIET_WAY_UNITS = 30.0  # goals.py CLEAR_WAY


def way_seconds(here: tuple[float, float], hostiles: Sequence[tuple[float, float]], look_seconds: float) -> float:
    """The seconds of a look the goal's way may grow in: QUIET_WAY_SECONDS with no hostile within QUIET_WAY_UNITS,
    else the look's share (WAY_SHARE)."""
    if all(math.dist(here, at) > QUIET_WAY_UNITS for at in hostiles):
        return max(QUIET_WAY_SECONDS, look_seconds * WAY_SHARE)
    return look_seconds * WAY_SHARE


# A look over OVER_BUDGET times its time is said (`Macro: look: ...`, with the stage that took the most), at most
# once in SAID_EVERY seconds of the look's clock, with how many more were since.
OVER_BUDGET = 2.0
SAID_EVERY = 1.0


def footing(field_: Field, here: Point, point: Point) -> Point | None:
    """`point`, or the nearest place within FOOTING_NEAR of it (rings of FOOTING_RINGS units, FOOTING_TURNS
    directions) the grids show as footing, off any wall and with a clear line from `here`; None when there is
    none. An escape's place is drawn from a threat's geometry, which knows nothing of the ground (the Chaos
    Sanctuary's star has unwalkable cells in it)."""
    for ring in (0.0, *FOOTING_RINGS):
        for k in range(FOOTING_TURNS if ring else 1):
            angle = k * math.tau / FOOTING_TURNS
            spot = (point[0] + ring * math.cos(angle), point[1] + ring * math.sin(angle))
            if field_.bar((math.floor(spot[0]), math.floor(spot[1]))) or field_.wall(*spot):
                continue
            if field_.clear(here, spot):
                return spot
    return None


def keeper(look: Look, seen: Observation, priced: Harm) -> int | None:
    """The hostile whose kill ends KEEP_SHARE or more of the harm `priced` (by its contributors): its own share and
    that of the hostiles bound to it (combat/threats `bound`: Baal's clone goes with him, so his kill ends both). None
    when no one hostile's does (a pack whose harm is spread: the retreats are as before) or it cannot be struck."""
    total = sum(points for _, points in priced.by)
    if total <= 0:
        return None
    ends = dict(priced.by)
    for unit, masters in threats.bound({m.unit: m.txt for m in look.hostiles}).items():
        for master in masters:
            ends[master] = ends.get(master, 0.0) + dict(priced.by).get(unit, 0.0)
        ends.pop(unit, None)
    found = max((unit for unit in ends if unit in seen.foes), key=lambda unit: (ends[unit], -unit), default=None)
    return found if found is not None and ends[found] >= KEEP_SHARE * total else None


def keeping(here: Point, at: Point, reach: float) -> list[Point]:
    """The places a retreat that keeps the fight is offered at (`KEEP_TURNS`): on the ring KEEP_MARGIN inside `reach`
    of `at` (the hostile `keeper` names), the nearest to `here` first, KEEP_MOST of them."""
    radius = max(reach - KEEP_MARGIN, 1.0)
    bearing = math.atan2(here[1] - at[1], here[0] - at[0])
    ring = [(at[0] + radius * math.cos(bearing + t), at[1] + radius * math.sin(bearing + t)) for t in KEEP_TURNS]
    return sorted(ring, key=lambda point: math.dist(here, point))[:KEEP_MOST]


def in_flight(
    hostile: Sequence, flights: Flights | None, read: Sequence[tuple[int, int, float, float]] | None = None
) -> tuple[tuple[int, Point, float, int], ...]:
    """The missiles in flight the read models of `hostile` ask for (combat/threats `missiles`), each with its
    owner, its heading and its class (a model of more than one, Baal's, tells them apart): a missile flies straight
    from where its owner stood, so the heading is the line from the owner to it (Diablo's stand while he casts:
    rca/2026-10-13/diablo.md, 0.5 degrees in the takes). Nothing is read when no such hostile is about, or when the
    reading fails (the price then has the mode alone). `read`: the missiles the look read already (of these classes
    and maybe others), in place of a read of its own."""
    owners = {m.unit_id: (m.x, m.y) for m in hostile if threats.of(m.txt_id) is not None}
    if not owners or (flights is None and read is None):
        return ()
    kinds = threats.missiles({m.txt_id for m in hostile})
    if read is None:
        assert flights is not None
        try:
            read = flights(kinds)
        except OSError, ValueError:
            return ()
    found = []
    for owner, txt, x, y in read:
        at = owners.get(owner)
        if at is not None and txt in kinds and (x, y) != at:
            found.append((owner, (x, y), math.atan2(y - at[1], x - at[0]), txt))
    return tuple(found)


@dataclass
class LookClock:
    """A look's own clock (`Safety.timer`): its deadline and each stage's seconds (`laps`, for `Safety.over`). No
    timer: never late, no laps."""

    timer: Callable[[], float] | None
    seconds: float  # the look's time (`SafetySettings.look_seconds`)
    began: float = 0.0
    deadline: float = math.inf
    laps: dict[str, float] = field(default_factory=dict)
    lapped: float = 0.0

    def __post_init__(self) -> None:
        if self.timer is not None:
            self.began = self.timer()
            self.deadline = self.began + self.seconds
        self.lapped = self.began

    def late(self) -> bool:
        return self.timer is not None and self.timer() >= self.deadline

    def lap(self, stage: str) -> None:
        """The seconds since the last stage ended are `stage`'s."""
        if self.timer is not None:
            now = self.timer()
            self.laps[stage] = self.laps.get(stage, 0.0) + now - self.lapped
            self.lapped = now

    def ms(self) -> float | None:
        """Milliseconds since the look began; None without a timer."""
        return round((self.timer() - self.began) * 1000, 1) if self.timer is not None else None


def bounded_way(facts: Facts, clock: LookClock, until: float) -> tuple[Facts, list[Leg]]:
    """`facts` with the goal's way asked once a look, grown until `until` on the look's clock (travel.py `planning`):
    the act asked for, the Hold branch's advance and the arbiter all go by that one leg. The list holds it once
    asked."""
    goals_way = facts.way
    legs: list[Leg] = []

    def way() -> Leg:
        if not legs:
            with planning(clock.timer, until):
                legs.append(goals_way())
        return legs[0]

    return replace(facts, way=way), legs


def life_budget(
    loot: Loot, felt: Pressure, settings: SafetySettings, look: Look, here: Point, insisting: float
) -> tuple[float, float | None, float, float]:
    """The life an act may cost (combat/harm.py `budget`), the belt's spendable life it counts, the price of life
    (kappa) and the fight's factor in it (`SafetySettings.dear`: dearer while a dear class is in the fight)."""
    # The belt counted (`stock_share`): a low potion stock keeps a share of the budget, half at least
    spendable = stock_life(loot, settings.healing_points, settings.floor)
    allowance = budget(loot.life, loot.max_life, felt, settings, insisting=insisting, spendable=spendable)
    supply = on_belt(loot)
    kappa = life_price(Supply(supply[PotionType.HEALING], supply[PotionType.REJUVENATION]), loot.max_life, settings)
    dear = life_factor(look, here, settings)
    kappa *= dear
    return allowance, spendable, kappa, dear


class Held(NamedTuple):
    """Holding here as priced (`Safety.hold`)."""

    harm: Harm  # to the next decision, with the losses and bar of the longer escape horizon
    ahead: Harm  # over that horizon
    seconds: float
    unstruck: float  # the strike gap (`Candidate.unstruck`)


@dataclass
class Pricing:
    """One look's candidates (`Safety.price`), what they are priced from and the forecast here."""

    facts: Facts
    look: Look
    seen: Observation
    settings: SafetySettings
    attack: Attack
    leg: Callable[[Point], Leg]
    jumps: Sequence[Jump]
    barred: Callable[[Point], bool] | None
    hands: Hands
    options: Callable[[Point], tuple[Step, ...]] | None
    battle_ready: bool
    teleport_hands: Hands
    goal: Goal
    clock: LookClock
    legs: list[Leg]  # the goal's way once asked (`bounded_way`)
    allowance: float
    kappa: float
    candidates: list[Candidate] = field(default_factory=list)
    # The forecast here (`__post_init__`)
    here: Point = field(init=False)
    field_: Field = field(init=False)
    swap_path: tuple[tuple[Point, float, Hands], ...] = field(init=False)
    swap_seconds: float = field(init=False)
    killed: dict[int, float] = field(init=False)  # what the strikes from here kill, and when
    worth: float = field(init=False)  # what casting from here takes over the HORIZON (stance `taken`)
    clear: float = field(init=False)  # holding's clear time (`clear_time`)
    remaining: float = field(init=False)  # local ETA stand-in, full routed leg supplied by navigation
    # A hostile bound to a summoner about (combat/threats `bound`: Baal's clone) dies with it: a strike on it is lost
    # while the summoner lives, so a stand that reaches only such is no strike (baal-sim.md fix 2)
    lost: dict[int, tuple[int, ...]] = field(init=False)
    landing: list[float] = field(default_factory=list, init=False)  # `landed_here`, once a look

    def __post_init__(self) -> None:
        seen, here = self.seen, self.seen.origin
        self.here = here
        self.field_ = Field(seen.blocked, self.barred)
        self.swap_path = ((here, SWAP_SECONDS, self.hands),) if self.hands != 'battle' else ()
        self.swap_seconds = SWAP_SECONDS if self.swap_path else 0.0
        self.killed = self.deaths_from(here, self.swap_seconds)
        self.worth, _ = taken(seen, self.attack, self.field_, here, 0.0)
        self.clear = self.clear_time()
        self.remaining = math.dist(here, self.goal.place) / 20.0
        self.lost = threats.bound({unit: foe.txt for unit, foe in seen.foes.items()})

    def deaths_from(self, spot: Point, after: float) -> dict[int, float]:
        """What the build's own strikes kill from `spot`, begun `after` seconds from now (stance `falls`); nothing
        with attack mode off."""
        if not self.facts.attacking:
            return {}
        return falls(self.seen, self.attack, self.field_, spot, after, after + FALL_HORIZON)

    def clear_time(self) -> float:
        """Seconds holding here takes to clear what is in reach, within 0.36 and 10: by the strikes' forecast where it
        kills all of it, else what is left of it at the pace here."""
        seen, killed = self.seen, self.killed
        in_reach = [u for u, f in seen.foes.items() if math.dist(self.here, f.at) <= self.attack.reach]
        if in_reach and all(u in killed for u in in_reach):
            # The forecast's own pace is quicker than the strikes' (`strike_spread`): its median stands for them.
            spread = self.settings.strike_spread
            clear = (max(killed[u] for u in in_reach) - self.swap_seconds) * spread[len(spread) // 2]
        else:
            clear = sum(seen.foes[u].left for u in in_reach) / max(self.worth / HORIZON, 1.0)
        return max(0.36, min(clear, 10.0))

    def landed_here(self) -> float:
        """What casting from here takes over the HORIZON as the casts land by distance (a firing stand's pace)."""
        if not self.landing:
            self.landing.append(taken(self.seen, self.attack, self.field_, self.here, 0.0, landed=True)[0])
        return self.landing[0]

    def holding(self, seen_: Look, deaths: dict[int, float] | None = None) -> tuple[Harm, Harm]:
        """Holding here priced on `seen_` (`deaths`: the forecast's by default): the work until the next decision,
        and the longer escape horizon."""
        deaths = self.killed if deaths is None else deaths
        settings, here, dwell = self.settings, self.here, min(self.settings.hold_dwell, self.clear)
        held = harm_path(seen_, (*self.swap_path, (here, dwell, 'battle')), settings, deaths)
        # Priced to the next decision, vetoed over the longer escape horizon: repeated short holds must not walk
        # the loop into a place every way out of is lethal.
        ahead = harm_path(seen_, (*self.swap_path, (here, max(settings.horizon, dwell), 'battle')), settings, deaths)
        return replace(held, losses=ahead.losses, barred=held.barred or ahead.barred), ahead

    def strikes_from(self, spot: Point) -> bool:
        return any(
            math.dist(spot, foe.at) <= self.attack.reach and self.field_.clear(spot, foe.at)
            for unit, foe in self.seen.foes.items()
            if unit not in self.lost
        )

    def feasible(self, c: Candidate) -> bool:
        return c.harm.worst <= self.allowance and veto(c.harm, self.look.life, self.settings) is None

    def move_price(
        self, step: Step, *, retreat=False, firing=False, why: str | None = None, dodge=False, keeps=False
    ) -> tuple[tuple, float]:
        """A move to `step` priced and added to the candidates: its path and seconds."""
        look, settings, here, hands = self.look, self.settings, self.here, self.hands
        gap = math.dist(here, step.spot)
        jump = next((j for j in self.jumps if j.skill == step.skill), None)
        seconds = jump.takes(gap) if jump else (0.31 if step.skill == TELEPORT else 0.36 + gap / 20.0)
        # The set a Teleport is cast with: the staff's (`travel`), or the battle set's where Teleport is the
        # character's own (Enigma): no swap there and back. Priced with both swaps, every Teleport to a firing spot
        # lost to the stand (172 of 172 on Catacombs 4, 2026-10-18: rca/2026-10-18/sluggish-engagement-findings.md)
        needs = self.teleport_hands if step.skill == TELEPORT else 'battle'
        swap = SWAP_SECONDS if needs != hands else 0.0
        seconds += swap + settings.move_overhead
        # A charged hop leaves quickly, a delayed jump or walk does not; the stand after the landing and the exposure
        # before the swap both count.
        dwell = settings.landing_dwell if step.skill is not None else 0.12
        path = []
        if swap:
            path.append((here, swap, hands))
        if step.skill is None:
            # The straight walk in three slices; the navigator checked its footing and line.
            for fraction in (0.0, 0.5, 1.0):
                point = (
                    here[0] + (step.spot[0] - here[0]) * fraction,
                    here[1] + (step.spot[1] - here[1]) * fraction,
                )
                path.append((point, (seconds - swap) / 3, needs))
        else:
            path.append((here, max(0.12, seconds - swap), needs))
        path.append((step.spot, dwell, needs))
        # Strikes begin at the landing, after the swap back to the battle set where the move took the other.
        landed = self.deaths_from(step.spot, SWAP_SECONDS if needs != 'battle' else 0.0)
        arrival = sum(part for _, part, _ in path[:-1])
        struck = {u: t + arrival for u, t in landed.items()}
        damage = harm_path(look, tuple(path), settings, struck)
        future = harm(look, step.spot, settings.horizon, needs, settings, landed)
        damage = replace(damage, barred=damage.barred or veto(future, look.life, settings))
        if needs == 'battle' and not self.battle_ready:
            damage = replace(damage, barred='battle weapon swap is unavailable')
        duration = math.dist(step.spot, self.goal.place) / 20.0
        if firing and not why:
            # A firing stand: holding's clear time at the stand's pace over its next HORIZON seconds against here's,
            # the move's own seconds lost inside them (stance `taken` from `seconds` on, as `camp` chose it), both as
            # the casts land by distance. Counted on top as well until 2026-10-14, a stand taking twice what here does
            # lost to holding in a safe fight (rca/2026-10-14/run-1932-findings.md §4, Fixes).
            there_worth, _ = taken(self.seen, self.attack, self.field_, step.spot, seconds, landed=True)
            duration += self.clear * self.landed_here() / max(there_worth, 1.0)
        else:
            duration += seconds
        if firing and why:
            # An escape's own seconds are in `seconds` already: its stand's pace is counted from its landing.
            there_worth, _ = taken(self.seen, self.attack, self.field_, step.spot, 0.0)
            duration += self.clear * self.worth / max(there_worth, 1.0)
        step = PricedStep(step.spot, step.skill, step.camp, needs, seconds)
        act = Move(step, self.goal, why or ('retreat' if retreat else FIRING if firing else ''), dodge=dodge)
        unstruck = seconds + (SWAP_SECONDS if needs != 'battle' else 0.0)  # the strike needs the battle set
        self.candidates.append(Candidate(act, duration, damage, retreat, unstruck, self.strikes_from(step.spot), keeps))
        return tuple(path), duration

    def burnt_out(self, path: tuple, seconds: float, priced: Harm) -> None:
        """The act asked for, begun once what lies on its way has burnt out (combat/threats `Lingering`: Diablo's
        fire wall, which outlives him; rca/2026-10-14/run-0305-findings.md §5.6): standing here meanwhile, then the
        same path, priced as one, at the time it has all gone and at half that. Or a step out of it first (the
        model's places). Offered when what lies on the ground is part of the act's price."""
        look, here = self.look, self.here
        if not look.ground or not any(unit == GROUND_UNIT and points > 0 for unit, points in priced.by):
            return
        gone = max(model.clears(lying) for model, lying in look.ground)
        for wait in sorted({gone / 2, gone}):
            if wait <= 0:
                continue
            later = harm_path(look, ((here, wait, self.hands), *path), self.settings)
            self.candidates.append(Candidate(NoWay(BURNING), wait + seconds, later, False, wait + seconds, False))
        places = [place for model, lying in look.ground for place in model.escapes(lying, here)]
        for point, why in places:
            if self.clock.late():
                break
            spot = footing(self.field_, here, point)
            if spot is not None and math.dist(here, spot) > 2:
                self.move_price(Step(spot), why=f'{STEPPING} {why}')

    def asked_for(self, base: Move | Hold | Operate | NoWay, fresh: bool, posted) -> None:
        """The act asked for: a use where it stands, a move (with shorter approaches when it is over the budget), or
        a running fight's advance."""
        facts = self.facts
        if isinstance(base, Operate):
            self.operate(base)
        elif isinstance(base, Move):
            self.approach(base)
        # A running fight also compares advancing once it is safe, not only the old in-reach branch.
        elif (
            isinstance(base, Hold)
            and not facts.there
            and not facts.settling
            and (fresh or (posted is not None and posted.runs))
            and (self.legs or not self.clock.late())  # past the look's time no way is asked: the next look's
        ):
            step = facts.way()
            if isinstance(step, Step):
                self.move_price(step)

    def operate(self, base: Operate) -> None:
        """A use: the hands walk to a drop or object (in three slices, as a leg's) and work it there for its dwell.
        No strike meanwhile, so nothing is credited as killed."""
        here, place = self.here, self.goal.place
        gap = math.dist(here, place)
        walk = WALK_LATENCY + gap / RUN_SPEED if gap > 2 else 0.0
        path: tuple = tuple(
            ((here[0] + (place[0] - here[0]) * f, here[1] + (place[1] - here[1]) * f), walk / 3, self.hands)
            for f in (0.0, 0.5, 1.0)
            if walk
        )
        path += ((place if walk else here, self.settings.use_dwell, self.hands),)
        damage = harm_path(self.look, path, self.settings)
        used = walk + self.settings.use_dwell
        self.candidates.append(Candidate(base, used, damage, False, used, self.strikes_from(place if walk else here)))
        self.burnt_out(path, used, damage)

    def approach(self, base: Move) -> None:
        """A move toward the goal; over the budget or vetoed, the navigator's earlier stands on the same approach
        too (a long leg may end inside a pack), before a retreat is conceded."""
        here = self.here
        path, seconds = self.move_price(base.step)
        self.burnt_out(path, seconds, self.candidates[-1].harm)
        last = self.candidates[-1]
        if last.harm.worst > self.allowance or veto(last.harm, self.look.life, self.settings):
            for fraction in (0.25, 0.5, 0.75):
                if self.clock.late():
                    break
                point = (
                    here[0] + (base.step.spot[0] - here[0]) * fraction,
                    here[1] + (base.step.spot[1] - here[1]) * fraction,
                )
                shorter = self.leg(point)
                if isinstance(shorter, Step) and math.dist(here, shorter.spot) > 2:
                    self.move_price(shorter)
                    last = self.candidates[-1]
                    assert isinstance(last.act, Move)
                    self.candidates[-1] = replace(last, act=replace(last.act, reason='safe approach'))

    def firing_stand(self, unsafe: bool, hold_harm: Harm) -> None:
        """Camp's stand (stance `camp`, with the old crowd and keep-away floors) priced beside holding, so the sweep
        never moves outside the safety constraint: when nothing is safe, near a hostile with no clear line to strike
        it (the act that keeps the strike gap, I2), or when holding takes over half the budget."""
        facts = self.facts
        lineless = facts.near and facts.attacking and not facts.in_reach
        if not self.clock.late() and (
            unsafe or lineless or (facts.in_reach and hold_harm.worst > self.allowance * 0.5)
        ):
            found = camp(self.seen, self.attack, barred=self.barred, jumps=self.jumps)
            if found is not None:
                self.move_price(Step.to(found), firing=True)

    def retreat_to(self, point: Point, asked: list[Point], at: Point | None = None) -> None:
        """The navigator's ways toward `point`, each a retreat (a real leg: an open point may be behind a wall), not
        within ESCAPE_SAME of one `asked` already. `at`: the hostile a retreat that keeps the fight stays within the
        strike's reach and line of (`keeper`)."""
        here = self.here
        offered = self.options(point) if self.options is not None else (self.leg(point),)
        for step in offered:
            if (
                isinstance(step, Step)
                and math.dist(here, step.spot) > 2
                and (at is None or (math.dist(step.spot, at) <= self.attack.reach and self.field_.clear(step.spot, at)))
                and all(math.dist(step.spot, other) >= ESCAPE_SAME for other in asked)
            ):
                asked.append(step.spot)
                self.move_price(step, retreat=True, keeps=at is not None)

    def obstructed(self) -> Candidate | None:
        """The first move or use toward the goal over the budget (its blockers bar the way: `Safety.blocked_by`)."""
        return next(
            (
                c
                for c in self.candidates
                if not c.retreat and isinstance(c.act, (Move, Operate)) and c.harm.worst > self.allowance
            ),
            None,
        )

    def record(
        self,
        chosen: Act,
        *,
        dear: float,
        insisting: float,
        spendable: float | None,
        blocked_by: tuple[int, ...],
        draws: dict[int, DrawPrice] | None,
    ) -> dict:
        """The look's decision as `Safety.decision` keeps it."""
        facts, goal, look, here, hands = self.facts, self.goal, self.look, self.here, self.hands
        settings, allowance = self.settings, self.allowance
        return {
            'looked_at': facts.now,
            'goal': goal.label,
            'goal_place': goal.place,
            'life': look.life,
            'hands': hands,
            'budget': round(allowance, 1),
            'dear': dear,
            'floor_raised': insisting > 0,
            'stock_share': round(stock_share(settings, spendable), 3),
            'chosen': type(chosen).__name__,
            'chosen_place': chosen.step.spot if isinstance(chosen, Move) else here,
            'reason': getattr(chosen, 'reason', ''),
            'blocked_by': blocked_by,
            'killed': {unit: round(at, 2) for unit, at in sorted(self.killed.items(), key=lambda r: r[1])[:8]},
            'draws': {unit: round(price.worth, 2) for unit, price in (draws or {}).items()},
            'late': self.clock.late(),
            'ms': self.clock.ms(),
            'candidates': [
                {
                    'act': type(c.act).__name__,
                    'why': c.act.reason if isinstance(c.act, Move) else '',
                    'place': c.act.step.spot if isinstance(c.act, Move) else here,
                    'skill': c.act.step.skill if isinstance(c.act, Move) else None,
                    'hands': c.act.step.needs if isinstance(c.act, Move) else hands,
                    'T': round(c.seconds, 3) if math.isfinite(c.seconds) else None,
                    'H': round(c.harm.mean, 1),
                    'worst': round(c.harm.worst, 1),
                    'veto': veto(c.harm, look.life, settings),
                    'retreat': c.retreat,
                    'dodge': isinstance(c.act, Move) and c.act.dodge,
                    'keeps': c.keeps,
                    'contributors': c.harm.by,
                    'stand_ins': c.harm.stand_ins,
                    'blocked_by': blockers(c.harm, allowance),
                }
                for c in self.candidates
            ],
        }


@dataclass
class Safety:
    profiles: dict[str, Protection] = field(default_factory=dict)
    identity: tuple[str, int] | None = None
    blocked_goal: tuple | None = None
    blocked_since: float = 0.0
    last_press: float = -math.inf
    first_press: float = -math.inf
    decision: dict = field(default_factory=dict)
    blocked_by: tuple[int, ...] = ()
    trail: deque = field(default_factory=lambda: deque(maxlen=TRAIL_POINTS))  # the way the character came
    # Seconds of the look's own clock (time.perf_counter in the game) a decision may take before it settles for
    # the best found so far; None: no clock, the caps alone bound it (the arena: a play the same for a seed).
    timer: Callable[[], float] | None = None
    # Each hostile's mode as last seen and the clock at which it was first seen in it (unit -> (mode, since)).
    modes: dict[int, tuple[int, float]] = field(default_factory=dict)
    # The build's draw as the last look was given it, and the companions it would send then: (index into the look's
    # companions, class). Empty: it cannot be cast (not on a key, or no companion of the kind it needs).
    draw: Draw | None = None
    sendable: tuple[tuple[int, int], ...] = ()
    # What the draw was found worth onto each hostile weighed at the last look of a fight (`weigh`), and that look's
    # clock; None: not weighed (no draw, no hold to price).
    draws: dict[int, DrawPrice] | None = None
    drawn_at: float = -math.inf
    # The casters of what lingers on the ground (combat/threats `Lingering`) last seen alive: unit -> (its model, where
    # it stood, the clock then). Their missiles are read for the model's `lasts` seconds after, its death or not.
    casters: dict[int, tuple[threats.Lingering, Point, float]] = field(default_factory=dict)
    # What lies on the ground as first read: (class, x and y in half units) -> the clock it was first read at.
    lying_since: dict[tuple[int, int, int], float] = field(default_factory=dict)
    # The place a step across a read model's act was chosen from, by that hostile: unit -> (its mode as `modes` had
    # it then, the place). Not offered again while the hostile is in that mode: the same act under way (Diablo's
    # stream re-aims at where the character goes, so back is no way out: rca/2026-10-14/run-0305-findings.md §5.2).
    stepped: dict[int, tuple[tuple[int, float] | None, Point]] = field(default_factory=dict)
    # The better place the fight's look offered last (`offer`) and the clock then; None: none.
    stand: tuple[Step, float] | None = None
    # The look's clock when a look over its time was last said (`over`), and how many have been since
    over_said: float = -math.inf
    over_since: int = 0

    def offer(self, step: Step | None, now: float) -> None:
        """The fight's look found `step` the better place to fight from (None: it stands well): priced as a firing
        stand at the looks of the next STAND_FRESH seconds, in a level run's or a pressed fight (`price`)."""
        self.stand = (step, now) if step is not None else None

    def look(
        self,
        world: World,
        loot: Loot,
        hands: str,
        blocked=None,
        shield: Shield | None = None,
        settings: SafetySettings | None = None,
        *,
        now: float | None = None,
        flights: Flights | None = None,
        draw: Draw | None = None,
    ) -> Look:
        """The look the arbiter prices. `now` (the run's clock) dates each hostile's mode; `flights` reads the
        missiles in flight of the classes the read models of the hostiles about ask for (combat/threats), and
        only when such a hostile is about: the look stays light otherwise. `draw`: the build's (`weigh`), with the
        companions it would send noted from the same world."""
        player = world.player
        assert player is not None
        identity = (world.game_name, player.unit_id)
        if identity != self.identity:
            self.profiles.clear()
            self.blocked_goal = None
            self.identity = identity
            self.trail.clear()
            self.modes.clear()
            self.casters.clear()
            self.lying_since.clear()
            self.stepped.clear()
            self.stand = None
        here = (player.x, player.y)
        if not self.trail or math.dist(self.trail[-1], here) >= TRAIL_STEP:
            self.trail.append(here)
        stats = dict(loot.stats)
        if stats:
            self.profiles[hands] = Protection(
                resists=tuple(
                    (kind, stats.get(stat, 0) - (HELL_PENALTY if kind not in ('physical', 'magic') else 0))
                    for stat, kind in RESISTS
                ),
                defence=stats.get(31, 0),
                level=stats.get(12, 94),
                block=0.0,  # raw stat 20 is not final block; shield/class/dex are not all observed
                flat=(('physical', stats.get(34, 0)),),
            )
        # Unknown set: no resistance, no block. Never copy the battle set onto
        # the travel set. An observed set is replaced at each look. The build's
        # guard is credited only while the game shows it up, with the share of
        # its pool `guard_left` names (the client is not told of its fall).
        battle = self.profiles.get('battle', Protection())
        travel = self.profiles.get('travel', Protection())
        if shield is not None and shield.shown(world):
            left = shield.rule.most * (settings or SafetySettings()).guard_left / 100
            battle = replace(battle, guard=shield.rule, pool=left)
            travel = replace(travel, guard=shield.rule, pool=left)
        hostile = [m for m in world.monsters if not m.ally and m.owner == NO_OWNER and m.mode not in (0, 12)]
        modes: dict[int, tuple[int, float]] = {}
        for m in hostile:
            known = self.modes.get(m.unit_id)
            modes[m.unit_id] = known if known is not None and known[0] == m.mode else (m.mode, now or 0.0)
        self.modes = modes
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        self.draw = draw
        self.sendable = ()
        if draw is not None and draw.skill in world.slots:
            self.sendable = tuple((i, m.txt_id) for i, m in enumerate(companions) if draw.sends(world, m))
        clock = now or 0.0
        for m in hostile:
            model = threats.of(m.txt_id)
            if model is not None and model.lingering is not None:
                self.casters[m.unit_id] = (model.lingering, (m.x, m.y), clock)
        self.casters = {unit: kept for unit, kept in self.casters.items() if clock - kept[2] <= kept[0].lasts}
        lingering = {model for model, _, _ in self.casters.values()}
        kinds = threats.missiles({m.txt_id for m in hostile}) | frozenset(
            kind for model in lingering for kind in model.missiles
        )
        read: Sequence[tuple[int, int, float, float]] | None = None
        if flights is not None and kinds:
            try:
                read = flights(kinds)
            except OSError, ValueError:
                read = None
        missiles = in_flight(hostile, None, read) if read is not None else ()
        return Look(
            tuple(
                Hostile(
                    m.unit_id,
                    m.txt_id,
                    (m.x, m.y),
                    m.flags,
                    m.modifiers,
                    m.tier,
                    active=m.mode != 1,
                    life=m.life / m.max_life if m.max_life else 1.0,
                    mode=m.mode,
                    mode_frames=round((now - modes[m.unit_id][1]) * 25) if now is not None else 0,
                )
                for m in hostile
            ),
            tuple((m.x, m.y) for m in companions),
            battle,
            travel,
            float(loot.life),
            blocked,
            missiles=missiles,
            ground=self.lying(lingering, read or (), clock),
        )

    def lying(
        self, lingering: set[threats.Lingering], read: Sequence[tuple[int, int, float, float]], clock: float
    ) -> tuple[tuple[threats.Lingering, tuple[threats.Lying, ...]], ...]:
        """What lies on the ground by its model (`Look.ground`), from the missiles the look read: each with the place
        its caster stood at when last seen (a maker's way) and the seconds it has been read (a flame's age)."""
        if not lingering:
            self.lying_since.clear()
            return ()
        found: dict[threats.Lingering, list[threats.Lying]] = {}
        since: dict[tuple[int, int, int], float] = {}
        for owner, kind, x, y in read:
            model = next((model for model in lingering if kind in model.missiles), None)
            if model is None:
                continue
            key = (kind, round(x * 2), round(y * 2))
            since[key] = self.lying_since.get(key, clock)
            caster = self.casters.get(owner)
            found.setdefault(model, []).append(
                model.read(kind, (x, y), caster[1] if caster is not None else None, clock - since[key])
            )
        self.lying_since = since
        return tuple((model, tuple(items)) for model, items in found.items())

    def price(
        self,
        facts: Facts,
        posted,
        look: Look,
        loot: Loot,
        felt: Pressure,
        settings: SafetySettings,
        seen: Observation,
        attack: Attack,
        leg: Callable[[Point], Leg],
        jumps=(),
        barred=None,
        hands: Hands = 'battle',
        options: Callable[[Point], tuple[Step, ...]] | None = None,
        battle_ready: bool = True,
        teleport_hands: Hands = 'travel',
    ) -> Facts:
        """Assemble prices without selecting a goal; the decision is pursuit.decide's.

        The candidates are priced in the order they matter: the act asked for
        and holding, then shorter approaches and the firing stand, then the
        escapes the threat's geometry gives, then the plain rays. The rays
        and every tier after the first is cut short once the look's deadline
        has passed (`timer`): the act asked for and holding are always priced,
        and with nothing safe among them two escapes still are, so the answer
        is the best found in time."""
        clock = LookClock(self.timer, settings.look_seconds)
        until = clock.began + way_seconds(seen.origin, [m.at for m in look.hostiles], settings.look_seconds)
        facts, legs = bounded_way(facts, clock, until)
        base = decide(facts, posted)
        clock.lap("the goal's way")
        self.blocked_by = ()
        if not isinstance(base, (Move, Hold, Operate, NoWay)):
            return facts
        goal = facts.goal
        if goal is None:
            # A stand-alone fight still has a safety constraint and retreat candidates.
            from inventory_tracking.macros.travel import STANDING

            goal = Goal('the fight', seen.origin, 'fight', attack.reach, STANDING)
        key = (goal.do, goal.unit, goal.route, goal.stage, goal.place)
        fresh = posted is not None and posted.fresh(facts.now)
        # A fresh press asks for the goal; so does a level run at every look (`run_insists`).
        running = posted is not None and posted.runs and settings.run_insists and not posted.spent
        asking = fresh or running
        insisting = self.insisting(facts.now, posted, key, asking, running)
        allowance, spendable, kappa, dear = life_budget(loot, felt, settings, look, seen.origin, insisting)
        p = Pricing(
            facts, look, seen, settings, attack, leg, jumps, barred, hands, options, battle_ready, teleport_hands,
            goal, clock, legs, allowance, kappa,
        )  # fmt: skip
        clock.lap('the forecast')
        held = self.hold(p)
        clock.lap('holding')
        # What an escape could save (holding's life at the look's price) against the least it costs (a walk's start
        # and overhead; the swap where the set in hand is not the battle set): below it no escape is worth pricing.
        saving = kappa * held.harm.mean
        least = settings.move_overhead + WALK_LATENCY + (SWAP_SECONDS if hands != 'battle' else 0.0)
        waiting = isinstance(base, NoWay)
        if waiting and held.harm.worst <= allowance and veto(held.harm, look.life, settings) is None:
            if saving <= least:
                # Waiting for a summoned pack or a boss to appear is no failed safety constraint: the goal and its
                # reason are kept.
                return facts
            # Waiting priced as an act (staying, the goal's reason kept) when an escape could be worth more.
            p.candidates.append(Candidate(base, held.seconds + p.remaining, held.harm, False, 0.0, False))
        if facts.in_reach and facts.attacking and (settings.fight_through or not fresh):
            hold = Candidate(Hold(facts.goal), held.seconds + p.remaining, held.harm, False, held.unstruck, True)
            p.candidates.append(hold)
        p.asked_for(base, fresh, posted)
        clock.lap('the act asked for')
        unsafe = not any(p.feasible(c) for c in p.candidates)
        p.firing_stand(unsafe, held.harm)
        clock.lap('the firing stand')
        self.offered_stand(p, fresh, posted)
        if not unsafe and ((facts.in_reach and facts.attacking) or waiting) and saving > least:
            self.stepping(p, held.harm, saving, least)
        clock.lap('the escapes')
        if unsafe:
            self.retreats(p, held)
        clock.lap('the retreats')
        priced = replace(
            facts,
            candidates=tuple(p.candidates),
            priced=True,
            budget=allowance,
            life=look.life,
            kappa=kappa,
            safety=settings,
        )
        obstructed = p.obstructed()
        if obstructed is not None:
            self.blocked_by = blockers(obstructed.harm, allowance)
        chosen = decide(priced, posted)
        self.remember(chosen, look, p.here, asking, key, facts.now, posted)
        self.decision = p.record(
            chosen, dear=dear, insisting=insisting, spendable=spendable, blocked_by=self.blocked_by, draws=self.draws
        )
        if clock.timer is not None:
            clock.lap('the choice')
            self.over(facts.now, clock.timer() - clock.began, settings.look_seconds, clock.laps, chosen)
        return priced

    def insisting(self, now: float, posted, key: tuple, asking: bool, running: bool) -> float:
        """Seconds the goal `key` has been asked for and blocked without a gap of 0.7 s (`budget`'s `insisting`); 0
        when not."""
        if (
            asking
            and key == self.blocked_goal
            and now - self.last_press < 0.7
            and (running or posted.pressed_at > self.first_press)
        ):
            return now - self.blocked_since
        return 0.0

    def hold(self, p: Pricing) -> Held:
        """Holding here; in a fight with the build's draw (`weigh`) where it pays: the companions sent onto the hostile
        it pays most on, its cast in the hold's time and its strike gap (T + kappa x H over its span), so the hold
        with it competes with the escapes and the retreat as one act."""
        facts, look = p.facts, p.look
        hold_harm, future = p.holding(look)
        hold_seconds = p.clear + p.swap_seconds
        hold_unstruck = p.swap_seconds
        self.draws, self.drawn_at = (None if self.draw is None else {}), facts.now
        if facts.in_reach and facts.attacking:
            pressed = hold_harm.worst > p.allowance
            drawn = self.weigh(
                look, p.seen, p.settings, p.kappa, p.here, p.clear, p.swap_path, p.killed, pressed=pressed
            )
            if drawn is not None:
                target = next(m.at for m in look.hostiles if m.unit == drawn.unit)
                assert self.draw is not None
                sent = tuple(index for index, _ in self.sendable)
                later = {unit: at + drawn.cost for unit, at in p.killed.items()}  # no strike during the cast
                drawn_look = sent_onto(look, sent, target, self.draw.reach, self.draw.beside, self.draw.pack)
                hold_harm, future = p.holding(drawn_look, later)
                hold_seconds += drawn.cost - drawn.gain
                hold_unstruck += drawn.cost
        if not p.battle_ready:
            hold_harm = replace(hold_harm, barred='battle weapon swap is unavailable')
        return Held(hold_harm, future, hold_seconds, hold_unstruck)

    def offered_stand(self, p: Pricing, fresh: bool, posted) -> None:
        """In a running fight (a level run's or a press's), the better place its own look found (`offer`): a closer
        stand whose casts take more (stance `taken` counts what lands from there), priced as a firing stand against
        holding by T + kappa x H and held to the commitment (pursuit.py `arbitrate`); its harm decides how near a
        dangerous pack it goes."""
        facts, offered = p.facts, self.stand
        if (
            offered is not None
            and 0.0 <= facts.now - offered[1] <= STAND_FRESH
            and facts.in_reach
            and facts.attacking
            and (fresh or (posted is not None and posted.runs))
            and math.dist(p.here, offered[0].spot) > 2
            and not any(math.dist(offered[0].spot, foe.at) < KEEP_AWAY for foe in p.seen.foes.values())
        ):
            p.move_price(offered[0], firing=True)

    def stepping(self, p: Pricing, hold_harm: Harm, saving: float, least: float) -> None:
        """Escapes while something is safe, priced whenever what one could save (`saving`) may exceed the least it
        costs (`least` and the walk there): stands the strike goes on from, competing with holding or waiting by
        T + kappa x H (STEPPING: the life saved is why, not a better strike pace). The read models' places first (an
        act under way, combat/threats), then the threat's geometry where a strike can be made from; ESCAPES_MOST."""
        here, count = p.here, 0
        for point, why, dodge in self.offered(here, p.look, hold_harm):
            if count >= ESCAPES_MOST or p.clock.late():
                break
            if why == AWAY and not p.strikes_from(point):
                continue
            if saving <= least + math.dist(here, point) / RUN_SPEED:
                continue
            spot = footing(p.field_, here, point)
            if spot is None:
                continue
            count += 1
            p.move_price(Step(spot), firing=True, why=f'{STEPPING} {why}', dodge=dodge)

    def retreats(self, p: Pricing, held: Held) -> None:
        """Nothing is safe: the retreats, each a real leg (equal harm prefers less time). First within the strike's
        reach of what ends the harm (`keeper`, the nearest first: the fight goes on, pursuit.py `arbitrate` prefers
        one that fits the budget), then the escapes (`offered`), then the plain rays when no retreat fits; last,
        holding (never past the lethal veto) or, out of reach, standing idle (WAITING)."""
        facts, look, seen, settings, here = p.facts, p.look, p.seen, p.settings, p.here
        asked: list[Point] = []
        threat = held.harm if held.harm.by else held.ahead
        ender = keeper(look, seen, threat)
        if ender is not None:
            at = seen.foes[ender].at
            for index, point in enumerate(keeping(here, at, p.attack.reach)):
                if index >= 2 and p.clock.late():
                    break
                p.retreat_to(point, asked, at)
        places = [point for point, _, _ in self.offered(here, look, threat)]
        for index, point in enumerate(places[:ESCAPES_MOST]):
            if index >= 2 and p.clock.late():
                break
            p.retreat_to(point, asked)
        if not places or not any(p.feasible(c) for c in p.candidates if c.retreat):
            for i in range(RAYS):
                if p.clock.late():
                    break
                angle = i * math.tau / RAYS
                p.retreat_to((here[0] + 22 * math.cos(angle), here[1] + 22 * math.sin(angle)), asked)
        # Fighting in place may be the least-harm escape if it removes the threats sooner than a walk.
        if facts.in_reach and facts.attacking and veto(held.harm, look.life, settings) is None:
            p.candidates.append(Candidate(Hold(facts.goal), held.seconds, held.harm, True, held.unstruck, True))
        elif not (facts.in_reach and facts.attacking):
            # Standing, striking nothing: chosen only when it is the least harm of all.
            idle = harm(look, here, settings.horizon, p.hands, settings)
            p.candidates.append(Candidate(NoWay(WAITING), math.inf, idle, True))

    def remember(self, chosen: Act, look: Look, here: Point, asking: bool, key: tuple, now: float, posted) -> None:
        """What the choice leaves for the next looks: the read models' acts stepped across from here (`stepped`), and
        the goal asked for blocked while the choice is neither a move toward it nor a use (`insisting`)."""
        if isinstance(chosen, Move) and chosen.reason.startswith(STEPPING):
            for m in look.hostiles:
                if threats.of(m.txt) is not None:
                    self.stepped[m.unit] = (self.modes.get(m.unit), here)
        blocked_goal = asking and (
            not isinstance(chosen, (Move, Operate))
            or (isinstance(chosen, Move) and chosen.reason.startswith('retreating'))
        )
        if blocked_goal:
            if self.blocked_goal != key or now - self.last_press >= 0.7:
                self.blocked_since = now
                self.first_press = posted.pressed_at
            self.blocked_goal = key
            self.last_press = now
        else:
            self.blocked_goal = None

    def over(self, now: float, took: float, budget: float, laps: dict[str, float], chosen) -> None:
        """A look that took more than OVER_BUDGET times its time (`SafetySettings.look_seconds`) is said with the
        stages that took the most of it (`Macro: look: 412 ms, over budget (80 ms): the goal's way 388 ms; ... ->
        Move`), at most once in SAID_EVERY seconds (`now`, the look's clock), with how many more were since."""
        if took <= budget * OVER_BUDGET:
            return
        if now - self.over_said < SAID_EVERY:
            self.over_since += 1
            return
        stages = sorted(laps.items(), key=lambda row: -row[1])
        most = '; '.join(f'{stage} {seconds * 1000:.0f} ms' for stage, seconds in stages[:3])
        more = f' ({self.over_since} more since)' if self.over_since else ''
        LOG.info(
            'Macro: look: %.0f ms, over budget (%.0f ms): %s -> %s%s',
            took * 1000, budget * 1000, most, type(chosen).__name__, more,
        )  # fmt: skip
        self.over_said, self.over_since = now, 0

    def weigh(
        self,
        look: Look,
        seen: Observation,
        settings: SafetySettings,
        kappa: float,
        here: Point,
        clear: float,
        lead: tuple[tuple[Point, float, Hands], ...],
        killed: dict[int, float],
        *,
        pressed: bool = False,
    ) -> DrawPrice | None:
        """The build's draw (macros/build.py `Draw`) weighed at this look of a fight, onto the hostiles holding's harm
        comes most from (DRAW_TARGETS), the one it gains most on and the nearest leaders (DRAW_LEADERS): the life it
        saves over its span, at the look's price of life, plus what it gains of the fight, less the cast; kept by unit
        (`draws`, the buff row reads them: `priced`). The best of them when it pays, else None. Not onto a hostile the
        companions hold already or one the draw does not fit; with no companion it would send, nothing is weighed.
        `pressed`: holding without it is over the life budget (kept with each price).

        The life it saves is what the takes measured it to turn (rca/2026-10-14/death-mark-engage.md §4): the share
        `Draw.turns` of the blows the pack within `Draw.pack` of the hostile would deal the character, priced with no
        companion to take any (the control's share at the character is in `turns`; by the nearest body alone, two
        demons standing on the character took half its attackers and a draw "freed" them: De Seis's seal at -40
        life, 02:23:00 on 2026-10-14), from the companions' landing (`arrives`) on; less the cast's own exposure, as
        no strike is cast meanwhile and what it kills dies that much later."""
        draw = self.draw
        if draw is None or not self.sendable:
            return None
        sent = tuple(index for index, _ in self.sendable)
        # The companions' blows count as gained only from those idle now (no hostile within their landing distance and
        # DRAW_HELD): one already striking a hostile of the fight clears it as fast where it is.
        engaged = draw.beside + DRAW_HELD
        classes = tuple(
            txt for index, txt in self.sendable
            if all(math.dist(look.companions[index], m.at) > engaged for m in look.hostiles)
        )  # fmt: skip
        span = min(draw.lasts, max(settings.horizon, clear))
        path = (*lead, (here, span, 'battle'))
        alive = {m.unit: m.at for m in look.hostiles if m.unit in seen.foes and draw.fits(seen, m.unit)}
        if not alive:
            return None
        base = harm_path(look, path, settings, killed)
        gains = {unit: draw.gain(seen, unit, classes) for unit in alive}
        units = [unit for unit, _ in base.by if unit in alive][:DRAW_TARGETS]
        best_gain = max(gains, key=lambda unit: (gains[unit], -unit))
        if best_gain not in units:
            units.append(best_gain)
        leaders = sorted((u for u in alive if seen.foes[u].elite), key=lambda u: (math.dist(here, alive[u]), u))
        units += [unit for unit in leaders if unit not in units][:DRAW_LEADERS]
        later = {other: at + draw.seconds for other, at in killed.items()}  # no strike during the cast
        exposed = max(0.0, harm_path(look, path, settings, later).mean - base.mean)
        alone = dict(harm_path(replace(look, companions=()), path, settings, later).by) if draw.turns > 0 else {}
        landed = min(1.0, draw.arrives / span) if span > 0 else 1.0
        prices = self.draws if self.draws is not None else {}
        for unit in units:
            target = alive[unit]
            if all(math.dist(look.companions[index], target) <= engaged for index in sent):
                continue  # held already: a cast changes nothing of where they stand
            turned = sum(alone.get(m.unit, 0.0) for m in look.hostiles if math.dist(m.at, target) <= draw.pack)
            life = draw.turns * turned * (1.0 - landed) - exposed
            prices[unit] = DrawPrice(unit, life, kappa * life, gains[unit], draw.seconds, span, pressed)
        self.draws = prices
        best = max(prices.values(), key=lambda price: (price.worth, -price.unit), default=None)
        return best if best is not None and best.worth > 0 else None

    def priced(self, now: float) -> dict[int, DrawPrice] | None:
        """The draw's prices of the last look of a fight while fresh (DRAW_FRESH), for the buff row that casts it
        (macros/build.py `BuffFacts.draws`); None: none is."""
        if self.draws is None or not 0.0 <= now - self.drawn_at <= DRAW_FRESH:
            return None
        return self.draws

    def offered(self, here: Point, look: Look, priced) -> list[tuple[Point, str, bool]]:
        """The places an escape may go to, with why and whether it is a dodge (`Move.dodge`): those the read models
        of the hostiles offer for their acts under way (combat/threats `Threat.escapes`), a dodge while the act's
        missiles are in flight, then the threat's geometry (`escapes`); two nearer than ESCAPE_SAME are one."""
        found: list[tuple[Point, str, bool]] = []
        for m in look.hostiles:
            model = threats.of(m.txt)
            if model is not None:
                flying, kinds = threats.flying_of(look.missiles, m.unit)
                places = model.escapes(threats.Acting(m.at, m.mode, m.mode_frames, flying, kinds), here)
                left = self.stepped.get(m.unit)
                if left is not None and left[0] == self.modes.get(m.unit):
                    places = tuple((point, why) for point, why in places if math.dist(point, left[1]) >= ESCAPE_SAME)
                found.extend((point, why, bool(flying)) for point, why in places)
        for lingering, lying in look.ground:
            found.extend((point, why, False) for point, why in lingering.escapes(lying, here))
        found.extend((point, AWAY, False) for point in self.escapes(here, look, priced))
        unique: list[tuple[Point, str, bool]] = []
        for point, why, dodge in found:
            if all(math.dist(point, other) >= ESCAPE_SAME for other, _, _ in unique):
                unique.append((point, why, dodge))
        return unique

    def escapes(self, here: Point, look: Look, priced) -> list[Point]:
        """Places to escape to, from the threat's geometry, the likeliest first: away from the threat's centre
        (each hostile weighted by its share of the harm where the character stands, else by nearness), near and
        far and turned either side; the last point of the way the character came that is no nearer that centre;
        a step behind each companion, away from it (a monster goes for the nearest of them). None without a
        hostile about: the caller asks the plain rays."""
        weights = dict(priced.by) if priced.by else {}
        about = [(m.at, weights.get(m.unit, 0.0)) for m in look.hostiles]
        if not about:
            return []
        if not any(w > 0 for _, w in about):
            about = [(at, 1.0 / max(math.dist(here, at), 1.0)) for at, _ in about]
        total = sum(w for _, w in about)
        centre = (sum(at[0] * w for at, w in about) / total, sum(at[1] * w for at, w in about) / total)
        away = math.dist(here, centre)
        found: list[Point] = []
        if away > 1e-6:
            angle = math.atan2(here[1] - centre[1], here[0] - centre[0])
            for turn, reach in ((0.0, ESCAPE_REACH[1]), (0.0, ESCAPE_REACH[0]), (ESCAPE_TURN, ESCAPE_REACH[1]),
                                (-ESCAPE_TURN, ESCAPE_REACH[1])):  # fmt: skip
                found.append((here[0] + reach * math.cos(angle + turn), here[1] + reach * math.sin(angle + turn)))
        back = next(
            (
                point
                for point in reversed(self.trail)
                if math.dist(point, here) >= ESCAPE_REACH[0] and math.dist(point, centre) >= away
            ),
            None,
        )
        if back is not None:
            found.insert(1, back)
        for companion in sorted(look.companions, key=lambda at: math.dist(here, at)):
            gap = math.dist(companion, centre)
            if gap > 1e-6 and math.dist(companion, here) > 2:
                found.append(
                    (
                        companion[0] + (companion[0] - centre[0]) / gap * BEHIND,
                        companion[1] + (companion[1] - centre[1]) / gap * BEHIND,
                    )
                )
                break
        unique: list[Point] = []
        for point in found:
            if all(math.dist(point, other) >= ESCAPE_SAME for other in unique):
                unique.append(point)
        return unique

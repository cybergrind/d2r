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

from inventory_tracking.combat import threats
from inventory_tracking.combat.harm import (
    Hands,
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
    veto,
)
from inventory_tracking.combat.policy import Observation, Point
from inventory_tracking.combat.stance import HORIZON, RUN_SPEED, WALK_LATENCY, Field, camp, falls, taken
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.macros.build import Attack, Leg, NoWay, PricedStep, Shield, Step
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.pursuit import Candidate, Facts, Hold, Move, Operate, decide
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.world import NO_OWNER, Loot, World
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
FIRING = 'firing spot'  # the reason of a move to a stand the strike is made from (pursuit.py's commitment)
# The reason of an escape priced against holding (not a retreat): a stand the strike goes on from, taken for the
# life it saves, so not held to the firing stand's commitment (pursuit.py), which is against changing stands for
# a strike pace barely better. `Macro: pursuit: stepping across ...` in the log.
STEPPING = 'stepping'
AWAY = 'away from the threat'  # why a place of the threat's geometry is offered
# A missile the look reads for a read model (combat/threats): (owner unit, missile class, x, y).
Flights = Callable[[frozenset[int]], Sequence[tuple[int, int, float, float]]]


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


def in_flight(hostile: Sequence, flights: Flights | None) -> tuple[tuple[int, Point, float], ...]:
    """The missiles in flight the read models of `hostile` ask for (combat/threats `missiles`), each with its
    owner and its heading: a missile flies straight from where its owner stood, so the heading is the line from
    the owner to it (Diablo's stand while he casts: rca/2026-10-13/diablo.md, 0.5 degrees in the takes). Nothing is
    read when no such hostile is about, or when the reading fails (the price then has the mode alone)."""
    owners = {m.unit_id: (m.x, m.y) for m in hostile if threats.of(m.txt_id) is not None}
    if not owners or flights is None:
        return ()
    try:
        read = flights(threats.missiles({m.txt_id for m in hostile}))
    except OSError, ValueError:
        return ()
    found = []
    for owner, _txt, x, y in read:
        at = owners.get(owner)
        if at is not None and (x, y) != at:
            found.append((owner, (x, y), math.atan2(y - at[1], x - at[0])))
    return tuple(found)


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
    ) -> Look:
        """The look the arbiter prices. `now` (the run's clock) dates each hostile's mode; `flights` reads the
        missiles in flight of the classes the read models of the hostiles about ask for (combat/threats), and
        only when such a hostile is about: the look stays light otherwise."""
        player = world.player
        assert player is not None
        identity = (world.game_name, player.unit_id)
        if identity != self.identity:
            self.profiles.clear()
            self.blocked_goal = None
            self.identity = identity
            self.trail.clear()
            self.modes.clear()
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
            tuple((m.x, m.y) for m in world.monsters if m.ally or m.owner != NO_OWNER),
            battle,
            travel,
            float(loot.life),
            blocked,
            missiles=in_flight(hostile, flights),
        )

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
    ) -> Facts:
        """Assemble prices without selecting a goal; the decision is pursuit.decide's.

        The candidates are priced in the order they matter: the act asked for
        and holding, then shorter approaches and the firing stand, then the
        escapes the threat's geometry gives, then the plain rays. The rays
        and every tier after the first is cut short once the look's deadline
        has passed (`timer`): the act asked for and holding are always priced,
        and with nothing safe among them two escapes still are, so the answer
        is the best found in time."""
        timer = self.timer
        began = timer() if timer is not None else 0.0
        deadline = began + settings.look_seconds if timer is not None else math.inf

        def late() -> bool:
            return timer is not None and timer() >= deadline

        base = decide(facts, posted)
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
        insisting = 0.0
        if (
            asking
            and key == self.blocked_goal
            and facts.now - self.last_press < 0.7
            and (running or posted.pressed_at > self.first_press)
        ):
            insisting = facts.now - self.blocked_since
        allowance = budget(loot.life, loot.max_life, felt, settings, insisting=insisting)
        supply = on_belt(loot)
        kappa = life_price(Supply(supply[PotionType.HEALING], supply[PotionType.REJUVENATION]), loot.max_life, settings)
        here = seen.origin
        # The life price by fight (`SafetySettings.dear`): dearer while a dear class is in the fight.
        dear = life_factor(look, here, settings)
        kappa *= dear
        field_ = Field(seen.blocked, barred)
        striking = facts.attacking  # attack mode on: what is in reach of a stand is struck from it

        def deaths_from(spot: Point, after: float) -> dict[int, float]:
            """What the build's own strikes kill from `spot`, begun `after` seconds from now (stance `falls`)."""
            if not striking:
                return {}
            return falls(seen, attack, field_, spot, after, after + FALL_HORIZON)

        swap_path = ((here, SWAP_SECONDS, hands),) if hands != 'battle' else ()
        swap_seconds = SWAP_SECONDS if swap_path else 0.0
        killed = deaths_from(here, swap_seconds)
        worth, _ = taken(seen, attack, field_, here, 0.0)
        rate = worth / HORIZON
        in_reach = [u for u, f in seen.foes.items() if math.dist(here, f.at) <= attack.reach]
        if in_reach and all(u in killed for u in in_reach):
            # The forecast's own pace is quicker than the strikes' (`strike_spread`): its median stands for them.
            spread = settings.strike_spread
            clear = (max(killed[u] for u in in_reach) - swap_seconds) * spread[len(spread) // 2]
        else:
            clear = sum(seen.foes[u].left for u in in_reach) / max(rate, 1.0)
        clear = max(0.36, min(clear, 10.0))
        remaining = math.dist(here, goal.place) / 20.0  # local ETA stand-in, full routed leg supplied by navigation
        candidates = []
        hold_harm = harm_path(look, (*swap_path, (here, min(settings.hold_dwell, clear), 'battle')), settings, killed)
        # Price the work until the next decision, but veto a stand that cannot
        # survive the longer escape horizon. Repeated short holds must not walk
        # the loop into a state from which every departure is lethal.
        future = harm_path(
            look,
            (*swap_path, (here, max(settings.horizon, min(settings.hold_dwell, clear)), 'battle')),
            settings,
            killed,
        )
        hold_harm = replace(hold_harm, losses=future.losses, barred=hold_harm.barred or future.barred)
        if not battle_ready:
            hold_harm = replace(hold_harm, barred='battle weapon swap is unavailable')
        hold_seconds = clear + swap_seconds
        # What an escape could save (holding's life at the look's price) against the least it costs (a walk's start
        # and overhead; the swap where the set in hand is not the battle set): below it no escape is worth pricing.
        saving = kappa * hold_harm.mean
        least = settings.move_overhead + WALK_LATENCY + (SWAP_SECONDS if hands != 'battle' else 0.0)
        waiting = isinstance(base, NoWay)
        if waiting and hold_harm.worst <= allowance and veto(hold_harm, look.life, settings) is None:
            if saving <= least:
                # Waiting for a summoned pack or a boss to appear is not a failed
                # safety constraint. With no danger, keep the goal and its reason.
                return facts
            # Waiting is an act priced as one when an escape could be worth more than it (an act under way at
            # where the character waits): staying, the goal's reason kept, against the escapes below.
            candidates.append(Candidate(base, hold_seconds + remaining, hold_harm, False, 0.0, False))
        if facts.in_reach and facts.attacking and (settings.fight_through or not fresh):
            hold = Candidate(Hold(facts.goal), hold_seconds + remaining, hold_harm, False, swap_seconds, True)
            candidates.append(hold)

        def strikes_from(spot: Point) -> bool:
            return any(
                math.dist(spot, foe.at) <= attack.reach and field_.clear(spot, foe.at) for foe in seen.foes.values()
            )

        def move_price(step: Step, *, retreat=False, firing=False, why: str | None = None):
            gap = math.dist(here, step.spot)
            jump = next((j for j in jumps if j.skill == step.skill), None)
            seconds = jump.takes(gap) if jump else (0.31 if step.skill == TELEPORT else 0.36 + gap / 20.0)
            needs = 'travel' if step.skill == TELEPORT else 'battle'
            swap = SWAP_SECONDS if needs != hands else 0.0
            seconds += swap + settings.move_overhead
            # A charged hop can leave quickly; a delayed jump/walk cannot. The
            # post-landing stand and the exposure before the swap both count.
            dwell = settings.landing_dwell if step.skill is not None else 0.12
            path = []
            if swap:
                path.append((here, swap, hands))
            if step.skill is None:
                # Three integration slices of the actual straight walking leg;
                # the navigator already checked its footing and line.
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
            landed = deaths_from(step.spot, SWAP_SECONDS if needs != 'battle' else 0.0)
            arrival = sum(part for _, part, _ in path[:-1])
            struck = {u: t + arrival for u, t in landed.items()}
            damage = harm_path(look, tuple(path), settings, struck)
            future = harm(look, step.spot, settings.horizon, needs, settings, landed)
            damage = replace(damage, barred=damage.barred or veto(future, look.life, settings))
            if needs == 'battle' and not battle_ready:
                damage = replace(damage, barred='battle weapon swap is unavailable')
            duration = seconds + math.dist(step.spot, goal.place) / 20.0
            if firing:
                # An escape's own seconds are in `seconds` already: its stand's pace is counted from its landing.
                there_worth, _ = taken(seen, attack, field_, step.spot, 0.0 if why else seconds)
                duration += clear * worth / max(there_worth, 1.0)
            step = PricedStep(step.spot, step.skill, step.camp, needs, seconds)
            act = Move(step, goal, why or ('retreat' if retreat else FIRING if firing else ''))
            unstruck = seconds + (SWAP_SECONDS if needs != 'battle' else 0.0)  # the strike needs the battle set
            candidates.append(Candidate(act, duration, damage, retreat, unstruck, strikes_from(step.spot)))

        if isinstance(base, Operate):
            # The hands walk to a drop or object and work it there: the walk in three slices, as a leg's, then
            # the act's own dwell at its place. No strike is made meanwhile, so nothing is credited as killed.
            gap = math.dist(here, goal.place)
            walk = WALK_LATENCY + gap / RUN_SPEED if gap > 2 else 0.0
            path: tuple = tuple(
                ((here[0] + (goal.place[0] - here[0]) * f, here[1] + (goal.place[1] - here[1]) * f), walk / 3, hands)
                for f in (0.0, 0.5, 1.0)
                if walk
            )
            path += ((goal.place if walk else here, settings.use_dwell, hands),)
            damage = harm_path(look, path, settings)
            used = walk + settings.use_dwell
            candidates.append(Candidate(base, used, damage, False, used, strikes_from(goal.place if walk else here)))
        elif isinstance(base, Move):
            move_price(base.step)
            if candidates[-1].harm.worst > allowance or veto(candidates[-1].harm, look.life, settings):
                # A long navigation leg may end inside a pack. Ask navigation for
                # earlier stands on that same approach before conceding a retreat.
                for fraction in (0.25, 0.5, 0.75):
                    if late():
                        break
                    point = (
                        here[0] + (base.step.spot[0] - here[0]) * fraction,
                        here[1] + (base.step.spot[1] - here[1]) * fraction,
                    )
                    shorter = leg(point)
                    if isinstance(shorter, Step) and math.dist(here, shorter.spot) > 2:
                        move_price(shorter)
                        last = candidates[-1]
                        assert isinstance(last.act, Move)
                        candidates[-1] = replace(last, act=replace(last.act, reason='safe approach'))
        # A running fight must also compare advancing once it is safe, rather than
        # treating the old in-reach branch as the arbiter.
        elif (
            isinstance(base, Hold)
            and not facts.there
            and not facts.settling
            and (fresh or (posted is not None and posted.runs))
        ):
            step = facts.way()
            if isinstance(step, Step):
                move_price(step)

        def feasible(c: Candidate) -> bool:
            return c.harm.worst <= allowance and veto(c.harm, look.life, settings) is None

        unsafe = not any(feasible(c) for c in candidates)
        # Camp retains the old crowd/keep-away floors. Price its answer alongside
        # holding, rather than letting the sweep move outside the safety constraint.
        # Near a hostile with no clear line to strike it, the firing stand is the act that keeps the strike gap (I2).
        lineless = facts.near and facts.attacking and not facts.in_reach
        if not late() and (unsafe or lineless or (facts.in_reach and hold_harm.worst > allowance * 0.5)):
            found = camp(seen, attack, barred=barred, jumps=jumps)
            if found is not None:
                move_price(Step.to(found), firing=True)
        # An escape is priced whenever what it could save may exceed what it costs, not only when nothing else is
        # safe: holding's life at the look's price (all of it, were the escape to cost none) against the least
        # seconds a walk there takes (its start, the walk, the overhead; the swap where the set in hand is not
        # the battle set; `saving`, `least` above). Offered as a stand the strike goes on from, competing with
        # holding or waiting by T + kappa x H (STEPPING: the life it saves is why, not a better strike pace): the
        # read models' places first (an act under way, combat/threats), then the threat's geometry where a strike
        # can be made from.
        staying = (facts.in_reach and facts.attacking) or waiting
        if not unsafe and staying and saving > least:
            offered = 0
            for point, why in self.offered(here, look, hold_harm):
                if offered >= ESCAPES_MOST or late():
                    break
                if why == AWAY and not strikes_from(point):
                    continue
                if saving <= least + math.dist(here, point) / RUN_SPEED:
                    continue
                spot = footing(field_, here, point)
                if spot is None:
                    continue
                offered += 1
                move_price(Step(spot), firing=True, why=f'{STEPPING} {why}')
        if unsafe:
            # Every retreat is a real navigational leg; never assume that an open
            # point is reachable through a wall. Equal harm prefers less time.
            asked: list[Point] = []

            def escape(point: Point) -> None:
                offered = options(point) if options is not None else (leg(point),)
                for step in offered:
                    if (
                        isinstance(step, Step)
                        and math.dist(here, step.spot) > 2
                        and all(math.dist(step.spot, other) >= ESCAPE_SAME for other in asked)
                    ):
                        asked.append(step.spot)
                        move_price(step, retreat=True)

            places = [point for point, _ in self.offered(here, look, hold_harm if hold_harm.by else future)]
            for index, point in enumerate(places[:ESCAPES_MOST]):
                if index >= 2 and late():
                    break
                escape(point)
            if not places or not any(feasible(c) for c in candidates if c.retreat):
                for i in range(RAYS):
                    if late():
                        break
                    angle = i * math.tau / RAYS
                    escape((here[0] + 22 * math.cos(angle), here[1] + 22 * math.sin(angle)))
            # Fighting in place may be the least-harm escape if it removes the
            # threats sooner than a walk. It still never lifts the lethal veto.
            if facts.in_reach and facts.attacking and veto(hold_harm, look.life, settings) is None:
                candidates.append(Candidate(Hold(facts.goal), hold_seconds, hold_harm, True, swap_seconds, True))
            elif not (facts.in_reach and facts.attacking):
                # Staying where it stands, striking nothing, is an act too, priced as one: chosen only when it is
                # the least harm of all (no strike from here would lower it, every way out costs more).
                idle = harm(look, here, settings.horizon, hands, settings)
                candidates.append(Candidate(NoWay(WAITING), math.inf, idle, True))
        priced = replace(
            facts,
            candidates=tuple(candidates),
            priced=True,
            budget=allowance,
            life=look.life,
            kappa=kappa,
            safety=settings,
        )
        obstructed = next(
            (
                c
                for c in candidates
                if not c.retreat and isinstance(c.act, (Move, Operate)) and c.harm.worst > allowance
            ),
            None,
        )
        if obstructed is not None:
            self.blocked_by = blockers(obstructed.harm, allowance)
        chosen = decide(priced, posted)
        blocked_goal = asking and (
            not isinstance(chosen, (Move, Operate))
            or (isinstance(chosen, Move) and chosen.reason.startswith('retreating:'))
        )
        if blocked_goal:
            if self.blocked_goal != key or facts.now - self.last_press >= 0.7:
                self.blocked_since = facts.now
                self.first_press = posted.pressed_at
            self.blocked_goal = key
            self.last_press = facts.now
        else:
            self.blocked_goal = None
        self.decision = {
            'looked_at': facts.now,
            'goal': goal.label,
            'goal_place': goal.place,
            'life': look.life,
            'hands': hands,
            'budget': round(allowance, 1),
            'dear': dear,
            'floor_raised': insisting > 0,
            'chosen': type(chosen).__name__,
            'chosen_place': chosen.step.spot if isinstance(chosen, Move) else here,
            'reason': getattr(chosen, 'reason', ''),
            'blocked_by': self.blocked_by,
            'killed': {unit: round(at, 2) for unit, at in sorted(killed.items(), key=lambda r: r[1])[:8]},
            'late': late(),
            'ms': round((timer() - began) * 1000, 1) if timer is not None else None,
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
                    'contributors': c.harm.by,
                    'stand_ins': c.harm.stand_ins,
                    'blocked_by': blockers(c.harm, allowance),
                }
                for c in candidates
            ],
        }
        return priced

    def offered(self, here: Point, look: Look, priced) -> list[tuple[Point, str]]:
        """The places an escape may go to, with why: those the read models of the hostiles offer for their acts
        under way (combat/threats `Threat.escapes`), then the threat's geometry (`escapes`); two nearer than
        ESCAPE_SAME are one."""
        found: list[tuple[Point, str]] = []
        for m in look.hostiles:
            model = threats.of(m.txt)
            if model is not None:
                flying = tuple((at, heading) for owner, at, heading in look.missiles if owner == m.unit)
                found.extend(model.escapes(threats.Acting(m.at, m.mode, m.mode_frames, flying), here))
        found.extend((point, AWAY) for point in self.escapes(here, look, priced))
        unique: list[tuple[Point, str]] = []
        for point, why in found:
            if all(math.dist(point, other) >= ESCAPE_SAME for other, _ in unique):
                unique.append((point, why))
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

"""Observation and candidate assembly for the pure pursuit arbiter.

The only memory is observed weapon profiles and how long the same pressed goal
has been blocked. Nothing here delivers input or chooses a goal.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace

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
    life_price,
    veto,
)
from inventory_tracking.combat.policy import Observation, Point
from inventory_tracking.combat.stance import HORIZON, Field, camp, taken
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.macros.build import Attack, Leg, NoWay, PricedStep, Step
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.pursuit import Candidate, Facts, Hold, Move, Operate, decide
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.world import NO_OWNER, Loot, World
from inventory_tracking.models import PotionType


RESISTS = ((36, 'physical'), (39, 'fire'), (41, 'lightning'), (43, 'cold'), (45, 'poison'), (37, 'magic'))
# Stats store unpenalized percentages. Difficulty is not yet an observation: the
# macro's supported economy is Hell. Keep this explicit, never assume capped gear.
HELL_PENALTY = 100.0
SWAP_SECONDS = 0.75


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

    def look(self, world: World, loot: Loot, hands: str, blocked=None) -> Look:
        player = world.player
        assert player is not None
        identity = (world.game_name, player.unit_id)
        if identity != self.identity:
            self.profiles.clear()
            self.blocked_goal = None
            self.identity = identity
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
        # Unknown set: no resistance, no block, no guard credit. Never copy the
        # battle set onto the travel set. An observed set is replaced at each look.
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
                )
                for m in world.monsters
                if not m.ally and m.owner == NO_OWNER and m.mode not in (0, 12)
            ),
            tuple((m.x, m.y) for m in world.monsters if m.ally or m.owner != NO_OWNER),
            self.profiles.get('battle', Protection()),
            self.profiles.get('travel', Protection()),
            float(loot.life),
            blocked,
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
        """Assemble prices without selecting a goal; the decision is pursuit.decide's."""
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
        insisting = 0.0
        if (
            fresh
            and key == self.blocked_goal
            and facts.now - self.last_press < 0.7
            and posted.pressed_at > self.first_press
        ):
            insisting = facts.now - self.blocked_since
        allowance = budget(loot.life, loot.max_life, felt, settings, insisting=insisting)
        supply = on_belt(loot)
        kappa = life_price(Supply(supply[PotionType.HEALING], supply[PotionType.REJUVENATION]), loot.max_life, settings)
        here = seen.origin
        field_ = Field(seen.blocked, barred)
        worth, _ = taken(seen, attack, field_, here, 0.0)
        rate = worth / HORIZON
        clear = sum(f.left for f in seen.foes.values() if math.dist(here, f.at) <= attack.reach) / max(rate, 1.0)
        clear = max(0.36, min(clear, 10.0))
        remaining = math.dist(here, goal.place) / 20.0  # local ETA stand-in, full routed leg supplied by navigation
        candidates = []
        swap_path = ((here, SWAP_SECONDS, hands),) if hands != 'battle' else ()
        hold_harm = harm_path(look, (*swap_path, (here, min(settings.hold_dwell, clear), 'battle')), settings)
        # Price the work until the next decision, but veto a stand that cannot
        # survive the longer escape horizon. Repeated short holds must not walk
        # the loop into a state from which every departure is lethal.
        future = harm_path(
            look, (*swap_path, (here, max(settings.horizon, min(settings.hold_dwell, clear)), 'battle')), settings
        )
        hold_harm = replace(hold_harm, losses=future.losses, barred=hold_harm.barred or future.barred)
        if not battle_ready:
            hold_harm = replace(hold_harm, barred='battle weapon swap is unavailable')
        hold_seconds = clear + (SWAP_SECONDS if swap_path else 0.0)
        if isinstance(base, NoWay) and hold_harm.worst <= allowance and veto(hold_harm, look.life, settings) is None:
            # Waiting for a summoned pack or a boss to appear is not a failed
            # safety constraint. With no danger, keep the goal and its reason.
            return facts
        if facts.in_reach and facts.attacking and (settings.fight_through or not fresh):
            candidates.append(Candidate(Hold(facts.goal), hold_seconds + remaining, hold_harm))

        def move_price(step: Step, *, retreat=False, firing=False):
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
            damage = harm_path(look, tuple(path), settings)
            future = harm(look, step.spot, settings.horizon, needs, settings)
            damage = replace(damage, barred=damage.barred or veto(future, look.life, settings))
            if needs == 'battle' and not battle_ready:
                damage = replace(damage, barred='battle weapon swap is unavailable')
            duration = seconds + math.dist(step.spot, goal.place) / 20.0
            if firing:
                there_worth, _ = taken(seen, attack, field_, step.spot, seconds)
                duration += clear * worth / max(there_worth, 1.0)
            step = PricedStep(step.spot, step.skill, step.camp, needs, seconds)
            act = Move(step, goal, 'retreat' if retreat else 'firing spot' if firing else '')
            candidates.append(Candidate(act, duration, damage, retreat))

        if isinstance(base, Operate):
            # The hands may approach a drop or object: price that place too.
            path = ((here, settings.operate_dwell, hands),)
            if math.dist(here, goal.place) > 2:
                path += ((goal.place, settings.operate_dwell, hands),)
            damage = harm_path(look, path, settings)
            candidates.append(Candidate(base, settings.operate_dwell, damage))
        elif isinstance(base, Move):
            move_price(base.step)
            if candidates[-1].harm.worst > allowance or veto(candidates[-1].harm, look.life, settings):
                # A long navigation leg may end inside a pack. Ask navigation for
                # earlier stands on that same approach before conceding a retreat.
                for fraction in (0.25, 0.5, 0.75):
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

        unsafe = not any(c.harm.worst <= allowance and veto(c.harm, look.life, settings) is None for c in candidates)
        # Camp retains the old crowd/keep-away floors. Price its answer alongside
        # holding, rather than letting the sweep move outside the safety constraint.
        if unsafe or (facts.in_reach and hold_harm.worst > allowance * 0.5):
            found = camp(seen, attack, barred=barred, jumps=jumps)
            if found is not None:
                move_price(Step.to(found), firing=True)
        if unsafe:
            # Every retreat is a real navigational leg; never assume that an open
            # point is reachable through a wall. Equal harm prefers less time.
            for i in range(8):
                angle = i * math.tau / 8
                point = (here[0] + 22 * math.cos(angle), here[1] + 22 * math.sin(angle))
                offered = options(point) if options is not None else (leg(point),)
                for step in offered:
                    if isinstance(step, Step) and math.dist(here, step.spot) > 2:
                        move_price(step, retreat=True)
            # Fighting in place may be the least-harm escape if it removes the
            # threats sooner than a walk. It still never lifts the lethal veto.
            if facts.in_reach and facts.attacking and veto(hold_harm, look.life, settings) is None:
                candidates.append(Candidate(Hold(facts.goal), hold_seconds, hold_harm, True))
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
        blocked_goal = fresh and (
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
            'floor_raised': insisting > 0,
            'chosen': type(chosen).__name__,
            'chosen_place': chosen.step.spot if isinstance(chosen, Move) else here,
            'reason': getattr(chosen, 'reason', ''),
            'blocked_by': self.blocked_by,
            'candidates': [
                {
                    'act': type(c.act).__name__,
                    'place': c.act.step.spot if isinstance(c.act, Move) else here,
                    'skill': c.act.step.skill if isinstance(c.act, Move) else None,
                    'hands': c.act.step.needs if isinstance(c.act, Move) else hands,
                    'T': round(c.seconds, 3),
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

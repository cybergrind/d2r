"""The pursuit: a key press is an intent, and one pure decision per look says what is done about it
(rca/2026-10-13/kp4-findings.md §3.2 design B; behind `BuildSettings.pursuit`). Design notes: history/pursuit.md.

The press posts a `Pursuit` and returns; the input loop (attack mode, hunt.py) names the goal the key means
now (goals.py `goal_of`) and asks `decide`: `Move` toward it, `Defer` to the route's own step, `Operate` at it,
`Hold` the strike, or `NoWay` with a reason said once per change (`Told`).

The leash: a pickup press runs the whole level (the player, 2026-10-13: "one press of KP_1, then it runs the whole
level automatically") until what is left is not this loop's or the level is left; an open passage carries the run into
the next level (`carried`). The player's hand pauses a run, it does not end it ("we shouldn't prevent user from
sorting", 2026-10-13). A valuable with no room is waited by (`WAIT`; "when valuable doesn't fit: we need to stop
near it").
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TypeGuard

from inventory_tracking.combat.harm import Harm, SafetySettings, veto
from inventory_tracking.combat.pack import BACK_SAID as PACK_BACK_SAID
from inventory_tracking.combat.threats.dolls import BAIT_SAID
from inventory_tracking.combat.threats.manaburn import MANA_SAID
from inventory_tracking.macros.build import Leg, NoWay, Step
from inventory_tracking.macros.goals import ENTRY_GOAL_NEAR, PICK_UP, PURSUED, WAIT, Goal
from inventory_tracking.routes.model import ENTER, FIGHT, STAND, USE


# How a level run with no route stage left ends (runner.py `_run_over`: on a level done, its way on is dropped)
NOTHING_LEFT = 'nothing is left to go to on this level'
# How a level run whose level was left ends (runner.py `_run_over`: no run of the level counted for the agenda)
LEVEL_LEFT = 'the level was left'


# Seconds a press stands for "go on": the longest gap between presses of a player who keeps going (kp4-findings.md
# §2.4, §2.5); under runner.py EXPIRES, so no move begins for a press older than that.
FRESH = 0.7
# Seconds the hand is still (no click, no pointer move, no panel) before a paused level run resumes (take
# 20261013T181240Z-108: the sorting hand was never still over 0.43 s, 1.01 s with the inventory open).
SETTLE = 1.5
PAUSED = "the level run is paused: the player's hand"
OPERATED = frozenset((USE, STAND, PICK_UP))  # goals something is done at; at the others the character only is
# How far the loop goes without a fresh press (architecture §2.1): NONE, nowhere; FULL, the stages of the press's level.
NONE, FULL = 'none', 'full'
# Seconds a carried run waits for the new level's card (level guide poll 0.5 s, then rooms and walls are read).
ENTERING = 3.0
ENTERING_SAID = 'the level is being read: the run goes on once its card is up'
# A level run with nothing to go to on a level whose map the level guide has not read yet (`Facts.mapped`) waits for it
# MAP_WAIT seconds from its post or its carrying, holding what is in reach; past the wait, what is in reach is fought
# before the run ends. The small levels' runs ended 0.4 s after the arrival, their maps read at ~0.6 s, and the agenda
# took them for done, their hostiles alive (Durance of Hate Level 1, the Forgotten Reliquary and Temple, 09:05-09:09 on
# 2026-10-21; rca/2026-10-21/small-levels-findings.md). False (before 2026-10-21): such a run ends at once.
WAIT_FOR_MAP = True
MAP_WAIT = 3.0
MAP_SAID = "the level's map is not read yet: the run goes on once it is"
# A boss of the game's ledger alive on the level with no place known for it (macros/bossledger.py; `Facts.bosses_left`,
# the coordinator's relay of the boss-ledger findings, 2026-10-22, rca/2026-10-22/boss-ledger-findings.md cause 4; the
# player: "we need to kill all bosses, no exceptions to that"): a level run whose route has nothing left but what takes
# a press (the loot) or no stage at all is not ended (`ends_run`) while the level has an unexplored room: the judge
# hands that room as its goal (hunting/judging.py `boss_explore`). No room left, the run ends as before, the bosses
# named. The agenda's boss goal takes a boss with a known place (agenda.py BOSS_GOALS). Bounded by the ledger's hold
# (zonenav.py BOSSES_HOLD off, or the level's runs past its allowance and BOSS_RUNS: no count). False: ended as before.
BOSS_EXPLORE = True
BOSS_EXPLORE_SAID = 'alive on this level, its place not known'


@dataclass(frozen=True)
class Pursuit:
    """The mailbox: the key last pressed and when. The goal is named anew at every look, never kept.
    `advance`: the press asks for its goal before what is in reach (the teleport key); `leash`: how far the
    loop goes without a press, on level `area`; `spent`: handed to a routine; `paused`: the player's hand has
    the run; `onward`: the level the run's open passage leads into (`heading`); `entered`: clock the run was
    carried into its level; `rush`: the KP_6 loop's run (the player, 2026-10-16: "don't fight what isn't
    attacking"): its goal first, a strike only where the arbiter prices it."""

    key: str
    pressed_at: float
    advance: bool = True
    leash: str = NONE
    area: int | None = None
    spent: bool = False
    paused: bool = False
    onward: int | None = None
    entered: float | None = None
    rush: bool = False
    # Posted by the KP_6 loop's leg (runner.py `_loop_level_run`): never half of a double press, and a new run, not
    # the one before (a run held into the next game switched to a full clear, 10:26:40 on 2026-10-18)
    looped: bool = False
    # The terror zone level run (macros/tzloop.py): the agenda's targets first (agenda.py `Agenda.in_level`)
    agenda: bool = False
    # The levels the run may be carried into or walk on into (the trip's, running/legs.py `_loop_level_run`); None:
    # any. Games 30 and 31 on 2026-10-19 walked from the River of Flame into the Chaos Sanctuary, off the trip.
    allowed: frozenset[int] | None = None

    def fresh(self, now: float) -> bool:
        """Made within FRESH seconds (a clock that went back keeps nothing alive) and not handed on."""
        return not self.spent and 0.0 <= now - self.pressed_at <= FRESH

    @property
    def leashed(self) -> bool:
        """A level run is held, working or paused."""
        return self.leash == FULL

    @property
    def runs(self) -> bool:
        """A level run works now: held and not paused."""
        return self.leash == FULL and not self.paused

    def may_enter(self, area: int | None) -> bool:
        """Whether the run may go on into level `area` (`allowed`); an unknown level is not, under a limit."""
        return self.allowed is None or (area is not None and area in self.allowed)

    def entering(self, now: float) -> bool:
        """The run was carried into its level less than ENTERING seconds ago."""
        return self.entered is not None and 0.0 <= now - self.entered <= ENTERING

    def awaits_map(self, now: float) -> bool:
        """Within MAP_WAIT seconds of the run's carrying into its level, else of its post (WAIT_FOR_MAP)."""
        since = self.entered if self.entered is not None else self.pressed_at
        return 0.0 <= now - since <= MAP_WAIT


def heading(pursuit: Pursuit, goal: Goal | None) -> Pursuit | None:
    """The run with `onward` noted once its goal is an open passage naming a level (levels/model.py `Target.into`);
    None: nothing to note. A door is no crossing: it takes a press."""
    if not pursuit.leashed or goal is None or not goal.crossed or goal.mark is None:
        return None
    into = goal.mark.into
    if into is None or into == pursuit.area or into == pursuit.onward or not pursuit.may_enter(into):
        return None
    return replace(pursuit, onward=into)


def carried(pursuit: Pursuit, area: int | None, now: float) -> Pursuit | None:
    """The run carried into `area` once, when it is the level its passage led into (`onward`), working or paused as
    it was. None otherwise; any other level change ends the run (`decide`)."""
    if not pursuit.leashed or pursuit.area is None or area is None or area == pursuit.area or area != pursuit.onward:
        return None
    if not pursuit.may_enter(area):
        return None  # off the trip: the run ends (`decide`, "the level was left")
    return replace(pursuit, area=area, onward=None, entered=now)


def settled(hand_at: float, now: float, panels: bool) -> bool:
    """A paused run resumes: the hand still SETTLE seconds since `hand_at` and no panel open (I7)."""
    return not panels and now - hand_at >= SETTLE


@dataclass(frozen=True)
class Facts:
    """What one decision is made from, read at one look. `way` is asked only when a move is wanted."""

    now: float
    goal: Goal | None  # what the key means now (goals.py `goal_of`); None: nothing known to go to
    there: bool  # within `Goal.near` of the goal (a fight: with a shot at it)
    in_reach: bool  # a hostile stands in the attack's reach
    attacking: bool  # attack mode is on
    way: Callable[[], Leg]  # the next move toward the goal, or why there is none
    area: int | None = None  # the character's level (a run ends off its own level)
    # An object just used is still bringing what it calls (teleport.py `Use.brings`): no move begins (architecture §2.6)
    settling: bool = False
    candidates: tuple[Candidate, ...] = ()
    priced: bool = False
    budget: float = 0.0
    life: float = float('inf')
    kappa: float = 0.0
    safety: SafetySettings = field(default_factory=SafetySettings)
    quiet: float = 0.0  # seconds since the last strike, counted while `near`
    near: bool = False  # a hostile within the strike's reach, line or not: the strike gap counts (I2)
    rush: bool = False  # the KP_6 loop's run (`Pursuit.rush`): no strike gap, the price alone
    hurt: bool = False  # life lost within HURT_SECONDS (hunting/judging.py `safety_priced`)
    # Units past the goal's `near` for a distance goal (a place, a door), else inf. Under `least_move` (the
    # navigator's shortest move, travel.py AROUND_LEAST) a way with no step left is an arrival (`moved`).
    beyond: float = math.inf
    least_move: float = 0.0
    # The level guide has read this level's map (its rooms): a run with nothing to go to without it waits (MAP_WAIT)
    mapped: bool = True
    # Units from the character to the look's nearest hostile (macros/safety.py `Safety.price`); None: not priced
    clear: float | None = None
    # Bosses of the game's ledger alive on this level with no place known (BOSS_EXPLORE, hunting/judging.py)
    bosses_left: int = 0


@dataclass(frozen=True)
class Move:
    """One move toward `goal`. `dodge`: a step out of a hostile's act under way (combat/threats `Threat.escapes`),
    not held to the strike gap (I2) and clicked without the settle (travel.py `step_walk` `hurry`). `onward`: the
    next place of a walk round an act under way (combat/threats `Threat.around`, macros/safety.py WALK_ROUND): taken
    over the rest while it fits the budget and the veto (`arbitrate`), and clicked while the character still walks."""

    step: Step
    goal: Goal
    reason: str = ''
    dodge: bool = False
    onward: bool = False


@dataclass(frozen=True)
class Hold:
    """Stay and strike what is in reach."""

    goal: Goal | None = None
    reason: str = ''


@dataclass(frozen=True)
class Operate:
    """Do what is done at the goal: use its object, note the stand, take the drop."""

    goal: Goal


@dataclass(frozen=True)
class Defer:
    """Hand the press to the route's own step (a door, a border, the loot, the leaving). None: the key's own
    routine takes it."""

    goal: Goal | None


@dataclass(frozen=True)
class Ended:
    """The level run is over: the leash goes back to none, and `reason` is said."""

    reason: str


Act = Move | Hold | Operate | Defer | Ended | NoWay


@dataclass(frozen=True)
class Candidate:
    act: Act
    seconds: float
    harm: Harm
    retreat: bool = False
    # Seconds the act keeps the character from striking: the arbiter's strike gap (I2). 0: a strike.
    unstruck: float = 0.0
    strikes: bool = False  # the act ends with a hostile in reach and a clear line: a strike follows
    # A retreat ending within strike reach of the hostile whose kill ends most harm (macros/safety.py `keeper`)
    # (rca/2026-10-14/baal-sim.md fix 1)
    keeps: bool = False
    # Units from the act's way to the look's nearest hostile: a walk's along it, a jump's at its landing
    # (macros/safety.py `clearance`); None: not priced
    clear: float | None = None


RUSH_HARM_SHARE = 0.05  # of life: harm a move or use of the loop's run may be priced at over a hold
NO_STEP_LEFT = 'no step toward it is left'  # the arrival said for that (`moved`)
ENTRY_REACH = 10.0  # units from a door's entry with no way nearer: the run ends there (`to_the_door`; NEAR_WARP)
FIRING_SPOT = 'firing spot'  # reason of a move to a firing stand (macros/safety.py FIRING)
PASSAGE = 'an open passage: walking through into the next level'
THROUGH_WALK = 40.0  # units: a passage no hop gets nearer to is walked from this near (`through`)
KEEPING = 'retreating within strike reach: no act here fits the life budget'
OVER_BUDGET = 'no progress act fits the life budget'
# The retreat's line says why no progress act was made (`short_of`; the player, 2026-10-21: "it looks like we
# have some major issue with estimate"): of 1482 such retreats in the day's takes 1157 had every progress act vetoed
# (a keep range 1623 times), not over the budget, and the line said "fits the life budget" for both; at 21:07:23 at
# 2723 of 2943 life and a full belt every act was priced 0 (rca/2026-10-21/herald-left-findings.md C2). False: the
# one line, as before.
RETREAT_SAYS_WHY = True
# The death at 23:35:33.97 on 2026-10-21 (Disused Fane, take 20261021T203514Z-95, rca/2026-10-21/death-findings.md):
# the life under its floor (budget 0) for the last 5.7 s, five "retreats" landed 2-5 units from the tier 2 Herald's pack
# (their harm priced 2-11 on kills that never came), the sixth was a walk of 16 onto three Flesh Hunters running in.
# The player, 2026-10-21: "we must not die or we lose exp and our gear"; "we must have top priority to no die ourselves
# and prevent loosing experience". True: with no progress act fitting, a retreat move whose way comes within
# AWAY_UNITS of a hostile is left for one clear of them, else for one ending farther from them than the character
# stands, else for fighting out (`away_from`). False: the least harm among them all, as before.
RETREAT_AWAY = True
AWAY_UNITS = 10.0
# The same death: at 23:35:33.94 every act was vetoed and the least lethal was a walk of 16 through a second unique
# Flesh Hunter pack (Fire Enchanted, Conviction, Extra Fast); 804 life went in the next frame. True: with every act
# vetoed the jump landing clear of the hostiles (AWAY_UNITS, else farther than the character stands) is made first,
# and a walk whose way comes within AWAY_UNITS of one is never the least lethal while another act is priced
# (`vetoed_escape`). False: the least lethal of them all, as before.
VETOED_ESCAPE = True
VETOED_AWAY = 'safety: every act is vetoed; the jump clearest of the hostiles is this move'
# 2026-10-22: Battle Orders due in a fight that is not safe to cast in (macros/cta.py REBUFF, the player: "predict when
# it runs off, retreat and rebuff"): the safety's Teleport to a spot clear of the hostiles (macros/safety.py
# `rebuff_back`) is taken first unless vetoed, as the hop back from a Herald's pack is. False: priced as a plain move.
REBUFF_FIRST = True
REBUFF_SAID = 'rebuffing Battle Orders clear of the hostiles'
# Moves toward a level run's boss skip the strike gap while nothing hurts (`onward`): F1 of
# rca/2026-10-18/andariel-cadence-findings.md §5 (the player, 2026-10-18: "F1: ok"). Off: I2 as before.
RUSH_THE_BOSS = True


def the_runs_boss(goal: Goal | None, pursuit: Pursuit | None) -> bool:
    """`goal` is the boss of the route's fight stage on a working level run, not one on the way (`Goal.clearing`)."""
    return (
        pursuit is not None
        and pursuit.runs
        and goal is not None
        and goal.do == FIGHT
        and not goal.clearing
        and goal.stage is not None
        and goal.stage.kind == FIGHT
    )


def onward(facts: Facts, feasible: list[Candidate], pursuit: Pursuit | None) -> list[Candidate]:
    """Moves toward a level run's boss the strike gap does not hold (RUSH_THE_BOSS): unhurt, the navigator's own
    moves no more harmful than the least hold or RUSH_HARM_SHARE of life. Empty otherwise."""
    if not RUSH_THE_BOSS or facts.hurt or not the_runs_boss(facts.goal, pursuit):
        return []
    holds = [c for c in feasible if isinstance(c.act, Hold)]
    if not holds:
        return []
    least = max(min(c.harm.mean for c in holds), RUSH_HARM_SHARE * facts.life)
    return [c for c in feasible if isinstance(c.act, Move) and not c.act.reason and c.harm.mean <= least]


def short_of(facts: Facts, allowed: list[Candidate]) -> str:
    """Why no progress act is made, for the retreat's line (RETREAT_SAYS_WHY): over the budget (the least worst
    progress act's worst and mean, the budget, the life), or every one vetoed (the first's veto), or none priced."""
    if not RETREAT_SAYS_WHY:
        return OVER_BUDGET
    priced = [c for c in allowed if not c.retreat]
    if priced:
        best = min(priced, key=lambda c: c.harm.worst)
        return (
            f'{OVER_BUDGET} (the least worst progress act: worst {best.harm.worst:.0f}, mean {best.harm.mean:.0f}, '
            f'budget {facts.budget:.0f} of {facts.life:.0f} life)'
        )
    vetoes = [veto(c.harm, facts.life, facts.safety) for c in facts.candidates if not c.retreat]
    said = next((why for why in vetoes if why), None)
    return f'every progress act is vetoed ({said})' if said is not None else 'no progress act was priced'


def judged_move(c: Candidate) -> bool:
    """A move whose clearance is priced (`Candidate.clear`)."""
    return isinstance(c.act, Move) and c.clear is not None


def nearer(c: Candidate, facts: Facts) -> bool:
    """A priced move whose way comes nearer a hostile than the character stands (a walk straight away does not: its
    nearest pass is where it starts)."""
    return c.clear is not None and facts.clear is not None and c.clear < facts.clear - 1e-6


def away_from(facts: Facts, escapes: list[Candidate]) -> list[Candidate]:
    """The retreats to choose among (RETREAT_AWAY): the moves whose way stays AWAY_UNITS clear of the hostiles while
    one is priced; else those never nearer a hostile than the character stands; else none of the moves while another
    act is priced (fighting out). Every other act stays; unpriced clearances leave the retreats as they are."""
    if not RETREAT_AWAY or facts.clear is None:
        return escapes
    moves = [c for c in escapes if judged_move(c)]
    if not moves:
        return escapes
    others = [c for c in escapes if not judged_move(c)]
    clear = [c for c in moves if c.clear is not None and c.clear >= AWAY_UNITS]
    if clear:
        return [*clear, *others]
    unturned = [c for c in moves if not nearer(c, facts)]
    if unturned:
        return [*unturned, *others]
    return others or escapes


def vetoed_escape(facts: Facts, lethal: Callable[[Candidate], float]) -> tuple[Candidate | None, list[Candidate]]:
    """With every act vetoed (VETOED_ESCAPE): the jump to make, landing AWAY_UNITS clear of the hostiles, else farther
    from them than the character stands, the least lethal of those (the clearest on a tie); None when none is priced.
    Then the acts the least lethal is chosen among: a walk whose way comes nearer a hostile than the character stands
    only while nothing else is priced."""
    candidates = list(facts.candidates)
    if not VETOED_ESCAPE or facts.clear is None:
        return None, candidates
    skilled = [
        c
        for c in candidates
        if judged_move(c) and isinstance(c.act, Move) and c.act.step.skill is not None and not c.harm.barred
    ]
    here = facts.clear
    away = [c for c in skilled if c.clear is not None and c.clear >= AWAY_UNITS]
    away = away or [c for c in skilled if c.clear is not None and c.clear > here]
    if away:
        return min(away, key=lambda c: (lethal(c), -(c.clear or 0.0), c.harm.mean, c.seconds)), candidates
    walked = [c for c in candidates if not (isinstance(c.act, Move) and c.act.step.skill is None and nearer(c, facts))]
    return None, walked or candidates


def arbitrate(facts: Facts, pursuit: Pursuit | None = None) -> Act:
    """One price in seconds, constrained by both life budget and the unliftable veto. `pursuit`: the mailbox, for a
    level run's boss (`onward`); None: no run."""
    if facts.rush:
        # The loop's run fights only what the price makes it: firing stands outpriced the chest
        # (rca/2026-10-16/loop-shack-stalls-findings.md §1). Dodges and retreats stay.
        kept = tuple(c for c in facts.candidates if not (isinstance(c.act, Move) and c.act.reason == FIRING_SPOT))
        holds = [c for c in kept if isinstance(c.act, Hold)]
        if holds and not facts.hurt:
            # Nor a hold while unhurt when moving on is no more harmful than the hold or RUSH_HARM_SHARE of life
            # (rca/2026-10-17/movement-findings.md §4 #1); a hostile that costs life is still fought.
            least = max(min(c.harm.mean for c in holds), RUSH_HARM_SHARE * facts.life)
            moving = tuple(c for c in kept if not isinstance(c.act, Hold))
            if any(veto(c.harm, facts.life, facts.safety) is None and c.harm.mean <= least for c in moving):
                kept = moving
        facts = replace(facts, candidates=kept)
    allowed = [c for c in facts.candidates if veto(c.harm, facts.life, facts.safety) is None]
    # A hop back from a tier 4-5 Herald's pack comes first while it is not vetoed (combat/pack.py, the player,
    # 2026-10-21 ~10:00: "a Teleport back when anything is within 10")
    # So does the way in to dolls a demon holds (combat/threats/dolls.py DOLL_BAIT, off; the player, 2026-10-21 14:58)
    # And the leave under the mana floor (combat/threats/manaburn.py MANA_FLOOR; the player, 2026-10-21 ~15:50: "we
    # were tanking most of T5 herald damage without being able to hit (=low mana)")
    # And the rebuff of Battle Orders clear of the hostiles (REBUFF_FIRST; macros/cta.py REBUFF)
    saids = (PACK_BACK_SAID, BAIT_SAID, MANA_SAID, *((REBUFF_SAID,) if REBUFF_FIRST else ()))
    backs = [c for c in allowed if isinstance(c.act, Move) and c.act.reason.startswith(saids)]
    if backs:
        return min(backs, key=lambda c: c.seconds + facts.kappa * c.harm.mean).act
    feasible = [c for c in allowed if c.harm.worst <= facts.budget and not c.retreat]
    if facts.near and facts.attacking and not facts.rush:
        # No attack pause (I2): with a hostile in reach, keep only acts after which a strike comes within
        # `strike_gap`, if any fits; with the gap spent, those that strike soonest. Retreats and dodges
        # (`Move.dodge`, rca/2026-10-14/diablo-handling.md fix 1) are exempt. The loop's run has no gap
        # (rca/2026-10-16/loop-chests-findings.md §1).
        striking = [c for c in feasible if c.strikes]
        if striking:
            room = max(facts.safety.strike_gap - facts.quiet, min(c.unstruck for c in striking))
            # Nor moves toward a level run's boss while unhurt (`onward`, RUSH_THE_BOSS)
            rushed = onward(facts, feasible, pursuit)
            feasible = [
                c
                for c in feasible
                if (c.strikes and c.unstruck <= room) or (isinstance(c.act, Move) and c.act.dodge) or c in rushed
            ]
    if feasible:

        def price(c: Candidate) -> float:
            return c.seconds + facts.kappa * c.harm.mean

        # A walk round an act under way goes on while it fits: each look prices only to the next place, so the hold
        # at its end that a further place would spare is not seen (macros/safety.py WALK_ROUND)
        rounding = [c for c in feasible if isinstance(c.act, Move) and c.act.onward]
        if rounding:
            return min(rounding, key=price).act
        chosen = min(feasible, key=price)
        holding = next((c for c in feasible if isinstance(c.act, Hold)), None)
        if holding is not None and isinstance(chosen.act, Move) and chosen.act.reason == 'firing spot':
            improvement = price(holding) - price(chosen)
            if improvement < max(facts.safety.commit_seconds, price(holding) * facts.safety.commit_share):
                return holding.act
        return chosen.act
    escapes = [c for c in allowed if c.retreat]
    # A retreat that keeps the strike on what ends the harm comes first: one out of reach only defers the harm
    # (rca/2026-10-14/baal-sim.md weakness 2). Else the least harm.
    keeping = [c for c in escapes if c.keeps and isinstance(c.act, Move) and c.harm.worst <= facts.budget]
    if keeping:
        kept = min(keeping, key=lambda c: c.seconds + facts.kappa * c.harm.mean)
        assert isinstance(kept.act, Move)
        return Move(kept.act.step, kept.act.goal, KEEPING)
    # Never toward the pack while no progress act fits the life (RETREAT_AWAY)
    escapes = away_from(facts, escapes)
    if escapes:
        chosen = min(escapes, key=lambda c: (c.harm.mean, c.harm.worst, c.seconds))
        if isinstance(chosen.act, Move):
            return Move(chosen.act.step, chosen.act.goal, f'retreating: {short_of(facts, allowed)}')
        if isinstance(chosen.act, Hold):
            return Hold(chosen.act.goal, 'fighting out: less harm than any reachable retreat')
        return chosen.act
    if not facts.candidates:
        return NoWay('safety: no act was priced')

    # Every act is vetoed (I3 does not apply): make the least often lethal one and say so, never a stop that
    # strikes nothing.
    def lethal(c: Candidate) -> float:
        return sum(loss >= facts.life for loss in c.harm.losses) / max(len(c.harm.losses), 1)

    # A jump clear of the hostiles first, never a walk through them (VETOED_ESCAPE)
    away, candidates = vetoed_escape(facts, lethal)
    if away is not None:
        assert isinstance(away.act, Move)
        return Move(away.act.step, away.act.goal, f'retreating: {VETOED_AWAY}')
    chosen = min(candidates, key=lambda c: (bool(c.harm.barred), lethal(c), c.harm.mean, c.seconds))
    said = 'safety: every act is vetoed; the least lethal is'
    if isinstance(chosen.act, Move):
        return Move(chosen.act.step, chosen.act.goal, f'retreating: {said} this move')
    if isinstance(chosen.act, Hold):
        return Hold(chosen.act.goal, f'fighting out: {said} the fight')
    if isinstance(chosen.act, NoWay):
        return NoWay(f'{said} standing here')
    return chosen.act


def decide(facts: Facts, pursuit: Pursuit | None, enabled: bool = True) -> Act:
    """What the loop does at this look. `enabled` (`BuildSettings.pursuit`) off: hold what is in reach, else nothing."""
    goal = facts.goal
    if not enabled:
        return Hold() if facts.in_reach else NoWay('the pursuit is off')
    if facts.priced or facts.candidates:
        return arbitrate(facts, pursuit)
    pressed = pursuit is not None and pursuit.fresh(facts.now)
    if pursuit is not None and pursuit.leashed:
        if pursuit.area is not None and facts.area is not None and facts.area != pursuit.area:
            return Ended(LEVEL_LEFT)
        if not (pressed and pursuit.advance):
            if pursuit.paused:
                return Hold(goal) if facts.in_reach and facts.attacking else NoWay(PAUSED)
            if goal is None and pursuit.entering(facts.now):
                # Carried in a moment ago: the card is not up yet, which ends nothing
                return Hold() if facts.in_reach and facts.attacking else NoWay(ENTERING_SAID)
            if WAIT_FOR_MAP and not pressed and not facts.mapped and not routed(goal) and pursuit.awaits_map(facts.now):
                # In a moment ago, the map not read: nothing to go to is not known yet
                return Hold() if facts.in_reach and facts.attacking else NoWay(MAP_SAID)
            return run_level(facts, pressed, pursuit)
    if pursuit is not None and pressed:
        if goal is None:
            return NoWay('the key has nothing to go to: no stage, no mark and no boss is known here')
        if goal.do == ENTER:
            return entering(facts, goal)
        if goal.do not in PURSUED:
            return Defer(goal)
        if goal.do == PICK_UP:
            return Operate(goal)  # the hands walk to a drop themselves
        if facts.settling:
            # A second's wait for what the object brings, the strike held (architecture §2.6)
            if facts.in_reach and facts.attacking:
                return Hold(goal)
            return NoWay('what the object used brings comes first', arrived=True)
        if facts.there:
            return arrived(facts, goal)
        return moved(facts, goal)
    if facts.in_reach:
        return Hold(goal)
    if not facts.attacking:
        return NoWay('no fresh press, and attack mode is off')
    if goal is not None and goal.do == PICK_UP:
        # Attack mode's side goal first: a potion a low belt restocks in the quiet (hunt.py `restocking`)
        return arrived(facts, goal) if facts.there else moved(facts, goal)
    if goal is not None and goal.do == FIGHT and goal.known and not facts.there:
        return moved(facts, goal)
    if goal is not None and goal.do == FIGHT and facts.there:
        return arrived(facts, goal)
    if goal is not None and goal.do == FIGHT:
        return NoWay(f'{goal.label}: nothing in reach, and its place is not known')
    return NoWay('nothing in reach and no fight to go to')


def routed(goal: Goal | None) -> TypeGuard[Goal]:
    """A route stage on the level, or something of the run's own to go to (`run_level`)."""
    return goal is not None and bool(goal.route or goal.do in (PICK_UP, WAIT) or goal.guarded or goal.clearing)


def ends_run(goal: Goal | None, pressed: bool) -> bool:
    """Whether `run_level` ends a level run on `goal` with no press: no route stage, or one that takes a press (the
    loot). BOSS_EXPLORE's test."""
    if pressed:
        return False
    if not routed(goal):
        return True
    return goal.do != ENTER and goal.do not in PURSUED


def unfound(facts: Facts) -> str:
    """'; 2 bosses alive on this level, its place not known: no room left' for an end with `bosses_left`, else ''."""
    count = facts.bosses_left
    if not BOSS_EXPLORE or count <= 0:
        return ''
    return f'; {count} boss{"es" if count > 1 else ""} of the ledger {BOSS_EXPLORE_SAID}: no room left to explore'


def run_level(facts: Facts, pressed: bool, pursuit: Pursuit | None = None) -> Act:
    """A level run's look without an `advance` press: what is in reach first, a drop on the way, then the route's
    stage of this level. What is left that is not this loop's ends the run, or is handed on with a fresh press."""
    goal = facts.goal
    if not routed(goal):
        # No route stage on this level: the key is its own step (a pickup, a chest, the sweep)
        if pressed:
            return Defer(None)
        if WAIT_FOR_MAP and not facts.mapped and facts.in_reach and facts.attacking:
            return Hold()  # the map's wait over and still no map: what is in reach is fought before the run ends
        return Ended(f'{NOTHING_LEFT}: no route stage, no boss known{unfound(facts)}')
    if goal.do == ENTER and not (facts.there and pressed):
        return to_the_door(facts, goal, pursuit)
    if goal.do not in PURSUED:
        if pressed:
            return Defer(goal)
        return Ended(f'what is left of the route is {goal.label}, which takes a press{unfound(facts)}')
    # The loop's run at its chest or drop with idle hostiles in reach: the open or pickup is offered, the price may
    # still hold. The player, 2026-10-17: "we don't even need to kill some trash mobs and can loot and leave";
    # "strikes on hp loss".
    if facts.in_reach and facts.attacking:
        if facts.rush and goal.do in OPERATED and not facts.hurt and not facts.settling:
            found = arrived(facts, goal) if facts.there else moved(facts, goal)
            if isinstance(found, Operate):
                return found
        return Hold(goal)
    if facts.settling:
        return NoWay('what the object used brings comes first', arrived=True)
    if facts.there:
        return arrived(facts, goal)
    return moved(facts, goal)


def to_the_door(facts: Facts, goal: Goal, pursuit: Pursuit | None = None) -> Act:
    """The route's way to another level, fighting on the way (goals.py `clear_way`; the player, 2026-10-14: "go to
    the level's goal clearing everything along the way"). A warp ends the run at it (going through takes a press,
    U13); an open passage (`Goal.crossed`) is walked through (`through`) and the run carries on."""
    if facts.in_reach and facts.attacking:
        return Hold(goal)
    if goal.crossed and pursuit is not None and not pursuit.may_enter(goal.mark.into if goal.mark else None):
        return Ended(f'{goal.label} leads off the trip: going through takes a press')
    if goal.crossed:
        return through(facts, goal)
    ended = Ended(f'at {goal.label}: going through takes a press')
    if facts.there:
        return ended
    found = moved(facts, goal)
    if isinstance(found, NoWay) and found.arrived and NO_STEP_LEFT in found.reason:
        return Ended(f'{found.reason}: going through takes a press')
    if isinstance(found, NoWay) and goal.near == ENTRY_GOAL_NEAR and facts.beyond + goal.near <= ENTRY_REACH:
        # No hop lands nearer the door's remembered entry (goals.py `way_out`): the press goes through from here
        # (teleport.py `step_toward`); the run once stood 48 s 5.4 units off it (12:46:41 on 2026-10-18)
        return Ended(f'{found.reason}, {facts.beyond + goal.near:.1f} from the entry: going through takes a press')
    return ended if isinstance(found, NoWay) and found.arrived else found


def through(facts: Facts, goal: Goal) -> Act:
    """An open passage on a level run: the goal's place is a tile inside the next level (levels/exits.py `through`),
    reached by the navigator as near as the ground goes, then one straight walk crosses. The player, 2026-10-15: "we
    need to move our target slightly further so the map changes"."""
    walk = Move(Step(goal.place), goal, f'{goal.label}: {PASSAGE}')
    if facts.there:
        return walk
    found = moved(facts, goal)
    if isinstance(found, NoWay) and (found.arrived or facts.beyond + goal.near <= THROUGH_WALK):
        # No hop lands nearer a passage a walk reaches: walked from here (Outer Steppes into the Plains of Despair,
        # 00:02:18 on 2026-10-20: "no footing in view brings the character nearer", 23 units off, 45 s idle)
        return walk
    return found


def entering(facts: Facts, goal: Goal) -> Act:
    """A fresh press for a way to another level: the navigator goes there, and the route's step takes the press
    once there (its click goes through, a move by other means does not; rca/2026-10-14/run-1932-findings.md §1.2.2).
    Without a way, the step is handed the press."""
    if facts.there:
        return Defer(goal)
    found = moved(facts, goal)
    if isinstance(found, Move):
        return found
    return Defer(goal)


def arrived(facts: Facts, goal: Goal) -> Act:
    """The goal is near enough: what is done there."""
    if goal.do in OPERATED:
        return Operate(goal)
    if facts.in_reach and facts.attacking:
        return Hold(goal)
    if goal.do == WAIT:
        # By a valuable with no room: held until there is room or a press goes on
        return NoWay(f'inventory full: {goal.label} here — make room', arrived=True)
    if goal.do != FIGHT:
        return NoWay(f'at {goal.label}', arrived=True)
    if not facts.attacking:
        return NoWay(f'{goal.label} is in reach: attack mode is off', arrived=True)
    if goal.unit is None:
        # The boss is yet to come to the fight's place
        return NoWay(f'{goal.label}: nothing in reach here yet', arrived=True)
    return NoWay(f'{goal.label} is in reach and is not struck (left alone for now)', arrived=True)


def moved(facts: Facts, goal: Goal) -> Act:
    """The next move toward the goal; on the navigator's arrival, what is done there; without a way, its reason."""
    found = facts.way()
    if isinstance(found, Step):
        return Move(found, goal)
    if found.arrived:
        if goal.do == FIGHT and not facts.in_reach and facts.attacking:
            return NoWay(f'{goal.label}: as near as a move ends, and nothing in reach ({found.reason})', arrived=True)
        return arrived(facts, goal)
    if facts.beyond < facts.least_move:
        # No step left and the goal nearer than any move: as near as it gets (run-1904-findings.md §3.4)
        done = arrived(facts, goal)
        if isinstance(done, NoWay) and done.arrived:
            near = f'{NO_STEP_LEFT}, {facts.beyond:.1f} units past its {goal.near:g}: {found.reason}'
            return NoWay(f'{done.reason} ({near})', arrived=True)
        return done
    return NoWay(f'no way toward {goal.label}: {found.reason}')


@dataclass
class Told:
    """What the loop last said of a decision that moved nothing, so the same reason is not said again."""

    reason: str | None = None

    def new(self, reason: str | None) -> bool:
        """Whether `reason` differs from the one before (None: a move or strike, nothing to say)."""
        changed = reason is not None and reason != self.reason
        self.reason = reason
        return changed

"""The pursuit: a press is an intent, and one decision per look says what is done about it
(rca/2026-10-13/kp4-findings.md §3.2 design B, §6; behind `BuildSettings.pursuit`, off by default).

Before it a press of the teleport key during attack mode was a routine of its own: it cancelled the mode,
ended the sweep, made its step or none, and held the mode back half a second after. Mashed by a pack the
mode never reached a strike (6.2 s by Vizier seal 1 at 09:06 on 2026-10-13), and with the route at a
fight whose boss stood out of reach nothing moved at all (48 presses, 25 s).

Here the press posts a `Pursuit` (which key, when) and returns: nothing is cancelled. The one loop that
makes the inputs (attack mode, hunt.py) looks at the game, names the goal the key means now
(macros/goals.py `goal_of`) and asks `decide`, which is pure:

- a fresh press whose goal is not near enough: `Move`, the next move toward the goal as the navigator
  gives it (macros/travel.py `Travel.toward`). The strike is given up for this act alone;
- a fresh press whose goal the route's own press still performs (a door, a border, the loot, the
  leaving): `Defer`, and the loop hands the press to that step; a door or a border only once the character is
  at it (`entering`): the way there is the navigator's, as for any goal;
- a fresh press whose goal is near enough: `Operate` (an object used, a stand noted, a drop taken), or
  for a fight `Hold`: the strike goes on, and no press takes it away;
- no fresh press: `Hold` with something in reach (the fight as it was). With nothing in reach and the
  goal a fight whose boss has a known place: `Move` to where it can be struck from, which is what ends
  "attack mode idles with the boss 52 units away". Otherwise `NoWay`, and the loop does what it did
  before (the sweep, the idle look).

Whatever is neither a move nor a strike is a `NoWay` with its reason, which the loop says once per
change (`Told`), not once per press. A press is fresh for FRESH seconds; a newer one replaces it, so a
held or mashed key only moves the stamp.

**The leash** (rca/2026-10-13/architecture-goals-navigation.md §2.1, Q4; rca/2026-10-13/kp1-level-run.md).
A press says how far the loop may go without another: `Pursuit.leash`. The teleport key's press is
`advance` (its goal now, before what is in reach) and leaves the leash as it was. The pickup key's is
not `advance` and sets the leash FULL on the level it was pressed on (the player, 2026-10-13: "one press
of KP_1, then it runs the whole level automatically"): with no fresh `advance` press, the loop then
holds what is in reach, takes a drop worth it on the way, and otherwise goes for the route's stage of
this level (reach, use, stand, fight) as if pressed, stage after stage, with no further press. How much of
the level it works (its goal, fighting what is on the way, or a full clear first) is the run mode's
(macros/runmode.py, 2026-10-14); a way to another level is gone to, and the run ends at a door (a warp: going
through it costs a press, U13), while an open passage is walked through (`through`, 2026-10-15) and the run goes on
as the run of the level it leads into (`carried`; the player, 2026-10-15: "it should carry into the Chaos Sanctuary
run"), in the same mode. It ends (`Ended`) when what is left of the route is not this loop's (the loot, the leaving,
a door), when nothing is known to go to, or when the level is left any other way (a waypoint, the town); the runner
ends it for attack mode off (KP_3) and the macro request (Mod+X). A fresh pickup press whose goal is the
route's own press (the loot, the leaving) or none is handed to the old pickup step (`Defer`), which is what
the key did at the end of a route before.

**The player's hand pauses a run, it does not end it** (the player, 2026-10-13: "we shouldn't prevent user
from sorting"; asked whether the run should resume on its own after the hand: "yes";
rca/2026-10-13/run-2110-findings.md moment 2). The hand wins at once (I7: a click is the player's move, a panel
open is never clicked into): the record is `paused`, and while it is the loop does only what attack mode
does with no run, the strike at what is in reach (a fresh teleport press still asks for its goal). The run
goes on by itself once the hand has been still SETTLE seconds with no panel open (`settled`); a fresh pickup
press starts it anew at once; attack mode off, the macro request and the level left still end it.

**A valuable with no room for it** (the player, 2026-10-13: "when valuable doesn't fit: we need to stop near
it"): a goal of its own, `WAIT` by the drop, in the run's order where a drop to take would be. The character
goes next to it and stays (what comes is fought, as the arbiter prices it), saying so, until there is room
(the drop is then one to take: a pickup goal) or the player goes on (a fresh press lets it go).
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from inventory_tracking.combat.harm import Harm, SafetySettings, veto
from inventory_tracking.macros.build import Leg, NoWay, Step
from inventory_tracking.macros.goals import ENTRY_GOAL_NEAR, PICK_UP, PURSUED, WAIT, Goal
from inventory_tracking.routes.model import ENTER, FIGHT, STAND, USE


# Seconds a press stands for "go on": the longest gap between two presses of a player who keeps going
# (kp4-findings.md §2.4, §2.5: 0.2 to 0.4 s between the presses of a mashed key, 40 to 700 ms from the end
# of a step to the next press of a travelling player). A key not pressed again within it has been let
# go, and the character stops at the latest that long after. It is under the 1.0 s a queued press is
# worth beginning (runner.py EXPIRES), so no move is begun for a press older than that.
FRESH = 0.7
# Seconds the player's hand is still (no click, no pointer moved by it, no panel open) before a paused level
# run goes on by itself. The game of 21:10 on 2026-10-13 (take 20261013T181240Z-108, run2110_hands.py): while
# the player sorted and walked back by hand the hand was never still longer than 0.43 s with the panels closed
# (21:14:08.7-11.4, 21:15:28-31.5) nor 1.01 s with the inventory open (21:14:04.7-05.7); the first press of
# KP_1 came 0.31 s after the hand's last move (21:14:11.37 -> 11.68).
SETTLE = 1.5
PAUSED = "the level run is paused: the player's hand"  # said once a pause, and the loop's reason meanwhile
OPERATED = frozenset((USE, STAND, PICK_UP))  # the goals something is done at; at the others the character only is
# How far the loop goes without a fresh press (architecture §2.1): NONE, nowhere of its own; FULL, the route's
# stages of the level the press was made on, objects included, and the drops worth a stop on the way.
NONE, FULL = 'none', 'full'
# Seconds a run carried into a level across its way out (`carried`) waits for that level's card before it finds
# nothing to go to there: the level guide sees a new level at its next poll (every 0.5 s, config.py
# level_guide_poll_interval) and then reads its rooms and walls, and until then the card is still the level left
# (hunt.py `goal`: none). A fresh run is a press made with the card up; this one comes with the crossing.
ENTERING = 3.0
ENTERING_SAID = 'the level is being read: the run goes on once its card is up'


@dataclass(frozen=True)
class Pursuit:
    """The mailbox: the key last pressed and when (the clock the loop reads). The goal is not kept: it is
    named anew from the game at every look, so a goal reached, a boss dead or a stage done changes it
    without a press. `advance`: the press asks for its goal now, before what is in reach (the teleport
    key); `leash`: how far the loop goes without one (the module text), on level `area` (None until the
    loop's first look names it); `spent`: the press was handed to a routine and asks for nothing more;
    `paused`: the player's hand has the run (the module text), which then goes on by itself. `onward`: the level
    the run's way out leads into, noted once the run goes for an open passage (`heading`): the level change into it
    carries the run on (`carried`); `entered`: when the run was carried into its level (the clock), None for a run
    pressed on it. `rush`: the KP_6 loop's run (the player, 2026-10-16: "don't fight what isn't attacking", for the loop
    only): its goal first, a strike only where the arbiter prices it under the move (`arbitrate`, no strike gap)."""

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
    # Posted by the KP_6 loop's leg (runner.py `_loop_level_run`): no key's press, so never half of a double press,
    # and a run of its own, not the one before (a game's last run held into the next: two posts 0.35 s apart switched
    # the run to a full clear of Catacombs Level 2, 80 s, 10:26:40 on 2026-10-18)
    looped: bool = False
    # The terror zone kinds' level run (macros/tzloop.py, goals-plan.md): its targets are the agenda's
    # (`Hunter.agenda_target`, agenda.py `Agenda.in_level`), the route's stage of the level after them
    agenda: bool = False

    def fresh(self, now: float) -> bool:
        """Whether the press still asks for a move: made no longer than FRESH ago (and not after `now`:
        a clock that went back keeps nothing alive), and not handed on."""
        return not self.spent and 0.0 <= now - self.pressed_at <= FRESH

    @property
    def leashed(self) -> bool:
        """Whether a level run is held (the leash FULL), working or paused by the player's hand."""
        return self.leash == FULL

    @property
    def runs(self) -> bool:
        """Whether a level run works now: held and not paused (what the loop and its pricing go by)."""
        return self.leash == FULL and not self.paused

    def entering(self, now: float) -> bool:
        """Whether the run was carried into its level less than ENTERING seconds ago (`carried`)."""
        return self.entered is not None and 0.0 <= now - self.entered <= ENTERING


def heading(pursuit: Pursuit, goal: Goal | None) -> Pursuit | None:
    """The level run with the level its way out leads into noted (`Pursuit.onward`), once its goal is an open
    passage (`Goal.crossed`) that names one (levels/model.py `Target.into`); None: nothing to note (no run, another
    goal, or noted already). A door's way out is no crossing of the run's: going through it takes a press."""
    if not pursuit.leashed or goal is None or not goal.crossed or goal.mark is None:
        return None
    into = goal.mark.into
    if into is None or into == pursuit.area or into == pursuit.onward:
        return None
    return replace(pursuit, onward=into)


def carried(pursuit: Pursuit, area: int | None, now: float) -> Pursuit | None:
    """The level run carried on into level `area` (the module text): the run that went for its level's open passage
    (`heading`) is the run of the level it crossed into, from `now`, once (`onward` is spent with it), working or
    paused as it was. None: no run, the same level, or a level the run's way out does not lead into (a waypoint, the
    town, the player's own way): that ends the run (`decide`: the level was left)."""
    if not pursuit.leashed or pursuit.area is None or area is None or area == pursuit.area or area != pursuit.onward:
        return None
    return replace(pursuit, area=area, onward=None, entered=now)


def settled(hand_at: float, now: float, panels: bool) -> bool:
    """Whether a run paused by the player's hand goes on: the hand still SETTLE seconds since `hand_at` (its
    last click, pointer move or panel seen) and no panel open now (I7: nothing is clicked into one)."""
    return not panels and now - hand_at >= SETTLE


@dataclass(frozen=True)
class Facts:
    """What one decision is made from, read by the loop at one look. `way` is the navigator's answer for
    the goal's place, asked only when a move is wanted."""

    now: float
    goal: Goal | None  # what the key means now (goals.py `goal_of`); None: nothing is known to go to
    there: bool  # the goal is near enough: within `Goal.near` of its place (a fight: with a shot at it)
    in_reach: bool  # a hostile stands in the attack's reach
    attacking: bool  # attack mode is on: what is in reach is struck
    way: Callable[[], Leg]  # the next move toward the goal by the means in hand, or why there is none
    area: int | None = None  # the level the character is on (a level run ends off its own level)
    # An act is still in flight: an object used brings what it calls (a seal's pack) within that time
    # (teleport.py `Use.brings`). A level run begins no move before it is over (architecture §2.6, `Wait`).
    settling: bool = False
    candidates: tuple[Candidate, ...] = ()
    priced: bool = False
    budget: float = 0.0
    life: float = float('inf')
    kappa: float = 0.0
    safety: SafetySettings = field(default_factory=SafetySettings)
    quiet: float = 0.0  # seconds since the fight last saw a strike, counted while `near`
    near: bool = False  # a hostile within the strike's reach, a clear line or not: the strike gap counts (I2)
    rush: bool = False  # the KP_6 loop's run (`Pursuit.rush`): no strike gap, the price alone
    hurt: bool = False  # life lost within HURT_SECONDS (hunt.py `safety_priced`): the loop's run may stand and strike
    # Units the character stands past the goal's `near`, for a goal whose arrival is a distance from its place (a
    # place, a door); inf for the others. Under `least_move`, the shortest move the navigator makes (a walk along the
    # way: travel.py AROUND_LEAST), a way with no step left is an arrival (`moved`).
    beyond: float = math.inf
    least_move: float = 0.0


@dataclass(frozen=True)
class Move:
    """Go: one move toward `goal`, by the way the navigator chose. `dodge`: a step out of a hostile's act under way,
    its missiles in flight (a read model's escape, combat/threats `Threat.escapes`): a move in flight the strike gap
    does not hold (I2, `arbitrate`), whose click is made without the settle (macros/travel.py `step_walk` `hurry`)."""

    step: Step
    goal: Goal
    reason: str = ''
    dodge: bool = False


@dataclass(frozen=True)
class Hold:
    """Stay and strike what is in reach (the fight as it is)."""

    goal: Goal | None = None
    reason: str = ''


@dataclass(frozen=True)
class Operate:
    """Do what is done at the goal: use its object, note the stand, take the drop."""

    goal: Goal


@dataclass(frozen=True)
class Defer:
    """The goal is one the route's own press performs (a door or a border to go through, the loot, the
    leaving): the loop hands the press to that step as it was, and says so. None: the key's own routine
    takes the press (a pickup press on a level with nothing for the run to go to)."""

    goal: Goal | None


@dataclass(frozen=True)
class Ended:
    """The level run is over (the module text): the leash goes back to none, and `reason` is said."""

    reason: str


Act = Move | Hold | Operate | Defer | Ended | NoWay


@dataclass(frozen=True)
class Candidate:
    act: Act
    seconds: float
    harm: Harm
    retreat: bool = False
    # Seconds the act keeps the character from striking (the move, the swap back the strike needs, a use's walk
    # and dwell): the arbiter's strike gap (I2). 0: a strike.
    unstruck: float = 0.0
    strikes: bool = False  # the act ends with a hostile in the strike's reach and a clear line: a strike follows
    # A retreat that ends within the strike's reach of the hostile whose kill ends most of the harm (macros/safety.py
    # `keeper`): the fight goes on from it, so the retreat does not throw the fight (rca/2026-10-14/baal-sim.md fix 1).
    keeps: bool = False


RUSH_HARM_SHARE = 0.05  # of the life: the harm a move or a use of the loop's run may be priced at over a hold
NO_STEP_LEFT = 'no step toward it is left'  # the arrival said for that (`moved`)
ENTRY_REACH = 10.0  # units from a door's entry with no way nearer: the run ends there (`to_the_door`; NEAR_WARP)
FIRING_SPOT = 'firing spot'  # the reason of a move to a stand the strike is made from (macros/safety.py FIRING)
PASSAGE = 'an open passage: walking through into the next level'  # `through`'s move, said once
KEEPING = 'retreating within strike reach: no act here fits the life budget'  # `Macro: pursuit: retreating within ...`
# The approach to a level run's boss is not held to the strike gap while nothing hurts (`onward`): F1 of
# rca/2026-10-18/andariel-cadence-findings.md §5, the player at 18:00 on 2026-10-18: "F1: ok". After A1 the Teleport
# toward Andariel landed among her pack 0.6 to 0.9 s after the last strike, the gap's room left only the hold, and every
# hop cost a strike: 1.34 s a hop cycle where a chained hop takes ~0.6 s, 1.96 s a fight (§2.1; 11:41:45.63, take
# 084143Z-37). Off: I2 as it was, so the change is measured alone (arrival -> Andariel dead, median 7.60 s on 23 games).
RUSH_THE_BOSS = True


def the_runs_boss(goal: Goal | None, pursuit: Pursuit | None) -> bool:
    """Whether `goal` is the boss of the route's fight stage (goals.py `fight_goal`) on a level run that works: not a
    fight on its way or of the rest of the level (`Goal.clearing`), not a goal of the key's own press."""
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
    """The moves toward a level run's boss that the strike gap does not hold (RUSH_THE_BOSS): while nothing hurts the
    character (`Facts.hurt`), the navigator's own moves toward the goal no more harmful than the hold, by the rush
    branch's test (`arbitrate`: the least harm of a hold, or RUSH_HARM_SHARE of the life). None otherwise."""
    if not RUSH_THE_BOSS or facts.hurt or not the_runs_boss(facts.goal, pursuit):
        return []
    holds = [c for c in feasible if isinstance(c.act, Hold)]
    if not holds:
        return []
    least = max(min(c.harm.mean for c in holds), RUSH_HARM_SHARE * facts.life)
    return [c for c in feasible if isinstance(c.act, Move) and not c.act.reason and c.harm.mean <= least]


def arbitrate(facts: Facts, pursuit: Pursuit | None = None) -> Act:
    """One price in seconds, constrained by both life budget and the unliftable veto. `pursuit`: the mailbox, for a
    level run's boss (`onward`); None: no run."""
    if facts.rush:
        # The KP_6 loop's run fights only what the price makes it: a stand to fire from is the fight's, priced by its
        # clear time, and it outpriced the chest itself (22:04:12 on 2026-10-16: 16 walks to one in 17 s, none taken;
        # rca/2026-10-16/loop-shack-stalls-findings.md §1). A dodge and a retreat stay.
        kept = tuple(c for c in facts.candidates if not (isinstance(c.act, Move) and c.act.reason == FIRING_SPOT))
        holds = [c for c in kept if isinstance(c.act, Hold)]
        if holds and not facts.hurt:
            # Nor a stand to strike from where nothing has hurt the character and moving on is no more harmful: 94% of
            # the loop's strikes followed no loss of life in the 3 s before, 3.5 s a stay (rca/2026-10-17/
            # movement-findings.md §4 #1). A hostile that costs life on the way is still fought (2026-10-16).
            # The harm priced for an open or a move among idle hostiles is over the hold's and still small: at 02:22:26
            # on 2026-10-17 the run stood 1.7 s by a shack's chest and then struck. A move or a use priced under
            # RUSH_HARM_SHARE of the life is made; one dearer is still fought for (300 of 1,784 life, 2026-10-16).
            least = max(min(c.harm.mean for c in holds), RUSH_HARM_SHARE * facts.life)
            moving = tuple(c for c in kept if not isinstance(c.act, Hold))
            if any(veto(c.harm, facts.life, facts.safety) is None and c.harm.mean <= least for c in moving):
                kept = moving
        facts = replace(facts, candidates=kept)
    allowed = [c for c in facts.candidates if veto(c.harm, facts.life, facts.safety) is None]
    feasible = [c for c in allowed if c.harm.worst <= facts.budget and not c.retreat]
    if facts.near and facts.attacking and not facts.rush:
        # The KP_6 loop's run has none: its chests first, a strike only where the price has it (a hostile that costs
        # life on the way), not every Hell Buzzard in the blades' 22 units (rca/2026-10-16/loop-chests-findings.md §1).
        # No attack pause (I2): while a hostile is within the strike's reach, the act is one after which a strike
        # comes within `strike_gap` of the last, whenever such an act fits the budget (a strike here first, an act
        # that waits for one more strike, a firing stand before a walk). A retreat is not held to it, nor is a step
        # out of an act under way (`Move.dodge`: "unless a move is in flight", I2): the missiles in flight bound it
        # to their act (Diablo's stream is under 1.9 s; rca/2026-10-14/diablo-handling.md fix 1), and a strike
        # there gave its place to the hold (R2: 5 of 6 priced fights).
        # With the gap already spent (no strike yet), the acts that strike soonest.
        striking = [c for c in feasible if c.strikes]
        if striking:
            room = max(facts.safety.strike_gap - facts.quiet, min(c.unstruck for c in striking))
            # Nor a move toward a level run's boss while nothing hurts (`onward`, RUSH_THE_BOSS: the player, 18:00 on
            # 2026-10-18): the hops chain to her and the strike is held where she is in reach; the first loss of life
            # makes I2 whole again. The key's own press and every other goal keep the gap (KP_1's Diablo and seals
            # see it only through `hurt`).
            rushed = onward(facts, feasible, pursuit)
            feasible = [
                c
                for c in feasible
                if (c.strikes and c.unstruck <= room) or (isinstance(c.act, Move) and c.act.dodge) or c in rushed
            ]
    if feasible:

        def price(c: Candidate) -> float:
            return c.seconds + facts.kappa * c.harm.mean

        chosen = min(feasible, key=price)
        holding = next((c for c in feasible if isinstance(c.act, Hold)), None)
        if holding is not None and isinstance(chosen.act, Move) and chosen.act.reason == 'firing spot':
            improvement = price(holding) - price(chosen)
            if improvement < max(facts.safety.commit_seconds, price(holding) * facts.safety.commit_share):
                return holding.act
        return chosen.act
    escapes = [c for c in allowed if c.retreat]
    # A retreat that keeps the strike on what ends the harm and fits the budget comes first, the cheapest of them by
    # the same price (the nearest such place, as a rule): one out of reach only defers the harm, as the hostile does
    # not die meanwhile (rca/2026-10-14/baal-sim.md weakness 2: 4.5 s a fight out of Baal's reach). Else the least harm.
    keeping = [c for c in escapes if c.keeps and isinstance(c.act, Move) and c.harm.worst <= facts.budget]
    if keeping:
        kept = min(keeping, key=lambda c: c.seconds + facts.kappa * c.harm.mean)
        assert isinstance(kept.act, Move)
        return Move(kept.act.step, kept.act.goal, KEEPING)
    if escapes:
        chosen = min(escapes, key=lambda c: (c.harm.mean, c.harm.worst, c.seconds))
        if isinstance(chosen.act, Move):
            return Move(chosen.act.step, chosen.act.goal, 'retreating: no progress act fits the life budget')
        if isinstance(chosen.act, Hold):
            return Hold(chosen.act.goal, 'fighting out: less harm than any reachable retreat')
        return chosen.act
    if not facts.candidates:
        return NoWay('safety: no act was priced')

    # Every priced act is vetoed: no safe act exists at this look (I3 does not apply). Standing still without a
    # strike is no escape either (it is priced as one where it is an act: the idle candidate), so the act whose
    # rollouts are the least often lethal is made, and said: never a stop that strikes nothing.
    def lethal(c: Candidate) -> float:
        return sum(loss >= facts.life for loss in c.harm.losses) / max(len(c.harm.losses), 1)

    chosen = min(facts.candidates, key=lambda c: (bool(c.harm.barred), lethal(c), c.harm.mean, c.seconds))
    said = 'safety: every act is vetoed; the least lethal is'
    if isinstance(chosen.act, Move):
        return Move(chosen.act.step, chosen.act.goal, f'retreating: {said} this move')
    if isinstance(chosen.act, Hold):
        return Hold(chosen.act.goal, f'fighting out: {said} the fight')
    if isinstance(chosen.act, NoWay):
        return NoWay(f'{said} standing here')
    return chosen.act


def decide(facts: Facts, pursuit: Pursuit | None, enabled: bool = True) -> Act:
    """What the loop does at this look (the module text). `enabled`: the build's switch
    (`BuildSettings.pursuit`); off, the answer is the old loop's own: hold what is in reach, else nothing."""
    goal = facts.goal
    if not enabled:
        return Hold() if facts.in_reach else NoWay('the pursuit is off')
    if facts.priced or facts.candidates:
        return arbitrate(facts, pursuit)
    pressed = pursuit is not None and pursuit.fresh(facts.now)
    if pursuit is not None and pursuit.leashed:
        if pursuit.area is not None and facts.area is not None and facts.area != pursuit.area:
            return Ended('the level was left')
        if not (pressed and pursuit.advance):
            if pursuit.paused:
                # The player's hand has the run: attack mode's own strike at what is in reach, no move of the run's
                return Hold(goal) if facts.in_reach and facts.attacking else NoWay(PAUSED)
            if goal is None and pursuit.entering(facts.now):
                # Carried into the level a moment ago (`carried`): its card is not up yet, which ends nothing
                return Hold() if facts.in_reach and facts.attacking else NoWay(ENTERING_SAID)
            return run_level(facts, pressed)
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
            # The act before is still in flight (a seal's pack is about to come): a wait of a second at most, said,
            # and the strike held meanwhile. The press is answered, not refused (architecture §2.6, `Wait`).
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
        # Attack mode's own side goal before its standing one: a potion a low belt restocks in the quiet (hunt.py
        # `restocking`; the player, 2026-10-14), gone to and picked up as a level run's drop is
        return arrived(facts, goal) if facts.there else moved(facts, goal)
    if goal is not None and goal.do == FIGHT and goal.known and not facts.there:
        return moved(facts, goal)
    if goal is not None and goal.do == FIGHT and facts.there:
        return arrived(facts, goal)
    if goal is not None and goal.do == FIGHT:
        return NoWay(f'{goal.label}: nothing in reach, and its place is not known')
    return NoWay('nothing in reach and no fight to go to')


def run_level(facts: Facts, pressed: bool) -> Act:
    """A level run's look with no fresh press that asks for its goal now (the module text): what is in
    reach first, a drop on the way next, then the route's stage of this level as a press would have it.
    What is left that is not this loop's ends the run, or with a fresh pickup press is handed on."""
    goal = facts.goal
    if goal is None or (not goal.route and goal.do not in (PICK_UP, WAIT) and not goal.guarded and not goal.clearing):
        # No route on this level (only the card's own mark, or nothing): the run has no stage to work, and the
        # key is what it was without one (its own step: a pickup, a chest, the sweep)
        if pressed:
            return Defer(None)
        return Ended('nothing is left to go to on this level: no route stage, no boss known')
    if goal.do == ENTER and not (facts.there and pressed):
        return to_the_door(facts, goal)
    if goal.do not in PURSUED:
        if pressed:
            return Defer(goal)
        return Ended(f'what is left of the route is {goal.label}, which takes a press')
    # The KP_6 loop's run at its chest or drop with idle hostiles in reach: the open or the pickup is offered, not a
    # stand alone; the price may still hold (`arbitrate`). Offered only a hold, it stood RUSH_UNMOVED and then struck,
    # about 4 s at a chest (19:21:34 on 2026-10-17: 4 away from it, 1.7 s standing, 2.3 s of strikes, then opened;
    # 30 of 31 strikes from 19:20 to 19:35 followed no loss of life). The player, 2026-10-17: "we don't even need to
    # kill some trash mobs and can loot and leave"; "strikes on hp loss". Arrived as the navigator has it too (`moved`:
    # no step left), 2-3 units off a chest whose `near` is less (19:41:17 on 2026-10-17, the first change missed it).
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


def to_the_door(facts: Facts, goal: Goal) -> Act:
    """The route's way on to another level is what is left of it here: the run goes to it, fighting what is in reach
    and what the goal names on the way (macros/goals.py `clear_way`). The player, 2026-10-14: "go to the level's goal
    clearing everything along the way" (rca/2026-10-14/kp1-mode.md). A door, stairs, a cave's mouth (a warp): the run
    ends at it, and going through takes a press (U13). An open passage (`Goal.crossed`: the River of Flame's bridge
    into the Chaos Sanctuary, a border) is walked through (`through`), and the run goes on in the next level
    (`carried`)."""
    if facts.in_reach and facts.attacking:
        return Hold(goal)
    if goal.crossed:
        return through(facts, goal)
    ended = Ended(f'at {goal.label}: going through takes a press')
    if facts.there:
        return ended
    found = moved(facts, goal)
    if isinstance(found, NoWay) and found.arrived and NO_STEP_LEFT in found.reason:
        return Ended(f'{found.reason}: going through takes a press')
    if isinstance(found, NoWay) and goal.near == ENTRY_GOAL_NEAR and facts.beyond + goal.near <= ENTRY_REACH:
        # The door's remembered entry (goals.py `way_out`) no hop lands nearer to: the press goes through from here (its
        # step walks or hops onto the entry, teleport.py `step_toward`). The run stood 48 s 5.4 units off it with "no
        # footing in view brings the character nearer by hops" (12:46:41 on 2026-10-18)
        return Ended(f'{found.reason}, {facts.beyond + goal.near:.1f} from the entry: going through takes a press')
    return ended if isinstance(found, NoWay) and found.arrived else found


def through(facts: Facts, goal: Goal) -> Act:
    """An open passage on a level run (the player, 2026-10-15: "the player doesn't go to the Chaos Sanctuary when only
    KP_1 was pressed; we need to move our target slightly further so the map changes"). The goal's place is a tile
    inside the next level (levels/exits.py `through`), off this level's ground: the navigator's way, by the class in
    hand, goes as near as the ground goes, and from within the goal's `near` (or where no step toward it is left) one
    straight walk to the place crosses, in either input mode. The level changed carries the run on as the next
    level's (`carried`: the player, 2026-10-15, "it should carry into the Chaos Sanctuary run")."""
    walk = Move(Step(goal.place), goal, f'{goal.label}: {PASSAGE}')
    if facts.there:
        return walk
    found = moved(facts, goal)
    return walk if isinstance(found, NoWay) and found.arrived else found


def entering(facts: Facts, goal: Goal) -> Act:
    """A fresh press whose goal is a way to another level (a door, a border): the press is a goal, not a step. The
    character goes to the way's place by the navigator, as a level run goes to it (`to_the_door`), and the route's
    own step takes the press once it is there: going through (the door's click) is that step's, which a move by
    other means does not do (rca/2026-10-14/run-1932-findings.md §1.2.2: handed on from 43 units off with the staff
    empty, the old step walked toward a place a Teleport would land on, into a pocket 276 units by the walked way
    from the door, three times). Where the navigator has no way, the step is handed the press as before."""
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
        # Stood by a valuable with no room for it: said, and held here until there is room or a press goes on
        return NoWay(f'inventory full: {goal.label} here — make room', arrived=True)
    if goal.do != FIGHT:
        return NoWay(f'at {goal.label}', arrived=True)
    if not facts.attacking:
        return NoWay(f'{goal.label} is in reach: attack mode is off', arrived=True)
    if goal.unit is None:
        # The fight's place is where its boss is to come (its mark, where one was last seen): nothing there yet
        return NoWay(f'{goal.label}: nothing in reach here yet', arrived=True)
    return NoWay(f'{goal.label} is in reach and is not struck (left alone for now)', arrived=True)


def moved(facts: Facts, goal: Goal) -> Act:
    """The next move toward the goal; where the navigator says the character is there already, what is
    done there; where it has no way, its reason with the goal's name."""
    found = facts.way()
    if isinstance(found, Step):
        return Move(found, goal)
    if found.arrived:
        if goal.do == FIGHT and not facts.in_reach and facts.attacking:
            return NoWay(f'{goal.label}: as near as a move ends, and nothing in reach ({found.reason})', arrived=True)
        return arrived(facts, goal)
    if facts.beyond < facts.least_move:
        # The way has no step left, and the goal is nearer than any move could bring it: as near as it gets (the
        # River's door, 22:08:45 on 2026-10-14: 23 s standing 0.5 units past its 5, run-1904-findings.md §3.4)
        done = arrived(facts, goal)
        if isinstance(done, NoWay) and done.arrived:
            near = f'{NO_STEP_LEFT}, {facts.beyond:.1f} units past its {goal.near:g}: {found.reason}'
            return NoWay(f'{done.reason} ({near})', arrived=True)
        return done
    return NoWay(f'no way toward {goal.label}: {found.reason}')


@dataclass
class Told:
    """What the loop last said of a decision that moved nothing: the same reason is not said again."""

    reason: str | None = None

    def new(self, reason: str | None) -> bool:
        """Whether `reason` differs from the one before (None: a move or a strike, nothing to say)."""
        changed = reason is not None and reason != self.reason
        self.reason = reason
        return changed

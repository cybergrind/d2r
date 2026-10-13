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
  leaving): `Defer`, and the loop hands the press to that step;
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
this level (reach, use, stand, fight) as if pressed, stage after stage, with no further press. It ends
(`Ended`) when what is left of the route is not this loop's (the loot, the leaving, a way to another
level: those cost a press, U13), when nothing is known to go to, or when the level is left; the runner
ends it for attack mode off (KP_3), the macro request (Mod+X) and the player's own move by hand. A fresh
pickup press whose goal is the route's own press (the loot, the leaving) or none is handed to the old
pickup step (`Defer`), which is what the key did at the end of a route before.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from inventory_tracking.combat.harm import Harm, SafetySettings, veto
from inventory_tracking.macros.build import Leg, NoWay, Step
from inventory_tracking.macros.goals import PICK_UP, PURSUED, Goal
from inventory_tracking.routes.model import FIGHT, STAND, USE


# Seconds a press stands for "go on": the longest gap between two presses of a player who keeps going
# (kp4-findings.md §2.4, §2.5: 0.2 to 0.4 s between the presses of a mashed key, 40 to 700 ms from the end
# of a step to the next press of a travelling player). A key not pressed again within it has been let
# go, and the character stops at the latest that long after. It is under the 1.0 s a queued press is
# worth beginning (runner.py EXPIRES), so no move is begun for a press older than that.
FRESH = 0.7
OPERATED = frozenset((USE, STAND, PICK_UP))  # the goals something is done at; at the others the character only is
# How far the loop goes without a fresh press (architecture §2.1): NONE, nowhere of its own; FULL, the route's
# stages of the level the press was made on, objects included, and the drops worth a stop on the way.
NONE, FULL = 'none', 'full'


@dataclass(frozen=True)
class Pursuit:
    """The mailbox: the key last pressed and when (the clock the loop reads). The goal is not kept: it is
    named anew from the game at every look, so a goal reached, a boss dead or a stage done changes it
    without a press. `advance`: the press asks for its goal now, before what is in reach (the teleport
    key); `leash`: how far the loop goes without one (the module text), on level `area` (None until the
    loop's first look names it); `spent`: the press was handed to a routine and asks for nothing more."""

    key: str
    pressed_at: float
    advance: bool = True
    leash: str = NONE
    area: int | None = None
    spent: bool = False

    def fresh(self, now: float) -> bool:
        """Whether the press still asks for a move: made no longer than FRESH ago (and not after `now`:
        a clock that went back keeps nothing alive), and not handed on."""
        return not self.spent and 0.0 <= now - self.pressed_at <= FRESH

    @property
    def runs(self) -> bool:
        """Whether a level run is on (the leash FULL)."""
        return self.leash == FULL


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


@dataclass(frozen=True)
class Move:
    """Go: one move toward `goal`, by the way the navigator chose."""

    step: Step
    goal: Goal
    reason: str = ''


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


def arbitrate(facts: Facts) -> Act:
    """One price in seconds, constrained by both life budget and the unliftable veto."""
    allowed = [c for c in facts.candidates if veto(c.harm, facts.life, facts.safety) is None]
    feasible = [c for c in allowed if c.harm.worst <= facts.budget and not c.retreat]
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
    if escapes:
        chosen = min(escapes, key=lambda c: (c.harm.mean, c.harm.worst, c.seconds))
        if isinstance(chosen.act, Move):
            return Move(chosen.act.step, chosen.act.goal, 'retreating: no progress act fits the life budget')
        if isinstance(chosen.act, Hold):
            return Hold(chosen.act.goal, 'fighting out: less harm than any reachable retreat')
        return chosen.act
    # Never select a vetoed action, even when all the choices are bad.
    return NoWay('safety: no unvetoed retreat is reachable')


def decide(facts: Facts, pursuit: Pursuit | None, enabled: bool = True) -> Act:
    """What the loop does at this look (the module text). `enabled`: the build's switch
    (`BuildSettings.pursuit`); off, the answer is the old loop's own: hold what is in reach, else nothing."""
    goal = facts.goal
    if not enabled:
        return Hold() if facts.in_reach else NoWay('the pursuit is off')
    if facts.priced or facts.candidates:
        return arbitrate(facts)
    pressed = pursuit is not None and pursuit.fresh(facts.now)
    if pursuit is not None and pursuit.runs:
        if pursuit.area is not None and facts.area is not None and facts.area != pursuit.area:
            return Ended('the level was left')
        if not (pressed and pursuit.advance):
            return run_level(facts, pressed)
    if pursuit is not None and pressed:
        if goal is None:
            return NoWay('the key has nothing to go to: no stage, no mark and no boss is known here')
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
    if goal is None or (not goal.route and goal.do != PICK_UP):
        # No route on this level (only the card's own mark, or nothing): the run has no stage to work, and the
        # key is what it was without one (its own step: a pickup, a chest, the sweep)
        if pressed:
            return Defer(None)
        return Ended('nothing is left to go to on this level: no route stage, no boss known')
    if goal.do not in PURSUED:
        if pressed:
            return Defer(goal)
        return Ended(f'what is left of the route is {goal.label}, which takes a press')
    if facts.in_reach and facts.attacking:
        return Hold(goal)
    if facts.settling:
        return NoWay('what the object used brings comes first', arrived=True)
    if goal.do == PICK_UP:
        return Operate(goal)
    if facts.there:
        return arrived(facts, goal)
    return moved(facts, goal)


def arrived(facts: Facts, goal: Goal) -> Act:
    """The goal is near enough: what is done there."""
    if goal.do in OPERATED:
        return Operate(goal)
    if facts.in_reach and facts.attacking:
        return Hold(goal)
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

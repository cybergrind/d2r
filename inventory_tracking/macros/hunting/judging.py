"""What a look does with its goal: the judge, the safety pricing, the escort and the guard. A part of
macros/hunt.py `Hunter`, its methods bound there."""

import itertools
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from inventory_tracking.combat import pack as herald_pack, threats
from inventory_tracking.combat.escort import around, escorts, in_danger, kept_alive
from inventory_tracking.combat.harm import harm, veto
from inventory_tracking.combat.policy import STRIKE_REACH, observe
from inventory_tracking.combat.stance import no_footing
from inventory_tracking.combat.survival import pressure
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import LYING_DEAD, NO_OWNER
from inventory_tracking.game.records import HEALING, Monster, World
from inventory_tracking.levels.model import SUPER_CHEST, UNIQUE_CHEST, Ground
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros import pursuit as pursuit_rules, route, zonenav
from inventory_tracking.macros.actuator import Abort, Cancelled
from inventory_tracking.macros.bossledger import Boss, said as bosses_said
from inventory_tracking.macros.build import NoWay, PricedStep
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import PICK_UP, WAIT, Goal, rest_of_level
from inventory_tracking.macros.hunting import choice, moves, revive, shrines
from inventory_tracking.macros.hunting.base import (
    BLOCK_SECONDS,
    COMES_TO_ITS_MARK,
    DECIDE_SECONDS,
    EMPTY_MARK_GOES_ON,
    FIRING_STAND,
    HURT_SECONDS,
    MARK_WAIT,
    NO_WAY_ENDS,
    NO_WAY_TO,
    OPEN_NEAR,
    PAIR_NEAR,
    SAID_AGAIN,
    SEEK_WAIT,
    SWAP_RETRY_SECONDS,
    UNSHOT_SECONDS,
    UNTOUCHABLE_SECONDS,
    YIELD_FRESH,
    YIELD_MOVED,
    YIELD_TAKES,
    Judged,
    paired,
)
from inventory_tracking.macros.pursuit import (
    FIRING_SPOT,
    Candidate,
    Defer,
    Ended,
    Facts,
    Hold,
    Move as Advance,
    Operate,
    Pursuit,
    carried,
    decide,
    ends_run,
    heading,
    the_runs_boss,
)
from inventory_tracking.macros.safety import AWAY, STEPPING
from inventory_tracking.macros.sight import RING_STEP, firing_spots, in_reach as in_reach_of
from inventory_tracking.macros.teleport import SPOT_NEAR, marked_thing
from inventory_tracking.macros.travel import (
    AROUND_LEAST,
    GROWING,
    SAFE_MOVE,
    STANDING,
    Point,
    Step,
    label,
    open_reaches,
    walk_reaches,
)
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import FIGHT, LEAVE, LOOT, USE


if TYPE_CHECKING:
    from inventory_tracking.macros.hunt import Hunter


# A chest is opened from where the character stands only where the walk to it is not round a wall (travel.py
# `open_reaches`) on every level run, not on the LK chests kind's (`Pursuit.rush`) alone. 02:32-02:40 on 2026-10-21
# (the act loop, an agenda kind, rush off; Kurast Bazaar, Upper and Lower Kurast): the super chests in the camp huts
# were clicked from 8.5-10 units outside their walls, where the walk round is 47-108 units or none; the game moved
# nobody, 15 clicks and 6 give-ups in 9 minutes (~40 s), 2 of the 14 chests left closed. Of the 15 places the take's
# grids hold, `open_reaches` refuses the 9 that failed and passes the 6 that opened
# (rca/2026-10-21/super-chest-misses-findings.md). Off: the rush runs alone, as before.
CHESTS_NOT_ACROSS_WALLS = True
CHESTS = frozenset((SUPER_CHEST, UNIQUE_CHEST))
# A leader the strike holds (echoing_strike/attack.py HOLD_LEADER) in reach with a clear shot is struck from where the
# character stands: the pursuit's own move toward a fight goal (the full clear's next monster or group, the leader's
# place) does not make the fight let go. Its safety moves still do (a dodge, a walk round, keep-range, a retreat: any
# other reason), and so does a firing spot: the closing in on a low-danger pack (test_ancients: 15 kills in 20 s
# instead of 18+ with firing spots held too, 2026-10-21 ~21:15). The
# coordinator, 2026-10-21 ~21:05, of the Herald fights' chip seconds: "With a held leader in reach, the fight must not
# yield to a move toward it or toward the full clear: strike from where we are"; 15 of the 85 jump-seconds of the
# day's Herald fights were "Teleport toward full clear" with the Herald in reach
# (rca/2026-10-21/arachnid-herald-1-findings.md). False: the fight lets go for any move the press asks.
HELD_STRIKES_ON = True
# DANCE_BUDGET (2026-10-22, the player on game cyberg64, 18:09:26-18:10:35, Lower Kurast: "we jumped around
# non-damaging, non-scary mobs for several minutes", "even if it was dangerous, what is estimated exp/hour if we're
# jumping around without kills?"; rca/2026-10-22/lk-dance-findings.md): 73 s of retreats, keeping-range hops and safe
# approaches with no kill, no chest and no pickup. True: once the run's acts have been only such moves (DANCING) for
# DANCE_SECONDS since its last progress (a kill seen, or the goal changed: a chest opened, a drop taken, a target
# gone), the goal is given up: the loop's chest (a rushed run's route `use` mark) is done with (route.py
# `note_empty`) and the run goes on to the next; a clearing goal (a full clear's, a TZ agenda's) is passed for
# PASS_SECONDS (choice.py `pass_by`), so the level's other packs come first and it is come back to. Never a boss
# stage's fight (the ledger's rule), a pickup, a wait or the boss's loot. False: no bound, as before.
DANCE_BUDGET = True
DANCE_SECONDS = 5.0
DANCING = ('retreating', 'pack: keeping range', 'safe approach')  # pursuit.py, combat/pack.py BACK_SAID, jump.py
# STILL_BUDGET (2026-10-22, Tower Cellar Level 1, 20:04:15-20:04:26, take 20261022T170322Z-21; rca/2026-10-22/
# flipflop-findings.md): DANCE_BUDGET counts the DANCING moves of one goal and takes a change of goal for progress, so
# the 26 Teleports between a group of 10 and the Next level mark (the goal changed at every look) never added up. True:
# any moves since the last progress (a kill seen, damage dealt, the goal reached; a drop, a wait, a boss stage's fight,
# the loot or the way out keep the clock at zero) that went round in a knot - over the last DANCE_SECONDS a way of
# STILL_TRAVEL and more, STILL_LOOPS times the width of the ground it covered, in STILL_MOVES moves and more - give up
# the look's goal as DANCE_BUDGET does (a clearing goal passed, the loop's chest done with), whatever goals they were
# for; a route's own goal is not, and the clock stays armed for the next clearing look. A way that goes somewhere (a
# walk, hops round a wall, there and back once) is no knot. The game's own watchdog is loop.py `no_progress`. False:
# DANCE_BUDGET only, as before.
STILL_BUDGET = True
# NET_PROGRESS (2026-10-22, Sewers Level 1 21:05:14-21:05:53, take 20261022T180453Z-92; rca/2026-10-22/
# potion-flipflop-findings.md): a Horror (skeleton5) died four times and a Horadrim Ancient (unraveler4, Resurrect2)
# raised it three times, the Ancient growing back 41 -> 81 of 128 meanwhile; each death and each blade on what came
# back or grew back restarted the budgets' clock ("progress"). True: progress is what lasts: a death of one never seen
# dead before on the level (`Hunter.slain`), or a life under what it was when the clock began (the clock's snapshot,
# not the last look's: what grew back and is struck again is no progress), never the life of one raised. The potion
# side goal is no goal the budgets keep (choice.py POTION_HELD): its pickup and its guards' fight are given up by a
# knot like a clearing goal, the potion then left (`Hunter.side_left`). False: any death or blow, as before.
NET_PROGRESS = True
# KNOT_PASSES_PLACE (2026-10-23, Claw Viper Temple Level 1, 03:26-03:31, cyberg46 shard game: the loop stopped itself,
# "no progress for 300 s"): a knot passed one Claw Viper of a row of 15 out of reach (no damage), the next look took
# the next one of the same row, 20 passes in 5 min. True: a knot passes every monster within KNOT_RADIUS of the passed
# goal's place with it; a unit passed by a knot again is passed for KNOT_AGAIN_SECONDS (the level's other ways first,
# the level run ends when nothing else is left). False: the goal's unit alone, PASS_SECONDS, as before.
KNOT_PASSES_PLACE = True
# DANCE_PASSES_PACK (2026-10-23, the same stop; rca/2026-10-23/approach-veto-findings.md): the 15 Claw Vipers of a
# tier 5 Mana Burn Herald pack stood in a row 22 wide behind a closed door, 2.5 units past it: no strike spot on the
# character's side, the door inside the burners' keep range (every progress act vetoed, "kept at range: a move into
# the pack's reach"). DANCE_BUDGET passed one viper a dance and STILL_BUDGET's knot those within KNOT_RADIUS, the next
# look took the next one. True: a knot, or a dance whose goal is of a tier 4-5 Herald pack, passes that whole pack
# (combat/pack.py `members` within PACK_SEEN of the goal's place) as a knot passes its radius (`pass_the_knot`).
# False: the goal's unit alone for a dance, the knot's radius for a knot, as before.
DANCE_PASSES_PACK = True
KNOT_RADIUS = 14.0
KNOT_AGAIN_SECONDS = 600.0
STILL_LOOPS = 3.0
STILL_TRAVEL = 60.0  # units: two Teleport hops and more
STILL_MOVES = 4
HELD_ON_SAID: set[int] = set()  # the held leaders the stay was said for
# PACK_FIGHT_FIRST (2026-10-23, the player: "your goal is to maximize exp/hour"; rca/2026-10-23/fight-yield-findings.md)
# Mausoleum, a tier 5 Herald pack of Hungry Dead, 09:37:41-46: with 4 of the pack in reach the agenda had no target
# ("the route's own goal") and the fight let go after one cast each time for "agenda: a super chest spot" 96 away and
# "agenda: Super chest" 74 away; the members followed, two more one-cast bouts on the way. Tonight's 1-cast yields to a
# goal that is no fight: 560 to an unexplored room (852 s to the next strike), 74 to a chest (90 s), pickups on the way.
# True: while a live member of a tier 4-5 Herald pack is in the strike's reach with a clear shot, the fight does not
# let go for a move or a use that goes for no fight (`pack_holds_fight`, `key_asks`); the safety's moves (a hop, a
# retreat, a dodge, a walk round, a firing spot), a fight goal's moves and the loop's end still do. False: as before.
PACK_FIGHT_FIRST = True
PACK_FIRST_SAID: set[int] = set()  # the packs the stay was said for (combat/pack.py `key_of`)
# DANCE_BY_UNIT (2026-10-23, fix B of rca/2026-10-23/jumps-findings.md; the player: "your goal is to maximize
# exp/hour"): DANCE_BUDGET's clock was keyed on the goal's label and place. At the Halls of the Dead door (14:40:07-48,
# take 20261023T113952Z-57) the label went "Amethyst, on the way: the fight first (1 in the way)" <-> "full clear: the
# elite 101 (1877455282)" at every look, one Herald for both, and a fight goal's place moves with its monster: the
# clock began again at every look, no DANCE_BUDGET in 41 s of dance. True: a goal with a unit is keyed on the unit (and
# what is done to it), whatever its label or place. False: the label and place, as before.
DANCE_BY_UNIT = False
# HELD_OFF (2026-10-23, rca/2026-10-23/fight-efficiency-findings.md shape a): after the keep range's hop the next look
# went back in. Take 20261023T123721Z-106, 15:39:58-15:40:11: a "pack: keeping range: mana burn" hop, a "safe
# approach" 3-5 units back toward the pack, the members came on, the next hop: 9 hops and 6 approaches in 13 s.
# True: once the safety hops out of a pack (combat/pack.py BACK_SAID), the moves toward it (the goal's own, a safe
# approach, a firing spot; never a retreat or a dodge) are not made while it comes on by itself and its threat is the
# same: the same hostiles alive and read, one of them COMING_UNITS nearer than at the last look, within
# HELD_OFF_SECONDS of the hop (`hold_off`). What is in reach is still struck; hops and retreats still go; a fresh
# advance press goes. False: as before.
HELD_OFF = False
HELD_OFF_SECONDS = 3.0
HELD_RADIUS = 24.0  # units: the hostiles the hop leaves (manaburn FAST_KEEP 18, pack LEAD_UNITS 4, a margin)
COMING_UNITS = 1.0  # a hostile this much nearer the character than at the last look comes on
HELD_OFF_SAID = 'held off'
SAFE_APPROACH = 'safe approach'  # macros/safety.py `approach`
# YIELD_KEEPS_KILLING (2026-10-23, the findings' shape b): the fight let go for the pursuit's own move while the strike
# still killed. 15:00-17:31: 709 yields to such a move (the next group 51 away, an unexplored room, the hostile by the
# Herald coming), 362 of them after a kill, 409 s of strike gap. True: the fight does not let go for the pursuit's own
# move (no reason: not a hop, retreat, dodge, walk round or firing spot) while the look's price lets the hold stand
# (not vetoed, within the life budget) and the fight here still kills (a kill or damage within the strike's reach in
# KEEPS_SECONDS, NET_PROGRESS's rules: `fight_kills`) or a live tier 4-5 Herald pack's member is in reach with a clear
# shot. Never on the KP_6 loop's rushed run, toward the level run's own boss, for the loot or the way out, or for a
# fresh advance press. False: as before.
YIELD_KEEPS_KILLING = True  # on 2026-10-23 ~19:50 (the player: "Turn both on"), gated: 0 new deaths over 1860 pairs
KEEPS_SECONDS = 2.0
KEEPS_SAID: set[str] = set()  # the goals the stay was said for
# REFUSED_PASS (2026-10-23, the death agent's canyon trace, rca/2026-10-23/death-canyon-findings.md §6, READ_THROWS
# on): the tier 5 Hell Slinger pack; land by the elite, 1-2 casts, "retreating: no progress act fits the life budget",
# and the full clear's next look goes back to the same elite: 37 hops, the first kill at 14 s (the arena: 43 Teleports
# and 2.2 kills a 32 s play). DANCE_BUDGET's clock starts again at every blow (damage is progress) and the approach
# between is no dance. True: the safety's retreats from one fight's place (within REFUSED_RADIUS of the first one's
# goal), REFUSED_TIMES of them with no kill there (NET_PROGRESS: none raised), whatever bouts and blows came between,
# give the goal up as a dance does, the hostiles round it with it (`pass_the_knot`: KNOT_RADIUS, a Herald pack whole).
# No refusal for REFUSED_LAPSE starts the count again. Never a kept goal. False: as before.
REFUSED_PASS = False
REFUSED_TIMES = 4
REFUSED_RADIUS = herald_pack.PACK_SEEN
REFUSED_LAPSE = 10.0  # seconds
REFUSED_SAID = 'retreating'  # pursuit.py `arbitrate`'s retreats (KEEPING too)
# T5_SKIP (2026-10-23, the player ~20:35 of a tier 5 Herald pack the safety refuses every spot near: "Skip it
# (Recommended)"; rca/2026-10-23/death-canyon-findings.md §10): the canyon's Slingers, land, a cast, "retreating: no
# progress act fits the life budget", back to the same Herald, 43 Teleports and 2.2 kills a 32 s play. True: a safety
# retreat with no spot kept in strike reach (pursuit.py "retreating: ...", not KEEPING) from a goal of a tier 5 Herald's
# pack (T5_TIER) gives the goal up at once, the whole pack passed for KNOT_AGAIN_SECONDS and its places no tour stop
# (`note_refused`): no wait, no dance; not while the fight kills (a hostile by it dead within T5_QUIET, none raised:
# the day's takes, 39 such packs: a skip at the first refusal loses 358 of their members' kills and 28 Heralds, one
# with no kill in 5 s 151 and 10, for 844 of the 1373 s). Never a kept goal. False: as before.
T5_SKIP = False
T5_TIER = 5
T5_QUIET = 5.0  # seconds
T5_SAID = 'retreating: '  # pursuit.py `arbitrate`: no progress act made; KEEPING ('retreating within ...') keeps a spot
# SLOW_FIGHT (2026-10-23, the coordinator: session 20261023T152949Z-3e645905, take 20261023T154020Z-94, Ruined Temple
# 18:40:56-18:41:41): a tier 5 Herald pack of Wailing Beasts, each immune to magic ("the demons are its answer"),
# "the Herald 3249094580 held until it dies" for 45 s: 11 strikes, the Herald 127 -> 119/128, then the zone skipped
# ("no kill and no level done for 90 s"). The fight holds (HELD_STRIKES_ON, PACK_FIGHT_FIRST) whatever it takes off.
# True: once the character has been in the strike's reach of a clearing goal's fight for SLOW_WATCH, the life the
# hostiles round it (SLOW_RADIUS) lost since (kills in full, none raised: NET_PROGRESS) is its rate; when what is left
# would take over SLOW_SECONDS more at that rate, the goal is given up as a dance's, the hostiles round it and its
# Herald pack with it, and the held leader no longer keeps the fight (`held_strikes_on`). Never a kept goal (a boss
# stage's fight). False: as before.
SLOW_FIGHT = False
SLOW_WATCH = 10.0  # seconds
SLOW_SECONDS = 60.0
SLOW_RADIUS = herald_pack.PACK_SEEN


@dataclass(frozen=True)
class HeldOff:
    """HELD_OFF: a keep-range hop's look: its clock, the level, the hostiles it left and where the last look saw them,
    and whether the hold was said."""

    at: float
    area: int
    seen: dict[int, Point]
    said: bool = False


def wall_checked(posted: Pursuit | None, goal: Goal) -> bool:
    """Whether `goal`'s object is opened only off a walk round a wall (`open_reaches`): on the KP_6 loop's rush run
    any object, on another level run a chest (CHESTS_NOT_ACROSS_WALLS)."""
    if posted is None or not posted.runs:
        return False
    chest = goal.mark is not None and goal.mark.use in CHESTS
    return posted.rush or (CHESTS_NOT_ACROSS_WALLS and chest)


def judge(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, *, in_reach: bool, attacking: bool = True
) -> Judged:
    """One look of the pursuit: the goal, the facts and the decision (pursuit.py `decide`); nothing is done.
    A fight's place is the nearest with a shot at the boss (`firing_target`)."""
    player = world.player
    assert player is not None
    # Read once, before the look's clock: a press posted later is the next look's (run-0025-findings.md §2.1)
    posted = self.pursuit
    here, now = (player.x, player.y), run.clock()
    if in_reach and self.only_bound(world, foes, ground, here):
        # A summoner's bound units (Baal's clone) are no fight to hold (rca/2026-10-14/baal-sim.md fix 2)
        in_reach = False
    if in_reach and self.nearing_only(world, foes, ground, here, now):
        in_reach = False  # the strikes did nothing from here (`untouched`)
    if self.recover_asked is not None:
        recover(self, now, foes)  # the loop's still watchdog: a new target before the game is left
        foes = [m for m in foes if m.unit_id not in self.untouchable]
    if posted is not None and posted.leashed and posted.area is None:
        named = replace(posted, area=player.area)  # the level run is of the level it was asked on
        self.swap(posted, named)
        posted = named
    onward = carried(posted, player.area, now) if posted is not None else None
    if posted is not None and onward is not None and self.swap(posted, onward):
        self.carry_on(run, posted, onward)  # before the mode is looked at: the player's switch goes with the run
        posted = onward
    pressed = posted is not None and posted.fresh(now)
    self.run_mode(run, player.area, posted)
    goal = self.goal(run, world, foes, pressed, posted)
    if posted is not None and posted.runs and not (pressed and posted.advance):
        goal = self.cleared(run, world, foes, ground, goal)  # the run's own look: what its mode adds
        goal = shrines.side_goal(self, run, world, goal, posted)  # an Experience Shrine on the way (2026-10-20)
        if choice.NEARER_CLEARING:
            goal = choice.from_nearer(self.missed, goal, now)  # the mode's own goal whose act missed: from nearer
    goal = revive.reviver_goal(self, world, foes, goal)  # a reviver raising its pack first (REVIVER_STAND)
    bosses = unfound_bosses(self, player.area) if posted is not None and posted.runs else []
    if bosses and ends_run(goal, pressed):
        goal = boss_explore(self, run, world, player, goal, bosses, now)  # pursuit.py BOSS_EXPLORE
    if not pressed and not (posted is not None and posted.leashed):
        goal = self.nearby(goal, here)
        goal = moves.engage_goal(self, foes, goal, here)  # the T5 pack's plan walks in (combat/engage.py)
    noted = heading(posted, goal) if posted is not None else None
    if posted is not None and noted is not None and self.swap(posted, noted):
        posted = noted  # across its level's open passage the run goes on (`carry_on`)
    self.pursued = goal
    level = self.known_level(player)
    rect = run.actuator.keys.focused_window_rect()
    place, there, beyond = None, False, math.inf
    spend = goal.spend if goal is not None else STANDING  # the way's intent (`way`)
    if goal is not None:
        place = goal.place
        if goal.do == FIGHT:
            there = in_reach_of(ground, here, goal.place, goal.near, world.doors)
            if not there and level is not None and goal.known:
                # As `firing_target`, quietly, on the attack's engage ring (run-1932-findings.md §4.2)
                engage = self.attack.engage
                spots = firing_spots(ground, goal.place, STRIKE_REACH, here, world.doors, engage) or [goal.place]
                if FIRING_STAND and goal.spend.short > 0:
                    # A stand-off (the dolls'): the spots at least that far from the monster first
                    off = min(goal.spend.short, STRIKE_REACH - RING_STEP) - 0.5
                    spots = [s for s in spots if math.dist(s, goal.place) >= off] + [
                        s for s in spots if math.dist(s, goal.place) < off
                    ]
                rooms = level.rooms
                place = next((s for s in spots if room_at(rooms, (s[0] / TILE_UNITS, s[1] / TILE_UNITS))), spots[0])
                if FIRING_STAND and place != goal.place:
                    spend = replace(goal.spend, short=0.0)  # onto the spot: it is the stand
        elif goal.shrine:
            there = shrines.there(ground, world, here, goal)  # clicked on a clear line, never across a wall
            beyond = max(goal.gap(here) - goal.near, 0.0)
        elif goal.do == USE and goal.mark is not None:
            thing = marked_thing(run, goal.mark)
            near = goal.gap(here) <= SPOT_NEAR or (
                thing is not None and math.dist(here, (thing.x, thing.y)) <= goal.near
            )
            there = thing is not None and near
            if thing is not None and posted is not None and wall_checked(posted, goal):
                # Never across a wall (`open_reaches`); the loop opens from beside the object (`OPEN_NEAR`), another
                # run's chest from its goal's reach. The way goes to the object's own place, which stays put; a place
                # beside it moved with every move (2026-10-16 22:50: the goal's cell changed in 112 of 213 looks)
                at = (thing.x, thing.y)
                if posted.rush:
                    things = run.things() if run.things is not None else ()
                    reach = PAIR_NEAR if paired(things, thing, here) else OPEN_NEAR
                else:
                    reach = goal.near
                there = there and open_reaches(ground, world.doors, here, at, reach)
                if not there:
                    place = at
        elif goal.do == PICK_UP:
            # Near enough to click is a walk within reach, not a straight line (run-0025-findings.md §2.2)
            there = walk_reaches(ground, world.doors, here, goal.place, goal.near)
            if not there and goal.unit is not None and goal.unit not in self.round_said:
                away = math.dist(here, goal.place)
                if away <= goal.near:
                    if len(self.round_said) > 200:
                        self.round_said.clear()
                    self.round_said.add(goal.unit)
                    LOG.info(
                        'Macro: pickup: %s: %.0f away with no clear line from (%.1f, %.1f): gone to first, '
                        'not clicked from afar',
                        goal.label, away, *here,
                    )  # fmt: skip
        else:
            there = goal.gap(here) <= goal.near
            beyond = max(goal.gap(here) - goal.near, 0.0)  # an arrival by distance (pursuit.py `moved`)

    def way():
        if goal is None or place is None or rect is None:
            return NoWay('no game window')
        rooms = level.rooms if level is not None else ()
        return self.travel.toward(run, world, ground, rect[2] / rect[3], place, spend, rooms)

    facts = Facts(
        now, goal, there, in_reach, attacking, way, player.area, now < self.settled_at,
        beyond=beyond, least_move=AROUND_LEAST, mapped=level is not None and bool(level.rooms), bosses_left=len(bosses),
    )  # fmt: skip
    # The strike gap counts while a hostile is within reach, clear line or not (I2)
    near = any(math.dist(here, (m.x, m.y)) <= self.reach for m in foes)
    rush = posted is not None and posted.rush and posted.runs
    facts = replace(facts, quiet=min(now - self.struck_at, 60.0) if near else 0.0, near=near, rush=rush)
    if self.pursuing and rect is not None:
        facts = self.safety_priced(run, world, foes, ground, facts, posted, rect)
    if facts.candidates:
        # A spot a move just failed to reach is not priced again for a while (`barred`)
        facts = replace(facts, candidates=tuple(c for c in facts.candidates if not self.barred(c.act, now)))
    facts, waits = hold_off(self, world, foes, facts, pressed and posted is not None and posted.advance, now)
    self.look_facts = facts  # the look's priced acts (YIELD_KEEPS_KILLING's hold)
    act = NoWay(waits) if waits is not None else decide(facts, posted, self.pursuing)
    if moves.DOOR_FIGHT:  # the pack behind a closed door: the mark, then the door (moves.py DOOR_FIGHT)
        act = moves.door_fight(self, world, foes, goal, act, in_reach=in_reach, hurt=facts.hurt, now=now)
    note_hold_off(self, world, foes, act, now)
    unshot(self, goal, act, foes, now)
    if (
        isinstance(act, Hold)
        and posted is not None
        and posted.looped
        and goal is not None
        and goal.do in (LOOT, LEAVE)
        and now - self.hurt_at > HURT_SECONDS
    ):
        # The route's boss dead, her pack is not fought while nothing hurts (the player, 2026-10-17: "we don't even
        # need to kill some trash mobs and can loot and leave")
        act = Ended(f"the route's boss is dead: {goal.label} next, what does not hurt is not fought")
    if isinstance(act, Advance) and self.barred(act, now):
        act = NoWay(f'{goal.label if goal else "the goal"}: the move there just did not take; looking again')
    self.empty_mark(world, goal, act, now)
    no_progress(self, run, world, goal, act, now, posted, there=there)
    if isinstance(act, Advance) and act.reason:
        place = act.step.spot
    if (
        isinstance(act, NoWay)
        and goal is not None
        and goal.shrine
        and act.reason.startswith('no way toward')
        and not act.reason.endswith(GROWING)
    ):
        shrines.no_way(self, goal, act.reason)  # a side goal: left, the level's own way is not explored for it
    elif (
        isinstance(act, NoWay)
        and goal is not None
        and goal.clearing
        and act.reason.startswith('no way toward')
        and not act.reason.endswith(GROWING)  # a way not grown yet in the look's time is no way that fails
    ):
        # a run's clearing goal it has no way to: the next look goes on
        self.pass_by(goal, act.reason, now, level.rooms if level is not None else ())
    elif (
        isinstance(act, NoWay)
        and goal is not None
        and self.agenda is not None
        and act.reason.startswith('no way toward')
        and (world.game_name, player.area) not in self.wayless
    ):
        # The route's goal with no way over the known rooms: explore to grow the way, never stand (2026-10-19
        # 09:46, the player: "we stuck and exit without visiting next location")
        self.wayless.add((world.game_name, player.area))
        LOG.info('Macro: agenda: no way to %s: the level is explored for it (cover)', goal.label)
    elif (
        isinstance(act, NoWay)
        and not act.arrived
        and goal is not None
        and self.agenda is not None
        and act.reason.startswith('no way toward')
        and (world.game_name, player.area) in self.wayless
    ):
        # Explored for it and still no way: the run ends, not the 45 s watchdog (01:04:16-01:05:01 on 2026-10-20,
        # Lost City: "no way toward Valley of Snakes" after its rooms, the game left by the watchdog)
        key = (world.game_name, player.area)
        if self.no_way_since is None or self.no_way_since[0] != key:
            self.no_way_since = (key, now)
        elif now - self.no_way_since[1] >= NO_WAY_ENDS:
            act = Ended(f'{NO_WAY_TO}{goal.label} after exploring for it {now - self.no_way_since[1]:.0f} s')
    else:
        self.no_way_since = None
    return Judged(act, goal, place, posted, pressed)


def dancing(act: object) -> bool:
    """Whether an act is a move that makes no progress by itself (DANCING): a retreat, a keeping-range hop, a safe
    approach."""
    return isinstance(act, Advance) and act.reason.startswith(DANCING)


def fallen(world: World) -> tuple[frozenset[int], dict[int, int]]:
    """The hostiles seen dead, and the live ones' life: what a kill or damage dealt is told by (`no_progress`)."""
    dead = frozenset(m.unit_id for m in world.monsters if m.mode in (0, LYING_DEAD) and not m.ally)
    lives = {
        m.unit_id: m.life
        for m in world.monsters
        if not m.ally and m.mode not in (0, LYING_DEAD) and getattr(m, 'life', 0) > 0
    }
    return dead, lives


def progressed(
    dead: frozenset[int],
    lives: dict[int, int],
    was_dead: frozenset[int],
    was: dict[int, int],
    raised: frozenset[int] = frozenset(),
) -> bool:
    """A hostile seen dead that was not, or one's life down (damage dealt), since `was_dead` and `was` (`fallen`);
    none of `raised` (NET_PROGRESS: seen dead before on the level) counts."""
    if not (dead - was_dead) <= raised:
        return True
    return any(life < was.get(unit, -1) for unit, life in lives.items() if unit not in raised)


def slain_before(self: Hunter, world: World, dead: frozenset[int]) -> frozenset[int]:
    """NET_PROGRESS: the hostiles seen dead on this level before this look (`Hunter.slain`, then this look's added);
    none with the switch off."""
    player = world.player
    if not NET_PROGRESS or player is None:
        return frozenset()
    area, slain = getattr(self, 'slain', (None, frozenset()))
    before = slain if area == player.area else frozenset()
    self.slain = (player.area, before | dead)
    return before


def side_potion(self: Hunter, goal: Goal) -> int | None:
    """POTION_HELD: the healing potion a side goal is for: its pickup, or its guards' fight (`first_fight` of the
    look's own goal, `Hunter.base`); None for any other goal or with the switch off."""
    potions = getattr(self, 'potions', None)
    if not choice.POTION_HELD or potions is None:
        return None
    base = goal if goal.do == PICK_UP else getattr(self, 'base', None) if goal.guarded and goal.do == FIGHT else None
    if base is None or base.do != PICK_UP or base.unit is None:
        return None
    return base.unit if potions.kinds.get(base.unit) == HEALING else None


def kept_goal(goal: Goal, self: Hunter | None = None) -> bool:
    """A goal no budget gives up: a drop, a wait, the boss's loot, the way out, a boss stage's fight; with `self`,
    not a healing potion's side goal (POTION_HELD, `side_potion`)."""
    if self is not None and side_potion(self, goal) is not None:
        return False
    return goal.do in (PICK_UP, WAIT, LOOT, LEAVE) or (goal.stage is not None and goal.stage.kind == FIGHT)


def dance_key(goal: Goal) -> tuple:
    """DANCE_BUDGET's clock key: the goal's unit and what is done to it (DANCE_BY_UNIT), else its label and place."""
    if DANCE_BY_UNIT and goal.unit is not None:
        return (goal.do, goal.unit)
    return (goal.label, goal.do, goal.unit, round(goal.place[0]), round(goal.place[1]))


def hops_back(act: object) -> bool:
    """Whether `act` is the safety's keep-range hop (combat/pack.py BACK_SAID, a Herald's or a draining pack's)."""
    return isinstance(act, Advance) and act.reason.startswith(herald_pack.BACK_SAID)


def note_hold_off(self: Hunter, world: World, foes: Sequence[Monster], act: object, now: float) -> None:
    """HELD_OFF: a keep-range hop chosen: the hostiles within HELD_RADIUS it leaves are held off from now."""
    player = world.player
    if not HELD_OFF or player is None or not hops_back(act):
        return
    here = (player.x, player.y)
    left = {m.unit_id: (m.x, m.y) for m in foes if math.dist(here, (m.x, m.y)) <= HELD_RADIUS}
    self.held_off = HeldOff(now, player.area, left) if left else None


def approaching(c: Candidate, here: Point, held: Iterable[Point]) -> bool:
    """Whether a priced act is a move toward the held-off hostiles (HELD_OFF): the goal's own move, a safe approach or
    a firing spot, never a retreat, a dodge or a walk round, landing nearer the nearest of them than here."""
    act = c.act
    if not isinstance(act, Advance) or c.retreat or act.dodge or act.onward:
        return False
    if act.reason not in ('', SAFE_APPROACH, FIRING_SPOT):
        return False
    places = list(held)
    nearest = min(math.dist(here, p) for p in places)
    return min(math.dist(act.step.spot, p) for p in places) < nearest - 0.5


def hold_off(
    self: Hunter, world: World, foes: Sequence[Monster], facts: Facts, advanced: bool, now: float
) -> tuple[Facts, str | None]:
    """HELD_OFF: the look's priced acts without the moves toward the hostiles a hop just left (`approaching`) while
    they come on and their threat is the same; and the reason to wait when that leaves no act. The hold ends with a
    fresh advance press (`advanced`), another level, HELD_OFF_SECONDS, one of them dead or out of the read, or none
    coming on."""
    held = getattr(self, 'held_off', None)
    player = world.player
    if not HELD_OFF or held is None or player is None or not facts.candidates:
        return facts, None
    here = (player.x, player.y)
    live = {m.unit_id: (m.x, m.y) for m in foes if m.unit_id in held.seen}
    coming = [u for u, p in live.items() if math.dist(here, p) < math.dist(here, held.seen[u]) - COMING_UNITS]
    if advanced or player.area != held.area or now - held.at > HELD_OFF_SECONDS or live.keys() != held.seen.keys():
        self.held_off = None  # the threat changed, or the press goes
        return facts, None
    if not coming:
        self.held_off = None  # they do not come on: gone to as before
        return facts, None
    kept = tuple(c for c in facts.candidates if not approaching(c, here, live.values()))
    dropped = len(facts.candidates) - len(kept)
    self.held_off = replace(held, seen=live, said=held.said or dropped > 0)
    if not dropped:
        return facts, None
    nearest = min(math.dist(here, p) for p in live.values())
    why = (
        f'{HELD_OFF_SAID}: {len(coming)} of the {len(live)} the hop left come on (the nearest at {nearest:.1f}): '
        'no move toward them (HELD_OFF)'
    )
    if not held.said:
        LOG.info('Macro: pursuit: %s; %d moves dropped', why, dropped)
    return replace(facts, candidates=kept), (why if not kept else None)


def danced(self: Hunter, world: World, goal: Goal | None, act: object, now: float) -> str | None:
    """DANCE_BUDGET: why the goal is given up after DANCE_SECONDS of DANCING acts since the last progress (a kill,
    damage dealt, the goal changed); None else."""
    if not DANCE_BUDGET or goal is None:
        self.dance = None
        return None
    key = dance_key(goal)
    dead, lives = fallen(world)
    raised = getattr(self, 'slain', (None, frozenset()))[1] if NET_PROGRESS else frozenset()  # `knotted` keeps it
    begun = self.dance
    if begun is None or begun[0] != key or progressed(dead, lives, begun[2], begun[3], raised):
        self.dance = (key, now, dead, lives) if dancing(act) else None  # progress: the clock starts at the next dance
        return None
    if not isinstance(act, Advance) or not dancing(act) or now - begun[1] < DANCE_SECONDS or kept_goal(goal, self):
        return None  # a drop, a wait, a boss stage: never given up so
    return f'{now - begun[1]:.0f} s of {act.reason.split(":")[0]} with no kill and no progress (DANCE_BUDGET)'


def refused(self: Hunter, world: World, goal: Goal | None, act: object, now: float) -> str | None:
    """REFUSED_PASS: why the goal is given up after REFUSED_TIMES safety retreats from its fight's place with no kill
    there; None else."""
    if not REFUSED_PASS or goal is None or kept_goal(goal, self):
        self.refusals = None
        return None
    dead, _ = fallen(world)
    begun = getattr(self, 'refusals', None)
    if begun is not None:
        place, count, last, was_dead = begun
        raised = getattr(self, 'slain', (None, frozenset()))[1] if NET_PROGRESS else frozenset()
        at = {m.unit_id: (m.x, m.y) for m in world.monsters}
        killed = any(math.dist(place, at[u]) <= REFUSED_RADIUS for u in dead - was_dead - raised if u in at)
        if killed or now - last > REFUSED_LAPSE:
            begun = self.refusals = None  # a kill there, or the fight went elsewhere: counted again
    if not isinstance(act, Advance) or act.dodge or not act.reason.startswith(REFUSED_SAID):
        return None
    if begun is None or math.dist(begun[0], goal.place) > REFUSED_RADIUS:
        self.refusals = (goal.place, 1, now, dead)
        return None
    place, count, _, was_dead = begun
    self.refusals = (place, count + 1, now, was_dead)
    if count + 1 < REFUSED_TIMES:
        return None
    return f'{count + 1} retreats from the fight at ({place[0]:.0f}, {place[1]:.0f}) with no kill there (REFUSED_PASS)'


def t5_pack(world: World, goal: Goal) -> list[int]:
    """T5_SKIP: the live members of a tier 5 Herald's pack the goal is of (its unit one, or its place within
    PACK_SEEN of one), every member within PACK_SEEN of the goal's place; none else."""
    hostile = [
        m for m in world.monsters
        if not getattr(m, 'ally', False) and getattr(m, 'owner', NO_OWNER) == NO_OWNER and m.mode not in (0, 12)
        and getattr(m, 'tier', 0) >= T5_TIER
    ]  # fmt: skip
    near = [m.unit_id for m in hostile if math.dist(goal.place, (m.x, m.y)) <= herald_pack.PACK_SEEN]
    if not near or (goal.unit is not None and goal.unit not in near and not goal.clearing):
        return []
    return near


def t5_killing(self: Hunter, world: World, goal: Goal, now: float) -> float:
    """T5_SKIP: the clock a hostile within PACK_SEEN of the goal's place was last seen dead that was not (none raised:
    NET_PROGRESS), against the look before; -inf before any. Kept over the looks (`Hunter.t5_dead`)."""
    dead = frozenset(
        m.unit_id for m in world.monsters
        if not getattr(m, 'ally', False) and getattr(m, 'owner', NO_OWNER) == NO_OWNER and m.mode in (0, LYING_DEAD)
        and math.dist(goal.place, (m.x, m.y)) <= herald_pack.PACK_SEEN
    )  # fmt: skip
    at, was = getattr(self, 't5_dead', (-math.inf, None))
    raised = getattr(self, 'slain', (None, frozenset()))[1] if NET_PROGRESS else frozenset()
    if was is not None and dead - was - raised:
        at = now
    setattr(self, 't5_dead', (at, dead))  # ruff: ignore[set-attr-with-constant] - a Hunter field once hunting/base.py is free to edit
    return at


def t5_refused(self: Hunter, world: World, goal: Goal | None, act: object, now: float) -> str | None:
    """T5_SKIP: why the goal is given up: the safety refused every spot by a tier 5 Herald's pack; None else."""
    if not T5_SKIP or goal is None or kept_goal(goal, self):
        return None
    killed = t5_killing(self, world, goal, now)
    if not isinstance(act, Advance) or act.dodge or not act.reason.startswith(T5_SAID):
        return None
    pack = t5_pack(world, goal)
    if not pack or now - killed < T5_QUIET:
        return None
    return f'the safety refused every spot by the tier 5 Herald pack of {len(pack)} (T5_SKIP)'


def slow_fight(self: Hunter, world: World, goal: Goal | None, now: float) -> str | None:
    """SLOW_FIGHT: why the goal is given up when its fight, SLOW_WATCH in the strike's reach, would take SLOW_SECONDS
    more at the rate it has taken life off the hostiles round it; None else."""
    player = world.player
    if not SLOW_FIGHT or player is None or goal is None or not goal.clearing or kept_goal(goal, self):
        self.slow = None
        return None
    here = (player.x, player.y)
    dead, lives = fallen(world)
    at = {m.unit_id: (m.x, m.y) for m in world.monsters if not m.ally and m.owner == NO_OWNER}
    near = {u for u, p in at.items() if math.dist(p, goal.place) <= SLOW_RADIUS}
    begun = getattr(self, 'slow', None)
    if begun is None or math.dist(begun[0], goal.place) > SLOW_RADIUS:
        engaged = any(u in lives and math.dist(here, at[u]) <= self.reach for u in near)
        self.slow = (goal.place, now, {u: lives[u] for u in near if u in lives}, dead) if engaged else None
        return None
    _, since, was, was_dead = begun
    raised = getattr(self, 'slain', (None, frozenset()))[1] if NET_PROGRESS else frozenset()
    known = {**{u: lives[u] for u in near if u in lives}, **was}  # one seen first counts from its life then
    self.slow = (goal.place, since, known, was_dead)
    elapsed = now - since
    if elapsed < SLOW_WATCH:
        return None
    dealt = sum(max(0, was[u] - lives[u]) for u in was if u in lives)
    dealt += sum(was[u] for u in was if u in dead and u not in was_dead and u not in raised)
    left = sum(lives[u] for u in near if u in lives)
    more = math.inf if dealt <= 0 else left / (dealt / elapsed)
    if more <= SLOW_SECONDS:
        return None
    return (
        f'{elapsed:.0f} s on the fight at ({goal.place[0]:.0f}, {goal.place[1]:.0f}): {dealt} of life taken, {left} '
        f'left, {more:.0f} s more at that rate (SLOW_FIGHT)'
    )


def knotted(self: Hunter, world: World, goal: Goal | None, act: object, now: float, there: bool) -> str | None:
    """STILL_BUDGET: why the moves since the last progress, whatever goals they were for, are a knot the look's goal
    is given up for; None else."""
    player = world.player
    if not STILL_BUDGET or player is None:
        self.still = None
        return None
    here = (player.x, player.y)
    dead, lives = fallen(world)
    moved = isinstance(act, Advance)
    raised = slain_before(self, world, dead)  # NET_PROGRESS: what dies again was raised
    begun = self.still
    if (
        begun is None
        or there
        or goal is None
        or kept_goal(goal, self)
        or progressed(dead, lives, begun[1], begun[2], raised)
    ):
        self.still = (now, dead, lives, [(now, here, moved)])  # progress: the clock starts again
        return None
    spots = [spot for spot in begun[3] if spot[0] >= now - DANCE_SECONDS] + [(now, here, moved)]
    # NET_PROGRESS: the clock's snapshot of each life stays (a life grown back is no bar raised); one seen first added
    known = {**lives, **begun[2]} if NET_PROGRESS else {**begun[2], **lives}
    self.still = (begun[0], begun[1], known, spots)
    if not moved or now - begun[0] < DANCE_SECONDS or sum(1 for spot in spots if spot[2]) < STILL_MOVES:
        return None
    places = [spot[1] for spot in spots]
    way = sum(math.dist(a, b) for a, b in itertools.pairwise(places))
    width = max(math.dist(a, b) for a in places for b in places)
    if way < STILL_TRAVEL or way < STILL_LOOPS * width:
        return None
    return (
        f'{now - begun[0]:.0f} s of moves, {way:.0f} units round a knot {width:.0f} wide, with no kill, no damage '
        'and no goal reached (STILL_BUDGET)'
    )


def no_progress(
    self: Hunter,
    run: Run,
    world: World,
    goal: Goal | None,
    act: object,
    now: float,
    posted: Pursuit | None,
    *,
    there: bool = False,
) -> bool:
    """The goal given up for moves with no progress: DANCE_BUDGET's dance (`danced`), else STILL_BUDGET's knot
    (`knotted`; `there`: the look's goal reached). True when given up now."""
    why = danced(self, world, goal, act, now)
    skipped = t5_refused(self, world, goal, act, now)
    refusal = skipped or refused(self, world, goal, act, now) or slow_fight(self, world, goal, now)
    knot = knotted(self, world, goal, act, now, there)
    why = why or refusal or knot
    if why is None or goal is None:
        return False
    player = world.player
    level = self.known_level(player) if player is not None else None
    rooms = level.rooms if level is not None else ()
    potion = side_potion(self, goal)
    if potion is not None:
        # POTION_HELD: the healing potion's detour went nowhere: the potion is left (choice.py `side_drop`'s ledger)
        if len(self.side_left) > 200:
            self.side_left.clear()
        self.side_left[potion] = f'left: {why}'
        self.potions.refuse(potion, why)
        LOG.info('Macro: pursuit: passing %s: the potion %d is left: %s', goal.label, potion, why)
        given = True
    elif posted is not None and posted.rush and goal.do == USE and goal.mark is not None:
        given = route.note_empty(run, goal.mark, self.bearings.progress, self.bearings.marks, f'skipped: {why}')
    elif goal.clearing:
        self.pass_by(goal, why, now, rooms)
        if (knot is not None and why == knot) or (refusal is not None and why == refusal) or pack_of(world, goal):
            # a knot, a refused place (REFUSED_PASS), or a dance on a Herald pack (DANCE_PASSES_PACK)
            pass_the_knot(self, world, goal, now)
        if refusal is not None and why == refusal:
            note_refused(self, world, goal, now)
        if skipped is not None and why == skipped:
            skip_pack(self, world, goal, now)
        given = True
    else:
        return False
    if given:
        self.dance = self.still = self.refusals = self.slow = None
    return given


def skip_pack(self: Hunter, world: World, goal: Goal, now: float) -> None:
    """T5_SKIP: the refused tier 5 Herald's pack passed whole for KNOT_AGAIN_SECONDS, said."""
    units = t5_pack(world, goal)
    until = now + KNOT_AGAIN_SECONDS
    for unit in units:
        self.passed[unit] = max(self.passed.get(unit, 0.0), until)
    LOG.info('Macro: run: skipping the tier 5 Herald pack of %d by (%.0f, %.0f) for %.0f s (T5_SKIP)',
             len(units), *goal.place, KNOT_AGAIN_SECONDS)  # fmt: skip


def pack_of(world: World, goal: Goal) -> list[int]:
    """DANCE_PASSES_PACK: the tier 4-5 Herald pack the goal's unit is of (its members within PACK_SEEN of the goal's
    place), or none."""
    if not DANCE_PASSES_PACK or goal.unit is None:
        return []
    hostile = [m for m in world.monsters if not getattr(m, 'ally', False) and getattr(m, 'owner', NO_OWNER) == NO_OWNER]
    if not any(m.unit_id == goal.unit and herald_pack.in_pack(getattr(m, 'tier', 0)) for m in hostile):
        return []
    return [m.unit for m in herald_pack.members(hostile) if math.dist(goal.place, m.at) <= herald_pack.PACK_SEEN]


def note_refused(self: Hunter, world: World, goal: Goal, now: float) -> None:
    """REFUSED_PASS: the refused fight's places (the goal's, the hostiles round it, its Herald pack's) are no tour
    stop for PASS_SECONDS (choice.py `refused_near`): the way on goes elsewhere, not back through it."""
    near = [(m.x, m.y) for m in world.monsters if math.dist(goal.place, (m.x, m.y)) <= KNOT_RADIUS]
    units = set(pack_of(world, goal))
    places = [goal.place, *near, *((m.x, m.y) for m in world.monsters if m.unit_id in units)]
    kept = [(at, until) for at, until in self.refused_places if until > now][-40:]
    self.refused_places = kept + [(at, now + choice.PASS_SECONDS) for at in places]


def pass_the_knot(self: Hunter, world: World, goal: Goal, now: float) -> None:
    """KNOT_PASSES_PLACE: the monsters round a goal passed by a knot are passed with it (longer when again), said."""
    if not KNOT_PASSES_PLACE:
        return
    if len(self.knots) > 400:
        self.knots.clear()
    near = [m.unit_id for m in world.monsters if math.dist(goal.place, (m.x, m.y)) <= KNOT_RADIUS]
    units = {*near, *(() if goal.unit is None else (goal.unit,)), *pack_of(world, goal)}
    again = 0
    for unit in units:
        self.knots[unit] = self.knots.get(unit, 0) + 1
        again += self.knots[unit] > 1
        until = now + (KNOT_AGAIN_SECONDS if self.knots[unit] > 1 else choice.PASS_SECONDS)
        self.passed[unit] = max(self.passed.get(unit, 0.0), until)
    LOG.info(
        'Macro: run: the knot passes %d monsters within %.0f of (%.0f, %.0f) with %s (%d again, for %.0f s)',
        len(units), KNOT_RADIUS, *goal.place, goal.label, again, KNOT_AGAIN_SECONDS,
    )  # fmt: skip


def empty_mark(self: Hunter, world: World, goal: Goal | None, act, now: float) -> None:
    """Notes a route's boss fight stood at with no boss (`goal.unit` None: by its mark or where one was last seen,
    the act an arrival that strikes nothing). After MARK_WAIT the stage is given up on this level for the game
    (`marks_empty`, read by `goal`) and the level is explored for it (`wayless`); said once. Not for a boss the game
    brings there later (COMES_TO_ITS_MARK). EMPTY_MARK_GOES_ON off: nothing noted."""
    player = world.player
    if (
        not EMPTY_MARK_GOES_ON
        or player is None
        or goal is None
        or goal.do != FIGHT
        or goal.unit is not None
        or not goal.route
        or goal.stage is None
        or goal.stage.kind != FIGHT
        or goal.stage.boss in COMES_TO_ITS_MARK
    ):
        return
    key = (world.game_name, player.area, goal.stage.boss)
    if not (isinstance(act, NoWay) and act.arrived):
        if isinstance(act, Hold) and not goal.known:
            self.mark_since.pop(key, None)  # a wave fought: the seek's wait counts afresh from its end
        return
    if key in self.marks_empty:
        return
    if len(self.mark_since) > 200:
        self.mark_since.clear()
    since = self.mark_since.setdefault(key, now)
    # A seek of a boss not known yet (Lister, after the Throne's waves) waits SEEK_WAIT: the waves come in turn
    if now - since < (MARK_WAIT if goal.known else SEEK_WAIT):
        return
    if len(self.marks_empty) > 200:
        self.marks_empty.clear()
    self.marks_empty.add(key)
    self.wayless.add((world.game_name, player.area))
    LOG.info(
        'Macro: run: %s: no boss here after %.0f s; the stage is left and the level explored for it',
        goal.label, now - since,
    )  # fmt: skip


def safety_priced(
    self: Hunter,
    run: Run,
    world: World,
    foes: list[Monster],
    ground: Ground,
    facts: Facts,
    posted: Pursuit | None,
    rect,
) -> Facts:
    """The facts with the safety's prices (safety.py `Safety.price`); unchanged with no life read."""
    player = world.player
    assert player is not None
    now = facts.now
    if run.loot is None:
        return facts
    loot = run.loot()
    if loot.max_life > 0 and loot.life > 0:
        if self.life_seen is not None and loot.life < self.life_seen:
            self.hurt_at = now
        self.life_seen = loot.life
        facts = replace(facts, hurt=now - self.hurt_at <= HURT_SECONDS)
        staff = self.worn(run)
        hands = 'travel' if staff is not None and staff.in_hand else 'battle'
        companions = [m for m in world.monsters if m.ally or m.owner != NO_OWNER]
        seen = self.attack.sees(observe(player, foes, companions, ground, world.doors), companions)
        draw = self.build.draw
        # Holding is priced with the draw only while its casts land (macros/safety.py DRAW_CASTABLE)
        self.safety.draw_lands = draw is None or self.buffs.lands(draw.skill, now, draw.lasts)
        look = self.safety.look(
            world, loot, hands, seen.blocked, self.build.shield, self.build.settings.safety,
            now=now, flights=getattr(run, 'flights', None), draw=self.build.draw,
        )  # fmt: skip
        facts = self.safety.price(
            facts,
            posted,
            look,
            loot,
            pressure(self.drinker.readings),
            self.build.settings.safety,
            seen,
            self.attack,
            lambda point: self.travel.leg(run, world, ground, rect[2] / rect[3], point, SAFE_MOVE),
            self.travel.jumps(run, world, SAFE_MOVE),
            no_footing(ground, world.doors),
            hands,
            options=lambda point: self.travel.options(run, world, ground, rect[2] / rect[3], point, SAFE_MOVE),
            battle_ready=now - self.swap_failed_at >= SWAP_RETRY_SECONDS,
            teleport_hands='battle' if self.own_teleport(run, now) else 'travel',
        )
        facts = self.escorted(run, world, ground, rect, look, facts)
    return facts


def escorted(self: Hunter, run: Run, world: World, ground: Ground, rect, look, facts: Facts) -> Facts:
    """The priced facts plus jumps that bring the mercenary (`JumpSource.brings`: Blade Warp) out of a place it
    dies at (combat/escort.py), priced as the others less its death's cost. Unchanged with nothing priced, no
    such jump, or no mercenary in danger."""
    player = world.player
    if not facts.priced or player is None:
        return facts
    brought = {source.jump.skill for movement in self.travel.sets for source in movement.sources if source.brings}
    ready = [jump for jump in self.travel.jumps(run, world, SAFE_MOVE) if jump.skill in brought]
    found = kept_alive(world.monsters, player.unit_id)
    if not ready or not found:
        return facts
    settings = self.build.settings.safety
    endangered = in_danger(look, found, settings)
    if not endangered:
        return facts
    here, jump = (player.x, player.y), ready[0]
    aspect = rect[2] / rect[3]
    landings: dict[Point, Step] = {}
    for point in around(here, jump.reach, jump.least):
        for step in self.travel.options(run, world, ground, aspect, point, SAFE_MOVE):
            if step.skill == jump.skill and math.dist(here, step.spot) > 2.0:
                landings[step.spot] = step
    goal = facts.goal or Goal('the fight', here, FIGHT, self.reach, STANDING)
    added = []
    for escort in escorts(look, endangered, landings, settings):
        seconds = jump.takes(math.dist(here, escort.spot))
        step = PricedStep(escort.spot, jump.skill, None, 'battle', seconds)
        priced = harm(look, escort.spot, settings.horizon, 'battle', settings)
        # The jump's seconds and overhead, less the death it spares
        spent = seconds + settings.move_overhead - escort.credit
        added.append(Candidate(Advance(step, goal, escort.line(), dodge=True), spent, priced, False, seconds))
    if not added:
        return facts
    return replace(facts, candidates=(*facts.candidates, *added))


def guard(self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground) -> Advance | None:
    """Attack mode with the pursuit loop off: the pursuit's safety look and arbiter, its answer taken only for a
    STEPPING move (a dodge, a place a read model offers; not AWAY) that a strike follows from. No retreat, firing
    stand or goal: the mode alone never goes back, so those left it out of reach (rca/2026-10-14/baal-sim.md
    fix 3). Looked at only while `guarded`. None: strike on."""
    player = world.player
    if self.pursuing or player is None or run.loot is None or not self.guarded(foes):
        return None
    rect = run.actuator.keys.focused_window_rect()
    if rect is None:
        return None
    here, now = (player.x, player.y), run.clock()
    near = any(math.dist(here, (m.x, m.y)) <= self.reach for m in foes)
    facts = Facts(now, None, False, True, True, lambda: NoWay('attack mode alone goes nowhere'), player.area)
    facts = replace(facts, quiet=min(now - self.struck_at, 60.0) if near else 0.0, near=near)
    priced = self.safety_priced(run, world, foes, ground, facts, None, rect)
    if not priced.priced:
        return None
    act = decide(priced, None)
    if not isinstance(act, Advance) or not act.reason.startswith(STEPPING) or act.reason.endswith(AWAY):
        return None
    # Only a landing a strike follows from, or the mode would stand out of reach (baal-sim.md weakness 4)
    landing = next((c for c in priced.candidates if isinstance(c.act, Advance) and c.act.step == act.step), None)
    return act if landing is not None and landing.strikes else None


def guarded(self: Hunter, foes: Sequence[Monster]) -> bool:
    """Whether `guard` looks: a read model's hostile about (combat/threats `of`) or what lingers after one."""
    return bool(self.safety.casters) or any(threats.of(m.txt_id) is not None for m in foes)


def take_guard(self: Hunter, run: Run, aspect: float, key_names, ground: Ground) -> None:
    """Makes the step `guard` chose, as a dodge (`hurry`); the player's own move first. The next look strikes."""
    act, self.guarding = self.guarding, None
    if act is None:
        return  # no look at the game: the mode alone as it was (the loop goldens' reads)
    world = run.world()
    player = world.player
    if player is None:
        return
    why = 'a move was asked for' if self.move is not None else self.moving(run, world)
    if why is not None:
        LOG.info('Macro: attack mode: the step is dropped (%s)', why)
        return
    here = (player.x, player.y)
    LOG.info(
        'Macro: attack mode: %s, to (%.1f, %.1f), %.1f away from (%.1f, %.1f)%s; the strike follows',
        act.reason, *act.step.spot, math.dist(here, act.step.spot), *here, ' (a dodge)' if act.dodge else '',
    )  # fmt: skip
    run.say(f'{act.reason[:1].upper()}{act.reason[1:]}')
    try:
        self.travel.make(run, act.step, world, aspect, key_names, ground, name=act.goal.label, hurry=act.dodge)
    except Abort as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: attack mode: the step to (%.1f, %.1f) failed (%s)', *act.step.spot, stop)


def key_asks(
    self: Hunter, run: Run, world: World, foes: list[Monster], ground: Ground, *, unstruck: bool = False
) -> bool:
    """Inside a fight: whether the press asks for something other than the strike (a move, a use, the route's
    step); the fight then lets go. Judged once a press and every DECIDE_SECONDS while fresh. `unstruck`: before
    the fight's first strike the Hold that began it stands, short of a fresh press
    (rca/2026-10-18/andariel-cadence-findings.md F2)."""
    now = run.clock()
    if not self.pursuing:
        return False
    if YIELD_KEEPS_KILLING and world.player is not None:
        fight_kills(self, world, (world.player.x, world.player.y), now)  # every look of the fight, judged or not
    current = self.pursuit.pressed_at if self.pursuit is not None else -math.inf
    stamp, at, asks = self.judged
    if stamp != current or (now - at >= DECIDE_SECONDS and not unstruck):
        found = self.judge(run, world, foes, ground, in_reach=True)
        act = found.act
        asks = (
            isinstance(act, Advance | Operate | Defer)
            or (isinstance(act, NoWay) and act.reason.startswith('safety:'))
            or (isinstance(act, Ended) and found.posted is not None and found.posted.looped)  # the loop's run over
        )
        if asks and isinstance(act, Advance) and held_strikes_on(self, world, foes, ground, act, now):
            asks = False
        if asks and isinstance(act, Advance | Operate) and pack_holds_fight(self, world, foes, ground, act, now):
            asks = False
        if asks and isinstance(act, Advance) and keeps_killing(self, world, foes, ground, found, now):
            asks = False
        if isinstance(act, Hold) and found.pressed:
            # A fresh press answered by the strike says so (I6)
            label = found.goal.label if found.goal is not None else 'the goal'
            self.tell(run, act.reason or f'{label}: the least-time safe act is the fight', again=SAID_AGAIN)
        self.judged = (current, now, asks)
        player = world.player
        # The act the fight is let go for is the one the next look makes (`yielded_act`, YIELD_TAKES)
        self.yielded = (
            (found, now, (player.x, player.y), player.area, current)
            if asks and YIELD_TAKES and isinstance(act, Advance | Operate) and player is not None
            else None
        )
    return asks


def held_strikes_on(
    self: Hunter, world: World, foes: list[Monster], ground: Ground, act: Advance, now: float | None = None
) -> bool:
    """Whether the fight stays for the leader its strike holds (HELD_STRIKES_ON): `act` is the pursuit's own move
    toward a fight goal (no reason: not the safety's, not a firing spot; no dodge or walk round) and the held leader
    is a foe in the strike's reach with a clear shot, not left alone as untouchable or neared. Said once a leader."""
    player = world.player
    holding = getattr(self.attack, 'holding', None)
    if not HELD_STRIKES_ON or player is None or not callable(holding) or act.dodge or act.onward:
        return False
    if act.reason or act.goal.do != FIGHT:  # a reason: the safety's, or a firing spot (FIRING) that stays
        return False
    unit = holding()
    leader = next((m for m in foes if m.unit_id == unit), None)
    if leader is None or unit in self.untouchable or unit in self.nearing:
        return False
    if SLOW_FIGHT and now is not None and self.passed.get(unit, -math.inf) > now:
        return False  # given up (SLOW_FIGHT): the held leader keeps no fight
    here = (player.x, player.y)
    if not in_reach_of(ground, here, (leader.x, leader.y), self.attack.reach, world.doors):
        return False
    if unit not in HELD_ON_SAID:
        if len(HELD_ON_SAID) > 200:
            HELD_ON_SAID.clear()
        HELD_ON_SAID.add(unit)
        LOG.info(
            'Macro: pursuit: %s: no move, the leader %d held is in reach %.1f away: struck from here',
            act.goal.label, unit, math.dist(here, (leader.x, leader.y)),
        )  # fmt: skip
    return True


def pack_holds_fight(
    self: Hunter, world: World, foes: list[Monster], ground: Ground, act: Advance | Operate, now: float
) -> bool:
    """Whether the fight stays for a tier 4-5 Herald pack in reach (PACK_FIGHT_FIRST): `act` goes for no fight (a
    chest, a room to explore, a pickup on the way, the way out) and is no safety move (no reason, no dodge or walk
    round), and a live member of the pack is a foe in the strike's reach with a clear shot, not left alone as
    untouchable, neared or passed. Said once a pack."""
    player = world.player
    if not PACK_FIGHT_FIRST or player is None or act.goal.do == FIGHT:
        return False
    if isinstance(act, Advance) and (act.reason or act.dodge or act.onward):
        return False
    here = (player.x, player.y)
    held = [
        m
        for m in foes
        if herald_pack.in_pack(m.tier)
        and m.unit_id not in self.untouchable
        and m.unit_id not in self.nearing
        and self.passed.get(m.unit_id, -math.inf) <= now
        and in_reach_of(ground, here, (m.x, m.y), self.attack.reach, world.doors)
    ]
    if not held:
        return False
    key = herald_pack.key_of(herald_pack.members(held))
    if key is not None and key not in PACK_FIRST_SAID:
        if len(PACK_FIRST_SAID) > 200:
            PACK_FIRST_SAID.clear()
        PACK_FIRST_SAID.add(key)
        LOG.info(
            'Macro: pursuit: %s waits: %d of a tier %d Herald pack in reach, the fight first (PACK_FIRST)',
            act.goal.label, len(held), max(m.tier for m in held),
        )  # fmt: skip
    return True


def fight_kills(self: Hunter, world: World, here: Point, now: float) -> float:
    """YIELD_KEEPS_KILLING: the clock the strike's reach last saw progress (a hostile in it seen dead that was not, or
    one's life down; none of those raised: NET_PROGRESS), against the look before; -inf before any."""
    reach = self.reach
    near = [
        m
        for m in world.monsters
        if not getattr(m, 'ally', False)
        and getattr(m, 'owner', NO_OWNER) == NO_OWNER
        and math.dist(here, (m.x, m.y)) <= reach
    ]
    dead = frozenset(m.unit_id for m in near if m.mode in (0, LYING_DEAD))
    lives = {m.unit_id: m.life for m in near if m.mode not in (0, LYING_DEAD) and getattr(m, 'life', 0) > 0}
    at, was_dead, was = getattr(self, 'killing', (-math.inf, None, {}))
    raised = getattr(self, 'slain', (None, frozenset()))[1] if NET_PROGRESS else frozenset()
    if was_dead is not None and progressed(dead, lives, was_dead, was, raised):
        at = now
    self.killing = (at, dead, lives)
    return at


def hold_stands(facts: Facts | None) -> bool:
    """Whether the look's priced hold is allowed: not vetoed and within the life budget (YIELD_KEEPS_KILLING)."""
    if facts is None or not facts.priced:
        return False
    return any(
        isinstance(c.act, Hold) and veto(c.harm, facts.life, facts.safety) is None and c.harm.worst <= facts.budget
        for c in facts.candidates
    )


def keeps_killing(self: Hunter, world: World, foes: list[Monster], ground: Ground, found: Judged, now: float) -> bool:
    """Whether the fight stays for its strikes (YIELD_KEEPS_KILLING): `found`'s act is the pursuit's own move (no
    reason, no dodge or walk round), not the rushed run's, toward the run's boss, the loot or the way out, nor a fresh
    advance press's; the look's hold stands (`hold_stands`); and the fight here still kills (`fight_kills` within
    KEEPS_SECONDS) or a tier 4-5 Herald pack's member is in reach (`pack_in_reach`). Said once a goal."""
    act, posted, player = found.act, found.posted, world.player
    if not YIELD_KEEPS_KILLING or player is None or not isinstance(act, Advance):
        return False
    if act.reason or act.dodge or act.onward:
        return False
    goal = act.goal
    if goal.do in (LOOT, LEAVE) or the_runs_boss(goal, posted) or (posted is not None and posted.rush):
        return False
    if found.pressed and posted is not None and posted.advance:
        return False
    if not hold_stands(getattr(self, 'look_facts', None)):
        return False
    since = now - getattr(self, 'killing', (-math.inf, None, {}))[0]
    pack = pack_in_reach(self, world, foes, ground, now) if since > KEEPS_SECONDS else []
    if since > KEEPS_SECONDS and not pack:
        return False
    if goal.label not in KEEPS_SAID:
        if len(KEEPS_SAID) > 200:
            KEEPS_SAID.clear()
        KEEPS_SAID.add(goal.label)
        why = f'the kill {since:.1f} s ago' if since <= KEEPS_SECONDS else f'{len(pack)} of a Herald pack in reach'
        LOG.info('Macro: pursuit: %s waits: the fight here still kills (%s) (YIELD_KEEPS)', goal.label, why)
    return True


def pack_in_reach(self: Hunter, world: World, foes: Sequence[Monster], ground: Ground, now: float) -> list[Monster]:
    """The live tier 4-5 Herald pack's members in the strike's reach with a clear shot, not left alone as untouchable,
    neared or passed."""
    player = world.player
    if player is None:
        return []
    here = (player.x, player.y)
    return [
        m
        for m in foes
        if herald_pack.in_pack(m.tier)
        and m.unit_id not in self.untouchable
        and m.unit_id not in self.nearing
        and self.passed.get(m.unit_id, -math.inf) <= now
        and in_reach_of(ground, here, (m.x, m.y), self.attack.reach, world.doors)
    ]


def yielded_act(self: Hunter, run: Run, world: World) -> tuple[Judged, float] | None:
    """The look `key_asks` let the fight go for, and its clock, while it still holds (YIELD_TAKES): within YIELD_FRESH,
    the character within YIELD_MOVED of where that look saw it on the same level, the same press, not hurt since and
    the move not barred since. Taken once; None: the next look judges again."""
    kept, self.yielded = self.yielded, None
    player = world.player
    if kept is None or not YIELD_TAKES or player is None:
        return None
    found, at, there, area, pressed_at = kept
    now = run.clock()
    current = self.pursuit.pressed_at if self.pursuit is not None else -math.inf
    if (
        not 0.0 <= now - at <= YIELD_FRESH
        or player.area != area
        or math.dist((player.x, player.y), there) > YIELD_MOVED
        or current != pressed_at
        or self.hurt_at >= at
        or self.barred(found.act, now)
    ):
        return None
    return found, at


def tell(self: Hunter, run: Run, reason: str | None, *, aloud: bool = True, again: float | None = None) -> None:
    """Says a decision that moved nothing, once per change of reason. Not `aloud`: the log only. `again`: seconds
    after which the same reason is said once more (I6)."""
    repeated = (
        again is not None and reason is not None and reason == self.told.reason and run.clock() - self.told_at >= again
    )
    if self.told.new(reason) or repeated:
        self.told_at = run.clock()
        LOG.info('Macro: pursuit: %s', reason)
        if aloud:
            run.say(f'{reason[:1].upper()}{reason[1:]}')  # type: ignore[index]


# (game, level) the run's exploring for its bosses was said on (`boss_explore`)
BOSS_EXPLORE_TOLD: set[tuple[str, int]] = set()


def unfound_bosses(self: Hunter, area: int) -> list[Boss]:
    """The bosses of the game's ledger alive on `area` with no place known and no unit taken (pursuit.py BOSS_EXPLORE):
    none with the switch or the ledger's hold off (zonenav.py BOSSES_HOLD), with no zone agenda, or once the level's
    runs are past its allowance and BOSS_RUNS (zonenav.py `fully_explored`'s bound)."""
    agenda = self.agenda
    if not pursuit_rules.BOSS_EXPLORE or not zonenav.BOSSES_HOLD or agenda is None or agenda.plan is None:
        return []
    plan = agenda.plan
    if isinstance(plan, Itinerary) and zonenav.on(plan):
        node = zonenav.graph_of(plan).nodes.get(area)
        if node is not None and agenda.worked[area] >= zonenav.runs_allowed(node) + zonenav.BOSS_RUNS:
            return []
    return [boss for boss in agenda.bosses.alive_in(area) if boss.place is None and boss.unit is None]


def boss_explore(
    self: Hunter, run: Run, world: World, player, goal: Goal | None, bosses: Sequence[Boss], now: float
) -> Goal | None:
    """The next unexplored room as the run's goal while `bosses` are alive on the level, their place not known
    (pursuit.py BOSS_EXPLORE); `goal` as it was with no room left (the run ends, the bosses named)."""
    room = self.next_room(run, player, player.area, now)
    if room is None:
        return goal
    spend = goal.spend if goal is not None else STANDING
    found = rest_of_level(room, goal, self.reach, spend)
    named = bosses_said(bosses)
    key = (world.game_name, player.area)
    if key not in BOSS_EXPLORE_TOLD:
        if len(BOSS_EXPLORE_TOLD) > 200:
            BOSS_EXPLORE_TOLD.clear()
        BOSS_EXPLORE_TOLD.add(key)
        # The watch tools may read it (d2-loop-watch logwords.py)
        LOG.info('Macro: run: %s %s: the run explores for %s before it ends (%s)', named,
                 pursuit_rules.BOSS_EXPLORE_SAID, 'it' if len(bosses) == 1 else 'them',
                 goal.label if goal is not None else 'no route stage')  # fmt: skip
    return replace(found, label=f'{named} {pursuit_rules.BOSS_EXPLORE_SAID}: {room[1]}')


def defer(self: Hunter, run: Run, goal: Goal | None, why: str, seen: Pursuit | bool | None = True) -> None:
    """Hands the press to the route's own step (a door, the loot, the leaving, a panel, the town) or the key's
    routine: raises Cancelled and takes the press out of the mailbox (a level run's leash stays). `seen`: the
    mailbox as the look read it; a press posted since stays (True: whatever it holds now)."""
    with self.mailbox:
        posted = self.pursuit if seen is True else seen
        if not isinstance(posted, Pursuit):
            posted = None
        if self.pursuit is posted:
            self.pursuit = replace(posted, spent=True) if posted is not None and posted.leashed else None
    key = posted.key if posted is not None else 'teleport'
    if self.hand_over is None:
        self.tell(run, f'{why}: nothing performs it here')
        return
    LOG.info("Macro: pursuit: %s: the route's own step takes the press", goal.label if goal is not None else why)
    self.hand_over(key)
    raise Cancelled


def blocked(self: Hunter, run: Run, units: frozenset[int]) -> None:
    """The hands found `units` in the way of the goal's act (teleport.py `Covered`): the fight with them
    comes first for that goal (`blockers`, goals.py `first_fight`)."""
    base = self.base
    if base is None:
        return
    held = self.blocking
    if held is not None and held[0] == base.label:
        units = units | held[1]
    self.blocking = (base.label, units, run.clock() + BLOCK_SECONDS)
    LOG.info('Macro: pursuit: %s: %d in the way of its act, the fight first', base.label, len(units))


def unshot(self: Hunter, goal: Goal | None, act: object, foes: Sequence[Monster], now: float) -> None:
    """A fight goal the moves are as near as they end to with nothing in reach (pursuit.py `moved`: a wall between, a
    stand-off kept): after UNSHOT_SECONDS its monster is left alone for UNTOUCHABLE_SECONDS (a boss never), so the next
    look's goal goes on: the pickup it barred, the next hostile, the route's stage."""
    stalled = (
        UNSHOT_SECONDS is not None
        and goal is not None
        and goal.do == FIGHT
        and goal.unit is not None
        and isinstance(act, NoWay)
        and act.arrived
        and 'nothing in reach' in act.reason
    )
    if not stalled or goal is None or goal.unit is None or UNSHOT_SECONDS is None:
        self.unshot_since = {}
        return
    since = self.unshot_since.get(goal.unit, now)
    self.unshot_since = {goal.unit: since}
    if now - since < UNSHOT_SECONDS:
        return
    prey = next((m for m in foes if m.unit_id == goal.unit), None)
    if prey is None or kept(self, goal, prey):
        return
    self.unshot_since = {}
    self.untouchable[prey.unit_id] = now + UNTOUCHABLE_SECONDS
    LOG.info(
        'Macro: pursuit: %s: no shot at %s from where the moves end for %.1f s: left alone for %.0fs',
        goal.label, label(prey), now - since, UNTOUCHABLE_SECONDS,
    )  # fmt: skip


def recover(self: Hunter, now: float, foes: Sequence[Monster]) -> None:
    """The loop's still watchdog asked for a recovery (`Hunter.recover_asked`; running/watch.py `still_recovery`): the
    last look's fight goal and what barred its act are left alone for UNTOUCHABLE_SECONDS (a boss never), a clearing
    goal with no monster is passed (`pass_by`), and the next look chooses again. The watchdog's leave stays the last
    resort."""
    self.recover_asked = None
    goal = self.pursued
    by_unit = {m.unit_id: m for m in foes}
    blockers = self.blocking[1] if self.blocking is not None else ()
    left = [unit for unit in blockers if unit in by_unit and not self.boss(by_unit[unit], pursued=False)]
    if goal is not None and goal.unit in by_unit and goal.do == FIGHT and not kept(self, goal, by_unit[goal.unit]):
        left.append(goal.unit)
    left = sorted(set(left))
    for unit in left:
        self.untouchable[unit] = now + UNTOUCHABLE_SECONDS
    self.blocking = None
    self.unshot_since = {}
    if goal is not None and goal.clearing and goal.unit is None:
        self.pass_by(goal, 'the loop stood still: recovering', now)
    LOG.info(
        'Macro: run: recovery from a stand: %s; %d left alone for %.0fs',
        goal.label if goal is not None else 'no goal', len(left), UNTOUCHABLE_SECONDS,
    )  # fmt: skip


def kept(self: Hunter, goal: Goal, monster: Monster) -> bool:
    """Whether `monster`, the goal's, is never left alone by `unshot` or `recover`: a boss (`Hunter.boss`: an act
    boss, a Herald, a dear class) or the monster of the route's own fight stage. A pickup's "fight first" monster is
    neither (the Kurast Sewers stall, 2026-10-21 17:51: "the elite 215 ... shot blocked" for 45 s)."""
    if self.boss(monster, pursued=False):
        return True
    return goal.unit == monster.unit_id and goal.stage is not None and goal.stage.kind == FIGHT and not goal.clearing

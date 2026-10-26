"""Observation and candidate assembly for the pure pursuit arbiter.

Memory: observed weapon profiles, how long a pressed goal has been blocked, the way the character came. Nothing here
delivers input or chooses a goal. A place's price counts the build's own strikes from it (stance `falls`) and its
guard (`Shield`); escapes come from the threat's geometry; caps and a deadline bound the look
(rca/2026-10-13/safety-pricing.md, "Second pass").
"""

import math
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import NamedTuple

from inventory_tracking.combat import bolts, harm as harm_module, pack as herald_pack, stand_ins, threats
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
    most_blow,
    sent_onto,
    stock_share,
    stood_in,
    unread,
    veto,
)
from inventory_tracking.combat.mechanics.life import monster_level, rank_share, terrorized
from inventory_tracking.combat.mechanics.tables import area_level
from inventory_tracking.combat.policy import Observation, Point
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.monsters import SHOT_REACH, shoots
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
from inventory_tracking.combat.threats import dolls, drain_escape, manaburn
from inventory_tracking.common import LOG
from inventory_tracking.config import with_overrides
from inventory_tracking.game.layout import NO_OWNER, STRIKING_MODES
from inventory_tracking.game.records import Loot, Monster, World
from inventory_tracking.game.view import DEFAULT_ASPECT, Viewport
from inventory_tracking.macros import pursuit as arbiter
from inventory_tracking.macros.build import Attack, Draw, DrawPrice, Leg, NoWay, PricedStep, Shield, Step
from inventory_tracking.macros.cta import ORDERS_CLEAR as CLEAR, OrdersLook, orders_state
from inventory_tracking.macros.drinking import on_belt
from inventory_tracking.macros.goals import Goal
from inventory_tracking.macros.pursuit import REBUFF_SAID, Act, Candidate, Facts, Hold, Move, Operate, decide
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.supply import spendable as stock_life
from inventory_tracking.macros.travel import planning
from inventory_tracking.models import PotionType


ESCAPE_REACH = (12.0, 22.0)  # units from the threat's weighted centre, near and far
ESCAPE_TURN = math.radians(40)
TRAIL_STEP = 4.0  # units between two points of the way the character came
TRAIL_POINTS = 24
ESCAPE_SAME = 4.0  # units: two escapes nearer than this are one
BEHIND = 4.0  # units beyond a companion, away from the threat
ESCAPES_MOST = 6  # escape places asked of the navigator in one look (the cost of a look)
RAYS = 8  # plain rays round the character, asked after those while time is left
FOOTING_RINGS = (1.5, 3.0)  # units round an escape's place where footing is looked for
FOOTING_TURNS = 8
FALL_HORIZON = 10.0  # seconds the character's own strikes are counted over for a stand's clear time
# A Teleport to one spot pressed DUD_HOPS times in a row over DUD_AFTER s with the character not moved past STILL_UNITS
# cast nothing (game 30, 21:36:45: a stand under the skill bar, pressed 5 times): the spot is barred for DUD_SECONDS,
# within DUD_UNITS of it. 2026-10-26 (rca/2026-10-26/cast-nothing-findings.md): counted at the press (hunting/moves.py
# `pursue` calls `Safety.hopped` for the act it makes), no longer at every look's choice: 1874 of 1909 drops over 31.6 h
# had never been pressed (the fight kept, or the pursuit's dead end filtered the act); the Key of Hate at 23:33:18 on
# 2026-10-25, chosen 7 looks while the fight struck, was barred 20 s and took 17.7 s to pick up
DUD_HOPS = 3
DUD_AFTER = 1.0
DUD_SECONDS = 20.0
DUD_UNITS = 3.0
STILL_UNITS = 1.5
DUD = 'a Teleport there cast nothing'
# A move back to where the last safety Teleport left, within BOUNCE_WINDOW s of it and with the character still within
# BOUNCE_NEAR of its landing, is barred (BOUNCED): two safety moves that undo each other (the aiming agent's RCA of
# JUMP_CLUSTER 20261021T182256Z-115, 21:23:39-43: "mana burn: ... within 18" hopped A -> B, the retreat at B went back
# to A, three times, no strike; the coordinator, 2026-10-21 ~21:30). The arbiter's least lethal act still takes it when
# everything is barred. False: as before.
BOUNCE_BACK = True
BOUNCE_WINDOW = 3.0  # seconds
# 2026-10-23 (the player: "try to push exp/hour more"; rca/2026-10-23/approach-veto-findings.md, keep-range-findings.md)
# The approach and the keep range's hop undid each other: the fight's place (combat/pack.py PLACES_KEEP_RANGE, on) and
# the safety's own moves have to land where the hop would not take the character out at once.
# PACK_RANGE_LANDING: no move that is not a retreat or a dodge lands where a tier 4-5 Herald's pack would bring the
# hop back (combat/pack.py `breaks_range`, the hop's own `why_back`, with the demons the draw sends), unless it leaves
# a spot that does so for one farther from the pack (PACK_RANGE_LANDED). Take 20261022T235532Z-51, 02:57:20.8:
# "Teleport toward full clear: the monster 174" landed 6-7 off three archers right after hop 3 of 3. False: as before
# (manaburn.py PACK_LANDING, off, alone).
PACK_RANGE_LANDING = True
PACK_RANGE_LANDED = "kept at range: a landing the pack's hop would leave at once"
REAGGRO_KINDS = (herald_pack.KEEP, herald_pack.PLACE)  # the jumps REAGGRO_BY_MARK bars (not a retreat)
# RANGE_STALL_LIFT (2026-10-24, rca/2026-10-24/canyon-spin-findings.md; the player: "exp/hour, never die", "the loop
# must never stand still"): Tal Rasha's Tomb, 15:42:21-15:47:13, take 20261024T124212Z-68. The run's way out (Canyon of
# the Magi) lay past a room whose south wall an idle tier 5 Herald pack of 15 Steel Weevils (scarab4) walked along,
# 16-26 off, behind a doorway no missile flies through: every landing toward the way out lay within PACK_BACK +
# LEAD_UNITS of a member (PACK_RANGE_LANDED), and the retreat and the safe approach undid each other 531 times in
# 292 s, 0 kills, 0 life lost, until the runner's 300 s watchdog stopped the loop. No budget gives up a route's own goal
# (hunting/judging.py `kept_goal`, STILL_BUDGET), and the knot had passed the pack already. True: once a goal that is
# no fight and no clearing goal (the budgets pass those) has had its progress barred by PACK_RANGE_LANDED for
# RANGE_STALL_SECONDS of retreats and safe approaches, with nothing in reach, no member on the character (the hop's own
# `why_back`) and no WAIT_LOST of the life lost, that bar alone is lifted for its moves (`Pricing.range_lifted`) until
# one of those changes; the rollouts' veto, the life budget and the pack's hop stay. False: as before. On from the
# restart after 16:40 on 2026-10-24 (arena: 410 GLUED pairs identical off/on, 0 new deaths; test_canyon_spin.py).
RANGE_STALL_LIFT = True
RANGE_STALL_SECONDS = 5.0  # hunting/judging.py DANCE_SECONDS
RANGE_STALL_MOVES = ('retreating', 'safe approach')  # pursuit.py `arbitrate`'s retreats, safety.py `approach`
# BURN_LANDING_MARGIN: a move that is not a retreat or a dodge lands no nearer a draining pack's burner than its keep
# range and the hop's own clearance beyond it (manaburn.py HOP_CLEAR), capped BURN_SHORT inside the strike's reach so a
# strike stays possible; manaburn.py `intrudes` bars only a landing inside the keep range. Take 20261022T235916Z-49,
# 03:00:07-51: 12 of 43 approach steps landed 18-21 off the nearest member of a Mana Burn pack (keep 18), the pack
# closed 1-2 units by the next look and the hop fired at 16.0-17.9: 24 jumps, 0 kills in 32 s. False: as before.
BURN_LANDING_MARGIN = True
BURN_SHORT = 2.0  # units inside the strike's reach the margin's edge stays
BOUNCE_NEAR = 3.0  # units
BOUNCED = 'back where the last safety hop left'
# A Teleport while a read model's act under way is walked out of (combat/threats `Threat.walked`: Diablo's lightning,
# the player 2026-10-20, combat/threats/diablo.py WALK_AROUND): barred but as a retreat, the life-danger escape (nothing
# else fits the budget or the veto: `Safety.retreats`)
WALKED = "Diablo's lightning is walked round, not hopped out of"
# A walk round an act under way that is walked out of (combat/threats `Threat.around`: Diablo's lightning), from the
# look that first sees it at the character to its end: each look offers the next place round him (both ways at the
# first, then the way taken: `Safety.rounds`), taken over the rest while it fits the budget and the veto (pursuit.py
# `Move.onward`; else the retreats, as before) and clicked while the character still walks (hunting/moves.py). The
# player, 2026-10-21 ~00:05: "diablo fight - we need cycle around him, close to him" (2026-10-20: "just walk around of
# him"). The arena duel against the walks across alone (WALK_AROUND), 20 seeds, at combat/threats/diablo.py
# AROUND_RADIUS 14, 22 / 44 strikes, from 9 units: life lost 137 -> 71 and 398 -> 269 (lightning 45 -> 6, 107 -> 9;
# fire wall 67 -> 36, 229 -> 198; ring 25 -> 29, 50 -> 62; melee 0, 12 -> 0); from 18 units, where the walks across
# stand off his wall, 58 -> 69 and 223 -> 267 (lightning 17 -> 3, 68 -> 6; wall 16 -> 37, 85 -> 203). Kills 1.7 to
# 3.6 s longer (10.2 -> 12.1, 19.7 -> 23.3; from 18 10.0 -> 11.8, 19.5 -> 23.1): no strike while the stream comes (a
# strike between the steps took the stream back: 122..174 lost). Circling between his casts too, a strike between
# steps, tripled the kill (30.5 s for 22 strikes) and lost more (212..297). False: steps across as before.
WALK_ROUND = True
# The player, 2026-10-21 ~10:00, of the tier 5 Herald fight of 09:30:41 ("we have tanked most of the damage in the most
# dumb way"; asked whether to fix the pricing first: "fix it first"; rca/2026-10-21/herald-fight-findings.md §2 step 5).
# Holding was priced "with the draw cast" (`hold`: Death Mark sends the demons, the pack turns) while the mark's three
# keys on the Herald had taken on no monster and it was not cast again: holding among 10 Bramble Hulks priced 28.5 life
# for the next 0.72 s against 403 and 467 lost (tests/inventory_tracking/macros/test_herald_pricing.py). True: holding
# is priced with the draw only while the draw lands (`draw_lands`: its keys of the last `Draw.lasts` seconds took on
# some monster, macros/buffs.py `Buffs.lands`); its prices are still kept for the build (`draws`). False: always, as
# before.
DRAW_CASTABLE = True
# The same fight: with nothing in the budget, fighting out was weighed against the retreats over its 0.72 s dwell while
# each retreat is priced over its whole way (1.2-2.7 s), so per second about equal harm read as "less harm than any
# reachable retreat". True: fighting out is weighed over the escape horizon (`Held.ahead`, max(horizon, dwell)), as a
# retreat is. False: over the dwell, as before.
ESCAPE_SAME_SPAN = True
RESISTS = ((36, 'physical'), (39, 'fire'), (41, 'lightning'), (43, 'cold'), (45, 'poison'), (37, 'magic'))
# Stats are unpenalized and difficulty is not observed: Hell assumed, never capped gear.
HELL_PENALTY = 100.0
SWAP_SECONDS = 0.75
WAITING = 'safety: waiting here: every way out costs more than standing'
# WAIT_LIFT (2026-10-23, rca/2026-10-23/death-canyon-findings.md §9): with the companions taken along by each Teleport
# (as the game does), the Chaos Sanctuary run stood on WAITING from 48 s to its stall at 103 s: an idle Mana Burn pack
# 23-29 off kept the seal's move barred ("kept at range") and never came ("the loop never stands"). True: after
# WAIT_HORIZON s standing with nothing in reach, no hostile seen WAIT_MOVED from where it stood and no WAIT_LOST of the
# life lost, the keep ranges' bars are lifted for the moves on the way (`Pricing.waited`) until one of those changes.
# False: as before.
WAIT_LIFT = True  # on 2026-10-23 ~20:30, gated: CS stalls 4/20 -> 1/20, kills 170 -> 190, 0 deaths, 1200 pairs same
WAIT_HORIZON = 4.0  # combat/threats/dolls.py PATIENCE's
WAIT_MOVED = 2.0  # units: a hostile that moved so far from its place at the wait's start is coming (or woke)
WAIT_LOST = 0.02  # of the most life
BURNING = 'safety: waiting for what burns on the way to go out'  # `burnt_out`
FIRING = 'firing spot'  # a move to a strike stand (held to pursuit.py's commitment)
# An escape priced against holding, taken for the life it saves, so not held to the firing stand's commitment.
STEPPING = 'stepping'
AWAY = 'away from the threat'  # why a place of the threat's geometry is offered
BOLT_DODGE = 'out of the lane of bolts in flight'  # why such a side step is offered (combat/bolts.py, BOLTS_IN_FLIGHT)
# The build's draw (build.py `Draw`), weighed in a fight (`Safety.weigh`) onto the DRAW_TARGETS largest harm shares,
# the best gain and the DRAW_LEADERS nearest leaders: the mark goes "on the leader / most dangerous monster" (the
# player, 2026-10-14). Not onto one companions already hold (within DRAW_HELD of their landing distance). A price
# lasts DRAW_FRESH seconds.
DRAW_TARGETS = 2
DRAW_LEADERS = 2
DRAW_HELD = 3.0
DRAW_FRESH = 0.5
# A retreat that keeps the fight (rca/2026-10-14/baal-sim.md fix 1): when one hostile's kill ends KEEP_SHARE of the
# harm here (with what is bound to it, combat/threats `bound`), on the ring KEEP_MARGIN inside the strike's reach.
KEEP_SHARE = 0.5
KEEP_MARGIN = 1.5
KEEP_TURNS = tuple(math.radians(turn) for turn in (0, 35, -35, 70, -70, 110, -110, 180))
KEEP_MOST = 4  # such places asked of the navigator in one look
# A missile the look reads for a read model (combat/threats): (owner unit, missile class, x, y).
Flights = Callable[[frozenset[int]], Sequence[tuple[int, int, float, float]]]
# The fight's own better stand (hunt.py -> stance `camp`) is priced as a firing stand for STAND_FRESH seconds
# (`offer`); without it a safe fight struck from the edge of its reach (rca/2026-10-14/run-1932-findings.md §4).
STAND_FRESH = 0.7
# Share of the look's time the goal's way may grow in (travel.py `planning`); unbounded, one look took 5.1 s
# (rca/2026-10-14/run-2040-findings.md §1.2).
WAY_SHARE = 0.5
# The way's time with no hostile within QUIET_WAY_UNITS: one look grows a cold field to the next chest (268 waits in
# 78 games at 40 ms, 2026-10-17); well within hunt.py STALE_LOOK 0.3 s.
QUIET_WAY_SECONDS = 0.15
QUIET_WAY_UNITS = 30.0  # goals.py CLEAR_WAY
# Units between the places tried, back from a landing a live doll bars toward the character, for the nearest one on the
# way that none bars (combat/threats/dolls.py DOLL_LAND, `Pricing.short_of_dolls`)
DOLL_STEP = 2.0


def way_seconds(here: tuple[float, float], hostiles: Sequence[tuple[float, float]], look_seconds: float) -> float:
    """Seconds of a look the goal's way may grow in (QUIET_WAY_SECONDS when quiet, else WAY_SHARE of it)."""
    if all(math.dist(here, at) > QUIET_WAY_UNITS for at in hostiles):
        return max(QUIET_WAY_SECONDS, look_seconds * WAY_SHARE)
    return look_seconds * WAY_SHARE


# A look over OVER_BUDGET times its time is logged, at most once in SAID_EVERY seconds (`Safety.over`).
OVER_BUDGET = 2.0
SAID_EVERY = 1.0


def footing(field_: Field, here: Point, point: Point) -> Point | None:
    """`point`, or the nearest footing on the FOOTING_RINGS round it, off walls and in line from `here`; None if
    none. A threat's geometry knows nothing of the ground (the Chaos Sanctuary's star has unwalkable cells)."""
    for ring in (0.0, *FOOTING_RINGS):
        for k in range(FOOTING_TURNS if ring else 1):
            angle = k * math.tau / FOOTING_TURNS
            spot = (point[0] + ring * math.cos(angle), point[1] + ring * math.sin(angle))
            if field_.bar((math.floor(spot[0]), math.floor(spot[1]))) or field_.wall(*spot):
                continue
            if field_.clear(here, spot):
                return spot
    return None


def clearance(here: Point, spot: Point, hostiles: Sequence[Point], walk: bool) -> float | None:
    """Units from a move's way to the nearest of `hostiles` (pursuit.py `Candidate.clear`): along the straight walk from
    `here` (the navigator's leg), else at the landing; None with no hostile about."""
    if not hostiles:
        return None
    if not walk:
        return min(math.dist(spot, at) for at in hostiles)
    dx, dy = spot[0] - here[0], spot[1] - here[1]
    length = dx * dx + dy * dy
    found = math.inf
    for at in hostiles:
        t = 0.0 if length <= 0 else max(0.0, min(1.0, ((at[0] - here[0]) * dx + (at[1] - here[1]) * dy) / length))
        found = min(found, math.dist(at, (here[0] + t * dx, here[1] + t * dy)))
    return found


# The death at 23:35:33.97 on 2026-10-21 (rca/2026-10-21/death-findings.md): the looks of the last 5 s ran late (81-99
# ms against `look_seconds` 0.08), so the retreats priced were the keeper's and the threat geometry's first two, all
# within 2-6 units of the Herald's pack or of the next pack (two packs either side put the threat's centre between
# them), and the rays round the character were never asked; 15-20 units south lay open ground. The player, 2026-10-21:
# "we must not die or we lose exp and our gear". True: with nothing safe, CLEAR_ASKED places on CLEAR_RINGS round the
# character farthest from every hostile are asked first, late or not (`clearest`). False: as before.
CLEAR_ESCAPES = True
CLEAR_RINGS = (14.0, 22.0)  # units from the character (ESCAPE_REACH)
CLEAR_TURNS = 12
CLEAR_ASKED = 2


# The kill credit while the life is under its floor (rca/2026-10-21/death-findings.md, "The kill credit"): the look's
# forecast deaths (stance `falls`) end a hostile's blows in the rollouts. Over the 1129 takes of 2026-10-21, of the
# kills forecast within 1.5 s at the looks that held with the life budget over 0, 61% came within 1.5 s; at the 310
# that held with the budget 0 (18 takes), 35% (25% at every budget-0 look); the death of 23:35:33.97 priced its holds
# and landings by the Herald's pack at 2-20 on kills that never came (the Night Lords lost 20% in 20 s). The player,
# 2026-10-21: "we must not die or we lose exp and our gear". True: with the life budget 0 a look credits no kill to the
# character's strikes (the hostiles strike through every dwell); over 0, as before. False: the credit always.
FLOOR_NO_CREDIT = True

# The Fane's arena (tests/.../situations/fane_death.py; rca/2026-10-21/fane-death-sim-findings.md), 2026-10-22. The
# player: "we must have top priority to no die ourselves and prevent loosing experience".
#
# CLEAR_FOOTING: the clear places (`clearest`) asked in a walled corridor all lay in the walls, so no retreat was ever
# priced there (drawn, rolled, seed 5: 12 s in the pack, 4 rejuvenations, dead at 16.68 s). True: only places on
# footing the window shows are asked. False: every ring place, as before.
CLEAR_FOOTING = True
# DANGER_LOOK: under late looks (81-99 ms against `look_seconds` 0.08, as the take's) the retreats past the first were
# cut look after look while the life was under its floor. True: with the life budget 0, or a rejuvenation just drunk
# (`Safety.alarmed`, set by the hunt), a look may take DANGER_SECONDS before it settles. False: `look_seconds` always.
DANGER_LOOK = True
DANGER_SECONDS = 0.2
# AURA_FORECAST: the forecast played no aura. Beside the Might unique the unique Night Lord's most blow is 452 physical
# x Might x Amplify Damage 1.82 + 452 fire x 0.91; the forecast priced it at 1235, under the life of the whole play.
# True: a hostile's blows are raised, on their physical points, by its own damagepercent (stat 25: the game's sum of
# the damage auras on it, Might, Concentration, Fanaticism; the Fane read 190 by the Might unique, 475 by Might and
# Concentration), else by the damage auras its stats 350/351 showed, summed (`unit_raise`; the look reads its full stat
# list already). Where the look holds no such read (a replay, the arena), the auras the Aura Enchanted hostiles' state
# words show raise every hostile within the aura's range (`raised`; none shown or unread: none. Taking an unshown one
# as Might priced the arena's Heralds, which play Might x2 within 16, at x2.9 within 46: 3 of 10 t5 Heralds dead in
# 60 s against 8, and the arena's r4 and boss-in-reach tests failing). Conviction and Amplify Damage on the character
# are in the resistances read already (stats 36-45: Conviction's cut showed fire 194 -> 109 at 23:35:24.18). False: no
# aura.
AURA_FORECAST = True
AURA_MOD = 30  # monumod `aura`: Aura Enchanted
# RAISE_KEEP (2026-10-22, the coordinator from the sim's pursuit-mode Fane deaths: the x5.75 unique Night Lord's stat 25
# read 285 or 475 as a Concentration minion walked in and out of its aura's range, x3.85 or x5.75: a look that read
# 285 priced the next second's 3645 blow at 2441): a hostile's raise is the most damagepercent read on it within
# RAISE_SECONDS (`Safety.kept_percent`). Amplify Damage on the character is in the read physical resistance already
# (stat 36: 18 -> -82 at 23:35:23.35 in the take; the arena shows it so, `most_blow` 3645 at x5.75). False: the read of
# the moment.
RAISE_KEEP = True
RAISE_SECONDS = 5.0
# The aura holder's state (states.txt) -> its skill (skills.txt `aurastate`), read from pricing/raw/game-excel
AURA_STATES = {33: 98, 42: 113, 49: 122, 35: 102, 43: 114, 46: 118, 28: 123, 40: 108, 36: 103}
# Skill -> (+% damage at level 1, per level, range at level 1, per level): skills.txt Might ln34 (Param3 40, Param4 10)
# and ln12 (16, 2); Concentration ln34 (60, 15), ln12 (16, 2); Fanaticism ln56/2 (50, 17, halved: the others'
# share) and ln12 (11, 1)
AURA_DAMAGE = {98: (40.0, 10.0, 16.0, 2.0), 113: (60.0, 15.0, 16.0, 2.0), 122: (25.0, 8.5, 11.0, 1.0)}
# Skill -> its level on the monsters: the aura level is not in the tables (the game sets it), so it is read off the
# takes: the stats 350/351 (`modifierlist_skill`/`_level`) of the 8123 Aura Enchanted first sightings in the 19,111
# takes of 2026-10-09..22 hold Might at 12-16 (16 at monster levels 67-93, 400 of them; the Fane's Might unique
# 120235824: 16), Concentration 16 (the Fane Herald's minions), Fanaticism 9-12 (12). The highest seen is taken:
# Might +190% (x2.9, its range 46 units), Concentration +285%, Fanaticism +118.5%. terror/danger.py `aura_physical`
# (Might 2.0) is level 7's; the arena plays that (tests/.../arena/mobs.py AURA_FACTOR).
AURA_LEVELS = {98: 16, 113: 16, 122: 12}
# ORDERS_PREDICT: the forecast priced a fight with the most life of the moment though Battle Orders would run out in it
# (2943 -> 1896 at the Fane, the death 1.3 s after). True: with Battle Orders on and under PREDICT_LEFT s left of it
# (macros/cta.py `orders_look`), the look prices the life as it will be after: the same share of the most life without
# it (`OrdersLook.factor`). Its age not known (a restart), the life of the moment: the rebuff comes at the first safe
# moment or by its retreat (REBUFF_RETREAT), and pricing every such fight after it cut the arena's Herald kills
# (fane-death-24: 15 of 20 -> 10 within the play). False: the life of the moment.
ORDERS_PREDICT = True
PREDICT_LEFT = 10.0  # seconds: macros/cta.py FIGHT_LEFT, the renewal's window
# REBUFF_RETREAT: Battle Orders due in a fight not safe to cast in (macros/cta.py REBUFF, `cast_safe`): Teleports to
# places at least REBUFF_CLEAR from every hostile (on REBUFF_RINGS, on footing), priced as dodges named REBUFF_SAID
# that the arbiter takes first unless vetoed (pursuit.py REBUFF_FIRST); its landing casts it (cta.py REBUFF_GRACE). At
# most REBUFF_HOPS while it stays due. False: none.
REBUFF_RETREAT = True
REBUFF_CLEAR = 14.0
REBUFF_RINGS = (18.0, 24.0)
REBUFF_ASKED = 4
REBUFF_HOPS = 3
# The rebuff retreat's landing (`Safety.landed`): the first jump landed REBUFF_LANDS s of the choice at most, for the
# Death Mark again after it (builds/warlock/mark.py REMARK_AFTER_REBUFF, 2026-10-22)
REBUFF_LANDS = 2.0
# KILL_FIRST (2026-10-22, the coordinator from the sim's round 4: "a low-life unit whose blow reaches the life is killed
# first, ahead of the rebuff, when its time to kill is under its time to reach us. Use the live life share. Doll
# Heralds always qualify (the player's ruling); apply the same time-to-kill test generally"; the player of
# danger-durance-1956: "you just aggro doll herald with death mark and then kill him VERY fast"): no rebuff retreat
# (`rebuff_back`) while a hostile in the strike's reach whose most blow (combat/harm.py `most_blow`, the auras on it)
# reaches the life can be killed before it reaches the character: its life to come (the look's share of its points,
# its rank's with combat/mechanics/life.py `rank_share`) over KILL_RATE under its walk to REACH_UNITS, and under the
# Battle Orders time left. A doll Herald (combat/threats/dolls.py `herald_doll`) always. The strike's own rules aim
# at it (echoing_strike/attack.py HOLD_LEADER). False: the rebuff retreat whatever is near.
KILL_FIRST = True
KILL_RATE = 8800.0  # points a second the strike takes off one foe in reach (the sim's Echoing Strike, 2026-10-22)
# CAST_REACH (2026-10-22, the coordinator from the sim's round 4: "the general cast-in-place check against a one-shot
# melee unit that can arrive within the cast time"; the Fane: one blow of 2056 at 1896 most life as Battle Orders ran
# out; the sim's pursuit-mode fane-death-24, seed 12: the swap, Battle Orders and the swap back at 7.58-8.58 s within
# 2.7 of the x5.75 unique Night Lord, its blow at 8.68): the Call to Arms is not swapped to (macros/cta.py
# `call_to_arms`, `orders_look` `safe`, `renew_orders`) while melee hostiles whose most blows together (combat/harm.py
# `most_blow`, at ZONE_LEVEL, the auras on them) reach the life can come within REACH_UNITS in CAST_SECONDS (the
# swap, the cast and the swap back: 1.0 s at 7.58-8.58): `Safety.cast_threat`, asked fresh at the cast. The rebuff
# retreat goes first (REBUFF_RETREAT: its landing, REBUFF_CLEAR from every hostile, is clear of this reach at a walk
# of 9 a second); a cast held CAST_HOLD_MOST s goes where it stands. False: nothing within ORDERS_CLEAR is enough.
CAST_REACH = True
CAST_SECONDS = 1.0
# BOUT_REACH (2026-10-22, the batch's pursuit-mode fane-death-24, seed 16, on-time looks: a Teleport landed at 6.82 s,
# the strike bout cast, marked and laid a sigil to 8.58 s with no look of the safety, the x5.75 unique Night Lord (3645
# a blow under Amplify Damage, over the 2943 most life) walked in, and the jump clearest chosen at 8.58 was still in
# the air at its blow, 9.16 s): the bout yields to the safety's next look (macros/hunt.py `fight`) when melee blows
# that together take the life can come within REACH_UNITS in REACH_SECONDS: the place REACH_BAR bars holding at.
# False: the bout yields by its own rules alone, as before.
BOUT_REACH = True
BOUT_REACH_EVERY = 0.25  # seconds after the safety's last look before the bout yields to another (macros/hunt.py)
# DOLL_ESCAPES (2026-10-22, the coordinator: "Confirm that the strike position keeps outside the death-blast radius ...
# for every doll it kills"; the sim's take scan: the only blows over 2000 in 2443 takes were Stygian Doll death blasts,
# 2603 and 2509): danger-durance-1956, 20 plays with every fix on: 4 of 108 doll deaths came within 4.5 units, 2.8-3.0,
# one blast each, every one the same way: a retreat (pursuit.py KEEPING, at 1.65 s) jumped from 15.6 units off a live
# Stygian Doll walking in to 6.6 off it, and it ran in and died on arrival at 2.84 s. True: with DOLL_LAND off (the
# player's, 2026-10-21 14:50), an escape's jump (a retreat, a dodge) landing within `dolls.land_units` of a live doll,
# where it stands or where its run-in has it at the landing, is barred when another escape lands clear of every doll
# and is not vetoed (`doll_landing`, `doll_escapes`: the escape logic as before wins otherwise). False: escapes land
# whatever dolls are near, as before.
DOLL_ESCAPES = True
# RETURN_GATE (2026-10-22, the coordinator, from the boss-ledger findings' open item "come back only when the safety
# gate allows", rca/2026-10-22/boss-ledger-findings.md; the player: recoveries "yes, should try", "we must not die",
# "we shouldn't get to the no hp potions and just 2 rejuv potions"): back through the portal for a boss after a beset
# recovery's town visit (macros/running/recovery.py BOSS_RECOVERY, asked at macros/tzloop.py `perform`'s portal
# return) only with life RETURN_LIFE of its most or more, RETURN_HEALING healing and RETURN_REJUVENATIONS rejuvenation
# potions on a read belt (short after the visit: it did not restock), and no veto on the act the last danger pricing
# chose (`Safety.decision`). Refused, the loop stops in town, naming the bosses (`return_refused`). Battle Orders is not
# asked here (no skill is cast in town): it is cast on the arrival before any fight when due or its age is not known
# (macros/cta.py ARRIVAL_LEFT; running/legs.py `orders_on_arrival`), and an arrival beset before the cast is the danger
# pricing's and the retreats' (cta.py REBUFF). False: back whatever.
RETURN_GATE = True
RETURN_LIFE = 0.9
RETURN_HEALING = 4
RETURN_REJUVENATIONS = 2
# REACH_BAR: fane-death-20, seed 19 (fane-death-sim-findings.md §7): three Teleports at 5.55-9.41 s landed 3.6 from the
# unique Night Lord, 14.8 from the Might unique; then 524 + 2058 came 0.12 s apart from 77% life, Battle Orders up.
# Nothing reacts between such blows. True: a move whose end (a walk's middle too) lies within REACH_UNITS (and what they
# walk in REACH_SECONDS) of melee hostiles whose most blows together (combat/harm.py `most_blow`: the auras on them and
# the resistances in) reach the life is barred as lethal, and so is holding where the character stands. False: the
# rollouts' veto alone.
REACH_BAR = True
# REJUV_REACTS (2026-10-22, the coordinator from the sim's round 4: the capped t5 Bramble Hulk Herald, 60 s, died in
# 18 of 20 plays with the fixes off and 6 of 20 on, and the all-but-one ablation named AURA_FORECAST alone): in an
# aura-raised fight (a hostile's `Hostile.raised` over 1) with a rejuvenation on the belt, the short rollouts' lethal
# veto (combat/harm.py `veto`, SafetySettings.veto_share) is not asked. A blow that cannot one-shot from the life as it
# is, with a rejuvenation in hand, is no veto: what takes the life only over several blows is answered by the drink
# (combat/survival.py EMERGENCY_REJUVENATION), and blows that together take it within REACH_SECONDS stay barred
# (REACH_BAR). Seed 3 of the Hulks: one Hold vetoed at 16 s as "lethal exposure in the short rollouts" (life 1783,
# worst 1010) moved the character 15 units off, the pack lost it and stood 30 off, and the run idled from 37 s, the
# Herald alive. Needs AURA_FORECAST and REACH_BAR. False: the veto as before. Off (2026-10-22, measured): the Hulk
# Herald stayed at 7 of 20 dead and fane-death-24's lowest life fell to 11% (coordinator: keep it off).
REJUV_REACTS = False
# RAISED_KEEP (2026-10-22, the coordinator from the sim's round 4: "a raised-fight retreat that keeps the nearest
# hostile in strike reach"): the capped t5 Bramble Hulk Herald with AURA_FORECAST on, seed 6 at 12.04 s: holding at
# full life (1783) priced 885 against a budget of 624, so the safety retreated; a retreat fit the budget (514), so
# `retreats` never ran, no retreat kept a hostile in strike reach (`keeper`), and the chosen one landed 22-26 off with
# the strike's reach 22: the pack lost the character and the Herald lived. True: in an aura-raised fight (a hostile's
# `Hostile.raised` over 1) where no act but a retreat fits the life, the retreats that keep `keeper`'s hostile in
# reach are priced too, and with the harm spread `keeper` names the one that brings the most of it (no KEEP_SHARE);
# the arbiter takes such a retreat first when it fits the budget (macros/pursuit.py KEEPING). False: as before.
RAISED_KEEP = True
# MOVED_ACTIVE (2026-10-22, the sim's pursuit-mode replay of fane-death-20, drawn, seed 5: dead at 19.72 s from 87%
# life, one blow of 3645 from the tier 2 unique of the Might pack, raised x5.75): it ran in from 20 to 2.7 units in
# 1.1 s while the look read it in mode 1 (neutral), so `Hostile.active` was False, and with no clear line from it the
# harm model priced it at nothing (combat/harm.py `hostile_exposure`): the pursuit's Teleport at 18.36 s and the hold
# at 18.77 s were priced 0, and the strike bout ran 0.7 s. The arena keeps a take's mode on a mob that walks; the
# client can show a stale mode to a late read too. True: a hostile whose place moved MOVED_UNITS or more between two
# looks is active for MOVED_SECONDS, whatever its mode. False: active by its mode alone, as before.
MOVED_ACTIVE = True
# ZONE_LEVEL (2026-10-22, the coordinator from the sim's pursuit-mode Fane deaths: four single blows of 2648-3592 from
# the x5.75 unique Night Lord at 2.7 units, from 81-87% life): the look's hostiles carried no level, so the harm model
# (combat/harm.py `kind_of`, combat/sim/monsters.py `Traits.of`) priced each at its monstats row's Level(H), the
# type's base (the client's stat 12 says the same, combat/mechanics/life.py), not the level it fights at. The Night
# Lord's table most came to 300 physical (`most_blow` 1727 at x5.75, under the 2943 life: REACH_BAR, CAST_REACH and
# KILL_FIRST saw no one-shot). The Fane take's blows match level 96 (death-findings.md Q1: 436 seen, level 96's most
# 434). True: every hostile of a look is priced at the level its foes are given life at (combat/mechanics/life.py
# `monster_level`: on a terrorized level the Terror Zone's, the character's level + `boost_level` 2 within
# `bound_incl_min` 70..`bound_incl_max` 96, never under the area's own, from the game's desecratedzones.json rotw hell
# defaults), else the area's own Hell level (combat/data/tables.json `areas`, levels.txt MonLvlEx(H)). The config holds
# no level by rank. False: the type's base level, as before.
ZONE_LEVEL = True
# LOOP_IGNORES_IDLE (2026-10-22, the player on game cyberg64, Lower Kurast, 18:09:26-18:10:35: "it was 1 elite pack,
# that weren't attacking us in non TZ level"; the standing ruling of 2026-10-16 for the KP_6 loop, "don't fight what
# isn't attacking"; rca/2026-10-22/lk-dance-findings.md): the Hell Buzzard champion pack (Extra Fast, Mana Burn,
# Spectral Hit) stood in mode 1 (neutral) in 82% of the take's frames, life 2930 of 2930, and held the loop 18 off its
# chests. True: on the loop's rushed run (`Facts.rush`) on a level not terrorized (combat/mechanics/life.py
# `terrorized`), with no life lost over the pressure window and the mana safe (manaburn.py DRAIN_GATE's `mana_safe`),
# a hostile is kept at range (manaburn.py `burners`) only while it strikes (game/layout.py STRIKING_MODES) within its
# keep range; the moment anything hurts or burns, every one is kept as before. False: kept by `burners` alone.
LOOP_IGNORES_IDLE = True
MOVED_UNITS = 1.0
MOVED_SECONDS = 1.0
# OBSERVED_SPEED (2026-10-22, the coordinator from the sim's diagnosis of fane-death-24, drawn, seed 4, pursuit: the
# x5.75 unique ran 12.3 units in 0.76 s, 15.0 -> 2.7 off, while the looks priced its walk at the table's 8.8 a second:
# the hold at 18.08-18.32 s 10.5-15 off carried none of its blow, and one of 3223 killed at full life; the arena runs
# it ~2x the game's, but Extra Fast uniques run so live): a hostile's walk in the pricing (combat/harm.py
# `Hostile.speed`: the rollouts, `most_blow`, REACH_BAR, CAST_REACH, BOUT_REACH, KILL_FIRST) is the larger of its
# table walk and the speed it was seen to move at over the last SPEED_LEAST-SPEED_SECONDS (`Safety.closing`).
# False: the table walk.
OBSERVED_SPEED = True
SPEED_LEAST = 0.25
SPEED_SECONDS = 1.0
REACH_UNITS = 4.0  # a melee swing's reach and the body's (combat/sim/casters.py REACH with a margin)
REACH_SECONDS = 0.5  # the landing's dwell and the next look's decision: what a walker closes meanwhile
REACH_SAID = 'within reach of blows that together take the life'
# FIGHT_CAST_OWN (2026-10-24, the coordinator's LONG_FIGHT of 10:58:54-10:59:33, take 20261024T075622Z-106: a tier 5
# Pit Lord Herald pack, 39 s, the life -421 in all, "fight casts held: blows of 3909 of 2943 can come within 1.0 s"
# x47 and no Death Mark or Sigil after the first; rca/2026-10-24/cast-hold-findings.md): macros/hunt.py
# FIGHT_CAST_REACH held the bout's casts by CAST_REACH's horizon, CAST_SECONDS, the Call to Arms' swap, cast and swap
# back (1.0 s), where a fight cast is as long as a strike (the take's casts, median: Death Mark 0.32 s, Engorge 0.34,
# the Sigil 0.52, Echoing Strike 0.40) and the bout strikes on by BOUT_REACH's REACH_SECONDS. At 10:58:55 the 1.0 s
# ring (4 + 11.7 a second) took in three minions 8.6-14.3 off (890 a blow each) and a Grizzly 8.1 off: 3909; in 0.5
# s, 1237. True: the fight casts' hold (`fight_cast_threat`) prices what can come within FIGHT_CAST_SECONDS, the bout's
# own horizon; the swap keeps CAST_SECONDS. False: CAST_SECONDS for both, as before.
FIGHT_CAST_OWN = False
FIGHT_CAST_SECONDS = REACH_SECONDS
# WALK_REACH (2026-10-22, the survival agent's round 6 from the pursuit-mode fane-death-20, drawn, seed 20, on-time
# looks, the `fast` pace: a walk of 4 to a firing spot posted at 20.79 s with the x5.75 unique Flesh Hunter 14.1 off
# (2575 a blow against 2527 life); the walk settled the strike's cast and waited out its click (macros/travel.py
# `step_walk`: settle up to 0.5 s, STEP_WALK_SECONDS 0.7) and gave the next look at 21.92 s, 1.1 s blind, with the
# unique 2.1 off and the blow at 21.96): REACH_BAR's place bar on a walk's end and middle counts what can come within
# REACH_UNITS in WALK_REACH_SECONDS, the walk's time with no look, not REACH_SECONDS. A jump lands in its own time and
# keeps REACH_SECONDS. With FIGHT_CAST_REACH, 320 pursuit plays: 9 deaths -> 0; the t5 Hulk Herald 16 of 20 dead (13
# with this off), 0 deaths. False: REACH_SECONDS for walks too.
WALK_REACH = True
WALK_REACH_SECONDS = 1.1


def aura_raise(skill: int, level: int) -> tuple[float, float]:
    """(+% physical damage, range in units) of a damage aura at `level` (AURA_DAMAGE); (0, 0) for another aura."""
    found = AURA_DAMAGE.get(skill)
    if found is None:
        return 0.0, 0.0
    base, per, reach, more = found
    return base + per * (level - 1), reach + more * (level - 1)


def auras_of(states: bytes | None) -> tuple[int, ...]:
    """The auras (skill ids) an Aura Enchanted monster's state words show (AURA_STATES); () unread or none shown."""
    if not states:
        return ()
    found = []
    for state, skill in AURA_STATES.items():
        word, bit = divmod(state, 32)
        if len(states) >= word * 4 + 4 and int.from_bytes(states[word * 4 : word * 4 + 4], 'little') >> bit & 1:
            found.append(skill)
    return tuple(sorted(found))


def raised(at: Point, holders: Sequence[tuple[Point, tuple[int, ...]]]) -> float:
    """The factor on the physical points of a hostile at `at` from the auras of `holders` (place, auras) at
    AURA_LEVELS, the holder's own included: each damage aura once, their +% added."""
    best: dict[int, float] = {}
    for place, auras in holders:
        for skill in auras:
            percent, reach = aura_raise(skill, AURA_LEVELS.get(skill, 1))
            if percent and math.dist(at, place) <= reach:
                best[skill] = max(best.get(skill, 0.0), percent)
    return 1.0 + sum(best.values()) / 100


# READ_THROWS (combat/bolts.py): with nothing safe, the retreats leave the read throwers' reach too (`out_of_throws`):
# CLEAR_RINGS end 14-22 from the character, inside the 30 of a pack of Slingers 20 off, so every way out of the canyon's
# javelins was priced in their lines and the least lethal act was the fight (2026-10-23, the arena's canyon-death-1452)
THROWS_CLEAR = 3.0  # units beyond SHOT_REACH from the nearest read thrower an escape lands at
THROWS_RINGS = (22.0, 30.0, 38.0)  # units from the character the escapes are looked for at
THROWS_ASKED = 2


def out_of_throws(here: Point, look: Look, footed: Callable[[Point], bool] | None = None) -> list[Point]:
    """THROWS_ASKED places on THROWS_RINGS round `here` out of the reach of every hostile whose throws the look read
    (`Hostile.throws`, SHOT_REACH + THROWS_CLEAR), the nearest to the character first, each passing `footed`. Empty with
    none read or none out of reach."""
    throwers = [h.at for h in look.hostiles if h.throws > 0]
    if not throwers:
        return []
    found: list[Point] = []
    for reach in THROWS_RINGS:
        ring = [
            (
                here[0] + reach * math.cos(k * math.tau / CLEAR_TURNS),
                here[1] + reach * math.sin(k * math.tau / CLEAR_TURNS),
            )
            for k in range(CLEAR_TURNS)
        ]
        scored = sorted(((min(math.dist(point, at) for at in throwers), point) for point in ring), reverse=True)
        for gap, point in scored:
            if gap < SHOT_REACH + THROWS_CLEAR or len(found) >= THROWS_ASKED:
                break
            if (footed is None or footed(point)) and all(math.dist(point, other) >= ESCAPE_SAME for other in found):
                found.append(point)
        if len(found) >= THROWS_ASKED:
            break
    return found


def clearest(
    here: Point,
    hostiles: Sequence[Point],
    footed: Callable[[Point], bool] | None = None,
    *,
    rings: Sequence[float] = CLEAR_RINGS,
    asked: int = CLEAR_ASKED,
) -> list[Point]:
    """`asked` places on `rings` round `here`, the farthest from every one of `hostiles` first, each farther from them
    than `here` is (CLEAR_ESCAPES); with `footed` (CLEAR_FOOTING) only places it passes. Empty with no hostile about."""
    if not hostiles:
        return []
    now = min(math.dist(here, at) for at in hostiles)
    ring = [
        (here[0] + reach * math.cos(k * math.tau / CLEAR_TURNS), here[1] + reach * math.sin(k * math.tau / CLEAR_TURNS))
        for reach in rings
        for k in range(CLEAR_TURNS)
    ]
    if footed is not None:
        ring = [point for point in ring if footed(point)]
    scored = sorted(((min(math.dist(point, at) for at in hostiles), point) for point in ring), reverse=True)
    found: list[Point] = []
    for gap, point in scored:
        if gap <= now or len(found) >= asked:
            break
        if all(math.dist(point, other) >= ESCAPE_SAME for other in found):
            found.append(point)
    return found


def idle_ignored(facts: Facts, look: Look, felt: Pressure, mana_safe: bool) -> bool:
    """Whether the keep range takes only the striking hostiles (LOOP_IGNORES_IDLE): the loop's rushed run, a level
    not terrorized, no life lost over the pressure window, the mana safe."""
    if not LOOP_IGNORES_IDLE or not facts.rush or felt.lost > 0.0 or not mana_safe:
        return False
    return facts.area is not None and not terrorized(facts.area, look.hostiles)


def priced_level(area: int, hostile: Sequence[Monster]) -> int | None:
    """The monster level a look's hostiles are priced at (ZONE_LEVEL): the Terror Zone's on a terrorized level, else
    the area's own; None (the type's base) with the switch off or the area not known."""
    if not ZONE_LEVEL:
        return None
    return monster_level(area, hostile) or area_level(area)


def kill_first(p: Pricing, left: float | None) -> str | None:
    """Why the rebuff retreat waits for a kill (KILL_FIRST): a doll Herald in the strike's reach, or a hostile in it
    whose most blow reaches the life and whose life to come takes under its walk to the character (and under `left`,
    Battle Orders' seconds left when known) at KILL_RATE. None: no such hostile."""
    if not KILL_FIRST:
        return None
    for m in p.look.hostiles:
        foe = p.seen.foes.get(m.unit)
        away = math.dist(p.here, m.at)
        if foe is None or away > p.attack.reach:
            continue
        if dolls.herald_doll(m):
            return f'a doll Herald {away:.0f} off: killed first'
        blow, speed = most_blow(m, p.look.battle)
        if shoots(m.txt) or blow < p.look.life:
            continue
        kill = foe.left * rank_share(foe.elite) / KILL_RATE
        reach = max(0.0, away - REACH_UNITS) / max(speed, 0.1)
        if kill < reach and (left is None or kill < left):
            return f'{m.txt} {away:.0f} off (a blow of {blow:.0f}) killed in {kill:.1f} s, here in {reach:.1f}: first'
    return None


def cast_reach(
    hostiles: Sequence[Hostile],
    here: Point,
    protection: Protection,
    life: float,
    *,
    bout: bool = False,
    seconds: float | None = None,
) -> str | None:
    """Why Battle Orders is not cast where the character stands (CAST_REACH, in CAST_SECONDS), or the strike bout
    yields (`bout`: BOUT_REACH, in REACH_SECONDS): the most blows together of the melee `hostiles` that can come within
    REACH_UNITS of `here` in that time reach `life`. None: the cast, or the bout, may go on here."""
    if not (BOUT_REACH if bout else CAST_REACH):
        return None
    seconds = seconds if seconds is not None else REACH_SECONDS if bout else CAST_SECONDS
    total, nearest = 0.0, math.inf
    for m in hostiles:
        if shoots(m.txt):
            continue
        blow, speed = most_blow(m, protection)
        away = math.dist(here, m.at)
        if blow and away <= REACH_UNITS + speed * seconds:
            total += blow
            nearest = min(nearest, away)
    if total < life:
        return None
    return f'blows of {total:.0f} of {life:.0f} can come within {seconds:.1f} s ({nearest:.0f} off)'


def keeper(look: Look, seen: Observation, priced: Harm, spread: bool = False) -> int | None:
    """The strikable hostile whose kill ends KEEP_SHARE or more of `priced`, counting what is bound to it (Baal's
    clone goes with him); None when the harm is spread, unless `spread` (RAISED_KEEP): then the one that ends the
    most."""
    total = sum(points for _, points in priced.by)
    if total <= 0:
        return None
    ends = dict(priced.by)
    for unit, masters in threats.bound({m.unit: m.txt for m in look.hostiles}).items():
        for master in masters:
            ends[master] = ends.get(master, 0.0) + dict(priced.by).get(unit, 0.0)
        ends.pop(unit, None)
    found = max((unit for unit in ends if unit in seen.foes), key=lambda unit: (ends[unit], -unit), default=None)
    return found if found is not None and (spread or ends[found] >= KEEP_SHARE * total) else None


def raised_fight(look: Look) -> bool:
    """An aura-raised fight: a hostile of the look with `Hostile.raised` over 1 (AURA_FORECAST)."""
    return any(m.raised > 1.0 for m in look.hostiles)


def keeping(here: Point, at: Point, reach: float) -> list[Point]:
    """KEEP_MOST places on the ring KEEP_MARGIN inside `reach` of `at` (`keeper`'s hostile), nearest `here` first."""
    radius = max(reach - KEEP_MARGIN, 1.0)
    bearing = math.atan2(here[1] - at[1], here[0] - at[0])
    ring = [(at[0] + radius * math.cos(bearing + t), at[1] + radius * math.sin(bearing + t)) for t in KEEP_TURNS]
    return sorted(ring, key=lambda point: math.dist(here, point))[:KEEP_MOST]


def shot_kinds(txt: int) -> frozenset[int]:
    """The bolt classes of an unread shooter type the look reads (combat/harm.py BOLTS_IN_FLIGHT, combat/bolts.py);
    empty while the switch is off or the type shoots none."""
    return bolts.classes_of(txt) if harm_module.BOLTS_IN_FLIGHT and threats.of(txt) is None else frozenset()


def in_flight(
    hostile: Sequence, flights: Flights | None, read: Sequence[tuple[int, int, float, float]] | None = None
) -> tuple[tuple[int, Point, float, int], ...]:
    """The missiles the read models of `hostile` ask for, as (owner, place, heading, class). A missile flies straight
    from its owner, so the heading is owner -> missile (rca/2026-10-13/diablo.md). Empty when no such hostile is about
    or the read fails. `read`: missiles already read, in place of a read of its own."""
    owners = {m.unit_id: (m.x, m.y) for m in hostile if threats.of(m.txt_id) is not None or shot_kinds(m.txt_id)}
    if not owners or (flights is None and read is None):
        return ()
    kinds = threats.missiles({m.txt_id for m in hostile}) | frozenset(k for m in hostile for k in shot_kinds(m.txt_id))
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
    """A look's deadline and per-stage seconds (`laps`). No timer: never late, no laps."""

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
    """`facts` whose goal's way is asked at most once a look, grown until `until` (travel.py `planning`); the list
    holds that leg once asked."""
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
    """(life an act may cost, the belt's spendable life, kappa, the fight's dearness factor)."""
    spendable = stock_life(loot, settings.healing_points, settings.floor)
    allowance = budget(loot.life, loot.max_life, felt, settings, insisting=insisting, spendable=spendable)
    supply = on_belt(loot)
    # An unread belt is priced as an empty one: its cells may hide a drunk potion (the player, 2026-10-19)
    stock = Supply(supply[PotionType.HEALING], supply[PotionType.REJUVENATION]) if loot.belt_read else Supply(0, 0)
    kappa = life_price(stock, loot.max_life, settings)
    dear = life_factor(look, here, settings)
    kappa *= dear
    return allowance, spendable, kappa, dear


class Held(NamedTuple):
    """Holding here as priced (`Safety.hold`)."""

    harm: Harm  # to the next decision, with the losses and bar of the longer escape horizon
    ahead: Harm  # over that horizon
    seconds: float
    unstruck: float  # the strike gap (`Candidate.unstruck`)


TOWARD_UNITS = 2.0  # `Pricing.toward_fight`: a move ends this much nearer the nearest hostile to go toward it


def burns_close(here: Point, spot: Point, burning: Sequence[manaburn.Burner], reach: float) -> bool:
    """BURN_LANDING_MARGIN: whether a landing at `spot` ends nearer a burner than its keep range and manaburn.py
    HOP_CLEAR beyond it (no farther out than BURN_SHORT inside the strike's `reach`), and over manaburn.py
    INTRUDE_SLACK nearer it than `here`."""
    if not BURN_LANDING_MARGIN:
        return False
    for b in manaburn.triggers(burning):  # not the drain fight's plain drainers (drain_escape.py, 2026-10-23)
        edge = min(b.keep + manaburn.HOP_CLEAR, max(b.keep, reach - BURN_SHORT))
        gap = math.dist(spot, b.at)
        if gap < edge and gap < math.dist(here, b.at) - manaburn.INTRUDE_SLACK:
            return True
    return False


def lands_in_range(here: Point, spot: Point, hostiles: Sequence, demons: Sequence[Point], jumped: bool = False) -> bool:
    """PACK_RANGE_LANDING: whether a landing at `spot` is one a tier 4-5 Herald pack's hop would leave at once
    (combat/pack.py `breaks_range`, with the demons the draw sends; none by a jump with ALONG_ALL), from a `here` that
    is not, or no farther from the pack than `here` (manaburn.py INTRUDE_SLACK)."""
    if not PACK_RANGE_LANDING or herald_pack.breaks_range(spot, hostiles, demons, jumped) is None:
        return False
    if herald_pack.breaks_range(here, hostiles, demons) is None:
        return True
    pack = herald_pack.members(hostiles)
    nearest = min(math.dist(here, m.at) for m in pack)
    return min(math.dist(spot, m.at) for m in pack) < nearest + manaburn.INTRUDE_SLACK


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
    # `shown(spot)`: the window shows the spot where a Teleport may be aimed (`Safety.shown`); None: every spot
    shown: Callable[[Point], bool] | None = None
    duds: tuple[Point, ...] = ()  # Teleport spots that cast nothing (`Safety.remember`): barred
    # The last safety Teleport's (origin, landing) while BOUNCE_BACK bars a move back to the origin (`Safety.left`)
    left: tuple[Point, Point] | None = None
    # A read model's act under way is walked out of (`Safety.walked_round`): a Teleport but a retreat is barred (WALKED)
    walking: bool = False
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
    # Hostiles bound to a living summoner (Baal's clone): striking them is lost (baal-sim.md fix 2)
    lost: dict[int, tuple[int, ...]] = field(init=False)
    landing: list[float] = field(default_factory=list, init=False)  # `landed_here`, once a look
    # DOLL_LAND (combat/threats/dolls.py, F2): the asked move's bar lifted (`Safety.doll_wait` past dolls.PATIENCE)
    patient: bool = False
    # WAIT_LIFT: the keep ranges' bars lifted after a wait that changed nothing (`Safety.wait_since`)
    waited: bool = False
    # The candidates (by index) of escapes landing near a live doll with one within dolls.CLOSE_UNITS of the character:
    # barred only when an escape landing clear of the dolls is priced too (`doll_escapes`)
    soft: list[int] = field(default_factory=list, init=False)
    close: bool = field(init=False)  # a live doll within dolls.CLOSE_UNITS of the character
    # The character's mana (whole points; None: unread) and the hostiles that drain it (combat/threats/manaburn.py)
    mana: float | None = None
    burning: tuple[manaburn.Burner, ...] = ()
    # The demons idle by the character with the pack on it (combat/pack.py REAGGRO_BY_MARK): the keep range's hop and
    # a voluntary Teleport are barred, the mark sends them (builds/warlock/mark.py REAGGRO_PACK)
    reaggro: bool = False
    # The character's strikes are credited with the kills they forecast (FLOOR_NO_CREDIT: not with the life budget 0)
    credit: bool = True
    # The demons the draw sends (`Safety.sendable`), where they stand, while attacking: the pack's keep range is judged
    # with them (PACK_RANGE_LANDING); None while not attacking (no keep range then)
    demons: tuple[Point, ...] | None = None
    # RANGE_STALL_LIFT: PACK_RANGE_LANDING's bar lifted for the goal's moves after its stall (`Safety.range_stall`)
    range_lifted: bool = False
    # MARK_HOLDS_JUMPS / NO_SHORT_HOPS_T5 (combat/pack.py `jump_hold`): the look's hold on jumps; None: none
    jump_hold: herald_pack.JumpHold | None = None

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
        self.close = dolls.close(here, self.look.hostiles)

    @property
    def starved(self) -> bool:
        """Whether the mana pays for no strike (manaburn.MANA_FLOOR, STRIKE_MANA): holding kills nothing."""
        return manaburn.MANA_FLOOR and self.mana is not None and self.mana < manaburn.STRIKE_MANA

    def teleport_paid(self) -> bool:
        """Whether the mana pays for a Teleport (manaburn.TELEPORT_MANA; unread mana: it does)."""
        return not manaburn.MANA_FLOOR or self.mana is None or self.mana >= manaburn.TELEPORT_MANA

    def deaths_from(self, spot: Point, after: float) -> dict[int, float]:
        """What the build's strikes from `spot`, begun after `after` s, kill and when; nothing with attack off, nor
        with no mana for a strike (`starved`)."""
        if not self.facts.attacking or self.starved or not self.credit:
            return {}
        return falls(self.seen, self.attack, self.field_, spot, after, after + FALL_HORIZON)

    def clear_time(self) -> float:
        """Seconds holding here takes to clear what is in reach (0.36..10): the forecast's, else life left / pace."""
        seen, killed = self.seen, self.killed
        in_reach = [u for u, f in seen.foes.items() if math.dist(self.here, f.at) <= self.attack.reach]
        if in_reach and all(u in killed for u in in_reach):
            # The forecast is quicker than the strikes: scaled by `strike_spread`'s median.
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
        """Holding here priced on `seen_`: (to the next decision, over the escape horizon)."""
        deaths = self.killed if deaths is None else deaths
        settings, here, dwell = self.settings, self.here, min(self.settings.hold_dwell, self.clear)
        held = harm_path(seen_, (*self.swap_path, (here, dwell, 'battle')), settings, deaths)
        # Vetoed over the longer horizon: short holds must not walk into a place every way out of is lethal.
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

    def toward_fight(self, spot: Point) -> bool:
        """Whether a move to `spot` ends over TOWARD_UNITS nearer a hostile than the character stands to its nearest."""
        found = [h.at for h in self.look.hostiles]
        if not found:
            return False
        gap = min(math.dist(self.here, at) for at in found)
        return min(math.dist(spot, at) for at in found) < gap - TOWARD_UNITS

    def burns_close(self, spot: Point) -> bool:
        """BURN_LANDING_MARGIN for a landing at `spot` from here (`burns_close`)."""
        return burns_close(self.here, spot, self.burning, self.attack.reach)

    def breaks_range(self, spot: Point, jumped: bool = False) -> bool:
        """PACK_RANGE_LANDING for a landing at `spot` from here (`lands_in_range`; `jumped`: by a jump, which takes
        the demons along with combat/pack.py ALONG_ALL); never while not attacking."""
        return self.demons is not None and lands_in_range(self.here, spot, self.look.hostiles, self.demons, jumped)

    @staticmethod
    def jump_kind(step: Step, *, retreat: bool, dodge: bool, why: str | None) -> str | None:
        """What kind of jump `step` is for the holds (combat/pack.py `held`, REAGGRO_BY_MARK): the keep range's hop
        (BACK_SAID), a retreat, or a voluntary move (no reason, no dodge); None for a walk and the other escapes (a
        threat's dodge, the mana leave, the rebuff, the doll bait), which no hold bars."""
        if step.skill is None:
            return None
        if why is not None and why.startswith(herald_pack.BACK_SAID):
            return herald_pack.KEEP
        if retreat:
            return herald_pack.RETREAT
        return herald_pack.PLACE if not dodge and not why else None

    def held_jump(self, step: Step, *, retreat: bool, dodge: bool, why: str | None) -> str | None:
        """Why the jump `step` is not made now (combat/pack.py `held`, MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5); None for
        a walk, an escape no hold bars, or with no hold."""
        kind = self.jump_kind(step, retreat=retreat, dodge=dodge, why=why)
        if kind is None or self.jump_hold is None:
            return None
        return herald_pack.held(self.jump_hold, step.spot, kind)

    def move_price(
        self,
        step: Step,
        *,
        retreat=False,
        firing=False,
        why: str | None = None,
        dodge=False,
        keeps=False,
        onward=False,
    ) -> tuple[tuple, float]:
        """A move to `step` priced and added to the candidates: its path and seconds."""
        look, settings, here, hands = self.look, self.settings, self.here, self.hands
        gap = math.dist(here, step.spot)
        jump = next((j for j in self.jumps if j.skill == step.skill), None)
        seconds = jump.takes(gap) if jump else (0.31 if step.skill == TELEPORT else 0.36 + gap / 20.0)
        # Teleport's set: the staff's, or battle where it is the character's own (Enigma: no swaps;
        # rca/2026-10-18/sluggish-engagement-findings.md)
        needs = self.teleport_hands if step.skill == TELEPORT else 'battle'
        swap = SWAP_SECONDS if needs != hands else 0.0
        seconds += swap + settings.move_overhead
        # A charged hop leaves quickly, a delayed jump or walk does not.
        dwell = settings.landing_dwell if step.skill is not None else 0.12
        path = []
        if swap:
            path.append((here, swap, hands))
        if step.skill is None:
            # The straight walk in three slices (the navigator checked footing and line).
            for fraction in (0.0, 0.5, 1.0):
                point = (
                    here[0] + (step.spot[0] - here[0]) * fraction,
                    here[1] + (step.spot[1] - here[1]) * fraction,
                )
                path.append((point, (seconds - swap) / 3, needs))
        else:
            path.append((here, max(0.12, seconds - swap), needs))
        path.append((step.spot, dwell, needs))
        # Strikes begin at the landing, after any swap back to the battle set.
        landed = self.deaths_from(step.spot, SWAP_SECONDS if needs != 'battle' else 0.0)
        arrival = sum(part for _, part, _ in path[:-1])
        struck = {u: t + arrival for u, t in landed.items()}
        damage = harm_path(look, tuple(path), settings, struck)
        future = harm(look, step.spot, settings.horizon, needs, settings, landed)
        damage = replace(damage, barred=damage.barred or veto(future, look.life, settings))
        reach: str | None = None  # the reach bar's, put on last with REACH_LIFT (pursuit.py)
        if REACH_BAR and not damage.barred:
            # Its end, and a walk's middle: a walk passes what stands by its way
            ends = (step.spot, *(((here[0] + step.spot[0]) / 2, (here[1] + step.spot[1]) / 2),) * (step.skill is None))
            within = WALK_REACH_SECONDS if WALK_REACH and step.skill is None else REACH_SECONDS
            near = max(self.reach_blows(spot, within) for spot in ends)
            if near >= look.life:
                reach = f'{REACH_SAID} ({near:.0f} of {look.life:.0f})'
                if not arbiter.REACH_LIFT:
                    damage = replace(damage, barred=reach)
        if needs == 'battle' and not self.battle_ready:
            damage = replace(damage, barred='battle weapon swap is unavailable')
        if step.skill == TELEPORT and any(math.dist(step.spot, dud) <= DUD_UNITS for dud in self.duds):
            damage = replace(damage, barred=DUD)
        if step.skill == TELEPORT and self.walking and not retreat:
            damage = replace(damage, barred=damage.barred or WALKED)
        if step.skill == TELEPORT and not self.teleport_paid():
            damage = replace(damage, barred=damage.barred or manaburn.NO_TELEPORT)
        if drain_escape.unpaid(step.skill, self.mana):  # Blade Warp's mana too (drain_escape.py MANA_ESCAPE)
            damage = replace(damage, barred=damage.barred or drain_escape.NO_MANA)
        kept = not (retreat or dodge or self.waited)  # a wait that changed nothing lifts the keep ranges (WAIT_LIFT)
        if kept and step.skill is None and herald_pack.walk_free(step.spot, here, look.hostiles, look.companions):
            kept = False  # the T5 pack's plan: the walk in behind the demons holding it (combat/engage.py ENGAGE_PLAN)
        if self.burning and kept and manaburn.intrudes(here, step.spot, self.burning) is not None:
            # A draining pack is fought from its keep range (manaburn.BURN_RANGE): no move deeper into it
            damage = replace(damage, barred=damage.barred or manaburn.LANDED)
        omens = herald_pack.omens(self.facts.now)
        if kept and manaburn.pack_landing(here, step.spot, look.hostiles, omens) is not None:
            # A tier 4-5 Herald's pack is fought from range (manaburn.PACK_LANDING): no move into its PACK_BACK
            damage = replace(damage, barred=damage.barred or manaburn.PACK_LANDED)
        if kept and self.burns_close(step.spot):
            # Nor to a burner's keep range's edge, where the next look's hop takes it out again (BURN_LANDING_MARGIN)
            damage = replace(damage, barred=damage.barred or manaburn.LANDED)
        if kept and not self.range_lifted and self.breaks_range(step.spot, step.skill is not None):
            # Nor where a Herald pack's hop would take it out at once (PACK_RANGE_LANDING), unless the stall lifted it
            # (RANGE_STALL_LIFT)
            damage = replace(damage, barred=damage.barred or PACK_RANGE_LANDED)
        if self.left is not None and math.dist(step.spot, self.left[0]) <= BOUNCE_NEAR:
            # Two safety moves that undo each other (BOUNCE_BACK)
            damage = replace(damage, barred=damage.barred or BOUNCED)
        if (
            manaburn.BURN_ENGAGE
            and kept
            and step.skill is not None
            and not why
            and self.burning
            and self.demons
            and not manaburn.clear_of(step.spot, self.burning)
            and manaburn.burn_held(self.demons, self.burning)
        ):
            # The demons on the burners: the jump in would bring them back and the keep range hop out again
            damage = replace(damage, barred=damage.barred or manaburn.ENGAGE_HELD)
        held = self.held_jump(step, retreat=retreat, dodge=dodge, why=why)
        if held is not None:
            # The demons on the mark or holding a tier 5 pack: the jump would bring them back (combat/pack.py
            # MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5)
            damage = replace(damage, barred=damage.barred or held)
        if self.reaggro and self.jump_kind(step, retreat=retreat, dodge=dodge, why=why) in REAGGRO_KINDS:
            # The demons re-aggro by the mark, not by a hop that brings the pack along (herald_pack.REAGGRO_BY_MARK)
            damage = replace(damage, barred=damage.barred or herald_pack.REAGGRO_SAID)
        damage = self.doll_landing(step, seconds - settings.move_overhead, damage, escape=retreat or dodge,
                                   asked=not (why or retreat or firing))  # fmt: skip
        duration = math.dist(step.spot, self.goal.place) / 20.0
        if firing and not why:
            # A firing stand: the clear time scaled by here's pace over the stand's (from its landing, as `camp`
            # chose it); the move's seconds lie inside it, not on top (rca/2026-10-14/run-1932-findings.md §4).
            there_worth, _ = taken(self.seen, self.attack, self.field_, step.spot, seconds, landed=True)
            duration += self.clear * self.landed_here() / max(there_worth, 1.0)
        else:
            duration += seconds
        if firing and why:
            # An escape's seconds are counted already; its pace from the landing.
            there_worth, _ = taken(self.seen, self.attack, self.field_, step.spot, 0.0)
            duration += self.clear * self.worth / max(there_worth, 1.0)
        step = PricedStep(step.spot, step.skill, step.camp, needs, seconds)
        act = Move(
            step, self.goal, why or ('retreat' if retreat else FIRING if firing else ''), dodge=dodge, onward=onward
        )
        unstruck = seconds + (SWAP_SECONDS if needs != 'battle' else 0.0)  # the strike needs the battle set
        clear = clearance(here, step.spot, [m.at for m in look.hostiles], step.skill is None)
        lift = False
        if reach is not None and arbiter.REACH_LIFT:
            # Barred by the reach bar alone and going away from every hostile: liftable when every act is vetoed
            lift = not damage.barred and self.away(step)
            damage = replace(damage, barred=damage.barred or reach)
        self.candidates.append(
            Candidate(act, duration, damage, retreat, unstruck, self.strikes_from(step.spot), keeps, clear, lift)
        )
        return tuple(path), duration

    def away(self, step: Step) -> bool:
        """Whether the end of a move to `step` (and a walk's middle) lies farther from every hostile than the character
        stands (pursuit.py REACH_LIFT)."""
        here, spot = self.here, step.spot
        ends = (spot, *(((here[0] + spot[0]) / 2, (here[1] + spot[1]) / 2),) * (step.skill is None))
        found = [m.at for m in self.look.hostiles]
        return bool(found) and all(math.dist(end, at) > math.dist(here, at) for end in ends for at in found)

    def doll_landing(self, step: Step, transit: float, damage: Harm, *, escape: bool, asked: bool) -> Harm:
        """DOLL_LAND (combat/threats/dolls.py, F2 of rca/2026-10-21/dolls-tz-findings.md): a jump landing within
        `dolls.land_units` of a live doll, where it stands or where its run-in has it after the hop's `transit` seconds,
        is barred (`dolls.LANDED`). Not with attack mode off (the player's own jump), not for the asked move once the
        dolls have held it dolls.PATIENCE seconds with nothing in reach (`patient`). An escape with a doll on the
        character is barred only if one landing clear is priced too (`soft`, `doll_escapes`)."""
        escaping = DOLL_ESCAPES and escape and not dolls.DOLL_LAND  # the escapes alone (DOLL_ESCAPES)
        if not (dolls.DOLL_LAND or escaping) or step.skill is None or not self.facts.attacking or damage.barred:
            return damage
        found = dolls.barring(self.here, step.spot, self.look.hostiles, transit)
        if found is None or (asked and self.patient):
            return damage
        if escape and (self.close or escaping):
            self.soft.append(len(self.candidates))  # the index `move_price` gives this candidate
            return damage
        return replace(damage, barred=f'{dolls.LANDED} ({found[0]:.1f} units, under {found[1]:.0f})')

    def doll_escapes(self) -> None:
        """The escapes landing near a live doll (`soft`) barred when another jump escape lands clear of every doll and
        is not vetoed; else they stand: the escape logic as before wins (DOLL_LAND)."""
        if not self.soft:
            return
        soft = set(self.soft)
        clear = any(
            index not in soft
            and isinstance(c.act, Move)
            and (c.retreat or c.act.dodge)
            and c.act.step.skill is not None
            and veto(c.harm, self.look.life, self.settings) is None
            for index, c in enumerate(self.candidates)
        )
        if not clear:
            return
        for index in soft:
            c = self.candidates[index]
            self.candidates[index] = replace(
                c, harm=replace(c.harm, barred=f'{dolls.LANDED} (an escape lands clear)'), lift=False
            )

    def short_of_dolls(self, step: Step) -> None:
        """A move toward the goal whose landing a live doll bars (DOLL_LAND): the place on its way nearest that landing
        that none bars, back toward the character by DOLL_STEP, priced as a safe approach; none: nothing more (the hold,
        the waits and the escapes stand)."""
        here, gap = self.here, math.dist(self.here, step.spot)
        away = gap - DOLL_STEP
        while away > 2 and not self.clock.late():
            point = (here[0] + (step.spot[0] - here[0]) * away / gap, here[1] + (step.spot[1] - here[1]) * away / gap)
            jump = next((j for j in self.jumps if j.skill == step.skill), None)
            transit = jump.takes(away) if jump else 0.31
            if dolls.barring(here, point, self.look.hostiles, transit) is None:
                shorter = self.leg(point)
                if isinstance(shorter, Step) and math.dist(here, shorter.spot) > 2:
                    self.move_price(shorter)
                    last = self.candidates[-1]
                    assert isinstance(last.act, Move)
                    self.candidates[-1] = replace(last, act=replace(last.act, reason='safe approach'))
                return
            away -= DOLL_STEP

    def burnt_out(self, path: tuple, seconds: float, priced: Harm) -> None:
        """When what lies on the ground (Diablo's fire wall, combat/threats `Lingering`) is part of the act's price:
        the act made after waiting for it to burn out (at its end and half that), and steps out of it
        (rca/2026-10-14/run-0305-findings.md §5.6)."""
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
        """The act asked for: a use, a move (with shorter approaches), or a running fight's advance."""
        facts = self.facts
        if isinstance(base, Operate):
            self.operate(base)
        elif isinstance(base, Move):
            self.approach(base)
        elif (
            isinstance(base, Hold)
            and not facts.there
            and not facts.settling
            and (fresh or (posted is not None and posted.runs))
            and (self.legs or not self.clock.late())  # late: the next look asks the way
        ):
            step = facts.way()
            if isinstance(step, Step):
                self.move_price(step)

    def operate(self, base: Operate) -> None:
        """A use: walk to the drop or object and work it for its dwell; no strike meanwhile, so no kills credited."""
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
        """A move toward the goal; over budget or vetoed, shorter stands on the same approach too (a long leg may end
        inside a pack)."""
        here = self.here
        path, seconds = self.move_price(base.step)
        moved = self.candidates[-1]  # the move's own price, not the waits and steps `burnt_out` adds after it
        self.burnt_out(path, seconds, moved.harm)
        if (moved.harm.barred or '').startswith(dolls.LANDED):
            self.short_of_dolls(base.step)
        if moved.harm.worst > self.allowance or veto(moved.harm, self.look.life, self.settings):
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
        """Camp's stand (stance `camp`) priced beside holding when nothing is safe, near a hostile with no line to it
        (I2), or holding takes over half the budget."""
        facts = self.facts
        lineless = facts.near and facts.attacking and not facts.in_reach
        if not self.clock.late() and (
            unsafe or lineless or (facts.in_reach and hold_harm.worst > self.allowance * 0.5)
        ):
            # Only where the window shows it, as `Hunter.better_stand`'s (a stand under the skill bar is never cast)
            found = camp(self.seen, self.attack, barred=self.barred, shown=self.shown, jumps=self.jumps)
            if found is not None:
                self.move_price(Step.to(found), firing=True)

    def reach_blows(self, spot: Point, seconds: float = REACH_SECONDS) -> float:
        """The most blows together of the melee hostiles that reach `spot` within `seconds` (REACH_BAR: REACH_SECONDS;
        WALK_REACH: a walk's WALK_REACH_SECONDS): each one's `most_blow` with the battle set's protection, of those
        within REACH_UNITS plus their walk."""
        key = ('reach', spot, seconds)
        known = self.look.memo.get(key)
        if known is not None:
            return known
        total = 0.0
        for m in self.look.hostiles:
            if shoots(m.txt):
                continue
            blow, speed = most_blow(m, self.look.battle)
            if blow and math.dist(spot, m.at) <= REACH_UNITS + speed * seconds:
                total += blow
        self.look.memo[key] = total
        return total

    def footed(self, spot: Point) -> bool:
        """Whether `spot` is footing the window shows (CLEAR_FOOTING): no wall within a unit of it, as the
        navigator's stride asks (macros/travel.py `stride_of`)."""
        if self.shown is not None and not self.shown(spot):
            return False
        barred = self.barred
        return barred is None or not any(barred((spot[0] + dx, spot[1] + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def retreat_to(self, point: Point, asked: list[Point], at: Point | None = None) -> None:
        """The navigator's legs toward `point` priced as retreats, not within ESCAPE_SAME of one `asked`. `at`: the
        `keeper` hostile the retreat must keep in reach and line."""
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
                    'onward': isinstance(c.act, Move) and c.act.onward,
                    'keeps': c.keeps,
                    'contributors': c.harm.by,
                    'stand_ins': c.harm.stand_ins,
                    'blocked_by': blockers(c.harm, allowance),
                }
                for c in self.candidates
            ],
        }


def chosen_veto(decision: dict) -> str | None:
    """The veto on the act the look of `decision` (`Safety.decision`) chose; None for none, or no look."""
    chosen, place = decision.get('chosen'), decision.get('chosen_place')
    for candidate in decision.get('candidates', ()):
        if candidate.get('act') == chosen and candidate.get('place') == place and candidate.get('veto'):
            return str(candidate['veto'])
    return None


def every_act_vetoed(decision: dict, since: float) -> bool:
    """Whether the look of `decision` (`Safety.decision`), made at `since` or after, found every act it priced vetoed
    (the hold too): standing, moving and jumping all priced lethal (macros/hunting/moves.py REJUV_VETOED)."""
    found = decision.get('candidates') or ()
    return decision.get('looked_at', -math.inf) >= since and bool(found) and all(c.get('veto') for c in found)


def retreat_chosen(decision: dict, since: float) -> bool:
    """Whether the look of `decision` (`Safety.decision`), made at `since` or after, chose a retreat: no progress act
    fitted the life budget or every one was vetoed (macros/hunting/moves.py REJUV_VETOED)."""
    if decision.get('looked_at', -math.inf) < since:
        return False
    chosen, place = decision.get('chosen'), decision.get('chosen_place')
    return any(
        c.get('retreat') and c.get('act') == chosen and c.get('place') == place
        for c in decision.get('candidates') or ()
    )


def return_refused(loot: Loot | None, decision: dict) -> str | None:
    """Why the character does not go back for a boss after a beset recovery's town visit (RETURN_GATE), None when it
    may: `loot` the life and belt as read now (None: unread), `decision` the last danger pricing (`Safety.decision`)."""
    if not RETURN_GATE:
        return None
    if loot is None or loot.max_life <= 0:
        return 'the life is not read'
    if loot.life < RETURN_LIFE * loot.max_life:
        return f'life {loot.life}/{loot.max_life}, under {RETURN_LIFE:.0%}'
    if not loot.belt_read:
        return 'the belt is not read'
    supply = on_belt(loot)
    healing, rejuvenations = supply[PotionType.HEALING], supply[PotionType.REJUVENATION]
    if healing < RETURN_HEALING or rejuvenations < RETURN_REJUVENATIONS:
        return (
            f'{healing} healing and {rejuvenations} rejuvenation potions on the belt, under {RETURN_HEALING} and '
            f'{RETURN_REJUVENATIONS}'
        )
    vetoed = chosen_veto(decision)
    if vetoed is not None:
        return f'the last danger pricing vetoed its act ({vetoed})'
    return None


# STAND_IN_EVIDENCE (2026-10-22, Sewers Level 3, 23:15:49-23:20:30, take 20261022T201417Z-49; rca/2026-10-22/
# walled-boss-findings.md §2; the player: "even if it was dangerous, what is estimated exp/hour if we're jumping around
# without kills?"): Radament, priced by the harm model's conservative stand-in for a boss with no read AI (harm.py
# `stood_in`: a shot of three times his table blow a second within its radius), kept every act toward him vetoed
# ("lethal exposure in the short rollouts", "no progress act fits the life budget"): 98 safe approaches and 96 retreats
# in 4.5 minutes, life 2943 of 2943 throughout, then two strikes from 21 units and he died in 13 s. The route's boss
# fight is no goal a budget gives up, so nothing ended it; the takes hold 145 s within his radius and 56 life lost.
# True: a stand-in hostile whose life has not fallen by STALL_DROP of its full in STALL_SECONDS (the fight with it
# stalled) is priced by the evidence, not the guess: the takes' seconds within its radius and life lost then
# (combat/stand_ins.py `prior`, its type's or the pool's) plus this fight's (`Evidence`), EVIDENCE_MARGIN times the
# life lost plus one table blow (`most_blow`) over those seconds, against the stand-in's own rate at the character
# (`Hostile.tempered`, combat/harm.py STAND_IN_TEMPER), never under EVIDENCE_FLOOR. Survival first: under
# EVIDENCE_SECONDS of evidence, or any life lost in the last EVIDENCE_HURT, it is whole, and so after a mana burn seen
# (its mana counted as lost). The one-blow bars (REACH_BAR, CAST_REACH) are not touched. False: the stand-in whole,
# as before
# On 2026-10-23: arena Radament 24/24 killed, 0 deaths; danger fights + Fane cuts unchanged (walled-boss-findings.md §2)
STAND_IN_EVIDENCE = True
EVIDENCE_SECONDS = 8.0
EVIDENCE_HURT = 3.0
EVIDENCE_MARGIN = 3.0
EVIDENCE_FLOOR = 0.1
EVIDENCE_STEP = 0.5  # the most seconds one look counts (a gap between looks is no exposure seen)
STALL_SECONDS = 10.0
STALL_DROP = 0.1  # of its full life

# READ_THROWS (combat/bolts.py): a type's throws at the character priced at the rate its last THROWS_HOLD seconds of
# looks read (`Safety.throws_read`): one look away from the lanes reads none at the new place, the pack throws on
THROWS_HOLD = 4.0
THROWS_SAID = 2.0  # a type's rate said again when it moved by this ratio
THROWS_PLACES = 2.0  # seconds of the character's places a bolt in flight may have been let go at (`throws_read`)
# STAND_NOT_RETREAT (pursuit.py): the bars a wait that changed nothing lifts (WAIT_LIFT, `Pricing.waited`); not a
# draining pack's (manaburn.py LANDED): the mana it burns is not priced as harm, so its stand's harm 0 says nothing
# (the arena's manaburn-death-1857 seed 15: a stand at its keep range, the pack on, lowest life 70% -> 29%)
KEEP_BARS = (PACK_RANGE_LANDED, manaburn.PACK_LANDED)


def kept_out(p: Pricing) -> bool:
    """STAND_NOT_RETREAT: no draining pack kept at range (`burning`), and a progress move fits the life budget and is
    barred by a keep range alone (KEEP_BARS), which a wait lifts; a stand does not end the life budget's refusal (the
    arena's radament-sewers, Radament holding his ground behind the sewer's walls: his kill at 23 s with the
    retreats, at 43 s with stands, seed 1)."""
    return not p.burning and any(
        isinstance(c.act, Move)
        and not c.retreat
        and not c.act.dodge
        and c.harm.barred in KEEP_BARS
        and c.harm.worst <= p.allowance
        for c in p.candidates
    )


@dataclass(frozen=True)
class Evidence:
    """What the fight has shown of one stand-in hostile (STAND_IN_EVIDENCE): seconds the character stood within its
    radius, and the life lost meanwhile (from any hostile: the bound is conservative)."""

    exposed: float = 0.0
    lost: float = 0.0


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
    # The look's clock (perf_counter in the game); None: caps alone bound it (the arena, deterministic per seed).
    timer: Callable[[], float] | None = None
    modes: dict[int, tuple[int, float]] = field(default_factory=dict)  # unit -> (mode, first seen in it)
    # unit -> (its place at the last look, when it was last seen moved): MOVED_ACTIVE
    moved: dict[int, tuple[Point, float]] = field(default_factory=dict)
    # unit -> its places read over the last SPEED_SECONDS: (clock, place), oldest first; `speeds`: the last look's
    # speeds from them (OBSERVED_SPEED)
    trails: dict[int, list[tuple[float, Point]]] = field(default_factory=dict)
    speeds: dict[int, float] = field(default_factory=dict)
    # The build's draw and the companions it would send: (index into the look's companions, class).
    draw: Draw | None = None
    sendable: tuple[tuple[int, int], ...] = ()
    # The draw's worth per hostile at the last fight look (`weigh`) and its clock; None: not weighed.
    draws: dict[int, DrawPrice] | None = None
    drawn_at: float = -math.inf
    # Casters of what lingers (unit -> model, place, clock last seen); read for the model's `lasts` seconds after.
    casters: dict[int, tuple[threats.Lingering, Point, float]] = field(default_factory=dict)
    lying_since: dict[tuple[int, int, int], float] = field(default_factory=dict)  # (class, 2x, 2y) -> first read
    # Unit -> (its mode, the place a step across its act was chosen from): not offered again in that mode (Diablo's
    # stream re-aims, so back is no way out: rca/2026-10-14/run-0305-findings.md §5.2).
    stepped: dict[int, tuple[tuple[int, float] | None, Point]] = field(default_factory=dict)
    stand: tuple[Step, float] | None = None  # the fight's last offered stand (`offer`) and its clock
    over_said: float = -math.inf
    over_since: int = 0
    aspect: float = DEFAULT_ASPECT  # the game window's width / height (`shown`)
    # The Teleport pressed at the last acts made: (spot, where the character stood, presses in a row, the first's clock)
    hops: tuple[Point, Point, int, float] | None = None
    duds: dict[Point, float] = field(default_factory=dict)  # Teleport spots that cast nothing -> barred until
    left_at: tuple[Point, Point, float] | None = None  # the last safety Teleport: (origin, spot, clock) (BOUNCE_BACK)
    walked_said: tuple | None = None  # the acts under way the hops left out (WALKED) were last said for
    # Unit -> (its mode, the way round it a walk goes: +1 / -1): a walk round its act under way (WALK_ROUND)
    rounds: dict[int, tuple[tuple[int, float] | None, int]] = field(default_factory=dict)
    # Whether the build's draw lands now (DRAW_CASTABLE): set by the hunt before each price (macros/buffs.py
    # `Buffs.lands`)
    draw_lands: bool = True
    # Hops out of a tier 4-5 Herald's pack made, by the pack (combat/pack.py `key_of`; PACK_HOPS at most)
    pack_hops: dict[int, int] = field(default_factory=dict)
    # DOLL_LAND (combat/threats/dolls.py): (the goal, since when) its asked move has been barred by dolls with nothing
    # in reach (`dolls_waited`); past dolls.PATIENCE the bar is lifted for it. And the goal its bars were last said for.
    doll_wait: tuple[tuple, float] | None = None
    dolls_said: tuple | None = None
    # WAIT_LIFT: (the goal, since when the character stood, the hostiles' places then, the life then) of a stand with
    # nothing in reach; kept while nothing changes, past WAIT_HORIZON the keep ranges' bars are lifted (`waited`)
    wait_since: tuple[tuple, float, dict[int, Point], float] | None = None
    wait_said: float | None = None  # the wait whose lift was said
    # STAND_NOT_RETREAT (pursuit.py): (the goal, since when the character first stood for it in place of a retreat
    # that saved nothing); kept until the goal changes or something comes in reach, past STAND_SECONDS as before
    stood: tuple[tuple, float] | None = None
    # RANGE_STALL_LIFT: (the goal, since when its progress has been barred by PACK_RANGE_LANDING, the life then), kept
    # while the looks are retreats and safe approaches with nothing changed; and the stall whose lift was said
    range_stall: tuple[tuple, float, float] | None = None
    range_said: float | None = None
    bait_hops: dict[int, int] = field(default_factory=dict)  # moves in to a held doll pack, by the pack (BAIT_HOPS)
    # Hops out of a draining pack (combat/threats/manaburn.py BURN_HOPS), by the pack: (hops, the last one's spot, where
    # the character stood when it was chosen): a hop chosen again before it lands is not counted again
    burn_hops: dict[int, tuple[int, Point, Point]] = field(default_factory=dict)
    burn_mark: dict[int, float] = field(
        default_factory=dict
    )  # manaburn.BURN_ENGAGE: the mark's key each pack's hop spent
    # manaburn.BURN_STALL_COMMIT: (the pack's key, since when its keep range has held the fight off, the life then, the
    # last look its bar held, the members' life then), the pack fought in now (None: none), and the packs a burn or a
    # hurt took that from for good
    burn_stall: tuple[int, float, float, float, dict[int, float]] | None = None
    burn_commit: int | None = None
    burn_spoiled: set[int] = field(default_factory=set)
    # The character's mana at the recent looks, (clock, points), for the mana floor (manaburn.MANA_FLOOR)
    mana_seen: deque = field(default_factory=lambda: deque(maxlen=32))
    mana_safe: bool = False  # the mana over manaburn.MANA_SAFE with no burn seen at the last look (DRAIN_GATE)
    # The mana's state at the last look (manaburn.ManaLook; None: unread, or no look priced) for the Rejuvenation for
    # mana (manaburn.MANA_REJUVENATION, macros/hunting/moves.py `pursue`), and the packs one went to (unit -> clock)
    mana_look: manaburn.ManaLook | None = None
    mana_drunk: dict[int, float] = field(default_factory=dict)
    # The mana's want at the last look a Rejuvenation may answer (manaburn.LEAVE_BURNERS_ONLY `short_of`)
    mana_short: str | None = None
    # combat/threats/drain_escape.py MANA_ESCAPE (2026-10-23): the last burn seen, why its leave is first at this look,
    # and the Teleport out a Rejuvenation for the mana makes at once (`RefillEscape`)
    burn_watch: drain_escape.BurnWatch = field(default_factory=drain_escape.BurnWatch)
    burn_leaving: str | None = None
    refill: drain_escape.RefillEscape | None = None
    # Battle Orders at the look (macros/cta.py `orders_look`: ORDERS_PREDICT, REBUFF_RETREAT), set by the hunt before
    # each price; None: not tracked (no Call to Arms, or not read)
    orders: OrdersLook | None = None
    # A rejuvenation drunk just now (DANGER_LOOK), set by the hunt before each price
    alarmed: bool = False
    # The last look's real threat for the jump hold (`real_threat`; combat/pack.py MARK_HOLDS_JUMPS): the fight's
    # better place asks it (macros/hunting/moves.py `better_stand`)
    hold_exempt: str | None = None
    idle_since: float | None = None  # since when the demons idle by the character with the pack on it (REAGGRO_BY_MARK)
    rebuffed_at: float = -math.inf  # clock of the last rebuff retreat chosen (macros/cta.py REBUFF_GRACE)
    rebuffing: bool = False  # this look: Battle Orders due, not safe to cast, a rebuff retreat asked (`rebuff_back`)
    killing_first: str | None = None  # this look: why the rebuff retreat waits for a kill (KILL_FIRST)
    rebuff_hops: tuple[int, Point] = (0, (math.inf, math.inf))  # rebuff retreats chosen while due, and from where
    unvetoed: tuple[SafetySettings, SafetySettings] | None = None  # (settings, its copy with no veto): `no_veto`
    rebuff_landed: float = -math.inf  # clock the last rebuff retreat landed (`landed`; mark.py REMARK_AFTER_REBUFF)
    # An Aura Enchanted hostile's state words, for its aura (AURA_FORECAST), set by the hunt; None: none read
    states_of: Callable[[Monster], bytes | None] | None = None
    auras_read: dict[int, tuple[int, ...]] = field(default_factory=dict)  # unit -> its auras (AURA_STATES) as read
    unit_auras: dict[int, dict[int, int]] = field(default_factory=dict)  # unit -> its damage auras read (`unit_raise`)
    # unit -> [(clock, its damagepercent read)] over the last RAISE_SECONDS (RAISE_KEEP); `raise_clock`: the last look's
    raise_reads: dict[int, list[tuple[float, int]]] = field(default_factory=dict)
    raise_clock: float = 0.0
    # STAND_IN_EVIDENCE: unit -> what the fight showed of it; the last look's clock and life, the last life lost's
    # clock; the factors last said, by unit
    evidence: dict[int, Evidence] = field(default_factory=dict)
    evidence_at: float | None = None
    evidence_life: float | None = None
    evidence_hurt: float = -math.inf
    evidence_said: dict[int, float] = field(default_factory=dict)
    evidence_lives: dict[int, tuple[float, float]] = field(default_factory=dict)  # unit -> since, its life then
    # READ_THROWS: by type, the (clock, throws a second) each look read over the last THROWS_HOLD s; the character's
    # place at the last look; the rates last said, by type
    throw_reads: dict[int, deque] = field(default_factory=dict)
    throw_places: deque = field(default_factory=deque)  # (clock, the character's place) over THROWS_PLACES s
    throw_said: dict[int, float] = field(default_factory=dict)

    def shown(self, here: Point) -> Callable[[Point], bool]:
        """Whether the window shows a spot's ground with the character at `here` (game/view.py `in_view`; the
        skill bar and the HUD are not)."""
        view = Viewport(self.aspect)
        return lambda spot: view.in_view(view.ground(here, spot[0], spot[1]))

    def offer(self, step: Step | None, now: float) -> None:
        """The fight's better stand (None: it stands well), priced as a firing stand for STAND_FRESH seconds."""
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
        """The look the arbiter prices. `now` dates each hostile's mode; `flights` reads missiles only when a read
        model's hostile is about; `draw`: the build's, with the companions it would send."""
        player = world.player
        assert player is not None
        identity = (world.game_name, player.unit_id)
        if identity != self.identity:
            self.profiles.clear()
            self.blocked_goal = None
            self.identity = identity
            self.trail.clear()
            self.modes.clear()
            self.moved.clear()
            self.trails.clear()
            self.casters.clear()
            self.lying_since.clear()
            self.stepped.clear()
            self.stand = None
            self.hops = None
            self.left_at = None
            self.duds.clear()
            self.walked_said = None
            self.rounds.clear()
            self.pack_hops.clear()
            self.doll_wait = None
            self.dolls_said = None
            self.wait_since = None
            self.wait_said = None
            self.bait_hops.clear()
            self.burn_hops.clear()
            self.burn_mark.clear()
            self.mana_seen.clear()
            self.mana_look = None
            self.mana_drunk.clear()
            self.mana_short = None
            self.auras_read.clear()
            self.unit_auras.clear()
            self.raise_reads.clear()
            self.rebuff_hops = (0, (math.inf, math.inf))
            self.rebuff_landed = -math.inf
            self.evidence.clear()
            self.evidence_at = self.evidence_life = None
            self.evidence_hurt = -math.inf
            self.evidence_said.clear()
            self.evidence_lives.clear()
            self.throw_reads.clear()
            self.throw_places.clear()
            self.throw_said.clear()
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
        # Unknown set: no resistance, no block; never copy battle onto travel. The guard counts only while shown,
        # at `guard_left` of its pool (the client is not told of its fall).
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
        moving = self.moving(hostile, now or 0.0)
        self.raise_clock = now or 0.0
        level = priced_level(player.area, hostile)
        closing = self.speeds = self.closing(hostile, now or 0.0)
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
        kinds |= frozenset(kind for m in hostile for kind in shot_kinds(m.txt_id))  # BOLTS_IN_FLIGHT
        read: Sequence[tuple[int, int, float, float]] | None = None
        if flights is not None and kinds:
            try:
                read = flights(kinds)
            except OSError, ValueError:
                read = None
        missiles = in_flight(hostile, None, read) if read is not None else ()
        # The auras: each hostile's own read (stats 350/351) when the look reads them, else round the holders
        per_unit = AURA_FORECAST and any(m.aura is not None or m.damage_percent is not None for m in hostile)
        holders = self.aura_holders(hostile) if AURA_FORECAST and not per_unit else ()
        seen = Look(
            tuple(
                Hostile(
                    m.unit_id,
                    m.txt_id,
                    (m.x, m.y),
                    m.flags,
                    m.modifiers,
                    m.tier,
                    level=level,
                    speed=closing.get(m.unit_id, 0.0),
                    active=m.mode != 1 or m.unit_id in moving,
                    life=m.life / m.max_life if m.max_life else 1.0,
                    mode=m.mode,
                    mode_frames=round((now - modes[m.unit_id][1]) * 25) if now is not None else 0,
                    raised=self.unit_raise(m) if per_unit else raised((m.x, m.y), holders) if holders else 1.0,
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
            cover=tuple((m.x, m.y) for m in companions if m.mode not in (0, 12) and m.life > 0),
        )
        vitals = manaburn.mana_of(loot.stats)
        burnt = 0.0
        if now is not None and vitals is not None and manaburn.burnt(tuple(self.mana_seen), now, *vitals):
            burnt = manaburn.fell(tuple(self.mana_seen), now, *vitals)
        settings = settings or SafetySettings()
        seen = self.tempered(seen, here, now, float(loot.life), settings, burnt)
        return self.throws_read(seen, here, now)

    def tempered(
        self, seen: Look, here: Point, now: float | None, life: float, settings: SafetySettings, burnt: float = 0.0
    ) -> Look:
        """STAND_IN_EVIDENCE: `seen` with each stand-in hostile's `tempered` share from what the fight showed of it
        (`Evidence`), the ledger brought up to this look first; `burnt`: the mana a burn seen took (manaburn.py
        `burnt`), a loss as the life's is. Unchanged with the switch off or no clock."""
        if not STAND_IN_EVIDENCE or now is None:
            return seen
        step = 0.0 if self.evidence_at is None else min(max(now - self.evidence_at, 0.0), EVIDENCE_STEP)
        drop = 0.0
        if self.evidence_life is not None and life < self.evidence_life:
            drop, self.evidence_hurt = self.evidence_life - life, now
        if burnt > 0:
            drop, self.evidence_hurt = drop + burnt, now
        self.evidence_at, self.evidence_life = now, life
        hostiles = list(seen.hostiles)
        for index, h in enumerate(hostiles):
            if not stood_in(h.txt):
                continue
            known = self.evidence.get(h.unit, Evidence())
            if rules.ai_distance(h.at, here) < rules.RADIUS:
                known = self.evidence[h.unit] = Evidence(known.exposed + step, known.lost + drop)
            stalled = self.stalled(h, now)
            share = self.evidence_share(seen, h, here, known, now, settings) if stalled else 1.0
            if share < 1.0:
                hostiles[index] = replace(h, tempered=share)
            said = self.evidence_said.get(h.unit, 1.0)
            if abs(share - said) >= 0.1 or (share >= 1.0) != (said >= 1.0):
                self.evidence_said[h.unit] = share
                seconds, lost = stand_ins.prior(h.txt)
                why = f'no fall of its life in {STALL_SECONDS:.0f} s' if stalled else 'its life falls'
                LOG.info(
                    'Macro: safety: the stand-in price of the %d (%d) is x%.2f: %s; %.0f s within its reach here, '
                    '%.0f life lost there, the takes %.0f s and %.0f%s (STAND_IN_EVIDENCE)',
                    h.txt, h.unit, share, why, known.exposed, known.lost, seconds, lost,
                    f', hurt {now - self.evidence_hurt:.1f} s ago' if now - self.evidence_hurt < EVIDENCE_HURT else '',
                )  # fmt: skip
        if hostiles == list(seen.hostiles):
            return seen
        return replace(seen, hostiles=tuple(hostiles))

    def throws_read(self, seen: Look, here: Point, now: float | None) -> Look:
        """READ_THROWS (combat/bolts.py): `seen` with each unread type's `Hostile.throws`, its rate at the character
        over its last THROWS_HOLD s of looks (`bolts.throw_count`: its bolts in flight at the character's places of the
        last THROWS_PLACES s, over their flight). Unchanged with the switch off or no clock."""
        if not bolts.READ_THROWS or now is None:
            return seen
        # Where the character stood over the last THROWS_PLACES s: a bolt let go at one of them still flies at it after
        # a hop (one look after a Teleport sees the pack's bolts at the old place, none yet at the new)
        self.throw_places.append((now, here))
        while self.throw_places and now - self.throw_places[0][0] > THROWS_PLACES:
            self.throw_places.popleft()
        places: list[Point] = []
        for _, place in reversed(self.throw_places):
            if all(math.dist(place, other) >= 1.0 for other in places):
                places.append(place)
        types: dict[int, list[Hostile]] = {}
        for h in seen.hostiles:
            if unread(h.txt) and bolts.classes_of(h.txt):
                types.setdefault(h.txt, []).append(h)
        rates: dict[int, float] = {}
        for txt, members in types.items():
            kinds = bolts.classes_of(txt)
            speeds = [speed for kind in kinds if (speed := bolts.speed_of(kind)) is not None]
            shooters = {h.unit: h.at for h in members}
            flying = [(m[0], m[1], m[2]) for m in seen.missiles if len(m) > 3 and m[0] in shooters and m[3] in kinds]
            coming, flight = (
                bolts.throw_count(flying, min(speeds), shooters, places, SHOT_REACH) if speeds else (0, 0.0)
            )
            reads = self.throw_reads.setdefault(txt, deque())
            reads.append((now, coming, flight))
            while reads and now - reads[0][0] > THROWS_HOLD:
                reads.popleft()
            # Its rate over the last THROWS_HOLD s of looks: the bolts seen coming over the flight seconds looked at
            seen_flight = sum(row[2] for row in reads)
            rates[txt] = held = sum(row[1] for row in reads) / seen_flight if seen_flight > 0 else 0.0
            said = self.throw_said.get(txt, 0.0)
            if held > 0 and max(held, said) / max(min(held, said), 1e-9) >= THROWS_SAID:
                self.throw_said[txt] = held
                LOG.info(
                    'Macro: safety: the %d throw %.2f a second each at the character, %d of them about '
                    '(READ_THROWS)', txt, held, len(members),
                )  # fmt: skip
        self.throw_reads = {txt: reads for txt, reads in self.throw_reads.items() if txt in types}
        if not any(rates.values()):
            return seen
        return replace(
            seen,
            hostiles=tuple(replace(h, throws=rates[h.txt]) if rates.get(h.txt) else h for h in seen.hostiles),
            memo={},
        )

    def stalled(self, h: Hostile, now: float) -> bool:
        """Whether the fight with stand-in hostile `h` has stalled (STAND_IN_EVIDENCE): its life has not fallen by
        STALL_DROP of its full in STALL_SECONDS, the clock started at its first sight or its last such fall."""
        since = self.evidence_lives.get(h.unit)
        if since is None or h.life <= since[1] - STALL_DROP:
            self.evidence_lives[h.unit] = since = (now, h.life)
        return now - since[0] >= STALL_SECONDS

    def evidence_share(
        self, seen: Look, h: Hostile, here: Point, known: Evidence, now: float, settings: SafetySettings
    ) -> float:
        """The share of `h`'s stand-in its evidence leaves (STAND_IN_EVIDENCE): 1 before EVIDENCE_SECONDS within its
        radius, or with life lost in the last EVIDENCE_HURT; else EVIDENCE_MARGIN times (the life lost there plus one
        table blow) a second, over the stand-in's own rate at the character, within [EVIDENCE_FLOOR, 1]."""
        seconds, lost = stand_ins.prior(h.txt)
        exposed, lost = seconds + known.exposed, lost + known.lost
        if exposed < EVIDENCE_SECONDS or now - self.evidence_hurt < EVIDENCE_HURT:
            return 1.0
        # Its rate at the character or, the larger, at the place a third into its radius on the way to the character
        # (the share prices every place, not the character's alone: one out of its sight or reach is no rate)
        gap = math.dist(h.at, here)
        inside = min(1.0, rules.RADIUS / 3 / gap) if gap > 0 else 1.0
        places = (here, (h.at[0] + (here[0] - h.at[0]) * inside, h.at[1] + (here[1] - h.at[1]) * inside))
        whole = replace(seen, hostiles=(replace(h, tempered=1.0),))
        rate = max(harm(whole, place, 1.0, 'battle', settings).mean for place in places)
        if rate <= 0:
            return self.evidence_said.get(h.unit, 1.0)  # no rate to scale: the share as it was
        blow = most_blow(h, seen.battle)[0] or settings.unknown_points
        bound = EVIDENCE_MARGIN * (lost + blow) / exposed
        # The share scales the stand-in's rate and its burst over the table blow (combat/harm.py STAND_IN_TEMPER): its
        # mean goes as share * (1 + (F - 1) * share) / F, F the burst factor; the share whose mean is the bound
        wanted, burst = min(1.0, bound / rate), settings.unknown_damage_factor
        share = wanted if burst <= 1 else (math.sqrt(1 + 4 * (burst - 1) * burst * wanted) - 1) / (2 * (burst - 1))
        return min(1.0, max(EVIDENCE_FLOOR, share))

    def unit_raise(self, m: Monster) -> float:
        """The factor the auras on a hostile put on its physical points (AURA_FORECAST): its damagepercent (stat 25,
        `Monster.damage_percent`: the game's sum of the damage auras on it) when read; else the damage auras its stats
        350/351 showed (`Monster.aura`), each kept for the unit once seen (a curse put on it later shows in their
        place), their +% summed."""
        if m.damage_percent is not None:
            return 1.0 + max(self.kept_percent(m.unit_id, m.damage_percent), 0) / 100
        if m.aura is not None and m.aura[0] in AURA_DAMAGE:
            seen = self.unit_auras.setdefault(m.unit_id, {})
            seen[m.aura[0]] = max(seen.get(m.aura[0], 0), m.aura[1])
        seen = self.unit_auras.get(m.unit_id, {})
        return 1.0 + sum(aura_raise(skill, level)[0] for skill, level in seen.items()) / 100

    def kept_percent(self, unit: int, percent: int) -> int:
        """The most damagepercent read on `unit` within RAISE_SECONDS of the last look (RAISE_KEEP), `percent` (this
        read) among them; `percent` alone with the switch off."""
        if not RAISE_KEEP:
            return percent
        now = self.raise_clock
        reads = [(at, value) for at, value in self.raise_reads.get(unit, ()) if now - at <= RAISE_SECONDS]
        if reads and reads[-1][0] == now:
            reads[-1] = (now, max(reads[-1][1], percent))  # one read a clock: the asks between looks add none
        else:
            reads.append((now, percent))
        self.raise_reads[unit] = reads
        return max(value for _, value in reads)

    def aura_holders(self, hostile: Sequence[Monster]) -> tuple[tuple[Point, tuple[int, ...]], ...]:
        """The Aura Enchanted hostiles (AURA_MOD) with their auras (AURA_FORECAST), read once a unit from its state
        words (`states_of`, AURA_STATES); one unread, or showing no aura, is left out (none known; an unread one is
        read again at the next look). The fallback where the look reads no unit's damagepercent (`unit_raise`)."""
        found = []
        for m in hostile:
            if AURA_MOD not in m.modifiers:
                continue
            auras = self.auras_read.get(m.unit_id)
            if auras is None and self.states_of is not None:
                try:
                    words = self.states_of(m)
                except OSError, ValueError:
                    words = None
                if words is not None:
                    auras = self.auras_read[m.unit_id] = auras_of(words)
            if auras:
                found.append(((m.x, m.y), auras))
        return tuple(found)

    def lying(
        self, lingering: set[threats.Lingering], read: Sequence[tuple[int, int, float, float]], clock: float
    ) -> tuple[tuple[threats.Lingering, tuple[threats.Lying, ...]], ...]:
        """What lies on the ground by model (`Look.ground`), each with its caster's last place and its age."""
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

        Priced in the order they matter: the act asked for and holding (always), shorter approaches and the firing
        stand, the threat's escapes, the plain rays. Past the deadline later tiers are cut (two escapes still priced
        when nothing is safe), so the answer is the best found in time."""
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
            from inventory_tracking.macros.travel import STANDING

            goal = Goal('the fight', seen.origin, 'fight', attack.reach, STANDING)
        key = (goal.do, goal.unit, goal.route, goal.stage, goal.place)
        doll_key = (goal.do, goal.unit, goal.label)  # a fight goal's place follows its monster: not in the key
        patient = (
            self.doll_wait is not None
            and self.doll_wait[0] == doll_key
            and facts.now - self.doll_wait[1] >= dolls.PATIENCE
        )
        waited = (
            WAIT_LIFT
            and not facts.in_reach
            and self.wait_since is not None
            and self.wait_since[0] == doll_key
            and facts.now - self.wait_since[1] >= WAIT_HORIZON
        )
        fresh = posted is not None and posted.fresh(facts.now)
        # A fresh press asks for the goal; so does a level run at every look (`run_insists`).
        running = posted is not None and posted.runs and settings.run_insists and not posted.spent
        asking = fresh or running
        insisting = self.insisting(facts.now, posted, key, asking, running)
        allowance, spendable, kappa, dear = life_budget(loot, felt, settings, look, seen.origin, insisting)
        orders = self.orders
        ending = orders is not None and orders.shown and orders.left is not None and orders.left < PREDICT_LEFT
        if ORDERS_PREDICT and orders is not None and ending:
            # The life as it will be once Battle Orders runs out: the same share of the most life without it
            look = replace(look, life=look.life / orders.factor)
            allowance = allowance / orders.factor if allowance > 0 else allowance
        if DANGER_LOOK and clock.timer is not None and (allowance <= 0 or self.alarmed):
            clock.deadline = max(clock.deadline, clock.began + DANGER_SECONDS)  # the escapes priced in full time
        if self.reacts(loot, look):
            # The rollouts' lethal veto off: a rejuvenation answers what builds over blows (REJUV_REACTS)
            settings = self.no_veto(settings)
        credit = not (FLOOR_NO_CREDIT and allowance <= 0)  # no kill credit under the life's floor (FLOOR_NO_CREDIT)
        # The mana floor (combat/threats/manaburn.py MANA_FLOOR): the mana reserve is in the budget as life is
        mana, leaving = self.mana_floor(facts, loot, look, seen.origin)
        self.mana_look = None
        if leaving is not None:
            allowance = 0.0
        walkers = self.walked_round(look, seen.origin) if facts.attacking else ()
        reaggro = facts.attacking and self.idle_after_hop(look, seen.origin, facts.now)  # REAGGRO_BY_MARK
        burning = self.kept_at_range(look, seen.origin, settings, loot, felt, mana, facts) if facts.attacking else ()
        p = Pricing(
            facts, look, seen, settings, attack, leg, jumps, barred, hands, options, battle_ready, teleport_hands,
            goal, clock, legs, allowance, kappa, shown=self.shown(seen.origin),
            duds=tuple(spot for spot, until in self.duds.items() if facts.now < until), walking=bool(walkers),
            left=self.bounce_from(seen.origin, facts.now),
            patient=patient, waited=waited, mana=mana, burning=burning, reaggro=reaggro,
            credit=credit, demons=self.demons_of(look) if facts.attacking else None,
            range_lifted=self.range_stalled(goal, key, facts),
        )  # fmt: skip
        if facts.attacking:
            self.hold_exempt = self.real_threat(p, felt, allowance, leaving)
            p.reaggro = p.reaggro and self.hold_exempt is None  # a real threat lets the hop through (REAGGRO_BY_MARK)
            p.jump_hold = herald_pack.jump_hold(
                facts.now, seen.origin, look.hostiles, look.companions, self.hold_exempt
            )  # MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5
        clock.lap('the forecast')
        held = self.hold(p)
        clock.lap('holding')
        self.rebuff_back(p)  # Battle Orders due and not safe to cast here (REBUFF_RETREAT)
        clock.lap('the rebuff')
        baiting = self.bait_stand(p)  # the way in to dolls a demon holds (DOLL_BAIT, off)
        # No escape is priced when holding's harm at kappa is below the least a move costs.
        saving = kappa * held.harm.mean
        least = settings.move_overhead + WALK_LATENCY + (SWAP_SECONDS if hands != 'battle' else 0.0)
        waiting = isinstance(base, NoWay)
        if waiting and held.harm.worst <= allowance and veto(held.harm, look.life, settings) is None:
            if saving <= least and baiting is None:
                return facts  # waiting for a pack or boss to appear is no failed safety constraint
            # Waiting priced as an act when an escape could be worth more.
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
        clock.lap('the offered stand')
        if not unsafe and ((facts.in_reach and facts.attacking) or waiting) and saving > least:
            self.rounding(p, walkers)
            self.stepping(p, held.harm, saving, least)
        clock.lap('the escapes')
        if unsafe:
            self.retreats(p, held)
        elif self.raised_keep(p, look):
            self.kept_retreats(p, held, spread=True)
        clock.lap('the retreats')
        backing = self.pack_back(p)
        clock.lap('the pack')
        if leaving is not None:
            self.mana_leave(p, held, leaving)
            clock.lap('the mana')
        p.doll_escapes()
        priced = replace(
            facts,
            candidates=tuple(p.candidates),
            priced=True,
            budget=allowance,
            life=look.life,
            kappa=kappa,
            safety=settings,
            clear=min((math.dist(p.here, m.at) for m in look.hostiles), default=None),
            throwers=tuple(m.at for m in look.hostiles if m.throws > 0),  # READ_THROWS (pursuit.py THROWN_OUT)
            stand=self.may_stand(doll_key, facts) and kept_out(p),  # STAND_NOT_RETREAT
        )
        obstructed = p.obstructed()
        if obstructed is not None:
            self.blocked_by = blockers(obstructed.harm, allowance)
        chosen = decide(priced, posted)
        if baiting is not None and isinstance(chosen, Move) and chosen.reason.startswith(dolls.BAIT_SAID):
            self.bait_hops[baiting] = self.bait_hops.get(baiting, 0) + 1
            LOG.info('Macro: safety: %s, hop %d of %d to (%.1f, %.1f)', chosen.reason, self.bait_hops[baiting],
                     dolls.BAIT_HOPS, *chosen.step.spot)  # fmt: skip
        if backing is not None and isinstance(chosen, Move) and chosen.reason.startswith(herald_pack.BACK_SAID):
            if p.burning:
                self.burn_hopped(backing, chosen, p.here)
            else:
                self.pack_hops[backing] = self.pack_hops.get(backing, 0) + 1
                LOG.info(
                    'Macro: safety: %s, hop %d of %d to (%.1f, %.1f)',
                    chosen.reason, self.pack_hops[backing], herald_pack.PACK_HOPS, *chosen.step.spot,
                )  # fmt: skip
        if leaving is not None and isinstance(chosen, Move) and chosen.reason.startswith(manaburn.MANA_SAID):
            LOG.info('Macro: safety: %s: %s to (%.1f, %.1f)', chosen.reason,
                     'Teleport' if chosen.step.skill == TELEPORT else 'a walk', *chosen.step.spot)  # fmt: skip
        if self.rebuffing:
            self.rebuff_chosen(chosen, look, p.here, facts.now)
        self.mana_look = self.mana_state(facts.now, loot, look, p.here, self.mana_short, chosen)
        self.remember(chosen, look, p.here, asking, key, facts.now, posted)
        self.went_round(chosen, look, p.here, walkers)
        self.said_walked(p, walkers, chosen)
        self.dolls_waited(p, doll_key, chosen)
        self.waits(p, doll_key, chosen, loot.max_life)
        self.range_stalls(p, key, chosen, loot)
        self.stands(doll_key, chosen, priced)  # STAND_NOT_RETREAT
        self.burn_stalls(p, chosen, loot)  # manaburn.BURN_STALL_COMMIT
        self.decision = p.record(
            chosen, dear=dear, insisting=insisting, spendable=spendable, blocked_by=self.blocked_by, draws=self.draws
        )
        if clock.timer is not None:
            clock.lap('the choice')
            self.over(facts.now, clock.timer() - clock.began, settings.look_seconds, clock.laps, chosen)
        return priced

    def rebuff_back(self, p: Pricing) -> bool:
        """Battle Orders due in a fight that is not safe to cast in (REBUFF_RETREAT; macros/cta.py `orders_look`):
        the first jumps to places on REBUFF_RINGS clear of the hostiles (`clearest`, on footing) landing REBUFF_CLEAR
        or more from every one, priced as dodges named REBUFF_SAID, which the arbiter takes first unless vetoed. At
        most two a look, REBUFF_HOPS chosen while it stays due. Whether one was priced."""
        orders = self.orders
        self.rebuffing = False
        self.killing_first = None
        if orders is None or orders.due is None:
            self.rebuff_hops = (0, (math.inf, math.inf))
            return False
        if not REBUFF_RETREAT or orders.safe or not p.facts.attacking or self.rebuff_hops[0] >= REBUFF_HOPS:
            return False
        first = kill_first(p, orders.left if orders.shown else None)
        if first is not None:
            self.killing_first = first
            return False
        hostiles = [m.at for m in p.look.hostiles]
        if not hostiles:
            return False
        self.rebuffing = True
        state = orders_state(orders.shown, orders.left, None, p.facts.now)
        priced = 0
        for point in clearest(p.here, hostiles, p.footed, rings=REBUFF_RINGS, asked=REBUFF_ASKED):
            if priced >= 2 or (priced and p.clock.late()):
                break
            offered = p.options(point) if p.options is not None else (p.leg(point),)
            for step in offered:
                if (
                    isinstance(step, Step)
                    and step.skill is not None
                    and math.dist(p.here, step.spot) > 2
                    and min(math.dist(step.spot, at) for at in hostiles) >= REBUFF_CLEAR
                ):
                    p.move_price(step, why=f'{REBUFF_SAID}: {state} ({orders.due})', dodge=True)
                    priced += 1
                    break
        return priced > 0

    def cast_threat(
        self, world: World, life: float | None, *, bout: bool = False, seconds: float | None = None
    ) -> str | None:
        """Why the Call to Arms is not swapped to here now (CAST_REACH), or (`bout`) the strike bout yields to the next
        look (BOUT_REACH), from `world` as read now: its hostiles at ZONE_LEVEL with the auras on them, the battle set's
        protection, `life` (None or 0: not read, no bar; a fake's 0 barred every cast of test_pets' hunt)."""
        player = world.player
        if not (BOUT_REACH if bout else CAST_REACH) or player is None or life is None or life <= 0:
            return None
        hostile = [m for m in world.monsters if not m.ally and m.owner == NO_OWNER and m.mode not in (0, 12)]
        if not hostile:
            return None
        per_unit = AURA_FORECAST and any(m.aura is not None or m.damage_percent is not None for m in hostile)
        holders = self.aura_holders(hostile) if AURA_FORECAST and not per_unit else ()
        level = priced_level(player.area, hostile)
        priced = [
            Hostile(
                m.unit_id, m.txt_id, (m.x, m.y), m.flags, m.modifiers, m.tier, level=level,
                speed=self.speeds.get(m.unit_id, 0.0),
                raised=self.unit_raise(m) if per_unit else raised((m.x, m.y), holders) if holders else 1.0,
            )
            for m in hostile
        ]  # fmt: skip
        battle = self.profiles.get('battle', Protection())
        return cast_reach(priced, (player.x, player.y), battle, float(life), bout=bout, seconds=seconds)

    def fight_cast_threat(self, world: World, life: float | None) -> str | None:
        """Why the bout's casts under the strike wait (macros/hunt.py FIGHT_CAST_REACH): `cast_threat` over
        FIGHT_CAST_SECONDS with FIGHT_CAST_OWN, else over CAST_SECONDS as the Call to Arms' swap."""
        return self.cast_threat(world, life, seconds=FIGHT_CAST_SECONDS if FIGHT_CAST_OWN else CAST_SECONDS)

    def reacts(self, loot: Loot, look: Look) -> bool:
        """REJUV_REACTS: an aura-raised fight (a hostile's `raised` over 1, AURA_FORECAST) with a rejuvenation on a read
        belt and REACH_BAR on: what is lethal only over several blows is answered by the drink, not vetoed."""
        if not (REJUV_REACTS and AURA_FORECAST and REACH_BAR) or not loot.belt_read:
            return False
        if on_belt(loot)[PotionType.REJUVENATION] < 1:
            return False
        return any(m.raised > 1.0 for m in look.hostiles)

    def no_veto(self, settings: SafetySettings) -> SafetySettings:
        """`settings` with the rollouts' veto share at 100 (REJUV_REACTS), made once a settings object."""
        kept = self.unvetoed
        if kept is None or kept[0] is not settings:
            kept = (settings, with_overrides(settings, veto_share=100.0))
            self.unvetoed = kept
        return kept[1]

    def landed(self, at: float) -> None:
        """A jump landed at clock `at` (combat/pack.py `HOP`): the rebuff retreat's when it is the first REBUFF_LANDS
        s of the choice at most (`rebuffed_at`), its landing kept in `rebuff_landed`."""
        if self.rebuff_landed < self.rebuffed_at <= at <= self.rebuffed_at + REBUFF_LANDS:
            self.rebuff_landed = at

    def rebuff_chosen(self, chosen: Act, look: Look, here: Point, now: float) -> None:
        """A jump chosen while Battle Orders is due that lands ORDERS_CLEAR or more from every hostile (the rebuff's,
        REBUFF_SAID, or another retreat's when the rebuff's was vetoed): its clock for the cast at its landing (cta.py
        REBUFF_GRACE), counted once while the character stands (REBUFF_HOPS), and said."""
        if not isinstance(chosen, Move) or chosen.step.skill is None:
            return
        clear = min((math.dist(chosen.step.spot, m.at) for m in look.hostiles), default=math.inf)
        if not chosen.reason.startswith(REBUFF_SAID) and not (chosen.reason.startswith('retreat') and clear >= CLEAR):
            return
        self.rebuffed_at = now
        count, stood = self.rebuff_hops
        if math.dist(stood, here) > STILL_UNITS:
            self.rebuff_hops = (count + 1, here)
            orders = self.orders
            state = orders_state(orders.shown, orders.left, None, now) if orders is not None else 'due'
            LOG.info(
                'Macro: buff: Battle Orders: %s: retreat to (%.1f, %.1f), %.0f clear of the hostiles, to cast it there '
                '(%d of %d)',
                state, *chosen.step.spot, clear, count + 1, REBUFF_HOPS,
            )  # fmt: skip

    def kept_at_range(
        self,
        look: Look,
        here: Point,
        settings: SafetySettings,
        loot: Loot,
        felt: Pressure,
        mana: float | None = None,
        facts: Facts | None = None,
    ) -> tuple[manaburn.Burner, ...]:
        """The hostiles kept at range (combat/threats/manaburn.py `burners`) whose threat warrants it (THREAT_GATE,
        `threatening`): the life lost and left (`felt`, `loot`), or the safety's own forecast, standing, of those
        hostiles alone; an Extra Fast drainer's forecast also against the mana's spare over the reserve (`mana`, None:
        unread, MANA_BUDGET). On the loop's run off a Terror Zone, unhurt, only the striking ones (LOOP_IGNORES_IDLE,
        `facts`: the look's)."""

        def priced(hostiles: list, place: Point) -> float:
            return harm(
                replace(look, hostiles=tuple(hostiles)), place, manaburn.THREAT_SECONDS, 'battle', settings
            ).mean

        found = manaburn.burners(look.hostiles)
        if found and facts is not None and idle_ignored(facts, look, felt, self.mana_safe):
            modes = {h.unit: h.mode for h in look.hostiles}
            found = [b for b in found if modes.get(b.unit) in STRIKING_MODES and math.dist(here, b.at) < b.keep]
        whole = loot.life / loot.max_life if loot.max_life else 1.0
        spare = max(0.0, mana - manaburn.RESERVE) if mana is not None else 0.0
        kept = manaburn.threatening(
            here, look.hostiles, found, priced, look.life, whole, felt.lost, self.mana_safe, spare
        )
        # One drain fight (drain_escape.py `widened`)
        kept = drain_escape.widened(here, found, kept, self.burn_leaving is not None, look.hostiles)
        return tuple(manaburn.committed(kept, self.commit_of(here, kept, look, felt, whole)))

    def commit_of(
        self, here: Point, kept: Sequence[manaburn.Burner], look: Look, felt: Pressure, whole: float
    ) -> int | None:
        """BURN_STALL_COMMIT: the pack fought in at this look (`burn_commit`) while it is `committable`, the mana safe,
        no burn remembered and the life unhurt; else None, and a burn or a hurt spoils the pack for good."""
        key = self.burn_commit
        if not manaburn.BURN_STALL_COMMIT or key is None:
            self.burn_commit = None
            return None
        hurt = felt.lost >= manaburn.FELT_SHARE or whole < manaburn.UNHURT
        if self.burn_leaving is not None or not self.mana_safe or hurt:
            self.burn_spoiled.add(key)
            self.burn_commit = None
            LOG.info('Macro: safety: the pack %d is kept at range again: %s', key,
                     'a burn' if self.burn_leaving is not None or not self.mana_safe else 'life lost')  # fmt: skip
            return None
        if manaburn.key_of(kept) != key or not manaburn.committable(here, kept, look.hostiles):
            return None  # not this pack at this look, or a drainer by type about: kept as found
        return key

    def burn_stalls(self, p: Pricing, chosen: Act, loot: Loot) -> None:
        """BURN_STALL_COMMIT's memory over the looks: a look whose progress move is barred by manaburn.LANDED starts
        the stall of the pack kept at range (`burn_stall`: its key, since when, the life then, the last barred look,
        the members' life then); the bar not again within STALL_GAP, a member DENTED or gone, another pack, a burn,
        the mana under MANA_SAFE or WAIT_LOST of the most life lost ends it. Past COMMIT_SECONDS the pack is fought in
        (`burn_commit`, `commit_of`) unless spoiled."""
        del chosen  # the stall is the bar's, whatever is chosen meanwhile (retreats, stands, far strikes)
        if not manaburn.BURN_STALL_COMMIT:
            self.burn_stall = None
            return
        now = p.facts.now
        key = manaburn.key_of(p.burning)
        lives = {m.unit: m.life for m in p.look.hostiles}
        calm = self.mana_safe and self.burn_leaving is None
        barred = any(
            isinstance(c.act, Move) and not c.retreat and not c.act.dodge and c.harm.barred == manaburn.LANDED
            for c in p.candidates
        )
        found = self.burn_stall
        if found is not None:
            stalled_key, since, life, last, then = found
            dented = any(lives.get(unit, 0.0) < was - manaburn.DENTED for unit, was in then.items())
            if (
                stalled_key != key
                or not calm
                or dented
                or now - last > manaburn.STALL_GAP
                or loot.life < life - WAIT_LOST * loot.max_life
            ):
                found = None
            elif barred:
                found = (stalled_key, since, life, now, then)
        if found is None and key is not None and barred and calm:
            members = {b.unit for b in manaburn.triggers(p.burning)}
            found = (key, now, float(loot.life), now, {u: v for u, v in lives.items() if u in members})
        if (
            found is not None
            and found[0] not in self.burn_spoiled
            and self.burn_commit != found[0]
            and now - found[1] >= manaburn.COMMIT_SECONDS
            and manaburn.committable(p.here, p.burning, p.look.hostiles)
        ):
            self.burn_commit = found[0]
            LOG.info('Macro: safety: %s: the pack %d after %.1f s', manaburn.COMMIT_SAID, found[0], now - found[1])
        self.burn_stall = found

    def bounce_from(self, here: Point, now: float) -> tuple[Point, Point] | None:
        """The last safety Teleport's (origin, landing) a move back to the origin is barred after (BOUNCE_BACK): under
        BOUNCE_WINDOW s ago, the character within BOUNCE_NEAR of its landing."""
        last = self.left_at
        if not BOUNCE_BACK or last is None or not 0.0 <= now - last[2] <= BOUNCE_WINDOW:
            return None
        return (last[0], last[1]) if math.dist(here, last[1]) <= BOUNCE_NEAR else None

    def real_threat(self, p: Pricing, felt: Pressure, allowance: float, leaving: str | None) -> str | None:
        """The real threat that lets a jump through the hold (combat/pack.py MARK_HOLDS_JUMPS, NO_SHORT_HOPS_T5), or
        None: surrounded, a hit of HOLD_BURST of the life within 1 s, the life budget spent, blows in reach that take
        the life (REACH_BAR's), a rejuvenation's alarm, a drainer kept at range or the mana floor's leave, a live doll
        close, HOLD_SHOOTERS ranged hostiles in reach."""
        here = p.here
        close = sum(1 for m in p.look.hostiles if math.dist(here, m.at) <= herald_pack.SURROUND_RADIUS)
        if close >= herald_pack.SURROUND_COUNT:
            return f'surrounded: {close} within {herald_pack.SURROUND_RADIUS:.0f}'
        if felt.burst >= herald_pack.HOLD_BURST:
            return f'hit: {felt.burst:.0%} of the life within 1 s'
        if allowance <= 0:
            return 'the life budget is spent'
        if p.reach_blows(here) >= p.look.life:
            # 2026-10-25 (apply-0b.md): danger-durance-1956 seed 17, the retreat held 0.43 s after the mark's key with
            # 4529 of 2907 in reach walked 16 into a wall and died; the jump lived
            return f'{REACH_SAID} here'
        if self.alarmed:
            return "the rejuvenation's alarm"
        if leaving is not None or (
            manaburn.drainer_close(here, p.burning) if manaburn.BURN_ENGAGE else any(b.drains for b in p.burning)
        ):
            return 'a drainer'
        if p.close:
            return 'a live doll close'
        table = bolts.threat_table().monsters
        shooters = sum(
            1
            for m in p.look.hostiles
            if math.dist(here, m.at) <= SHOT_REACH and getattr(table.get(m.txt), 'ranged', False)
        )
        if shooters >= herald_pack.HOLD_SHOOTERS:
            return f'ranged fire: {shooters} shooters within {SHOT_REACH:.0f}'
        return None

    def demons_of(self, look: Look) -> tuple[Point, ...]:
        """Where the companions the build's draw sends stand (`sendable`): the pack's demons (`pack_back`)."""
        return tuple(look.companions[i] for i, _ in self.sendable if i < len(look.companions))

    def idle_after_hop(self, look: Look, here: Point, now: float) -> bool:
        """The demons idle by the character with the pack on it (combat/pack.py `reaggro_due`): the keep range's hop
        and a voluntary Teleport are barred for the stretch's first REAGGRO_WAIT s, until the mark has landed
        (`reaggro_holds`, `Pricing.reaggro`)."""
        if not herald_pack.REAGGRO_BY_MARK:
            return False
        demons = [look.companions[i] for i, _ in self.sendable if i < len(look.companions)]
        if not herald_pack.reaggro_due(here, demons, [h.at for h in look.hostiles]):
            self.idle_since = None
            return False
        if self.idle_since is None:
            self.idle_since = now
        return herald_pack.reaggro_holds(now, self.idle_since)

    def pack_back(self, p: Pricing) -> int | None:
        """A Teleport back from a tier 4-5 Herald's pack (combat/pack.py, the player's rulings of 2026-10-21 ~10:00:
        "a Teleport back when anything is within 10", "surrounded: out with the demon between, re-engage, up to 3
        times"): with the pack on the character (`why_back`), the first Teleport legs to `hop_spots` priced as a dodge
        named BACK_SAID, which the arbiter takes over the rest unless vetoed. The pack's key while one is priced, else
        None. Not past PACK_HOPS a pack, nor with attack mode off."""
        facts, look, here = p.facts, p.look, p.here
        if not facts.attacking:
            return None
        demons = [look.companions[i] for i, _ in self.sendable if i < len(look.companions)]
        if p.burning:  # under a burn remembered the leave is the way out, not the hop (drain_escape.py)
            return None if self.burn_leaving is not None else self.burn_back(p, demons)
        pack = herald_pack.members(look.hostiles)
        key = herald_pack.key_of(pack)
        if key is None or self.pack_hops.get(key, 0) >= herald_pack.PACK_HOPS:
            return None
        why = herald_pack.why_back(here, pack, demons) or herald_pack.pulled(facts.now)  # a build's pull (pets.py)
        if why is None:
            return None
        priced = 0
        for point in herald_pack.hop_spots(here, pack, demons):
            if priced >= 2 or (priced and p.clock.late()):
                break
            offered = p.options(point) if p.options is not None else (p.leg(point),)
            for step in offered:
                if (
                    isinstance(step, Step)
                    and step.skill == TELEPORT
                    and math.dist(here, step.spot) > 2
                    and all(math.dist(step.spot, m.at) >= herald_pack.PACK_BACK for m in pack)
                ):
                    p.move_price(step, why=f'{herald_pack.BACK_SAID}: {why}', dodge=True)
                    priced += 1
                    break
        return key if priced else None

    def burn_back(self, p: Pricing, demons: list[Point]) -> int | None:
        """A hop back from a draining pack (combat/threats/manaburn.py BURN_RANGE; the player, 2026-10-21 ~15:50, "a
        battle against bird that burned all mana, we were tanking most of T5 herald damage without being able to hit"):
        with a burner on the character within its keep range (`why_back`), the first legs to `hop_spots` landing clear
        of every burner, priced as a dodge named BACK_SAID (the arbiter takes it first unless vetoed): a Teleport while
        the mana pays for one, else a walk. The pack's key while one is priced, else None; not past BURN_HOPS a pack."""
        here, burning = p.here, p.burning
        key = manaburn.key_of(burning)
        # A drainer closing in is on the character, a demon by it or not, past the hop budget too (drain_escape.py)
        coming = self.burn_watch.closing_in(p.facts.now, here, burning, p.look.hostiles)
        if key is None or (self.burn_hops.get(key, (0, here, here))[0] >= manaburn.BURN_HOPS and not coming):
            return None
        if (
            manaburn.BURN_ENGAGE
            and not coming
            and -math.inf < herald_pack.MARK.at <= self.burn_mark.get(key, -math.inf)
            and manaburn.burn_held(demons, burning)
        ):
            return None  # the demons on the burners, the mark's hop spent: the next waits for a new mark (BURN_ENGAGE)
        demons = [] if coming else demons
        why = manaburn.why_back(here, burning, demons) or herald_pack.pulled(p.facts.now)  # a build's pull (pets.py)
        if why is None:
            return None
        priced = 0
        for point in manaburn.hop_spots(here, burning, demons):
            if priced >= 2 or (priced and p.clock.late()):
                break
            offered = p.options(point) if p.options is not None else (p.leg(point),)
            for step in offered:
                if (
                    isinstance(step, Step)
                    and math.dist(here, step.spot) > 2
                    and (step.skill == TELEPORT) == p.teleport_paid()
                    and manaburn.clear_of(step.spot, burning)
                ):
                    p.move_price(step, why=f'{herald_pack.BACK_SAID}: {why}', dodge=True)
                    priced += 1
                    break
        if not priced and drain_escape.urgent(burning, coming):  # no landing clear: the clearest (drain_escape.py)
            said = f'{herald_pack.BACK_SAID}: {why}'
            priced = drain_escape.price_clearest(p, burning, TELEPORT, said, self.burn_watch)
        return key if priced else None

    def burn_hopped(self, key: int, chosen: Move, here: Point) -> None:
        """Count a hop out of a draining pack once: not again while it is chosen anew to about the same spot with the
        character not moved (the take of 15:46:13.64-13.77 counted one unlanded hop as two)."""
        count, spot, stood = self.burn_hops.get(key, (0, (math.inf, math.inf), here))
        if count and math.dist(spot, chosen.step.spot) <= DUD_UNITS and math.dist(stood, here) <= STILL_UNITS:
            return
        self.burn_hops[key] = (count + 1, chosen.step.spot, here)
        self.burn_mark[key] = herald_pack.MARK.at  # BURN_ENGAGE: the mark this hop spent
        LOG.info('Macro: safety: %s, hop %d of %d to (%.1f, %.1f)', chosen.reason, count + 1, manaburn.BURN_HOPS,
                 *chosen.step.spot)  # fmt: skip

    def mana_floor(self, facts: Facts, loot: Loot, look: Look, here: Point) -> tuple[float | None, str | None]:
        """The character's mana (None: unread) and why the mana floor is crossed (combat/threats/manaburn.py
        MANA_FLOOR, `mana_low`: the mana burnt or under the reserve with a hostile in reach; with LEAVE_BURNERS_ONLY
        only a burn seen or a mana burner in reach, `leave_for`), or None. Remembers the look's mana for the next, and
        the want a Rejuvenation may answer (`mana_short`), and whether the mana is safe (`mana_safe`, DRAIN_GATE)."""
        self.mana_short = None
        self.mana_safe = False
        self.burn_leaving = None
        read = manaburn.mana_of(loot.stats)
        if read is None:
            return None, None
        mana, most = read
        history = tuple(self.mana_seen)
        self.mana_seen.append((facts.now, mana, most))
        if not facts.attacking:
            return mana, None
        near = manaburn.threatened(here, look.hostiles)
        low = manaburn.mana_low(history, facts.now, mana, most, len(near))
        burn = manaburn.burnt(history, facts.now, mana, most)
        self.mana_safe = most > 0 and mana >= manaburn.MANA_SAFE * most and not burn
        drainers = sum(1 for m in near if drain_escape.drains(m))  # by type too with MANA_ESCAPE
        leaving = manaburn.leave_for(low, burn, drainers)
        self.mana_short = manaburn.short_of(leaving, low, mana)
        self.burn_watch.walked(facts.now, here)
        self.burn_watch.seen(history, facts.now, mana, most, drain_escape.drainers_near(here, look.hostiles))
        self.burn_leaving = self.burn_watch.leaving(facts.now, mana, most, drainers)
        if self.burn_leaving is not None:  # the burn remembered (drain_escape.py `BurnWatch`)
            leaving = leaving or self.burn_leaving
            self.mana_safe = False
            self.mana_short = self.mana_short or leaving
        return mana, leaving

    @staticmethod
    def mana_state(
        now: float, loot: Loot, look: Look, here: Point, leaving: str | None, chosen: Act
    ) -> manaburn.ManaLook | None:
        """The look's mana state (manaburn.ManaLook): the mana, the floor's why, the dangerous pack in reach, and
        whether the act chosen is a Teleport out (a dodge or a retreat). None with the mana unread."""
        read = manaburn.mana_of(loot.stats)
        if read is None:
            return None
        danger, key = manaburn.dangerous(here, look.hostiles)
        out = (
            isinstance(chosen, Move)
            and chosen.step.skill == TELEPORT
            and (chosen.dodge or chosen.reason.startswith('retreat'))
        )
        return manaburn.ManaLook(now, read[0], read[1], leaving, danger, key, out)

    def mana_leave(self, p: Pricing, held: Held, why: str) -> None:
        """The leave under the mana floor (MANA_FLOOR), priced as dodges named MANA_SAID that the arbiter takes first
        unless vetoed: the draining pack's hop spots, then the threat's escapes (`offered`); a Teleport while the mana
        pays for one, else a walk. At most ESCAPES_MOST places."""
        here, demons = p.here, [p.look.companions[i] for i, _ in self.sendable if i < len(p.look.companions)]
        # Under a burn remembered: out of every drainer's reach first (drain_escape.py `far_spots`)
        watch = self.burn_watch
        far = drain_escape.far_spots(here, p.burning, p.look.hostiles, p.footed, watch) if self.burn_leaving else []
        places = far or (manaburn.hop_spots(here, p.burning, demons) if p.burning else [])
        threat = held.harm if held.harm.by else held.ahead
        places += [] if far else [point for point, _, _ in self.offered(here, p.look, threat)]
        self.refill = drain_escape.refill_of(p, places[:ESCAPES_MOST], TELEPORT, why)
        asked: list[Point] = []
        for index, point in enumerate(places[:ESCAPES_MOST]):
            if index >= 2 and p.clock.late():
                break
            offered = p.options(point) if p.options is not None else (p.leg(point),)
            for step in offered:
                if (
                    isinstance(step, Step)
                    and math.dist(here, step.spot) > 2
                    and (step.skill == TELEPORT) == p.teleport_paid()
                    and all(math.dist(step.spot, other) >= ESCAPE_SAME for other in asked)
                    and (
                        not p.burning
                        or manaburn.clear_of(step.spot, p.burning)
                        or step.skill != TELEPORT
                        or (far and drain_escape.gains(here, step.spot, p.burning, p.look.hostiles))  # the way out
                    )
                ):
                    asked.append(step.spot)
                    p.move_price(step, why=f'{manaburn.MANA_SAID}: {why}', dodge=True)
                    break

    def bait_stand(self, p: Pricing) -> int | None:
        """DOLL_BAIT's way in (combat/threats/dolls.py): with dolls a demon of the draw holds (`held_pack`), the
        navigator's first move to `bait_stand` priced as a dodge named BAIT_SAID, which the arbiter takes first while
        it is not vetoed. The held pack's key while one is priced, else None. Not past BAIT_HOPS a pack, nor with attack
        mode off."""
        if not dolls.DOLL_BAIT or not p.facts.attacking:
            return None
        demons = [p.look.companions[i] for i, _ in self.sendable if i < len(p.look.companions)]
        found = dolls.held_pack(p.here, p.look.hostiles, herald_pack.holders(p.here, demons))
        if found is None or self.bait_hops.get(found[1], 0) >= dolls.BAIT_HOPS:
            return None
        spot = dolls.bait_stand(p.here, found[0])
        if spot is None:
            return None
        for step in p.options(spot) if p.options is not None else (p.leg(spot),):
            if isinstance(step, Step) and math.dist(p.here, step.spot) > 2:
                gap = math.dist(step.spot, found[0])
                p.move_price(step, firing=True, why=f'{dolls.BAIT_SAID} from {gap:.0f}', dodge=True)
                return found[1]
        return None

    def walked_round(self, look: Look, here: Point) -> tuple[int, ...]:
        """The hostiles whose act under way is walked out of, not hopped out of (combat/threats `Threat.walked`)."""
        found = []
        for m in look.hostiles:
            model = threats.of(m.txt)
            if model is not None and model.walked is not None:
                flying, kinds = threats.flying_of(look.missiles, m.unit)
                if model.walked(threats.Acting(m.at, m.mode, m.mode_frames, flying, kinds), here):
                    found.append(m.unit)
        return tuple(found)

    def rounding(self, p: Pricing, walkers: tuple[int, ...]) -> None:
        """The next place of a walk round each act under way that is walked (WALK_ROUND), both ways round at first and
        then the way taken (`rounds`), priced as a dodge that goes on (`Move.onward`)."""
        if not WALK_ROUND:
            return
        for m in p.look.hostiles:
            model = threats.of(m.txt)
            if m.unit not in walkers or model is None or model.around is None:
                continue
            kept = self.rounds.get(m.unit)
            sides = (kept[1],) if kept is not None and kept[0] == self.modes.get(m.unit) else (1, -1)
            acting = threats.Acting(m.at, m.mode, m.mode_frames, *threats.flying_of(p.look.missiles, m.unit))
            for side in sides:
                found = model.around(acting, p.here, side)
                if found is None or p.clock.late():
                    continue
                spot = footing(p.field_, p.here, found[0])
                if spot is not None and math.dist(p.here, spot) > 2:
                    p.move_price(Step(spot), firing=True, why=f'{STEPPING} {found[1]}', dodge=True, onward=True)

    def went_round(self, chosen: Act, look: Look, here: Point, walkers: tuple[int, ...]) -> None:
        """A step across or round an act walked out of (STEPPING, a walk) sets the way round it for the next looks
        (`rounds`): the side of the line from it to the character the step went to."""
        self.rounds = {unit: kept for unit, kept in self.rounds.items() if kept[0] == self.modes.get(unit)}
        if not isinstance(chosen, Move) or not chosen.reason.startswith(STEPPING) or chosen.step.skill is not None:
            return
        spot = chosen.step.spot
        for m in look.hostiles:
            if m.unit not in walkers:
                continue
            cross = (here[0] - m.at[0]) * (spot[1] - m.at[1]) - (here[1] - m.at[1]) * (spot[0] - m.at[0])
            if abs(cross) > 1e-6:
                self.rounds[m.unit] = (self.modes.get(m.unit), 1 if cross > 0 else -1)

    def said_walked(self, p: Pricing, walkers: tuple[int, ...], chosen: Act) -> None:
        """Log, once an act under way, the Teleports left out for it (WALKED) and what is done instead."""
        left = sum(1 for c in p.candidates if c.harm.barred == WALKED)
        said = tuple((unit, self.modes.get(unit)) for unit in walkers)
        if not left or said == self.walked_said:
            return
        self.walked_said = said
        if isinstance(chosen, Move):
            spot = chosen.step.spot
            how = 'a walk' if chosen.step.skill is None else 'a jump'
            gap = math.dist(p.here, spot)
            act = f'{how} of {gap:.0f} to ({spot[0]:.1f}, {spot[1]:.1f}), {chosen.reason or "toward the goal"}'
        else:
            act = f'{type(chosen).__name__} {getattr(chosen, "reason", "")}'.strip()
        LOG.info('Macro: safety: %s: %d Teleport%s left out; %s', WALKED, left, '' if left == 1 else 's', act)

    def waits(self, p: Pricing, key: tuple, chosen: Act, most: float) -> None:
        """WAIT_LIFT's memory over the looks: a stand with nothing in reach starts the wait (`wait_since`); anything in
        reach, another goal, a hostile seen WAIT_MOVED from its place then or WAIT_LOST of the `most` life lost ends it.
        Kept through the moves the lift lets go, which the wait's own end would bar again."""
        if not WAIT_LIFT:
            return
        facts, look = p.facts, p.look
        places = {m.unit: m.at for m in look.hostiles}
        found = self.wait_since
        if found is not None and (
            facts.in_reach
            or found[0] != key
            or look.life < found[3] - WAIT_LOST * most
            or any(unit in places and math.dist(places[unit], at) >= WAIT_MOVED for unit, at in found[2].items())
        ):
            found = None
        standing = isinstance(chosen, NoWay) and (chosen.reason == WAITING or chosen.reason.endswith('standing here'))
        if found is None and standing and not facts.in_reach:
            found = (key, facts.now, places, look.life)
        if p.waited and found is not None and found[1] != self.wait_said:
            self.wait_said = found[1]
            LOG.info('Macro: safety: stood %.1f s with nothing coming: the keep ranges lifted for the way; %s',
                     facts.now - found[1], getattr(chosen, 'reason', '') or type(chosen).__name__)  # fmt: skip
        self.wait_since = found

    def may_stand(self, key: tuple, facts: Facts) -> bool:
        """STAND_NOT_RETREAT: whether standing may be chosen over a retreat that saves no harm (`Facts.stand`): nothing
        in reach, and the goal `key` stood for under STAND_SECONDS since its first such stand."""
        found = self.stood
        return (
            arbiter.STAND_NOT_RETREAT
            and not facts.in_reach
            and (found is None or found[0] != key or facts.now - found[1] < arbiter.STAND_SECONDS)
        )

    def stands(self, key: tuple, chosen: Act, facts: Facts) -> None:
        """STAND_NOT_RETREAT's memory over the looks: the first stand of the goal `key` chosen in place of a retreat
        starts its clock (`stood`); another goal or anything in reach ends it."""
        found = self.stood
        if not arbiter.STAND_NOT_RETREAT or facts.in_reach or (found is not None and found[0] != key):
            found = None
        if found is None and facts.stand and isinstance(chosen, NoWay) and chosen.reason == WAITING:
            found = (key, facts.now)
            LOG.info('Macro: safety: standing here: no retreat saves any harm (STAND_NOT_RETREAT, %.0f s at most '
                     'for %s)', arbiter.STAND_SECONDS, key[2])  # fmt: skip
        self.stood = found

    def range_stalled(self, goal: Goal, key: tuple, facts: Facts) -> bool:
        """RANGE_STALL_LIFT: whether this look's moves are priced without PACK_RANGE_LANDING's bar: the goal `key` (no
        fight and no clearing goal: the budgets pass those) stalled on it RANGE_STALL_SECONDS and more, with nothing in
        reach."""
        found = self.range_stall
        return (
            RANGE_STALL_LIFT
            and found is not None
            and found[0] == key
            and not goal.clearing
            and goal.do != 'fight'  # nor a fight: the safety's own, a clearing one the budgets'
            and not facts.in_reach
            and facts.now - found[1] >= RANGE_STALL_SECONDS
        )

    def range_stalls(self, p: Pricing, key: tuple, chosen: Act, loot: Loot) -> None:
        """RANGE_STALL_LIFT's memory over the looks: a retreat chosen while a progress move of the goal `key` is barred
        by PACK_RANGE_LANDED starts the stall (`range_stall`); another goal, anything in reach, a member of the pack on
        the character (the hop's own `why_back`), WAIT_LOST of the most life lost or an act that is no retreat or safe
        approach ends it. Kept through the goal's own moves the lift lets go, which its end would bar again."""
        if not RANGE_STALL_LIFT:
            self.range_stall = None
            return
        facts, look = p.facts, p.look
        on = herald_pack.why_back(p.here, herald_pack.members(look.hostiles), p.demons or ()) is not None
        said = chosen.reason if isinstance(chosen, Move) else None
        dancing = said is not None and (said.startswith(RANGE_STALL_MOVES) or (p.range_lifted and not said))
        found = self.range_stall
        if found is not None and (
            found[0] != key or facts.in_reach or on or not dancing or loot.life < found[2] - WAIT_LOST * loot.max_life
        ):
            found = None
        barred = any(
            isinstance(c.act, Move)
            and not c.retreat
            and not c.act.dodge
            and c.act.reason in ('', 'safe approach')
            and c.harm.barred == PACK_RANGE_LANDED
            for c in p.candidates
        )
        retreat = said is not None and said.startswith('retreating')
        if found is None and barred and retreat and not facts.in_reach and not on:
            found = (key, facts.now, float(loot.life))
        if p.range_lifted and found is not None and found[1] != self.range_said:
            self.range_said = found[1]
            LOG.info("Macro: safety: kept at range %.1f s with nothing in reach and nothing coming: the pack's landing "
                     'bar lifted for the way (RANGE_STALL_LIFT); %s', facts.now - found[1],
                     said or type(chosen).__name__)  # fmt: skip
        self.range_stall = found

    def dolls_waited(self, p: Pricing, key: tuple, chosen: Act) -> None:
        """DOLL_LAND's memory over the looks: since when the asked move to goal `key` has been barred by dolls with
        nothing in reach (`doll_wait`, lifted past dolls.PATIENCE: `patient`), and its line, said once a goal."""
        facts = p.facts
        barred = [
            c for c in p.candidates if isinstance(c.act, Move) and (c.harm.barred or '').startswith(dolls.LANDED)
        ]  # fmt: skip
        asked = any(
            isinstance(c.act, Move) and not c.retreat and not c.act.dodge and c.act.reason in ('', 'safe approach')
            for c in barred
        )
        if facts.in_reach or (self.doll_wait is not None and self.doll_wait[0] != key):
            self.doll_wait = None
        if asked and not facts.in_reach and self.doll_wait is None:
            self.doll_wait = (key, facts.now)
        said = ('patient', key) if p.patient else key
        if not (barred or p.patient) or said == self.dolls_said:
            return
        self.dolls_said = said
        if isinstance(chosen, Move):
            spot = chosen.step.spot
            how = 'a walk' if chosen.step.skill is None else 'a jump'
            gap = math.dist(p.here, spot)
            act = f'{how} of {gap:.0f} to ({spot[0]:.1f}, {spot[1]:.1f}), {chosen.reason or "toward the goal"}'
        else:
            act = f'{type(chosen).__name__} {getattr(chosen, "reason", "")}'.strip()
        if p.patient:
            LOG.info('Macro: safety: dolls: %s held %.0f s with nothing in reach: its landing is no longer barred; %s',
                     key[2], dolls.PATIENCE, act)  # fmt: skip
            return
        LOG.info('Macro: safety: dolls: %d landing%s near a live doll left out (%s); %s',
                 len(barred), '' if len(barred) == 1 else 's', key[2], act)  # fmt: skip

    def insisting(self, now: float, posted, key: tuple, asking: bool, running: bool) -> float:
        """Seconds the goal `key` has been asked for and blocked with no gap of 0.7 s; else 0."""
        if (
            asking
            and key == self.blocked_goal
            and now - self.last_press < 0.7
            and (running or posted.pressed_at > self.first_press)
        ):
            return now - self.blocked_since
        return 0.0

    def hold(self, p: Pricing) -> Held:
        """Holding here; in a fight where the build's draw pays (`weigh`), holding with the draw cast, as one act."""
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
            if drawn is not None and (self.draw_lands or not DRAW_CASTABLE):
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
        if REACH_BAR and not hold_harm.barred:
            near = p.reach_blows(p.here)  # standing within reach of blows that take the life (REACH_BAR)
            if near >= look.life:
                hold_harm = replace(hold_harm, barred=f'{REACH_SAID} ({near:.0f} of {look.life:.0f})')
        return Held(hold_harm, future, hold_seconds, hold_unstruck)

    def offered_stand(self, p: Pricing, fresh: bool, posted) -> None:
        """In a running fight, the stand its own look found (`offer`), priced as a firing stand against holding."""
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
        """While something is safe: up to ESCAPES_MOST strike stands (read models' places first, then the threat's
        geometry) whose `saving` may exceed `least` plus the walk, priced against holding (STEPPING)."""
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
        """Nothing is safe: retreats in reach of `keeper`'s hostile, then the escapes (`offered`), then the plain rays
        when none fits; last, holding (never past the veto) or, out of reach, standing idle (WAITING)."""
        facts, look, settings, here = p.facts, p.look, p.settings, p.here
        asked: list[Point] = []
        spread = RAISED_KEEP and facts.attacking and raised_fight(look)  # a kept place is for the strikes only
        if spread:
            # Before the clear ways, which would price a kept place as one of theirs, not kept (RAISED_KEEP)
            self.kept_retreats(p, held, asked, spread=True)
        if CLEAR_ESCAPES:
            # The ways farthest from every hostile first, late or not: a late look priced none (CLEAR_ESCAPES)
            for point in clearest(here, [m.at for m in look.hostiles], p.footed if CLEAR_FOOTING else None):
                p.retreat_to(point, asked)
        if bolts.READ_THROWS:
            # Out of the read throwers' reach (`out_of_throws`)
            for point in out_of_throws(here, look, p.footed if CLEAR_FOOTING else None):
                p.retreat_to(point, asked)
        threat = held.harm if held.harm.by else held.ahead
        if not spread:
            self.kept_retreats(p, held, asked)
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
        # Fighting in place may be the least-harm escape.
        if facts.in_reach and facts.attacking and veto(held.harm, look.life, settings) is None:
            # Weighed against the retreats over the escape horizon, as they are (ESCAPE_SAME_SPAN)
            fought = replace(held.ahead, barred=held.harm.barred) if ESCAPE_SAME_SPAN else held.harm
            p.candidates.append(Candidate(Hold(facts.goal), held.seconds, fought, True, held.unstruck, True))
        elif not (facts.in_reach and facts.attacking):
            idle = harm(look, here, settings.horizon, p.hands, settings)
            p.candidates.append(Candidate(NoWay(WAITING), math.inf, idle, True))

    def moving(self, hostile: Sequence[Monster], now: float) -> frozenset[int]:
        """The hostiles seen moved within MOVED_SECONDS (MOVED_ACTIVE): a place MOVED_UNITS or more from the last
        look's. The places kept for the next look."""
        moved: dict[int, tuple[Point, float]] = {}
        found = set()
        for m in hostile:
            at = (m.x, m.y)
            known = self.moved.get(m.unit_id)
            since = -math.inf if known is None else known[1]
            if known is not None and math.dist(known[0], at) >= MOVED_UNITS:
                since = now
            moved[m.unit_id] = (at, since)
            if MOVED_ACTIVE and now - since <= MOVED_SECONDS:
                found.add(m.unit_id)
        self.moved = moved
        return frozenset(found)

    def closing(self, hostile: Sequence[Monster], now: float) -> dict[int, float]:
        """Units a second each hostile was seen to move (OBSERVED_SPEED): from its place SPEED_LEAST s or more ago,
        within SPEED_SECONDS, to now (a frame's half-unit steps make a shorter span's speed noise). The places kept."""
        found: dict[int, float] = {}
        trails: dict[int, list[tuple[float, Point]]] = {}
        for m in hostile:
            at = (m.x, m.y)
            trail = [(t, p) for t, p in self.trails.get(m.unit_id, ()) if now - t <= SPEED_SECONDS]
            if not trail or trail[-1][0] < now:
                trail.append((now, at))
            trails[m.unit_id] = trail
            old = next(((t, p) for t, p in trail if now - t >= SPEED_LEAST), None)
            if OBSERVED_SPEED and old is not None:
                found[m.unit_id] = math.dist(old[1], at) / (now - old[0])
        self.trails = trails
        return found

    def kept_retreats(self, p: Pricing, held: Held, asked: list[Point] | None = None, spread: bool = False) -> None:
        """The retreats that keep `keeper`'s hostile in strike reach and line (`keeping`); `spread`: with the harm
        spread, the hostile that brings the most of it (RAISED_KEEP)."""
        threat = held.harm if held.harm.by else held.ahead
        ender = keeper(p.look, p.seen, threat, spread=spread)
        if ender is None:
            return
        at = p.seen.foes[ender].at
        asked = [] if asked is None else asked
        for index, point in enumerate(keeping(p.here, at, p.attack.reach)):
            if index >= 2 and p.clock.late():
                break
            p.retreat_to(point, asked, at)

    def raised_keep(self, p: Pricing, look: Look) -> bool:
        """RAISED_KEEP: an aura-raised fight where something fits the life, but no act save a retreat does, and no
        retreat priced keeps a hostile in reach."""
        if not (RAISED_KEEP and raised_fight(look) and p.facts.attacking):
            return False
        candidates = p.candidates
        if any(p.feasible(c) and not c.retreat for c in candidates):
            return False
        return not any(c.keeps for c in candidates)

    def remember(self, chosen: Act, look: Look, here: Point, asking: bool, key: tuple, now: float, posted) -> None:
        """Note the acts stepped across (`stepped`) and whether the asked goal stays blocked (`insisting`); the barred
        Teleport spots lapse. The Teleports that cast nothing are counted where they are pressed (`hopped`)."""
        self.duds = {spot: until for spot, until in self.duds.items() if now < until}
        if (
            isinstance(chosen, Move)
            and chosen.step.skill == TELEPORT
            and math.dist(here, chosen.step.spot) > BOUNCE_NEAR
        ):
            last = self.left_at
            if last is None or math.dist(last[1], chosen.step.spot) > DUD_UNITS:  # a new hop, not the same one again
                self.left_at = (here, chosen.step.spot, now)
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

    def hopped(self, chosen: Act, here: Point, now: float) -> None:
        """The act the pursuit makes (`chosen`, hunting/moves.py `pursue`): a Teleport to one spot pressed again and
        again with the character still: past DUD_HOPS presses over DUD_AFTER s the press casts nothing (a spot the
        window does not show, game 30 21:36:45), and the spot is barred. Another act made starts the count again; a
        look that makes none says nothing of the press and leaves it (2026-10-26, cast-nothing-findings.md)."""
        self.duds = {spot: until for spot, until in self.duds.items() if now < until}
        if not isinstance(chosen, Move) or chosen.step.skill != TELEPORT:
            self.hops = None
            return
        spot, last = chosen.step.spot, self.hops
        if last is None or math.dist(last[0], spot) > DUD_UNITS or math.dist(last[1], here) > STILL_UNITS:
            self.hops = (spot, here, 1, now)
            return
        looks = last[2] + 1
        self.hops = (last[0], last[1], looks, last[3])
        if looks >= DUD_HOPS and now - last[3] >= DUD_AFTER:
            self.duds[last[0]] = now + DUD_SECONDS
            self.hops = None
            LOG.info('Macro: safety: Teleport to (%.1f, %.1f) pressed %d times in a row over %.1fs, the character '
                     'still at (%.1f, %.1f): the spot is dropped for %.0fs', last[0][0], last[0][1], looks,
                     now - last[3], here[0], here[1], DUD_SECONDS)  # fmt: skip

    def over(self, now: float, took: float, budget: float, laps: dict[str, float], chosen) -> None:
        """Log a look over OVER_BUDGET times its time with its three costliest stages, at most once in SAID_EVERY
        seconds, counting the ones in between."""
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
        """The build's draw weighed onto the DRAW_TARGETS harm sources, the best gain and DRAW_LEADERS leaders: life
        saved at kappa plus the fight's gain, less the cast; kept per unit in `draws` (read by `priced`). The best
        when it pays, else None. `pressed`: holding without it is over budget.

        Life saved = `Draw.turns` of the blows the pack within `Draw.pack` would deal with no companion about, from
        the companions' landing on, less the cast's exposure (rca/2026-10-14/death-mark-engage.md §4)."""
        draw = self.draw
        if draw is None or not self.sendable:
            return None
        sent = tuple(index for index, _ in self.sendable)
        # Gain counts only from companions idle now; one already striking clears as fast where it is.
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
        """The draw's prices while fresh (DRAW_FRESH), for build.py `BuffFacts.draws`; else None."""
        if self.draws is None or not 0.0 <= now - self.drawn_at <= DRAW_FRESH:
            return None
        return self.draws

    def offered(self, here: Point, look: Look, priced) -> list[tuple[Point, str, bool]]:
        """Escape places as (place, why, dodge): the read models' (a dodge while their missiles fly), the ground's,
        then the threat's geometry; deduplicated by ESCAPE_SAME."""
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
        if harm_module.BOLTS_IN_FLIGHT and look.missiles:
            # Out of the lane of the bolts coming at the character (combat/bolts.py `dodges`), a dodge
            kinds = {h.unit: shot_kinds(h.txt) for h in look.hostiles}
            flying = [(m[1], m[2]) for m in look.missiles if len(m) > 3 and m[3] in kinds.get(m[0], ())]
            found.extend((point, BOLT_DODGE, True) for point in bolts.dodges(flying, here))
        found.extend((point, AWAY, False) for point in self.escapes(here, look, priced))
        unique: list[tuple[Point, str, bool]] = []
        for point, why, dodge in found:
            if all(math.dist(point, other) >= ESCAPE_SAME for other, _, _ in unique):
                unique.append((point, why, dodge))
        return unique

    def escapes(self, here: Point, look: Look, priced) -> list[Point]:
        """Escape places from the threat's geometry, likeliest first: away from its harm-weighted centre (near, far,
        turned), back along the trail, behind the nearest companion (a monster goes for the nearest). Empty with no
        hostile about."""
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

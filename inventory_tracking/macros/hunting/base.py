"""The level run's constants and helpers (macros/hunt.py and its parts in macros/hunting/)."""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from inventory_tracking.combat import pack as herald_pack
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import ATTACKABLE_FLAG, NO_OWNER
from inventory_tracking.game.records import Monster, Thing, World
from inventory_tracking.levels.model import Room, Target
from inventory_tracking.levels.route import passable, room_at
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.goals import (
    CLEAR_WAY,
    REACH,
    Goal,
)
from inventory_tracking.macros.movement import WALKS, WARPS
from inventory_tracking.macros.pursuit import (
    Act,
    Pursuit,
)
from inventory_tracking.macros.routines import (
    TOWN_NPCS,
)
from inventory_tracking.macros.skills import (
    TELEPORT,
    skill_name,
)
from inventory_tracking.macros.teleport import (
    REPRESS_SECONDS,
    entry_stand,
    scaled,
)
from inventory_tracking.macros.travel import (
    Point,
)
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, STAND, Script
from inventory_tracking.routes.progress import Progress
from inventory_tracking.terror.tracker import BARRICADES, UNKILLABLE


# monstats.txt hydra1-3: the Council's cast fire heads, which never die: not hostiles
HYDRAS = frozenset((351, 352, 353))
# monstats.txt tentacle1-3, tentaclehead1-3: Water Watchers under the water, unseen and harmless there (the player,
# 2026-10-19: "try to attack mobs that aren't visible and don't attack us at all")
SUBMERGED = frozenset(range(258, 264))
# monstats.txt MonType `vulture` (combat/data/tables.json): the blades pass through them in the air (modes AIRBORNE)
VULTURES = frozenset((110, 111, 112, 113, 608))
AIRBORNE = frozenset((1, 8))
# What the game lets be struck now: a monster whose flag word reads the "can be attacked" bit clear (game/layout.py
# ATTACKABLE_FLAG) is no hostile. Flayer Jungle, 16:54:56 on 2026-10-21 (the player: "we're often struggling with
# trying to kill enemies for extended periods of time, but actually we're not even hitting them"): an elite Slime
# Prince submerged in the bog (mode 14, flags 0x30000001) took 63 casts in 23.7 s, 80 s of strikes at submerged frogs
# that day (rca/2026-10-21/no-hits-findings.md; the design of rca/2026-10-19/untargetable-findings.md §3). False: the
# flag word is not looked at.
ATTACKABLE = True
# The stopgap when the flag word is unread (a replay's frames, a synthetic monster): monstats.txt frogdemon1-3 (Swamp
# Dweller, Bog Creature, Slime Prince) in mode 14, their Submerge (Sk1mode seq_froghidden), are no hostile
FROGS_SUBMERGED = True
FROGS = frozenset((247, 248, 249))
FROG_HIDDEN = 14  # monster mode SQ
FIRST_STRIKE_SECONDS = 0.3  # the held strike with no cast seen yet: the mark and sigil wait no longer
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to (as NEAR_WARP)
SAID_AGAIN = 1.2  # seconds before a held key whose act stays the strike hears its reason again (`tell`)
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
MOO_MOO_FARM = 39  # levels.txt: the Secret Cow Level
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives
# A look slower than STALE_LOOK has its move or use dropped (`Hunter.stale`): above the 0.24 s median look gap
# (rca/2026-10-14/run-2040-findings.md §2.1). STALE_MOVED: units the character may have moved since a second slow
# look in a row for its act still to be made.
STALE_LOOK = 0.3
STALE_MOVED = 2.0
# 2026-10-23 (rca/2026-10-23/realtime-2-findings.md §2): the safety's escape (a retreat or a dodge, moves.py
# `danger_act`) older than STALE_LOOK is made, not dropped, when the newest look still has the character within
# STALE_MOVED of where the act's look saw it: a danger look prices up to DANGER_SECONDS (0.2 s, macros/safety.py), so
# with the reads after it the first escape was dropped by construction (the death of 18:57:43: the retreat dropped
# 0.30 s old, the next look's made 0.36 s old, 0.41 s later under hits). Progress acts are still dropped. False: as
# before.
STALE_DANGER_KEPT = False
# 2026-10-23: one read of the worn staff for a whole judge (hunting/laps.py `staff_once`): each candidate the safety
# prices read it again (travel.py `move_facts`: 10-35 walks of the item table in a heavy look, 2-4 ms each before any
# GIL wait). It changes only by an act, and a judge makes none. False: read at each ask.
STAFF_ONCE = True  # on 2026-10-23 ~22:00: realtime-2 gate no worse (2440 plays + slow host k 1 and 1.5)
# 2026-10-23 (rca/2026-10-23/realtime-3-findings.md): one loot read for a whole judge (hunting/laps.py `loot_once`): the
# goal's drops (choice.py, sweep.py, shrines.py) and the safety's life and belt (judging.py `safety_priced`) read it
# apart, 4.9/9.7 ms each live (FRAMES on), ~15 a second. One judge prices from one read, the nearest to its look; the
# pursue's own read after the judge stays fresh. False: read at each ask.
LOOT_ONCE = True  # on 2026-10-24 ~09:50: realtime-3 gate passes (one loot read a judge)
# 2026-10-23: the act queue's parts (hunting/laps.py `LapBook`): an act whose first input came ACT_LAPS_OVER or more
# after its look is said with its parts, at most once a ACT_LAPS_SAID seconds, and every ACT_LAPS_EVERY seconds the
# parts' p50/p90 over the acts since. Measurement only: no decision changes. False: nothing timed.
ACT_LAPS = True  # on 2026-10-23 ~22:00: realtime-2 gate no worse (2440 plays + slow host k 1 and 1.5)
ACT_LAPS_OVER = 0.15
ACT_LAPS_SAID = 1.0
ACT_LAPS_EVERY = 60.0
# 2026-10-24 (rca/2026-10-24/realtime-4-findings.md): the judge's own thread CPU beside its wall time in the act
# queue's lines ('judge 374 (cpu 40; priced ...'): a judge whose wall is far over its CPU waited for the GIL (another
# thread of the service ran), one near it computed. Measurement only. False: wall time only, as before. On 10-24 12:30.
ACT_CPU = True
# A fight let go for the key's act (`key_asks`) makes that act at the mode's next look, not a fresh judgement of it:
# the two looks disagreed near the arbiter's commitment line, so the strike was let go and pressed again (game 30,
# 2026-10-19: 14 of 228 yields struck again; rca/2026-10-19/game30-run-findings.md S4). Taken within YIELD_FRESH of
# its look, with the character within YIELD_MOVED of where it stood, the press and the life unchanged. False: the next
# look judges again, as before.
YIELD_TAKES = True
YIELD_FRESH = STALE_LOOK
YIELD_MOVED = 1.0
# A route's boss fight reached by its mark (or where it was last seen) with no boss there: after MARK_WAIT seconds of
# "nothing in reach here yet" the stage is given up on that level for the game (`empty_mark`): a run of the agenda
# explores the level for it (`wayless`, COVER), any other run ends. 22:49:08-53 on 2026-10-19: 45 s at Khalim's Brain
# with Witch Doctor Endugu never in the unit table, then the no-move watchdog left the game. Not for a boss the game
# brings to its place later (COMES_TO_ITS_MARK: Diablo, 15.6 s after the last seal, game 30). False: waited as before.
EMPTY_MARK_GOES_ON = True
MARK_WAIT = 3.0
# Seconds a seek of a boss not known yet stands with nothing in reach before its stage is given up the same way: the
# Throne of Destruction at 04:44:37-04:45:22 on 2026-10-20, "seek Lister the Tormentor: nothing in reach here yet"
# with no living hostile in the read, until the no-move watchdog left the game. Over the gap between two waves.
SEEK_WAIT = 20.0
COMES_TO_ITS_MARK = frozenset(('Diablo',))
# Seconds a route's goal may have no way once its level was explored for it (`wayless`) before the run ends
NO_WAY_ENDS = 8.0
NO_WAY_TO = 'no way to '  # how such a run's end begins (runner.py `_run_over`: the way on is dropped)
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
# World units: a boss attack mode goes to by itself (pursuit.py `decide`); farther goals are KP_1's and KP_4's
# (the player, 2026-10-15: "only nearby"; run-2040-findings.md §5)
ALONE_BOSS_UNITS = 2 * SIGHT
# The sweep after a step asked for goes on by itself until nothing hostile is within SWEEP_UNITS, the player moves,
# FOLLOW_STEPS are taken or FOLLOW_SECONDS pass with no step.
FOLLOW_STEPS = 12
FOLLOW_SECONDS = 8.0  # since the press or the sweep's last step
BOSS_MARK_UNITS = 60.0  # world units from a level's mark: a boss or super unique this near is the one it marks
GATHER_CLEAR = 12.0  # world units: no hostile this near the character or a drop when the sweep stops for it
HOLD_SIGHT = 40.0  # world units: a valuable this near that the sweep does not take is stayed by
HOLD_UNITS = 25.0  # the sweep's own steps end no further than this from it
GATHER_CHECK = 0.3  # seconds between two looks of the sweep for something to pick up
# Seconds of Teleport within which the KP_6 loop's run takes a valuable beyond PICK_NEAR walked (`on_the_way`; the
# player, 2026-10-18: "we left Ko rune on ground and moved away"): at 84 units/s of hops, all a read reaches.
# Without Teleport the walked PICK_NEAR stays.
LOOP_PICK_SECONDS = 2.5
FAR_JUDGED = 0.5  # seconds a far valuable's Teleport reach is judged for (`on_the_way`): the navigator's eta is dear
SHACK_TRIES = 2  # times the KP_6 loop's run tries one of a shack's containers (`shack_goal`)
# A full clear opens a closed glowing super chest (objects.txt 397) within SUPER_NEAR before the rest of the level,
# left after SUPER_TRIES (the player, 2026-10-18: "in auto mode - we should open at least glowing superchests")
SUPER_NEAR = 60.0
SUPER_TRIES = 3
# Tries of one route chest before it is left as gone (route.py `note_empty`): one never under the pointer was tried
# 46 times until the watchdog (2026-10-18 01:37:56). A chest opens at the first or second try.
ROUTE_USE_TRIES = 8
# A move that left the character where it was: its spot and any within DEAD_END_NEAR are not moved to for
# DEAD_END_SECONDS (`barred`)
DEAD_END_SECONDS = 4.0
DEAD_END_NEAR = 3.0
# A move failing again within DEAD_END_NEAR of a spot failed at in the last STUCK_WINDOW seconds: stuck, and the
# loop may take the staff's Teleport for STUCK_SECONDS whatever the gold (`stuck`; 2026-10-17 21:49:56)
STUCK_WINDOW = 20.0
STUCK_SECONDS = 10.0
# Units: the KP_6 loop's run clicks an object from this near and hops nearer first; from further the game walks
# there and the open can outrun the act's 1.5 s (rca/2026-10-16/loop-chests-findings.md §3)
OPEN_NEAR = 12.0
# Units: a shack's other container is clicked from this near when the character stands by the one just opened
# (`paired`), not hopped to: 0.72 s against 1.75 s (2026-10-17; the player: "we teleport into center of it and then
# go to weapon stand and travel back to chest")
PAIR_NEAR = 18.0
PAIR_UNITS = 14.0  # a container this near the one opened is its shack's other
PAIR_BY = 4.0  # the character this near the one opened stands by it


# Seconds the monsters covering a goal's act (teleport.py `Covered`) stay its first fight while any lives
# (goals.py `first_fight`)
BLOCK_SECONDS = 15.0
GATHER_SECONDS = 3.0  # a pickup step's time, added to the sweep's own so that it goes on after
FOLLOW_CHECK = 0.7  # seconds between two looks for a better place while a fight goes on
SWEEP_UNITS = 60.0  # hostiles this near are gone to
STAND_OFF = 14.0  # units short of the nearest hostile a stride toward it ends (the player engages at 12 to 14)
# A place a fight is left for must be worth this many times the current one (with nothing in reach: stance.CAMP_GAIN)
SWEEP_GAIN = 2.0
RUN_IN_PLACE = 1.5  # seconds a character in a walk or run mode may not move before it counts as stuck
WAIT_LOG_SECONDS = 3.0  # between log lines on what attack mode is waiting for
# A place a step failed for is shunned for SHUN_SECONDS; STEP_FAILURES failures in a row end the sweep.
SHUN_UNITS = 6.0
SHUN_SECONDS = 10.0
STEP_FAILURES = 2
# A monster whose life UNTOUCHED_CASTS casts left unchanged (in the air, burrowed, immune) is no hostile for
# UNTOUCHABLE_SECONDS, then tried again.
UNTOUCHED_CASTS = 4
# The casts counted for it are the ones made, chained ones too (combat/controller.py `CastWatch.chained`): the casts
# seen to begin were 40 % of the casts made on 2026-10-21, and "4 casts" took 10 to 63 (rca/2026-10-21/
# no-hits-findings.md §4). False: the casts seen to begin (`CastWatch.casts`), as before. Off from 2026-10-21 18:10:
# live, 14 leaves in the first 12 min after the 17:58 restart against 1 in the 76 min before, of monsters losing life
# (the monster 129 2616831891: 128/128 at 18:10:12, "takes no damage (55/128 after 4 casts)" at 18:10:14); the
# NO_HARM_SECONDS floor catches the chained strikes that did nothing instead (no-hits-findings.md §8).
GUARD_COUNTS_HELD = False
# With the strike held and nothing in reach losing life for this many seconds, the monster the line goes through is
# left alone as one that takes no damage (`Hunter.unharmed`), a boss or the pursued fight's boss never (the
# coordinator's ruling, 2026-10-21: "leave THAT monster for a while, not the fight"). None: no floor.
NO_HARM_SECONDS: float | None = 3.0
# A fight goal whose monster no shot reaches from where the moves end (a wall between; the dolls' stand-off kept): its
# monster is left alone after this many seconds, as one that takes no damage (`judging.unshot`), so the goal goes on:
# the pickup it barred, the next hostile, the route's stage. Kurast Sewers 1, 17:51:43-17:52:29 on 2026-10-21: "the
# fight first (2 in the way): as near as a move ends, and nothing in reach", an Undead SoulKiller elite 22 away behind a
# wall, 45 s still and the game left (rca/2026-10-21/no-hits-findings.md §7). None: no leave.
UNSHOT_SECONDS: float | None = 3.0
# A fight goal out of reach goes to a firing spot (`firing_spots`) and stands on it: the way there ends on the spot, not
# the goal's stand-off short of it (a pickup's dolls are fought from 20: the spot 7 away was "as near as a move ends"
# and nothing moved), and a stand-off's spots at least that far from the monster (up to the rings' outer one) come
# first. False: the spot is gone to with the goal's own stand-off, as before.
FIRING_STAND = True
# Units along the line the pointer is tried at when an item's label lies under the aim (`off_labels`).
LABEL_SHIFTS = (0.0, 4.0, 8.0, -3.0, 12.0, -6.0)
LABEL_SECONDS = 0.5  # between two looks for a label under a pointer that stands
UNTOUCHABLE_SECONDS = 20.0
# A boss is never left alone so (`untouched`): for this long after its strikes did nothing, its fight counts only
# within the attack's engage ring (`nearing_only`)
NEARING_SECONDS = 6.0
# Units: with no hostile this near a level run is in the quiet: the whole upkeep between moves, and a low belt takes
# the potions near (`restock`)
QUIET_UNITS = CLEAR_WAY
ROOM_UNITS = 40.0  # a known hostile this much further than the nearest unexplored room still goes first
VANISH_UNITS = 25.0  # a remembered monster not among the live ones this near the character is not gone to again
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
HURT_SECONDS = 2.0  # after a loss of life the KP_6 loop's run may stand and strike (pursuit.py `arbitrate`)
# The field routine's quiet look (hunt.py `field_quiet`, loot/api.py `at_once`), stricter than the routine's own SIGHT:
# at 15:21:38 on 2026-10-20 it opened the inventory 1 s after a waypoint's arrival with hostiles near, a fight back
# cancelled it half way and the panels stayed open while the character was hit (game 6 of 20261020T115501Z-4b07df55)
AT_ONCE_CLEAR = 2 * SIGHT  # world units: no hostile read this near (60: twice the fight's sight)
AT_ONCE_SETTLE = 3.0  # seconds after a level's arrival (a waypoint, a portal, stairs): the first look's never
AT_ONCE_HURT = 3.0  # seconds after the character's life went down
OWN_TELEPORT_SECONDS = 5.0  # between reads of whether Teleport is the character's own (`Hunter.own_teleport`)
RUSH_UNMOVED = 1.5  # seconds with no move after which the loop's run fights what is in reach (blocking it)
TOUGH_POINTS = 40_000.0  # life points in reach from which a pack is worth the main weapons
HARD_SCORE = 4.0  # the threat score (terror/danger.py) of what is in reach from which it is, whatever its life
MAIN_AFTER = 1.0  # seconds after a step before the main weapons are swapped in for a fight
SWAP_RETRY_SECONDS = 5.0  # after a swap to the main weapons that did not come
INPUT_SECONDS = 1.0  # Echoing Strike on no input for this long (another skill selected) before it is a stopped fight
STRIKE_BACK_RETRY = 10.0  # seconds between two tries of the skill selection for the strike (`strike_back`)
MISSES_IN_A_ROW = 5  # fights that stopped one after another before attack mode gives up
IDLE_LOG_SECONDS = 3.0  # between log lines on what attack mode sees while nothing is in reach
# Navigation classes with no Teleport to spend (movement.py `Ways.means`): a far step goes by the class's own way
# (`class_step`)
NO_HOPS = frozenset((WARPS, WALKS))
# Times a casting delay is slept out before such a step: the look after the sleep may read it a tick short
PAUSES = 3
# The run mode (macros/runmode.py): a clearing goal (goals.py `clear_way`, `rest_of_level`) gone for CLEAR_SECONDS
# with no strike and no progress (`Travel.eta` down by PROGRESS_SECONDS), or with no way to it, is passed for
# PASS_SECONDS. A room has nothing to strike, hence the progress (rca/2026-10-14/run-1932-findings.md §1.2.1).
# Looks further apart than JUDGE_GAP with another goal's between do not count as time gone for it.
CLEAR_SECONDS = 10.0
ARRIVED_SECONDS = 2.0  # a place goal reached with no strike: passed sooner (choice.py `goes_on`, 2026-10-19)
PASS_SECONDS = 30.0
PROGRESS_SECONDS = 0.25
PROGRESS_LOOK = 1.0  # seconds between two askings of the way left to one clearing goal (`goes_on`)
JUDGE_GAP = 3.0
# Seconds a clearing goal left for another is not taken back while that other is still the run's (`Hunter.cleared`)
TAKE_BACK = 6.0
# The goals a run to its goal fights its way to (`Hunter.cleared`): a door to another level, a place, a stand.
WAYS = frozenset((ENTER, REACH, STAND))
REST_SECONDS = 1.0  # a full clear's look for the rest of the level (the tour's potential) is made this seldom
# The tour's stop a run goes to is kept while the tour still has it, until it is reached or passed, unless the tour's
# first stop is now under STOP_KEEP_SHARE of its way: 21:53:40-56 on 2026-10-19 (the Chaos Sanctuary) the run went to
# and fro between two stops 200 units apart four times, the first stop recomputed at every look (game30-run-findings.md
# S3). False: the tour's first stop at every look, as before.
KEEP_STOP = True
STOP_KEEP_SHARE = 0.5
# TZ leveling's run fights its way to a hostile in a striking mode (game/layout.py STRIKING_MODES) within CLEAR_WAY
# with a clear shot, not only to leaders: "don't waste time awaiting when mobs engage us and do it procatively" (the
# player, 2026-10-19 ~21:15). 21:05:24 on 2026-10-19: skeleton archers shot at the party from 25 away for 10 s while
# the run stood (rca/2026-10-19/tz-leveling-findings.md C4). False: leaders only, as before.
ENGAGE_STRIKERS = True
# A remembered monster this near is gone for before the tour's next room, one further off after the tour (the
# player, 2026-10-18: "we starts to go from one side to another back and forward"). About half a screen.
REMEMBERED_NEAR = 45.0
# A Herald's coming (rca/2026-10-17/herald-findings.md): a HERALD_OMEN missile (missiles.txt `heraldspawner`, 5.0 s)
# where a monster died; the Herald and its minions appear there as it ends (the player, 2026-10-17: "monitor when
# herald is about to appear ... and position us correctly"). While one is pending a full clear fights only within
# OMEN_NEAR of the spot, else stands OMEN_STAND from it on its own side. Missiles read every OMEN_LOOK s.
HERALD_OMEN = 737
OMEN_SECONDS = 8.0  # its 5 s and a margin for the Herald to show
OMEN_NEAR = 22.0
# The attack's reach (22) less a margin, so the pack is struck coming in (at the engage ring, 14, a tier 5 pack came
# up within 10 all at once: 2026-10-18 00:54:55)
OMEN_STAND = 20.0
OMEN_SLACK = 4.0  # a stand this near OMEN_STAND from the spot already is kept: no move
# The stand with a way out (2026-10-21, the player ~15:50: "another super-sketchy battle against bird that burned all
# mana, we were tanking most of T5 herald damage without being able to hit"; "make sure that we don't stuck or die";
# rca/2026-10-21/mana-burn-findings.md item 2). The pack's modifiers are not known before it shows, and a Mana Burn or
# Extra Fast pack (18.7 units a second at 15:46:12) is on the stand a second after it does: the stand is where a hop
# out lies behind it, away from the spot (`way_out`: WAY_OUT_UNITS beyond it in the level's rooms, the line between
# over no void wider than WAY_OUT_VOID tiles), turned round the spot by STAND_TURNS from the character's side when
# that one has none; once the pack shows, a draining one is kept at range by the safety (combat/threats/manaburn.py
# BURN_RANGE). False: the stand on the character's side whatever lies behind it, as before.
STAND_WAY_OUT = True
WAY_OUT_UNITS = 16.0  # a hop out (combat/threats/manaburn.py HOP_LENGTHS[0])
WAY_OUT_VOID = 1.0  # tiles of void the way out may cross (levels/route.py `passable`; a walk crosses none)
STAND_TURNS = (0.0, 30.0, -30.0, 60.0, -60.0, 90.0, -90.0)  # degrees round the spot from the character's side
OMEN_LOOK = 0.25
# Seconds of fighting a timed buff must last when the route's stage brings a boss (goals.py `boss_ahead`): renewed
# before it in the quiet (macros/buffs.py `lapsing`; run-1214-findings.md §3.4)
BOSS_AHEAD = 60.0

Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


@dataclass
class Bearings:
    """What a key's goal is named from besides the world (goals.py `goal_of`), handed in by the runner:
    the routes' progress, the level card's first mark, its marks by label, super uniques' and bosses'
    last-seen places by level."""

    progress: Progress | None = None
    card: Callable[[], Target | None] | None = None
    marks: Callable[[str], tuple[Point, ...]] | None = None
    supers: Callable[[int], list[Point]] | None = None

    def terror(self, area: int) -> bool:
        """Whether level `area` is a terror zone now (terror/tracker.py `terrorized`); False while unknown."""
        wanted = getattr(self.progress, 'wanted', None)
        return bool(wanted(area)) if wanted is not None else False

    def script(self, area: int) -> Script | None:
        """The route's script level `area` follows in this game (routes/progress.py `chosen`); None: no route."""
        chosen = self.progress.chosen(area) if self.progress is not None else None
        return chosen[1] if chosen is not None else None


@dataclass(frozen=True)
class Judged:
    """One look of the pursuit: what was decided, for which goal, and the place the navigator was asked for;
    the mailbox as the look read it, and whether its press was fresh at the look's clock."""

    act: Act
    goal: Goal | None
    place: Point | None
    posted: Pursuit | None = None
    pressed: bool = False


@dataclass
class Sweep:
    """The mode moving on its own after a pickup request with hostiles near: on while it has steps left
    and its last step or request is no older than FOLLOW_SECONDS."""

    steps: int = 0  # steps it may still take; 0: off
    until: float = -math.inf  # clock time it ends at unless a step or a request renews it
    looked: float = -math.inf  # clock time of its last look for a better place
    fails: int = 0  # steps that failed one after another
    shunned: list[tuple[Point, float]] = field(default_factory=list)  # places a step failed for, and when

    def start(self, now: float) -> None:
        self.steps, self.until, self.fails = FOLLOW_STEPS, now + FOLLOW_SECONDS, 0

    def end(self) -> None:
        self.steps = 0

    def spend(self, now: float) -> None:
        """One step is taken: counted, and the sweep goes on from it."""
        self.steps -= 1
        self.until = now + FOLLOW_SECONDS

    def due(self, now: float) -> bool:
        """Whether a fight under way should look for a better place now."""
        return self.steps > 0 and self.looked + FOLLOW_CHECK <= now <= self.until

    def forget(self, now: float) -> None:
        self.shunned = [(spot, at) for spot, at in self.shunned if now - at < SHUN_SECONDS]

    def shuns(self, spot: Point) -> bool:
        return any(math.dist(spot, left) < SHUN_UNITS for left, _ in self.shunned)

    def failed(self, now: float, walked: Point | None) -> None:
        """A step moved nothing; `walked` is where it was walked to, a place then left alone."""
        self.fails += 1
        if walked is not None:
            self.shunned.append((walked, now))
        if self.fails >= STEP_FAILURES:
            self.end()


def threat(run: Run) -> Callable[[Point, Point], int]:
    """How many hostiles stand within GATHER_CLEAR of the character or of a press's target (pickup.py
    `Threat`): presence, not what they could do."""

    def near(here: Point, spot: Point) -> int:
        return sum(
            1
            for monster in hostiles(run.world())
            if min(math.dist((monster.x, monster.y), here), math.dist((monster.x, monster.y), spot)) <= GATHER_CLEAR
        )

    return near


def passing_key(place: Point, unit: int | None, rooms: Sequence[Room] = ()) -> object:
    """What a clearing goal is judged by (`Hunter.cleared`): its monster, else its room (of `rooms`), else its
    place. Not a room's tile: that moves with the character (rca/2026-10-14/run-1932-findings.md §1.2.1)."""
    if unit is not None:
        return unit
    room = room_at(rooms, (place[0] / TILE_UNITS, place[1] / TILE_UNITS)) if rooms else None
    if room is not None:  # a large preset's 8 by 8 chunks are one room (`Room.block`, its whole bounds)
        return ('room', *(room.block or (room.x, room.y, room.width, room.height)))
    return (round(place[0]), round(place[1]))


@dataclass
class Judging:
    """How a clearing goal has gone (`Hunter.cleared`): seconds gone with no strike or progress (`idle`), the least
    way left seen (`best`, `Travel.eta`), the last judging look. Kept per goal key across other goals, so two goals
    taken in turn are still passed (run-1932-findings.md §1.2.1)."""

    idle: float
    best: float
    last: float
    checked: float = -math.inf  # the look that last asked the way left


def door_entry(card: Target | None) -> Point | None:
    """Where the character stands to click the card's door, world units (teleport.py `entry_stand`); None with none."""
    entry = entry_stand(card) if card is not None else None
    return scaled(entry) if entry is not None else None


def hostiles(world: World) -> list[Monster]:
    """Live monsters the hunt may strike: not owned, not allied, not townsfolk, scenery, a siege door
    or wall, a cast Hydra or a bird in the air, placed, and attackable now (`strikable`)."""
    return [
        m
        for m in world.monsters
        if m.owner == NO_OWNER
        and not m.ally
        and (m.x or m.y)
        and m.txt_id not in UNKILLABLE
        and m.txt_id not in HYDRAS
        and m.txt_id not in SUBMERGED
        and m.txt_id not in TOWN_NPCS
        and m.txt_id not in BARRICADES
        and not (m.txt_id in VULTURES and m.mode in AIRBORNE)
        and strikable(m)
    ]


def strikable(monster: Monster) -> bool:
    """Whether the game lets `monster` be struck now: its flag word's ATTACKABLE_FLAG (ATTACKABLE); with the word
    unread, anything but a frog demon submerged (FROGS_SUBMERGED)."""
    flags = monster.unit_flags
    if ATTACKABLE and flags is not None:
        return bool(flags & ATTACKABLE_FLAG)
    return not (FROGS_SUBMERGED and monster.txt_id in FROGS and monster.mode == FROG_HIDDEN)


def strike_input(run: Run, world: World, key_names, skill: int) -> tuple[tuple[str, ...], str]:
    """(what to hold, how to say it) for the strike `skill`: the right button when it holds it, else its
    skill key, else Shift+left. In controller mode its pad record (`Run.pad`): nothing to hold."""
    player = world.player
    assert player is not None
    if run.pad is not None:
        run.keys.update(key_names(world, (skill,)))  # Abort: on no pad record
        return (), f'pad {run.keys[skill]}'
    if player.right_skill == skill:
        return ('Button3',), 'right click'
    if skill in world.slots:
        try:
            run.keys.update(key_names(world, (skill,)))
            return (run.keys[skill],), f'key {run.keys[skill]}'
        except Abort as problem:
            if run.stops(problem):
                raise
            LOG.info('Macro: %s; trying the left mouse button', problem)
    if player.left_skill == skill:
        return ('Shift_L', 'Button1'), 'Shift+click'
    raise Abort(
        f'{skill_name(skill)} is on no skill key and on neither mouse button '
        f'(left {skill_name(player.left_skill)}, right {skill_name(player.right_skill)})'
    )


def paired(things: Sequence[Thing], thing: Thing, here: Point) -> bool:
    """Whether the character stands by an opened container (PAIR_BY) whose shack's other is `thing` (PAIR_UNITS)."""
    return any(
        other.unit_id != thing.unit_id
        and other.mode
        and math.dist((other.x, other.y), (thing.x, thing.y)) <= PAIR_UNITS
        and math.dist((other.x, other.y), here) <= PAIR_BY
        for other in things
    )


def act_window(step) -> float:
    """The seconds a priced move is given (`Hunter.priced_for`): its price, plus a Teleport's second press
    (REPRESS_SECONDS): ~5 % of Teleport keys cast nothing (rca/2026-10-17/teleport-not-cast-findings.md)."""
    return step.seconds + (REPRESS_SECONDS if step.skill == TELEPORT else 0.0)


def omen_distance() -> float:
    """Units from a Herald's omen spot the full clear waits at: PACK_OMEN_STAND with the pack tactic, else
    OMEN_STAND."""
    return herald_pack.PACK_OMEN_STAND if herald_pack.PACK_TACTIC and herald_pack.PACK_OMEN else OMEN_STAND


def way_out(spot: Point, stand: Point, rooms: Sequence[Room]) -> bool:
    """Whether a hop out lies behind `stand`, away from `spot` (STAND_WAY_OUT): the stand and the place WAY_OUT_UNITS
    beyond it in the level's rooms, the line between over no void wider than WAY_OUT_VOID tiles. True with no rooms
    known, or the stand on the spot."""
    away = math.dist(spot, stand)
    if not rooms or away < 1e-6:
        return True
    out = (
        stand[0] + (stand[0] - spot[0]) / away * WAY_OUT_UNITS,
        stand[1] + (stand[1] - spot[1]) / away * WAY_OUT_UNITS,
    )
    start, end = (stand[0] / TILE_UNITS, stand[1] / TILE_UNITS), (out[0] / TILE_UNITS, out[1] / TILE_UNITS)
    return (
        room_at(rooms, start) is not None
        and room_at(rooms, end) is not None
        and passable(rooms, start, end, WAY_OUT_VOID)
    )


def omen_stand(spot: Point, here: Point, rooms: Sequence[Room] = ()) -> Point:
    """Where a full clear waits for a Herald coming to `spot` (HERALD_OMEN): OMEN_STAND from it on the character's
    side (combat/pack.py PACK_OMEN_STAND, 24, with the pack tactic: the player, 2026-10-21 ~10:00, "the omen stand at
    24"); where it stands already when that is within OMEN_SLACK of it. With STAND_WAY_OUT and the level's `rooms`, a
    stand with a hop out behind it (`way_out`): the first of STAND_TURNS round the spot that has one, else the
    character's side as before."""
    stand = omen_distance()
    away = math.dist(spot, here)
    if abs(away - stand) <= OMEN_SLACK and (not STAND_WAY_OUT or way_out(spot, here, rooms)):
        return here
    bearing = math.atan2(here[1] - spot[1], here[0] - spot[0]) if away >= 1e-6 else 0.0

    def at(turn: float) -> Point:
        angle = bearing + math.radians(turn)
        return (spot[0] + stand * math.cos(angle), spot[1] + stand * math.sin(angle))

    if STAND_WAY_OUT and rooms:
        found = next((at(turn) for turn in STAND_TURNS if way_out(spot, at(turn), rooms)), None)
        if found is not None:
            return found
    if away < 1e-6:
        return (spot[0] + stand, spot[1])
    return (spot[0] + (here[0] - spot[0]) * stand / away, spot[1] + (here[1] - spot[1]) * stand / away)

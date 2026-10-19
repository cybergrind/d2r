"""The level run's constants and helpers (macros/hunt.py and its parts in macros/hunting/)."""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from inventory_tracking.common import LOG
from inventory_tracking.levels.model import Room, Target
from inventory_tracking.levels.route import room_at
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.game.layout import NO_OWNER
from inventory_tracking.macros.game.records import Monster, Thing, World
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


# monstats.txt hydra1-3 (AI Hydra, no life of their own): the fire heads the Council casts, which never die
# and are left out of the hostiles
HYDRAS = frozenset((351, 352, 353))
# monstats.txt tentacle1-3 and tentaclehead1-3 (258-263): the Water Watchers in the water (Great Marsh, the act 3
# rivers), unseen under it, untouched there and harmless but at its edge. The terror zone run struck each 4 times
# (~8 s) before `untouched` left it alone, ~25 s of one fight (09:04:24-55 on 2026-10-19; the player: "in marsh we can
# stuck and try to attack mobs that aren't visible and don't attack us at all"): left out of the hostiles
SUBMERGED = frozenset(range(258, 264))
# monstats.txt MonType `vulture` (vulture1-5: combat/data/tables.json): the birds the blades pass through in the air
# (AIRBORNE: their modes 1 and 8); on the ground they are fought like other monsters
VULTURES = frozenset((110, 111, 112, 113, 608))
AIRBORNE = frozenset((1, 8))
FIRST_STRIKE_SECONDS = 0.3  # the held strike this long with no cast seen yet: the mark and sigil wait no longer
WALK_CLICKS = 2  # clicks for one walk to a firing spot
WALK_UNITS = 10.0  # a firing spot this near, over clear ground, is walked to, not teleported to (as NEAR_WARP)
# A held key whose act stays the strike hears its reason again after this many seconds (`tell`): the card
# answers the presses (I6) without a line at every press of a mashed key.
SAID_AGAIN = 1.2
FIGHT_SECONDS = 60.0  # one fight ends here at the latest; attack mode looks again right after
POLL = 0.1  # seconds between looks in attack mode while nothing is fought
MOO_MOO_FARM = 39  # levels.txt: the Secret Cow Level
FRAME = 0.04  # seconds between looks during a fight: one game frame, so a move of the player's is yielded to at once
DECIDE_SECONDS = 0.12  # between two askings of the policy while its monster lives
# A look of the pursuit's that took longer than this has its move or use dropped (`Hunter.stale`): two and a half
# askings of the policy (DECIDE_SECONDS), above the clean game's look gap with a hostile near (0.24 s at the median,
# rca/2026-10-14/run-2040-findings.md §2.1), some 3 units of a run. STALE_MOVED: units the character may stand from
# where a second slow look in a row saw it for its act to be made (the host slow, the game the same).
STALE_LOOK = 0.3
STALE_MOVED = 2.0
SIGHT = 30.0  # world units: hostiles further off are not part of the decision
# World units: a boss attack mode goes to by itself (no level run, no fresh press: pursuit.py `decide`), as far as a
# boss standing within SIGHT of a hostile the fight sees can be: the Vizier's stall (57.4 off, his pack 19 to 51
# off; kp4-findings.md) is in it, Izual by the card's mark after a level run ended on a level change (342 off;
# run-2040-findings.md §5, the player's ruling 2026-10-15: "only nearby") is not: farther goals are KP_1's and KP_4's.
ALONE_BOSS_UNITS = 2 * SIGHT
# The sweep after a step asked for: the mode goes on stepping by itself, to a better place whenever
# there is one and toward the nearest hostile when nothing is in reach, until nothing hostile is within
# SWEEP_UNITS, the player moves by hand, FOLLOW_STEPS are taken or FOLLOW_SECONDS pass with no step.
FOLLOW_STEPS = 12
FOLLOW_SECONDS = 8.0  # since the press or the sweep's last step
BOSS_MARK_UNITS = 60.0  # world units from a level's mark: a boss or super unique this near is the one it marks
GATHER_CLEAR = 12.0  # world units: no hostile this near the character or a drop when the sweep stops for it
HOLD_SIGHT = 40.0  # world units: a valuable this near that the sweep does not take is stayed by
HOLD_UNITS = 25.0  # the sweep's own steps end no further than this from it
GATHER_CHECK = 0.3  # seconds between two looks of the sweep for something to pick up
# The KP_6 loop's run takes a valuable it reads beyond PICK_NEAR walked when Teleport brings it there within these
# seconds by the navigator (`on_the_way`; the player, 2026-10-18 18:24: "before running the level -- you must be sure
# that loot is visible, we left Ko rune on ground and moved away"). A hop makes 84 units a second (26 in 0.31 s), so
# 2.5 s is 210 units of hop way: all the read reaches (126 units off it was out of it, 18:22:19 on 2026-10-18). The Ko
# Rune lay 34.5 straight and 117 walked behind the character (a wall between: the hops had crossed it), and the run
# went on. With no Teleport in the moves the walked PICK_NEAR stays (the lava's Ith Rune: 26 straight, 226 walked).
LOOP_PICK_SECONDS = 2.5
FAR_JUDGED = 0.5  # seconds a far valuable's Teleport reach is judged for (`on_the_way`): the navigator's eta is dear
SHACK_TRIES = 2  # times the KP_6 loop's run tries one of a shack's containers (`shack_goal`)
# A full clear opens a closed glowing super chest (objects.txt 397) streamed within SUPER_NEAR before the rest of the
# level (the player, 00:19 on 2026-10-18: "we're not always opening target chest on all levels that has it (like cave
# 2 - I had to open it by hands). in auto mode - we should open at least glowing superchests"): the route's chest stage
# came only after the whole level, and a level whose route has none never opened one. Left after SUPER_TRIES tries.
SUPER_NEAR = 60.0
SUPER_TRIES = 3
# Tries of one route chest after which it is left as if gone (route.py `note_empty`): one never under the pointer, the
# same other object at every aim, was tried 46 times in 47 s until the loop's watchdog left the game (01:37:56-01:38:42
# on 2026-10-18, Lower Kurast). A chest opens at the first or second try; one covered by a monster has it fought first
ROUTE_USE_TRIES = 8
# A move that left the character where it was ("the character did not move"): its spot, and any within DEAD_END_NEAR
# units, is not moved to for DEAD_END_SECONDS (`barred`); the next look takes another way, goal or act
DEAD_END_SECONDS = 4.0
DEAD_END_NEAR = 3.0
# A move that fails again within DEAD_END_NEAR of a spot failed at in the last STUCK_WINDOW seconds: the run is stuck,
# and the loop's moves may take the staff's Teleport for STUCK_SECONDS whatever the gold (`stuck`): 21:49:56-21:50:40 on
# 2026-10-17 one Blade Warp 15 units east "did not move" eight times, the spot barred 4 s each with no other act (no
# walked way grown, Teleport off for the gold), until the 45 s watchdog left the game
STUCK_WINDOW = 20.0
STUCK_SECONDS = 10.0
# Units: the KP_6 loop's run clicks an object from this near, and hops nearer first. The games of 2026-10-16
# (rca/2026-10-16/loop-chests-findings.md §3): an open took 0.23-0.4 s from 2 to 6 units, 0.68 s from 14, 1.4 s from
# 20 (the game walks the character there), and from 18 to 23 units twice ran out of the act's 1.5 s; a Teleport hop
# lands 0.3-0.4 s after its key.
OPEN_NEAR = 12.0
# A shack's other container is clicked from this near when the character stands by the one it just opened (`paired`):
# chest and rack stand 12 apart on one row, and from beside one the other was 13-17 away, hopped to: 1.75 s from the
# first open to the second (81 times on 2026-10-17), against 0.72 s where it was clicked and walked to (160). The
# player, 21:50: "we teleport into center of it and then go to weapon stand and travel back to chest"
PAIR_NEAR = 18.0
PAIR_UNITS = 14.0  # a container this near the one opened is its shack's other
PAIR_BY = 4.0  # the character this near the one opened stands by it


# Seconds the monsters the hands found in the way of a goal's act (teleport.py `Covered`) stay the fight that
# comes first for that goal, while any of them lives (goals.py `first_fight`)
BLOCK_SECONDS = 15.0
GATHER_SECONDS = 3.0  # a pickup step's time, added to the sweep's own so that it goes on after
FOLLOW_CHECK = 0.7  # seconds between two looks for a better place while a fight goes on
SWEEP_UNITS = 60.0  # hostiles this near are gone to
STAND_OFF = 14.0  # units short of the nearest hostile a stride toward it ends (the player engages at 12 to 14)
# A place a fight is left for, asked for or not, has to be worth this many times where the character stands
# (with nothing in reach: stance.CAMP_GAIN); the worth counts the monsters where they stand, not where they come
SWEEP_GAIN = 2.0
# A character in a walk or run mode that has not moved for this many seconds is stuck, not going anywhere:
# the mode stops waiting for it.
RUN_IN_PLACE = 1.5
WAIT_LOG_SECONDS = 3.0  # between log lines on what attack mode is waiting for
# A place a step failed for is shunned for SHUN_SECONDS, and STEP_FAILURES failures in a row end the sweep.
SHUN_UNITS = 6.0
SHUN_SECONDS = 10.0
STEP_FAILURES = 2
# The seek order: the unexplored room is the first stop of a tour of all unexplored rooms (macros/tour.py).
# A remembered monster no longer where it was seen (within VANISH_UNITS of the character, not among the live
# ones) is not gone to again.
# A monster the strikes do nothing to (seen by its life, not by type: a bird in the air, something burrowed, an
# immune) is left alone: once UNTOUCHED_CASTS casts show its life unchanged, it is no hostile for
# UNTOUCHABLE_SECONDS (not fought, swept or sought toward), then tried again.
UNTOUCHED_CASTS = 4
# Units along the line the pointer is tried at when an item's label lies under the aim (`off_labels`).
LABEL_SHIFTS = (0.0, 4.0, 8.0, -3.0, 12.0, -6.0)
ITEM_UNIT_TYPE = 4  # in the record of the unit under the pointer
LABEL_SECONDS = 0.5  # between two looks for a label under a pointer that stands
UNTOUCHABLE_SECONDS = 20.0
# A boss is never left alone so (`untouched`): for this long after its strikes did nothing, the run's fight with it
# is near enough only within the attack's engage ring, and it counts as in reach only there (`nearing_only`)
NEARING_SECONDS = 6.0
# Units: with no hostile this near, a level run is in the quiet: the whole upkeep is asked between its moves, and a
# belt low on potions takes the ones lying near before the goal (`restock`). goals.py CLEAR_WAY: nearer, a hostile
# with a clear line is the run's fight on its way.
QUIET_UNITS = CLEAR_WAY
ROOM_UNITS = 40.0  # a known hostile this much further than the nearest unexplored room still goes first
VANISH_UNITS = 25.0
SLICE = 0.01  # seconds between looks at the left mouse button while the mode waits or fights
# Seconds after a loss of life within which the KP_6 loop's run may stand and strike (pursuit.py `arbitrate`)
HURT_SECONDS = 2.0
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
# The navigation classes with no Teleport to spend (macros/movement.py `Ways.means`): a step of the old keys toward a
# far place goes by the class's own way there (`class_step`), not by a Teleport landing made some other way.
NO_HOPS = frozenset((WARPS, WALKS))
# Times a casting delay worth it is slept out before such a step (`class_step`): the look after the sleep may read it
# a tick short of its end, and the step was then a walk of 4 units (the arena's seal moment, seed 1)
PAUSES = 3
# The run mode (macros/runmode.py): a level run's fight on its way or of the rest of the level (goals.py
# `clear_way`, `rest_of_level`) that has been gone for CLEAR_SECONDS with no strike and no progress by the way to it
# (its way left, `Travel.eta`, down by PROGRESS_SECONDS at least), or that the navigator has no way to, is passed for
# PASS_SECONDS (across lava, a monster that keeps away, a room no tour reaches): the run goes on. A room has nothing
# to strike: judged by strikes alone, one 119 units off was passed after a run of 153 units toward it in 10 s
# (22:54:12.99 on 2026-10-14, rca/2026-10-14/run-1932-findings.md §1.2.1). Two of its looks further apart than
# JUDGE_GAP with another goal's between are not counted as time gone for it: the goal was another's meanwhile.
CLEAR_SECONDS = 10.0
PASS_SECONDS = 30.0
PROGRESS_SECONDS = 0.25
PROGRESS_LOOK = 1.0  # seconds between two askings of the way left to one clearing goal (`goes_on`)
JUDGE_GAP = 3.0
# Seconds a clearing goal the run has left for another is not taken back while that other is still the run's to go
# for (`Hunter.cleared`): the passed room of 22:54:19 came back in turn with the door eight times in 9.6 s.
TAKE_BACK = 6.0
# The goals a run to its goal fights its way to (`Hunter.cleared`): a door to another level, a place, a stand.
WAYS = frozenset((ENTER, REACH, STAND))
REST_SECONDS = 1.0  # a full clear's look for the rest of the level (the tour's potential) is made this seldom
# A monster remembered alive this near is gone for before the tour's next room; one further off waits for the tour to
# be over (the player, 00:10 on 2026-10-18: "when we have lower mobs count, we starts to go from one side to another
# back and forward"). Of 179 legs to a remembered monster on 2026-10-17 evening, 126 went over 60 units (median 75,
# up to 211) where the tour's rooms were 51 off at the median: the nearest remembered one anywhere crossed the level
# and back. Those on the tour's way come into sight as it goes. About a screen's half width.
REMEMBERED_NEAR = 45.0
# A Herald's coming (rca/2026-10-17/herald-findings.md): the client holds a missile of class HERALD_OMEN
# (missiles.txt `heraldspawner`, Range 125 frames: 5.0 s) where a monster just killed died, and the Herald and its
# minions appear on that spot as it ends (6 Heralds of 6 on 2026-10-17; the one of take 20261017T201752Z-5 at
# (15546.5, 4918.5) 4.97 s after it). The player, 23:30: "monitor when herald is about to appear ... and position us
# correctly, expect tough enemy; right now we just teleporting out of heralds vicinity hunting for another enemies"
# (its 5 s went to a monster 65 units off, and the T5 pack was met at full life out of view). While one is pending
# a full clear fights only what is within OMEN_NEAR of the spot, else it stands OMEN_STAND from it (Echoing Strike's
# engage ring, its reach 22) on its own side; a live Herald is its first goal after. Missiles read every OMEN_LOOK s.
HERALD_OMEN = 737
OMEN_SECONDS = 8.0  # its 5 s and a margin for the Herald to show
OMEN_NEAR = 22.0
# 14 (the engage ring) at first: at 00:54:55 on 2026-10-18 a tier 5 Apparition Herald (Extra Fast, Cursed, Mana Burn,
# Aura Enchanted) and its 15 came up 13 units off, all 15 within 10 at once, and 2634 life went in 0.6 s, two
# rejuvenations drunk before: the stand is at the attack's reach (22) less a margin, so the pack is struck coming in
OMEN_STAND = 20.0
OMEN_SLACK = 4.0  # a stand this near OMEN_STAND from the spot already is kept: no move
OMEN_LOOK = 0.25
# Seconds of fighting a buff with a duration has to last through when the route's stage brings a boss (goals.py
# `boss_ahead`): renewed before it in the quiet (macros/buffs.py `lapsing`). The Chaos Sanctuary on 2026-10-14,
# 15:19:24.9 to 49.7: the last seal open to Diablo dead 25 s, his spawn wait in it; at 06:05 23 s; 31 s more of the
# player's hand at 15:19 (run-1214-findings.md §3.4: Consume, 300 s, ran out 300.7 s after the prebuff, in his fight).
BOSS_AHEAD = 60.0

Remembered = Callable[[int], list[tuple[int, float, float, bool]]]  # area -> (unit id, x, y, leader)


@dataclass
class Bearings:
    """What the goal of a key is named from besides the world (macros/goals.py `goal_of`), the runner's
    and handed to the hunt by it: the routes' progress, the level card's first mark and the places of
    its marks by label, the tracker's last-seen places of super uniques and bosses by level."""

    progress: Progress | None = None
    card: Callable[[], Target | None] | None = None
    marks: Callable[[str], tuple[Point, ...]] | None = None
    supers: Callable[[int], list[Point]] | None = None

    def terror(self, area: int) -> bool:
        """Whether level `area` is a terror zone now, by the routes' progress (its `wanted`: terror/tracker.py
        `terrorized`); False while that is not known."""
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
    """The mode moving on its own after a pickup request with hostiles near. It is on while it has
    steps left and its last step or request is no older than FOLLOW_SECONDS; the player's own move
    and STEP_FAILURES failed steps in a row end it. A place a walk failed for is left alone for
    SHUN_SECONDS."""

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
    """How many hostiles stand within GATHER_CLEAR of the character or of a thing a press would go to
    (pickup.py `Threat`): the sweep's measure of a stop that is safe, for the pickup key's potions and
    chests. Presence, not yet what they could do: the price of a place (Stage 4.3) is to take its place."""

    def near(here: Point, spot: Point) -> int:
        return sum(
            1
            for monster in hostiles(run.world())
            if min(math.dist((monster.x, monster.y), here), math.dist((monster.x, monster.y), spot)) <= GATHER_CLEAR
        )

    return near


def passing_key(place: Point, unit: int | None, rooms: Sequence[Room] = ()) -> object:
    """What a level run's clearing goal is passed and judged by (`Hunter.cleared`): its monster; else the room its
    place lies in (of `rooms`, the level's), else its place to the unit. A room's goal is the tile of it nearest by the
    way from where the character stands (`frontier`), which moves as the character does: keyed by its tile, a room
    passed came back under a new key 5 units on, and the run went back and forth between it and the route's door for
    9.6 s (22:54:19, 2026-10-14, rca/2026-10-14/run-1932-findings.md §1.2.1)."""
    if unit is not None:
        return unit
    room = room_at(rooms, (place[0] / TILE_UNITS, place[1] / TILE_UNITS)) if rooms else None
    if room is not None:  # a large preset's 8 by 8 chunks are one room (`Room.block`, its whole bounds)
        return ('room', *(room.block or (room.x, room.y, room.width, room.height)))
    return (round(place[0]), round(place[1]))


@dataclass
class Judging:
    """How a level run's clearing goal has gone (`Hunter.cleared`): the seconds it has been gone for with no strike
    and no progress by the way (`idle`), the least way left to it seen (`best`, seconds by the means in hand:
    `Travel.eta`), and the look that last judged it. Kept by the goal's key across other goals: the goal coming back
    after another goes on from where it was (the 10-s judge started again at every change of goal, and two goals
    taken in turn were never passed: run-1932-findings.md §1.2.1)."""

    idle: float
    best: float
    last: float
    checked: float = -math.inf  # the look that last asked the way left


def door_entry(card: Target | None) -> Point | None:
    """Where the character stands to click the card's door, world units: its remembered entry on footing (teleport.py
    `entry_stand`; macros/goals.py `way_out`: a level run's last hop lands on it); None with none."""
    entry = entry_stand(card) if card is not None else None
    return scaled(entry) if entry is not None else None


def hostiles(world: World) -> list[Monster]:
    """Live monsters the hunt may strike: not owned, not allied, not townsfolk, scenery, a siege door
    or wall, a cast Hydra or a bird in the air, placed."""
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
    ]


def strike_input(run: Run, world: World, key_names, skill: int) -> tuple[tuple[str, ...], str]:
    """(what to hold, how to say it) for `skill`, the attack's strike: the right mouse button when it
    holds the skill (as the player casts it), else its skill key, else the left button with Shift. In
    controller mode its pad record (macros/pad.py), held by `Run.pad`: nothing to name for the keys."""
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
    """Whether the character stands by a container it opened (PAIR_BY) whose shack's other is `thing` (PAIR_UNITS):
    `thing` is then clicked from PAIR_NEAR, not hopped to."""
    return any(
        other.unit_id != thing.unit_id
        and other.mode
        and math.dist((other.x, other.y), (thing.x, thing.y)) <= PAIR_UNITS
        and math.dist((other.x, other.y), here) <= PAIR_BY
        for other in things
    )


def act_window(step) -> float:
    """The seconds a priced move is given in the hands (`Hunter.priced_for`): its price, and for a Teleport the key's
    second press (teleport.py REPRESS_SECONDS). About 5% of Teleport keys since 2026-10-12 start a cast that moves
    nothing; the press again lands 0.26-0.39 s later, but the window ran out first in 115 of 126 (0.78-0.97 s after
    the key), the hop counted as failed and Teleport left for WARP_RETRY: about 1.6 s each
    (rca/2026-10-17/teleport-not-cast-findings.md). The price itself is unchanged."""
    return step.seconds + (REPRESS_SECONDS if step.skill == TELEPORT else 0.0)


def omen_stand(spot: Point, here: Point) -> Point:
    """Where a full clear waits for a Herald coming to `spot` (HERALD_OMEN): OMEN_STAND from it on the character's
    side; where it stands already when that is within OMEN_SLACK of it."""
    away = math.dist(spot, here)
    if abs(away - OMEN_STAND) <= OMEN_SLACK:
        return here
    if away < 1e-6:
        return (spot[0] + OMEN_STAND, spot[1])
    return (spot[0] + (here[0] - spot[0]) * OMEN_STAND / away, spot[1] + (here[1] - spot[1]) * OMEN_STAND / away)
